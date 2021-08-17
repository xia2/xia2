# A handler for all of the information which may be passed in on the command
# line. This singleton object should be able to handle the input, structure
# it and make it available in a useful fashion.
#
# This is a hook into a global data repository, should mostly be replaced with
# a Phil interface.


import collections
import copy
import logging
import os
import re
import sys

from dials.util import Sorry
from dxtbx.serialize import load
from xia2.Experts.FindImages import image2template_directory
from xia2.Handlers.Environment import which
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.PipelineSelection import add_preference
from xia2.Schema import imageset_cache, update_with_reference_geometry
from xia2.Schema.XProject import XProject

logger = logging.getLogger("xia2.Handlers.CommandLine")

PATTERN_VALID_CRYSTAL_PROJECT_NAME = re.compile(r"[a-zA-Z_]\w*$")


def load_experiments(filename):
    experiments = load.experiment_list(filename, check_format=False)

    imagesets = experiments.imagesets()
    params = PhilIndex.get_python_object()
    reference_geometry = params.xia2.settings.input.reference_geometry
    if reference_geometry is not None and len(reference_geometry) > 0:
        update_with_reference_geometry(imagesets, reference_geometry)
    for imageset in imagesets:
        template = imageset.get_template()
        if template not in imageset_cache:
            imageset_cache[template] = collections.OrderedDict()
        imageset_cache[template][imageset.get_scan().get_image_range()[0]] = imageset


def unroll_parameters(hdf5_master):
    """Determine auto-unroll parameters for Eiger data sets with multiple
    triggers - will mean several assumptions are made i.e. all are the
    same size and so on."""

    assert hdf5_master.endswith(".h5")

    import h5py

    try:
        with h5py.File(hdf5_master, "r") as master:
            root = master["/entry/instrument/detector"]
            ntrigger = root["detectorSpecific/ntrigger"][()]
            nimages = root["detectorSpecific/nimages"][()]
        if ntrigger > 1 and nimages > 1:
            return ntrigger, nimages
    except Exception:
        return None


def unroll_datasets(datasets):
    """Unroll datasets i.e. if input img:1:900:450 make this into 1:450;
    451:900"""

    unrolled = []

    for dataset in datasets:
        tokens = dataset.split(":")
        if len(tokens[0]) == 1:
            # because windows
            tokens = ["%s:%s" % (tokens[0], tokens[1])] + tokens[2:]
        if tokens[0].endswith(".h5") and len(tokens) != 4:
            # check if we need to auto-discover the unrolling parameters
            # for multiple trigger data sets
            unroll_params = unroll_parameters(tokens[0])
            if unroll_params:
                ntrigger, nimages = unroll_params
                if len(tokens) == 1:
                    tokens = [tokens[0], "1", ntrigger * nimages, nimages]
                elif len(tokens) == 3:
                    tokens.append(nimages)
        if len(tokens) in (1, 3):
            unrolled.append(dataset)
            continue
        if len(tokens) != 4:
            raise RuntimeError(
                "Dataset ranges must be passed as "
                "/path/to/image_0001.cbf:start:end[:chunk]"
            )
        start, end, incr = list(map(int, tokens[1:]))
        if start + incr - 1 > end:
            raise RuntimeError("chunk size greater than total")
        for s in range(start, end, incr):
            e = s + incr - 1
            if e > end:
                e = end
            unrolled.append("%s:%d:%d" % (tokens[0], s, e))

    return unrolled


def validate_project_crystal_name(parameter, value):
    if not PATTERN_VALID_CRYSTAL_PROJECT_NAME.match(value):
        raise Sorry(
            "%s name must consist only of alphanumeric characters and underscores. "
            "The first character must be a non-digit character." % parameter
        )


class _CommandLine:
    """A class to represent the command line input."""

    def __init__(self):
        """Initialise all of the information from the command line."""

        self._argv = []
        self._understood = []

        self._default_template = []
        self._default_directory = []
        self._hdf5_master_files = []
        self._default_start_end = {}

        # deprecated options prior to removal
        self._xinfo = None

    def get_argv(self):
        return self._argv

    def print_command_line(self):
        logger.info("Command line: %s", self.get_command_line())

    def get_command_line(self):
        import libtbx.load_env

        cl = libtbx.env.dispatcher_name
        if cl:
            if "xia2" not in cl or "python" in cl:
                cl = "xia2"
        else:
            cl = "xia2"

        for arg in sys.argv[1:]:
            if " " in arg:
                arg = '"%s"' % arg
            cl += " %s" % arg

        return cl

    def setup(self):
        """Set everything up..."""

        # check arguments are all ascii

        logger.debug("Start parsing command line: " + str(sys.argv))

        for token in sys.argv:
            try:
                token.encode("ascii")
            except UnicodeDecodeError:
                raise RuntimeError("non-ascii characters in input")

        self._argv = copy.deepcopy(sys.argv)

        # first of all try to interpret arguments as phil parameters/files

        from xia2.Handlers.Phil import master_phil
        from libtbx.phil import command_line

        cmd_line = command_line.argument_interpreter(master_phil=master_phil)
        working_phil, self._argv = cmd_line.process_and_fetch(
            args=self._argv, custom_processor="collect_remaining"
        )

        PhilIndex.merge_phil(working_phil)
        try:
            params = PhilIndex.get_python_object()
        except RuntimeError as e:
            raise Sorry(e)

        # sanity check / interpret Auto in input
        from libtbx import Auto

        if params.xia2.settings.input.atom is None:
            if params.xia2.settings.input.anomalous is Auto:
                PhilIndex.update("xia2.settings.input.anomalous=false")
        else:
            if params.xia2.settings.input.anomalous is False:
                raise Sorry("Setting anomalous=false and atom type inconsistent")
            params.xia2.settings.input.anomalous = True
            PhilIndex.update("xia2.settings.input.anomalous=true")

        if params.xia2.settings.resolution.keep_all_reflections is Auto:
            if (
                params.xia2.settings.small_molecule is True
                and params.xia2.settings.resolution.d_min is None
                and params.xia2.settings.resolution.d_max is None
            ):
                PhilIndex.update("xia2.settings.resolution.keep_all_reflections=true")
            else:
                PhilIndex.update("xia2.settings.resolution.keep_all_reflections=false")

        if params.xia2.settings.small_molecule is True:
            logger.debug("Small molecule selected")
            if params.xia2.settings.symmetry.chirality is None:
                PhilIndex.update("xia2.settings.symmetry.chirality=nonchiral")
            params = PhilIndex.get_python_object()

        # pipeline options
        self._read_pipeline()

        for (parameter, value) in (
            ("project", params.xia2.settings.project),
            ("crystal", params.xia2.settings.crystal),
        ):
            validate_project_crystal_name(parameter, value)

        logger.debug("Project: %s" % params.xia2.settings.project)
        logger.debug("Crystal: %s" % params.xia2.settings.crystal)

        # FIXME add some consistency checks in here e.g. that there are
        # images assigned, there is a lattice assigned if cell constants
        # are given and so on

        params = PhilIndex.get_python_object()
        mp_params = params.xia2.settings.multiprocessing
        from xia2.Handlers.Environment import get_number_cpus

        if mp_params.mode == "parallel":
            if mp_params.type == "qsub":
                if which("qsub") is None:
                    raise Sorry("qsub not available")
            if mp_params.njob is Auto:
                mp_params.njob = get_number_cpus()
                if mp_params.nproc is Auto:
                    mp_params.nproc = 1
            elif mp_params.nproc is Auto:
                mp_params.nproc = get_number_cpus()
        elif mp_params.mode == "serial":
            if mp_params.type == "qsub":
                if which("qsub") is None:
                    raise Sorry("qsub not available")
            if mp_params.njob is Auto:
                mp_params.njob = 1
            if mp_params.nproc is Auto:
                mp_params.nproc = get_number_cpus()

        PhilIndex.update("xia2.settings.multiprocessing.njob=%d" % mp_params.njob)
        PhilIndex.update("xia2.settings.multiprocessing.nproc=%d" % mp_params.nproc)
        params = PhilIndex.get_python_object()
        mp_params = params.xia2.settings.multiprocessing

        if mp_params.nproc > 1 and os.name == "nt":
            raise Sorry("nproc > 1 is not supported on Windows.")  # #191

        if params.xia2.settings.indexer is not None:
            add_preference("indexer", params.xia2.settings.indexer)
        if params.xia2.settings.refiner is not None:
            add_preference("refiner", params.xia2.settings.refiner)
        if params.xia2.settings.integrater is not None:
            add_preference("integrater", params.xia2.settings.integrater)
        if params.xia2.settings.scaler is not None:
            add_preference("scaler", params.xia2.settings.scaler)

        # If no multi-sweep refinement options have been set, adopt the default:
        #     True for small-molecule mode, False otherwise.
        if params.xia2.settings.multi_sweep_refinement is Auto:
            if (
                params.xia2.settings.small_molecule is True
                and params.xia2.settings.indexer == "dials"
            ):
                PhilIndex.update("xia2.settings.multi_sweep_refinement=True")
            else:
                PhilIndex.update("xia2.settings.multi_sweep_refinement=False")
            params = PhilIndex.get_python_object()

        # Multi-sweep refinement requires multi-sweep indexing.
        if params.xia2.settings.multi_sweep_refinement:
            # Check that the user hasn't specified multi_sweep_indexing False:
            assert params.xia2.settings.multi_sweep_indexing, (
                "It seems you have specified that xia2 should use multi-sweep "
                "refinement without multi-sweep indexing.\n"
                "This is not currently possible."
            )
            PhilIndex.update("xia2.settings.multi_sweep_indexing=True")
            params = PhilIndex.get_python_object()

        # If no multi-sweep indexing settings have yet been set (either because
        # small_molecule is False or because it is True but the user has specified that
        # multi_sweep_refinement is False), then adopt the default settings — True
        # for small-molecule mode, False otherwise.
        if params.xia2.settings.multi_sweep_indexing is Auto:
            if (
                params.xia2.settings.small_molecule is True
                and params.xia2.settings.indexer == "dials"
            ):
                PhilIndex.update("xia2.settings.multi_sweep_indexing=True")
            else:
                PhilIndex.update("xia2.settings.multi_sweep_indexing=False")
            params = PhilIndex.get_python_object()

        # Multi-sweep indexing is incompatible with parallel processing.
        assert not (
            params.xia2.settings.multi_sweep_indexing is True
            and params.xia2.settings.multiprocessing.mode == "parallel"
        ), (
            "Multi sweep indexing disabled:\n"
            "MSI is not available for parallel processing."
        )

        input_json = params.xia2.settings.input.json
        if input_json is not None and len(input_json):
            for json_file in input_json:
                assert os.path.isfile(json_file)
                load_experiments(json_file)

        reference_geometry = params.xia2.settings.input.reference_geometry
        if reference_geometry is not None and len(reference_geometry) > 0:
            reference_geometries = "\n".join(
                [
                    "xia2.settings.input.reference_geometry=%s" % os.path.abspath(g)
                    for g in params.xia2.settings.input.reference_geometry
                ]
            )
            logger.debug(reference_geometries)
            PhilIndex.update(reference_geometries)
            logger.debug("xia2.settings.trust_beam_centre=true")
            PhilIndex.update("xia2.settings.trust_beam_centre=true")
            params = PhilIndex.get_python_object()

        params = PhilIndex.get_python_object()
        if params.xia2.settings.input.xinfo is not None:
            xinfo_file = os.path.abspath(params.xia2.settings.input.xinfo)
            PhilIndex.update("xia2.settings.input.xinfo=%s" % xinfo_file)
            params = PhilIndex.get_python_object()
            self.set_xinfo(xinfo_file)

            # issue #55 if not set ATOM in xinfo but anomalous=true or atom= set
            # on commandline, set here, should be idempotent

            if params.xia2.settings.input.anomalous is True:
                crystals = self._xinfo.get_crystals()
                for xname in crystals:
                    xtal = crystals[xname]
                    logger.debug("Setting anomalous for crystal %s" % xname)
                    xtal.set_anomalous(True)
        else:
            xinfo_file = "%s/automatic.xinfo" % os.path.abspath(os.curdir)
            PhilIndex.update("xia2.settings.input.xinfo=%s" % xinfo_file)
            params = PhilIndex.get_python_object()

        if params.dials.find_spots.phil_file is not None:
            PhilIndex.update(
                "dials.find_spots.phil_file=%s"
                % os.path.abspath(params.dials.find_spots.phil_file)
            )
        if params.dials.index.phil_file is not None:
            PhilIndex.update(
                "dials.index.phil_file=%s"
                % os.path.abspath(params.dials.index.phil_file)
            )
        if params.dials.refine.phil_file is not None:
            PhilIndex.update(
                "dials.refine.phil_file=%s"
                % os.path.abspath(params.dials.refine.phil_file)
            )
        if params.dials.integrate.phil_file is not None:
            PhilIndex.update(
                "dials.integrate.phil_file=%s"
                % os.path.abspath(params.dials.integrate.phil_file)
            )
        if params.xds.index.xparm is not None:
            Flags.set_xparm(params.xds.index.xparm)
        if params.xds.index.xparm_ub is not None:
            Flags.set_xparm_ub(params.xds.index.xparm_ub)

        if params.xia2.settings.scale.freer_file is not None:
            freer_file = os.path.abspath(params.xia2.settings.scale.freer_file)
            if not os.path.exists(freer_file):
                raise RuntimeError("%s does not exist" % freer_file)
            from xia2.Modules.FindFreeFlag import FindFreeFlag

            column = FindFreeFlag(freer_file)
            logger.debug(f"FreeR_flag column in {freer_file} found: {column}")
            PhilIndex.update("xia2.settings.scale.freer_file=%s" % freer_file)

        if params.xia2.settings.scale.reference_reflection_file is not None:
            reference_reflection_file = os.path.abspath(
                params.xia2.settings.scale.reference_reflection_file
            )
            if not os.path.exists(reference_reflection_file):
                raise RuntimeError("%s does not exist" % reference_reflection_file)
            PhilIndex.update(
                "xia2.settings.scale.reference_reflection_file=%s"
                % reference_reflection_file
            )

        params = PhilIndex.get_python_object()

        datasets = unroll_datasets(PhilIndex.params.xia2.settings.input.image)

        for dataset in datasets:

            start_end = None

            # here we only care about ':' which are later than C:\
            if ":" in dataset[3:]:
                tokens = dataset.split(":")
                # cope with windows drives i.e. C:\data\blah\thing_0001.cbf:1:100
                if len(tokens[0]) == 1:
                    tokens = ["%s:%s" % (tokens[0], tokens[1])] + tokens[2:]
                if len(tokens) != 3:
                    raise RuntimeError("/path/to/image_0001.cbf:start:end")

                dataset = tokens[0]
                start_end = int(tokens[1]), int(tokens[2])

            from xia2.Applications.xia2setup import is_hdf5_name

            if os.path.exists(os.path.abspath(dataset)):
                dataset = os.path.abspath(dataset)
            else:
                directories = [os.getcwd()] + self._argv[1:]
                found = False
                for d in directories:
                    if os.path.exists(os.path.join(d, dataset)):
                        dataset = os.path.join(d, dataset)
                        found = True
                        break
                if not found:
                    raise Sorry(
                        "Could not find %s in %s" % (dataset, " ".join(directories))
                    )

            if is_hdf5_name(dataset):
                self._hdf5_master_files.append(dataset)
                if start_end:
                    logger.debug("Image range: %d %d" % start_end)
                    if dataset not in self._default_start_end:
                        self._default_start_end[dataset] = []
                    self._default_start_end[dataset].append(start_end)
                else:
                    logger.debug("No image range specified")

            else:
                template, directory = image2template_directory(os.path.abspath(dataset))

                self._default_template.append(os.path.join(directory, template))
                self._default_directory.append(directory)

                logger.debug("Interpreted from image %s:" % dataset)
                logger.debug("Template %s" % template)
                logger.debug("Directory %s" % directory)

                if start_end:
                    logger.debug("Image range: %d %d" % start_end)
                    key = os.path.join(directory, template)
                    if key not in self._default_start_end:
                        self._default_start_end[key] = []
                    self._default_start_end[key].append(start_end)
                else:
                    logger.debug("No image range specified")

        # finally, check that all arguments were read and raise an exception
        # if any of them were nonsense.

        with open("xia2-working.phil", "w") as f:
            f.write(PhilIndex.working_phil.as_str())
            f.write(
                os.linesep
            )  # temporarily required for https://github.com/dials/dials/issues/522
        with open("xia2-diff.phil", "w") as f:
            f.write(PhilIndex.get_diff().as_str())
            f.write(
                os.linesep
            )  # temporarily required for https://github.com/dials/dials/issues/522

        logger.debug("\nDifference PHIL:")
        logger.debug(PhilIndex.get_diff().as_str())

        logger.debug("Working PHIL:")
        logger.debug(PhilIndex.working_phil.as_str())

        nonsense = "Unknown command-line options:"
        was_nonsense = False

        for j, argv in enumerate(self._argv):
            if j == 0:
                continue
            if argv[0] != "-" and "=" not in argv:
                continue
            if j not in self._understood:
                nonsense += " %s" % argv
                was_nonsense = True

        if was_nonsense:
            raise RuntimeError(nonsense)

    # command line parsers, getters and help functions.

    def set_xinfo(self, xinfo):
        logger.debug(60 * "-")
        logger.debug("XINFO file: %s" % xinfo)
        with open(xinfo) as fh:
            logger.debug(fh.read().strip())
        logger.debug(60 * "-")
        self._xinfo = XProject(xinfo)

    def get_xinfo(self):
        """Return the XProject."""
        return self._xinfo

    def get_template(self):
        return self._default_template

    def get_start_ends(self, full_template):
        return self._default_start_end.get(full_template, [])

    def get_directory(self):
        return self._default_directory

    def get_hdf5_master_files(self):
        return self._hdf5_master_files

    @staticmethod
    def _read_pipeline():
        settings = PhilIndex.get_python_object().xia2.settings
        indexer, refiner, integrater, scaler = None, None, None, None
        if settings.pipeline == "3d":
            logger.debug("3DR pipeline selected")
            indexer, refiner, integrater, scaler = "xds", "xds", "xdsr", "xdsa"
        elif settings.pipeline == "3di":
            logger.debug("3DR pipeline; XDS indexing selected")
            indexer, refiner, integrater, scaler = "xds", "xds", "xdsr", "xdsa"
        elif settings.pipeline == "3dii":
            logger.debug("3D II R pipeline (XDS IDXREF all images) selected")
            indexer, refiner, integrater, scaler = "xdsii", "xds", "xdsr", "xdsa"
        elif settings.pipeline == "3dd":
            logger.debug("3DD pipeline (DIALS indexing) selected")
            indexer, refiner, integrater, scaler = "dials", "xds", "xdsr", "xdsa"
        elif settings.pipeline == "dials":
            logger.debug("DIALS pipeline selected")
            indexer, refiner, integrater, scaler = "dials", "dials", "dials", "dials"
        elif settings.pipeline == "dials-aimless":
            logger.debug("DIALS-LEGACY pipeline selected (DIALS, scaling with AIMLESS)")
            indexer, refiner, integrater, scaler = "dials", "dials", "dials", "ccp4a"

        if indexer is not None and settings.indexer is None:
            PhilIndex.update("xia2.settings.indexer=%s" % indexer)
        if refiner is not None and settings.refiner is None:
            PhilIndex.update("xia2.settings.refiner=%s" % refiner)
        if integrater is not None and settings.integrater is None:
            PhilIndex.update("xia2.settings.integrater=%s" % integrater)
        if scaler is not None and settings.scaler is None:
            PhilIndex.update("xia2.settings.scaler=%s" % scaler)

        if settings.scaler is not None:
            if settings.pipeline.startswith("2d"):
                allowed_scalers = ("ccp4a",)
            elif settings.pipeline.startswith("3d"):
                allowed_scalers = ("xdsa", "ccp4a")
            elif settings.pipeline.startswith("dials"):
                allowed_scalers = ("dials", "ccp4a")
            if settings.scaler not in allowed_scalers:
                raise ValueError(
                    "scaler=%s not compatible with pipeline=%s "
                    "(compatible scalers are %s)"
                    % (settings.scaler, settings.pipeline, " or ".join(allowed_scalers))
                )


CommandLine = _CommandLine()
CommandLine.setup()

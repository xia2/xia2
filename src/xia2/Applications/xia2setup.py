# an application to generate the .xinfo file for data
# reduction from a directory full of images, optionally with scan and
# sequence files which will be used to add matadata.


from __future__ import annotations

import collections
import logging
import os
import sys
import traceback

import h5py

from libtbx import easy_mp

from xia2.Applications.xia2setup_helpers import get_sweep
from xia2.Experts.FindImages import image2template_directory
from xia2.Handlers.CommandLine import CommandLine
from xia2.Handlers.Phil import PhilIndex
from xia2.Schema import imageset_cache
from xia2.Wrappers.XDS.XDSFiles import XDSFiles

logger = logging.getLogger("xia2.Applications.xia2setup")

image_extensions = [
    "img",
    "mccd",
    "mar2300",
    "mar1200",
    "mar1600",
    "mar3450",
    "osc",
    "cbf",
    "mar2000",
    "sfrm",
    "",
]

compression = ["", ".bz2", ".gz"]

known_image_extensions = []

for c in compression:
    for ie in image_extensions:
        ext = f"{ie}{c}"
        if ext:
            known_image_extensions.append(ext)

xds_file_names = [
    "ABS",
    "ABSORP",
    "BKGINIT",
    "BKGPIX",
    "BLANK",
    "DECAY",
    "X-CORRECTIONS",
    "Y-CORRECTIONS",
    "MODPIX",
    "FRAME",
    "GX-CORRECTIONS",
    "GY-CORRECTIONS",
    "DX-CORRECTIONS",
    "DY-CORRECTIONS",
    "GAIN",
]

known_sequence_extensions = ["seq"]

known_hdf5_extensions = [".h5", ".nxs"]

latest_sequence = None

target_template = None


def is_sequence_name(file):
    if os.path.isfile(file):
        if file.split(".")[-1] in known_sequence_extensions:
            return True

    return False


def is_image_name(filename):
    if os.path.isfile(filename):

        if os.path.split(filename)[-1] in XDSFiles:
            return False

        for xds_file in "ABSORP", "DECAY", "MODPIX":
            if os.path.join("scale", xds_file) in filename:
                return False

        for exten in known_image_extensions:
            if filename.endswith(exten):
                return True

        end = filename.split(".")[-1]
        try:
            if ".log." not in filename and len(end) > 1:
                return True
        except Exception:
            pass

        if is_hdf5_name(filename):
            return True

    return False


def is_hdf5_name(filename):
    if os.path.isfile(filename):
        if os.path.splitext(filename)[-1] in known_hdf5_extensions:
            return True

    return False


def is_xds_file(f):
    filename = os.path.split(f)[1]

    xds_files = [
        "ABS",
        "ABSORP",
        "BKGINIT",
        "BKGPIX",
        "BLANK",
        "DECAY",
        "DX-CORRECTIONS",
        "DY-CORRECTIONS",
        "FRAME",
        "GAIN",
        "GX-CORRECTIONS",
        "GY-CORRECTIONS",
        "MODPIX",
        "X-CORRECTIONS",
        "Y-CORRECTIONS",
    ]

    return filename.split(".")[0].split("_") in xds_files


def get_template(f):

    global target_template

    if not is_image_name(f):
        return

    if is_xds_file(f):
        return

    # in here, check the permissions on the file...

    template = None
    directory = None

    if not os.access(f, os.R_OK):
        logger.debug("No read permission for %s" % f)

    try:
        template, directory = image2template_directory(f)
        template = os.path.join(directory, template)

        if target_template:
            if template not in target_template:
                return

    except Exception as e:
        logger.debug(f"Exception A: {e} ({f})")
        logger.debug(traceback.format_exc())

    if template is None or directory is None:
        raise RuntimeError("template not recognised for %s" % f)

    return template


def parse_sequence(sequence_file):
    sequence = ""

    for record in open(sequence_file).readlines():
        if record[0].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ ":
            sequence += record.strip().upper()

    global latest_sequence
    latest_sequence = sequence


def visit(directory, files):
    files.sort()

    templates = set()

    for f in files:
        full_path = os.path.join(directory, f)

        if is_hdf5_name(full_path):
            from dxtbx.format import Registry

            format_class = Registry.get_format_class_for_file(full_path)
            if format_class is None:
                logger.debug(
                    "Ignoring %s (Registry can not find format class)" % full_path
                )
                continue
            elif format_class.is_abstract():
                continue
            templates.add(full_path)

        elif is_image_name(full_path):
            try:
                template = get_template(full_path)
            except Exception as e:
                logger.debug("Exception B: %s" % str(e))
                logger.debug(traceback.format_exc())
                continue
            if template is not None:
                templates.add(template)

        elif is_sequence_name(full_path):
            parse_sequence(full_path)

    return templates


def _linked_hdf5_data_files(h5_file):
    data_path = "/entry/data"
    with h5py.File(h5_file) as f:
        filenames = [
            f[data_path][k].file.filename for k in f[data_path] if k.startswith("data_")
        ]
    return frozenset(filenames)


def _filter_aliased_hdf5_sweeps(sweeps: list[str]) -> set[str]:
    """
    Deduplicate HDF5 (or NeXus) data files that share the same underlying data.

    For sweeps whose file names (or file name templates for one-file-per-image data)
    suggest they are not HDF5 data, pass the names through unchanged.  For HDF5 data
    in the externally-linked multiple-file layout described below, deduplicate any
    sweep names corresponding to the same underlying data.  For other HDF5 data,
    pass the sweep name through unchanged.

    Sometimes, diffraction data in HDF5 format may be stored in several files.  Raw
    image data may be in one or more files, some metadata perhaps stored in another
    file.  In such a layout, a top-level ('master') file serves to define the data
    structure, and may follow a standard for structured (meta)data, such as the NXmx
    application definition of the NeXus data standard.  In such cases, the top-level
    file is connected to the subordinate files by HDF5 external links.

    For historical reasons, such a data layout may use two or more top-level files,
    which are duplicates of each other.  For example, this is common at Diamond Light
    Source for data from Dectris Eiger detectors, because XDS specifically requires
    the top-level file to have a name ending in '_master.h5', whereas Diamond's
    internal standard is for top-level files following the NeXus standard to have a
    '.nxs' file extension.

    To avoid these duplicate top-level HDF5 files being misidentified as separate
    sweeps, this function serves to associate such top-level files with the
    underlying image data sets to which they are linked, and keep only one top-level
    file for each unique set of image data files.  This identification depends on the
    image data sets in the top-level file (which may be external links) having names
    like '/entry/data/data_<stuff>', where <stuff> is usually a string of numerals
    (see '_linked_hdf5_data_files').

    There are two known weakness of this method:
      - If one genuinely wishes to import multiple top-level files pointing to the
        same underlying image data (but perhaps with different metadata), they will
        be erroneously deduplicated.
      - The use of image data sets named '/entry/data/data_<stuff>' is not a
        requirement of a valid top-level HDF5 data file.  The top-level file will
        always have an image data set named '/entry/data/data', and may not bother
        with any redundant 'data_<stuff>' data sets/links.  Even if the image data
        are in separate files to the top-level file, '/entry/data/data' may link to
        them using the separate HDF5 virtual data set formalism, which obviates the
        need for external links called 'data_<stuff>'.  In such cases, any duplicates
        will be missed.

    Args:
        sweeps:  The sweep data file names, or file name templates.

    Returns:
        The unique sweep names, with duplicate top-level HDF5 files removed.
    """
    deduplicated = set()
    hdf5_sweeps: dict[frozenset[str], str] = {}

    for s in sweeps:
        if not is_hdf5_name(s) or not (filenames := _linked_hdf5_data_files(s)):
            deduplicated.add(s)
        elif filenames in hdf5_sweeps:
            # Bias in favour of using _master.h5 in place of .nxs, because of XDS
            if hdf5_sweeps[filenames].endswith(".nxs") and s.endswith("_master.h5"):
                hdf5_sweeps[filenames] = s
        else:
            hdf5_sweeps[filenames] = s

    return deduplicated.union(hdf5_sweeps[k] for k in hdf5_sweeps)


def _write_sweeps(sweeps, out):
    global latest_sequence
    _known_sweeps = sweeps

    sweeplist = sorted(_filter_aliased_hdf5_sweeps(_known_sweeps))
    assert sweeplist, "no sweeps found"

    # sort sweeplist based on epoch of first image of each sweep
    epochs = [
        _known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
        for sweep in sweeplist
    ]

    if len(epochs) != len(set(epochs)):
        logger.debug("Duplicate epochs found. Trying to correct epoch information.")
        cumulativedelta = 0.0
        for sweep in sweeplist:
            _known_sweeps[sweep][0].get_imageset().get_scan().set_epochs(
                _known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()
                + cumulativedelta
            )
            # could change the image epoch information individually, but only
            # the information from the first image is used at this time.
            cumulativedelta += sum(
                _known_sweeps[sweep][0].get_imageset().get_scan().get_exposure_times()
            )
        epochs = [
            _known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
            for sweep in sweeplist
        ]

        if len(epochs) != len(set(epochs)):
            logger.debug("Duplicate epoch information remains.")
        # This should only happen with incorrect exposure time information.

    sweeplist = [s for _, s in sorted(zip(epochs, sweeplist))]

    # analysis pass

    wavelengths = []

    settings = PhilIndex.get_python_object().xia2.settings
    wavelength_tolerance = settings.wavelength_tolerance
    min_images = settings.input.min_images
    min_oscillation_range = settings.input.min_oscillation_range

    for sweep in sweeplist:
        sweeps = _known_sweeps[sweep]

        # sort on exposure epoch followed by first image number
        sweeps = sorted(
            sweeps,
            key=lambda s: (
                s.get_imageset().get_scan().get_epochs()[0],
                s.get_images()[0],
            ),
        )
        for s in sweeps:
            if len(s.get_images()) < min_images:
                logger.debug("Rejecting sweep %s:" % s.get_template())
                logger.debug(
                    "  Not enough images (found %i, require at least %i)"
                    % (len(s.get_images()), min_images)
                )
                continue

            oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
            width = oscillation_range[1] - oscillation_range[0]
            if min_oscillation_range is not None and width < min_oscillation_range:
                logger.debug("Rejecting sweep %s:" % s.get_template())
                logger.debug(
                    "  Too narrow oscillation range (found %i, require at least %i)"
                    % (width, min_oscillation_range)
                )
                continue

            wavelength = s.get_wavelength()

            if wavelength not in wavelengths:
                have_wavelength = False
                for w in wavelengths:
                    if abs(w - wavelength) < wavelength_tolerance:
                        have_wavelength = True
                        s.set_wavelength(w)
                if not have_wavelength:
                    wavelengths.append(wavelength)

    assert wavelengths, "No sweeps found matching criteria"

    wavelength_map = {}

    project = settings.project
    crystal = settings.crystal

    out.write("BEGIN PROJECT %s\n" % project)
    out.write("BEGIN CRYSTAL %s\n" % crystal)

    out.write("\n")

    # check to see if a user spacegroup has been assigned - if it has,
    # copy it in...

    if settings.space_group is not None:
        out.write("USER_SPACEGROUP %s\n" % settings.space_group.type().lookup_symbol())
        out.write("\n")

    if settings.unit_cell is not None:
        out.write(
            "USER_CELL %.2f %.2f %.2f %.2f %.2f %.2f\n"
            % settings.unit_cell.parameters()
        )
        out.write("\n")
    if settings.chemical_formula:
        out.write("USER_CHEMICAL_FORMULA %s\n" % settings.chemical_formula)

    freer_file = PhilIndex.params.xia2.settings.scale.freer_file
    if freer_file is not None:
        out.write("FREER_FILE %s\n" % PhilIndex.params.xia2.settings.scale.freer_file)
        out.write("\n")

    if latest_sequence:
        out.write("BEGIN AA_SEQUENCE\n")
        out.write("\n")
        for sequence_chunk in [
            latest_sequence[i : i + 60] for i in range(0, len(latest_sequence), 60)
        ]:
            out.write("%s\n" % sequence_chunk)
        out.write("\n")
        out.write("END AA_SEQUENCE\n")
        out.write("\n")

    if settings.input.atom:
        out.write("BEGIN HA_INFO\n")
        out.write("ATOM %s\n" % settings.input.atom.lower())
        out.write("END HA_INFO\n")
        out.write("\n")
    elif settings.input.anomalous:
        out.write("BEGIN HA_INFO\n")
        out.write("ATOM X\n")
        out.write("END HA_INFO\n")
        out.write("\n")

    for j, wavelength in enumerate(wavelengths):
        anomalous = settings.input.anomalous
        if settings.input.atom is not None:
            anomalous = True
        if len(wavelengths) == 1 and anomalous:
            name = "SAD"
        elif len(wavelengths) == 1:
            name = "NATIVE"
        else:
            name = "WAVE%d" % (j + 1)

        wavelength_map[wavelength] = name

        out.write("BEGIN WAVELENGTH %s\n" % name)

        dmin = PhilIndex.params.xia2.settings.resolution.d_min
        dmax = PhilIndex.params.xia2.settings.resolution.d_max

        if dmin and dmax:
            out.write(f"RESOLUTION {dmin:f} {dmax:f}\n")
        elif dmin:
            out.write("RESOLUTION %f\n" % dmin)

        out.write("WAVELENGTH %f\n" % wavelengths[j])

        out.write("END WAVELENGTH %s\n" % name)
        out.write("\n")

    j = 0
    for sweep in sweeplist:
        sweeps = _known_sweeps[sweep]

        # sort on exposure epoch followed by first image number
        sweeps = sorted(
            sweeps,
            key=lambda s: (
                s.get_imageset().get_scan().get_epochs()[0],
                s.get_images()[0],
            ),
        )

        for s in sweeps:
            # require at least n images to represent a sweep...
            if len(s.get_images()) < min_images:
                logger.debug("Rejecting sweep %s:" % s.get_template())
                logger.debug(
                    "  Not enough images (found %i, require at least %i)"
                    % (len(s.get_images()), min_images)
                )
                continue

            oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
            width = oscillation_range[1] - oscillation_range[0]
            if min_oscillation_range is not None and width < min_oscillation_range:
                logger.debug("Rejecting sweep %s:" % s.get_template())
                logger.debug(
                    "  Too narrow oscillation range (found %i, require at least %i)"
                    % (width, min_oscillation_range)
                )
                continue

            key = os.path.join(s.get_directory(), s.get_template())
            if CommandLine.get_start_ends(key):
                start_ends = CommandLine.get_start_ends(key)
                start_good = (
                    min(s.get_images()) <= start_ends[0][0] <= max(s.get_images())
                )
                end_good = (
                    min(s.get_images()) <= start_ends[0][1] <= max(s.get_images())
                )
                if not all((start_good, end_good)):
                    logger.debug("Rejecting sweep %s:" % s.get_template())
                    if not start_good:
                        logger.debug(
                            "  Your specified start-point image lies outside the bounds of this sweep."
                        )
                    if not end_good:
                        logger.debug(
                            "  Your specified end-point image lies outside the bounds of this sweep."
                        )
                    logger.debug(
                        "  Your specified start and end points were %d & %d,"
                        % start_ends[0]
                    )
                    logger.debug(
                        "  this sweep consists of images from %d to %d."
                        % (min(s.get_images()), max(s.get_images()))
                    )
                    logger.debug(
                        """  If there are missing images in your sweep, but you have selected valid
  start and end points within a contiguous range of images, you will see this
  message, even though all is well with your selection, because xia2 treats
  each contiguous image range as a separate sweep."""
                    )
                    continue
            else:
                start_ends = [(min(s.get_images()), max(s.get_images()))]

            for start_end in start_ends:
                j += 1
                name = "SWEEP%d" % j

                out.write("BEGIN SWEEP %s\n" % name)

                if PhilIndex.params.xia2.settings.input.reverse_phi:
                    out.write("REVERSEPHI\n")

                out.write("WAVELENGTH %s\n" % wavelength_map[s.get_wavelength()])

                out.write("DIRECTORY %s\n" % s.get_directory())
                imgset = s.get_imageset()
                out.write("IMAGE %s\n" % os.path.split(imgset.get_path(0))[-1])
                out.write("START_END %d %d\n" % start_end)

                # really don't need to store the epoch in the xinfo file
                # out.write('EPOCH %d\n' % int(s.get_collect()[0]))
                if not settings.trust_beam_centre:
                    PhilIndex.params.xia2.settings.interactive = False
                    PhilIndex.get_python_object()

                if settings.detector_distance is not None:
                    out.write("DISTANCE %.2f\n" % settings.detector_distance)

                out.write("END SWEEP %s\n" % name)

                out.write("\n")

    out.write("END CRYSTAL %s\n" % crystal)
    out.write("END PROJECT %s\n" % project)


def _get_sweeps(templates):
    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    nproc = mp_params.nproc

    if params.xia2.settings.read_all_image_headers and nproc > 1:
        method = "multiprocessing"

        # If xia2 was a proper cctbx module, then we wouldn't have to do this
        # FIXME xia2 is now a proper cctbx module ;o)

        python_path = 'PYTHONPATH="%s"' % ":".join(sys.path)
        qsub_command = "qsub -v %s -V" % python_path

        args = [(template,) for template in templates]
        results_list = easy_mp.parallel_map(
            get_sweep,
            args,
            processes=nproc,
            method=method,
            qsub_command=qsub_command,
            asynchronous=True,
            preserve_order=True,
            preserve_exception_message=True,
        )

    else:
        results_list = [get_sweep((template,)) for template in templates]

    known_sweeps = {}
    for template, sweeplist in zip(templates, results_list):
        if sweeplist is not None:
            known_sweeps[template] = sweeplist
            for sweep in sweeplist:
                imageset = sweep.get_imageset()
                if template not in imageset_cache:
                    imageset_cache[template] = collections.OrderedDict()
                imageset_cache[template][
                    imageset.get_scan().get_image_range()[0]
                ] = imageset
    return known_sweeps


def _rummage(directories):
    """Walk through the directories looking for sweeps."""
    templates = set()
    visited = set()
    for path in directories:
        for root, dirs, files in os.walk(path, followlinks=True):
            realpath = os.path.realpath(root)
            if realpath in visited:
                # safety-check to avoid recursively symbolic links
                continue
            visited.add(realpath)
            templates.update(visit(root, files))

    return _get_sweeps(templates)


def write_xinfo(filename, directories, template=None, hdf5_master_files=None):
    global target_template

    target_template = template

    settings = PhilIndex.get_python_object().xia2.settings
    crystal = settings.crystal

    if not os.path.isabs(filename):
        filename = os.path.abspath(filename)

    directory = os.path.join(os.getcwd(), crystal, "setup")

    try:
        os.makedirs(directory)
    except OSError as e:
        if "File exists" not in str(e):
            raise

    # if we have given a template and directory on the command line, just
    # look there (i.e. not in the subdirectories)

    if CommandLine.get_template() and CommandLine.get_directory():
        # xia2 image=$(dials.data get -q x4wide)/X4_wide_M1S4_2_0001.cbf
        templates = set()
        for directory in CommandLine.get_directory():
            templates.update(visit(directory, os.listdir(directory)))
        sweeps = _get_sweeps(templates)
    elif hdf5_master_files is not None:
        # xia2 image=$(dials.data get -q vmxi_thaumatin)/image_15799_master.h5
        sweeps = _get_sweeps(hdf5_master_files)
    else:
        # xia2 $(dials.data get -q x4wide)
        sweeps = _rummage(directories)

    with open(filename, "w") as fout:
        _write_sweeps(sweeps, fout)

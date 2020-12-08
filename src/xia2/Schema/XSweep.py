# A versioning object representation of the sweep. This will include
# methods for handling the required actions which may be performed
# on a sweep, and will also include integration with the rest of the
# .xinfo hierarchy.
#

# The following properties defined elsewhere impact in the definition
# of the sweep:
#
# lattice - contained in XCrystal, to levels above XSweep.
#
# FIXME this needs to be defined!
#
# Headnote 001: LatticeInfo & Stuff.
#
# Ok, so this is complicated. The crystal lattice will apply to all sweeps
# measured from that crystal (*1) so that they should share the same
# orientation matrix. This means that this could best contain a pointer
# to an Indexer implementation. This can then decide what to do - for
# instance, we want to make sure that the indexing is kept common. That
# would mean that Mosflm would do a better job for indexing second and
# subsequent sets than labelit, perhaps, since the matrix can be passed
# as input - though this will need to be communicated to the factory.
#
# Index 1st sweep - store indexer pointer, pass info also to crystal. Next
# sweep will update this information at the top level, with the original
# Indexer still "watching". Next get() may trigger a recalculation.
# By the time the second sweep is analysed, the first should be pretty
# solidly sorted with the correct pointgroup &c.
#
# The upshot of all of this is that this will maintain a link to the
# indexer which was used, which need to keep an eye on the top level
# lattice, which in turn will be updated as a weighted average of
# Indexer results. Finally, the top level will maintain a more high-tech
# "Lattice handler" object, which can deal with lattice -- and lattice ++.
#
# (*1) This assumes, of course, that the kappa information or whatever
#      is properly handled.
#
# Bugger - slight complication! Want to make sure that multiple sweeps
# in the same wavelength have "identical" unit cells (since the error
# on the wavelength should be small) which means that the XWavelength
# level also needs to be able to handle this kind of information. Note
# well - this is an old thought, since the overall crystal unit cell
# is a kind of average from the wavelengths, which is in turn a kind
# of average from all of the sweeps. Don't miss out the wavelength
# level.
#
# This means that the lattice information will have to cascade up and
# down the tree, to make sure that everything is kept up-to-date. This
# should be no more difficult, just a little more complicated.


import copy
import inspect
import logging
import math
import os
import time

import pathlib
from xia2.Experts.Filenames import expand_path
from xia2.Experts.FindImages import (
    image2template_directory,
    template_directory_number2image,
)
from xia2.Handlers.Phil import PhilIndex

from xia2.Modules.Indexer import IndexerFactory
from xia2.Modules.Integrater import IntegraterFactory
from xia2.Modules.Refiner import RefinerFactory

logger = logging.getLogger("xia2.Schema.XSweep")


class _global_integration_parameters:
    """A global class to record the integration parameters which are exported
    for each crystal. This is a dictionary keyed by the crystal id."""

    # FIXME this is a threat to parallelism!
    # FIXME added copy.deepcopy to help prevent mashing of parameters...

    def __init__(self):
        self._parameter_dict = {}

    def set_parameters(self, crystal, parameters):
        self._parameter_dict[crystal] = copy.deepcopy(parameters)

    def get_parameters(self, crystal):
        return copy.deepcopy(self._parameter_dict.get(crystal, {}))


global_integration_parameters = _global_integration_parameters()

# Notes on XSweep
#
# This points through wavelength to crystal, so the lattice information
# (in particular, the lattice class e.g. tP) will be kept in
# self.getWavelength().getCrystal().getLattice() - this itself will be
# a versioning object, so should be tested for overdateness.
#
# The only dynamic object property that this has is the resolution, which
# may be set during processing or by the user. If it is set by the
# user then this should be used and not updated. It should also only
# be asserted once during processing => only update if currently None.
# Update 21/JUL/08 - now removed in the process of doing the resolution
# limits properly.

# Things which are needed to populate this object from the pointer to a
# single image.


class XSweep:
    """An object representation of the sweep."""

    def __init__(
        self,
        name,
        wavelength,
        sample,
        directory=None,
        image=None,
        beam=None,
        reversephi=False,
        distance=None,
        gain=0.0,
        dmin=0.0,
        dmax=0.0,
        polarization=0.0,
        frames_to_process=None,
        user_lattice=None,
        user_cell=None,
        epoch=0,
        ice=False,
        excluded_regions=None,
    ):
        """Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the images in directory starting with image,
        with beam centre optionally defined."""
        if excluded_regions is None:
            excluded_regions = []

        # FIXME bug 2221 if DIRECTORY starts with ~/ or ~graeme (say) need to
        # interpret this properly - e.g. map it to a full PATH.

        directory = expand_path(directory)

        self._name = name
        self._wavelength = wavelength
        self.sample = sample
        self._directory = directory
        self._image = image
        self._reversephi = reversephi
        self._epoch = epoch
        self._user_lattice = user_lattice
        self._user_cell = user_cell
        self._header = {}
        self._resolution_high = dmin
        self._resolution_low = dmax
        self._ice = ice
        self._excluded_regions = excluded_regions
        self._imageset = None

        # FIXME in here also need to be able to accumulate the total
        # dose from all experimental measurements (complex) and provide
        # a _epoch_to_dose dictionary or some such... may be fiddly as
        # this will need to parse across multiple templates. c/f Bug # 2798

        self._epoch_to_image = {}
        self._image_to_epoch = {}

        # to allow first, last image for processing to be
        # set... c/f integrater interface
        self._frames_to_process = frames_to_process

        # + derive template, list of images

        params = PhilIndex.get_python_object()
        if directory and image:
            self._template, self._directory = image2template_directory(
                os.path.join(directory, image)
            )

            from xia2.Schema import load_imagesets

            imagesets = load_imagesets(
                self._template,
                self._directory,
                image_range=self._frames_to_process,
                reversephi=(params.xia2.settings.input.reverse_phi or self._reversephi),
            )

            assert len(imagesets) == 1, "one imageset expected, %d found" % len(
                imagesets
            )
            self._imageset = copy.deepcopy(imagesets[0])
            start, end = self._imageset.get_array_range()
            self._images = list(range(start + 1, end + 1))

            # FIXME in here check that (1) the list of images is continuous
            # and (2) that all of the images are readable. This should also
            # take into account frames_to_process if set.

            if self._frames_to_process is None:
                self._frames_to_process = min(self._images), max(self._images)

            start, end = self._frames_to_process

            error = False

            if params.general.check_image_files_readable:
                for j in range(start, end + 1):
                    if j not in self._images:
                        logger.debug(
                            "image %i missing for %s"
                            % (j, self.get_imageset().get_template())
                        )
                        error = True
                        continue
                    image_name = self.get_imageset().get_path(j - start)
                    if not os.access(image_name, os.R_OK):
                        logger.debug("image %s unreadable" % image_name)
                        error = True
                        continue

                if error:
                    raise RuntimeError("problem with sweep %s" % self._name)

            beam_ = self._imageset.get_beam()
            scan = self._imageset.get_scan()
            if wavelength is not None:

                # If the wavelength value is 0.0 then first set it to the header
                # value - note that this assumes that the header value is correct
                # (a reasonable assumption)
                if wavelength.get_wavelength() == 0.0:
                    wavelength.set_wavelength(beam_.get_wavelength())

                # FIXME 08/DEC/06 in here need to allow for the fact
                # that the wavelength in the image header could be wrong and
                # in fact it should be replaced with the input value -
                # through the user will need to be warned of this and
                # also everything using the FrameProcessor interface
                # will also have to respect this!

                if (
                    math.fabs(beam_.get_wavelength() - wavelength.get_wavelength())
                    > 0.0001
                ):
                    logger.info(
                        "Header wavelength for sweep %s different"
                        " to assigned value (%4.2f vs. %4.2f)",
                        name,
                        beam_.get_wavelength(),
                        wavelength.get_wavelength(),
                    )

            # also in here look at the image headers to see if we can
            # construct a mapping between exposure epoch and image ...

            images = []

            if self._frames_to_process:
                start, end = self._frames_to_process
                for j in self._images:
                    if j >= start and j <= end:
                        images.append(j)
            else:
                images = self._images

            for j in images:
                epoch = scan.get_image_epoch(j)
                if epoch == 0.0:
                    epoch = float(
                        os.stat(self._imageset.get_path(j - images[0])).st_mtime
                    )
                self._epoch_to_image[epoch] = j
                self._image_to_epoch[j] = epoch

            epochs = self._epoch_to_image

            logger.debug(
                "Exposure epoch for sweep %s: %d %d"
                % (self._template, min(epochs), max(epochs))
            )

        self._input_imageset = copy.deepcopy(self._imageset)

        # + get the lattice - can this be a pointer, so that when
        #   this object updates lattice it is globally-for-this-crystal
        #   updated? The lattice included directly in here includes an
        #   exact unit cell for data reduction, the crystal lattice
        #   contains an approximate unit cell which should be
        #   from the unit cells from all sweeps contained in the
        #   XCrystal. FIXME should I be using a LatticeInfo object
        #   in here? See what the Indexer interface produces. ALT:
        #   just provide an Indexer implementation "hook".
        #   See Headnote 001 above. See also _get_indexer,
        #   _get_integrater below.

        self._indexer = None
        self._refiner = None
        self._integrater = None

        # I don't need this - it is equivalent to self.getWavelength(
        # ).getCrystal().getLattice()
        # self._crystal_lattice = None

        # this means that this module will have to present largely the
        # same interface as Indexer and Integrater so that the calls
        # can be appropriately forwarded.

        # finally configure the beam if set

        if beam is not None:
            from dxtbx.model.detector_helpers import set_mosflm_beam_centre

            try:
                set_mosflm_beam_centre(
                    self.get_imageset().get_detector(),
                    self.get_imageset().get_beam(),
                    beam,
                )
            except AssertionError as e:
                logger.debug("Error setting mosflm beam centre: %s" % e)

        self._beam_centre = beam
        self._distance = distance
        self._gain = gain
        self._polarization = polarization

        self._add_detector_identification_to_cif()

    # serialization functions

    def to_dict(self):
        obj = {}
        obj["__id__"] = "XSweep"

        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0] in ("_indexer", "_refiner", "_integrater") and a[1] is not None:
                obj[a[0]] = a[1].to_dict()
            elif a[0] == "_imageset":
                from dxtbx.serialize.imageset import imageset_to_dict

                obj[a[0]] = imageset_to_dict(a[1])
            elif a[0] == "_input_imageset":
                from dxtbx.serialize.imageset import imageset_to_dict

                obj[a[0]] = imageset_to_dict(a[1])
            elif a[0] == "_wavelength":
                # don't serialize this since the parent xwavelength *should* contain
                # the reference to the child xsweep
                continue
            elif a[0] == "sample":
                # don't serialize this since the parent xsample *should* contain
                # the reference to the child xsweep
                continue
            elif a[0].startswith("__"):
                continue
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "XSweep"
        return_obj = cls(name=None, sample=None, wavelength=None)
        for k, v in obj.items():
            if k in ("_indexer", "_refiner", "_integrater") and v is not None:
                from libtbx.utils import import_python_object

                cls = import_python_object(
                    import_path=".".join((v["__module__"], v["__name__"])),
                    error_prefix="",
                    target_must_be="",
                    where_str="",
                ).object
                v = cls.from_dict(v)
                if k == "_indexer":
                    v.add_indexer_sweep(return_obj)
                elif k == "_refiner":
                    v.add_refiner_sweep(return_obj)
                elif k == "_integrater":
                    v.set_integrater_sweep(return_obj, reset=False)
            if isinstance(v, dict):
                # if v.get('__id__') == 'ExperimentList':
                # from dxtbx.model.experiment_list import ExperimentListFactory
                # v = ExperimentListFactory.from_dict(v)
                if v.get("__id__") == "imageset":
                    from dxtbx.serialize.imageset import imageset_from_dict

                    v = imageset_from_dict(v, check_format=False)
            setattr(return_obj, k, v)
        if return_obj._indexer is not None and return_obj._integrater is not None:
            return_obj._integrater._intgr_indexer = return_obj._indexer
        if return_obj._integrater is not None and return_obj._refiner is not None:
            return_obj._integrater._intgr_refiner = return_obj._refiner
        if return_obj._indexer is not None and return_obj._refiner is not None:
            return_obj._refiner._refinr_indexers[
                return_obj.get_epoch(1)
            ] = return_obj._indexer
        return return_obj

    def get_image_name(self, number):
        """Convert an image number into a name."""

        return template_directory_number2image(self._template, self._directory, number)

    def get_template(self):
        return self._template

    def get_directory(self):
        return self._directory

    def get_all_image_names(self):
        """Get a full list of all images in this sweep..."""
        array_range = self._imageset.get_array_range()
        return [
            self._imageset.get_path(i)
            for i in range(0, array_range[1] - array_range[0])
        ]

    def get_image_range(self):
        """Get min / max numbers for this sweep."""

        return min(self._images), max(self._images)

    def get_imageset(self):
        return self._imageset

    def get_input_imageset(self):
        return self._input_imageset

    def get_header(self):
        """Get the image header information."""

        return copy.copy(self._header)

    def get_epoch(self, image):
        """Get the exposure epoch for this image."""

        return self._image_to_epoch.get(image, 0)

    def get_reversephi(self):
        """Get whether this is a reverse-phi sweep..."""
        return self._reversephi

    def get_image_to_epoch(self):
        """Get the image to epoch mapping table."""
        return copy.deepcopy(self._image_to_epoch)

    # to see if we have been instructed...

    def get_user_lattice(self):
        return self._user_lattice

    def get_user_cell(self):
        return self._user_cell

    def get_output(self):
        if self.get_wavelength():
            text = "SWEEP %s [WAVELENGTH %s]\n" % (
                self._name,
                self.get_wavelength().get_name(),
            )
        else:
            text = "SWEEP %s [WAVELENGTH UNDEFINED]\n" % self._name

        if self._template:
            text += "TEMPLATE %s\n" % self._template
        if self._directory:
            text += "DIRECTORY %s\n" % self._directory

        if self._header:
            # print some header information
            if "detector" in self._header:
                text += "DETECTOR %s\n" % self._header["detector"]
            if "exposure_time" in self._header:
                text += "EXPOSURE TIME %f\n" % self._header["exposure_time"]
            if "phi_start" in self._header:
                text += "PHI WIDTH %.2f\n" % (
                    self._header["phi_end"] - self._header["phi_start"]
                )

        if self._frames_to_process:
            frames = self._frames_to_process
            text += "IMAGES (USER) %d to %d\n" % (frames[0], frames[1])
        elif self._images:
            text += "IMAGES %d to %d\n" % (min(self._images), max(self._images))

        else:
            text += "IMAGES UNKNOWN\n"

        # add some stuff to implement the actual processing implicitly

        text += "MTZ file: %s\n" % self.get_integrater_intensities()

        return text

    def summarise(self):
        summary = ["Sweep: %s" % self._name]

        if self._template and self._directory:
            summary.append("Files %s" % os.path.join(self._directory, self._template))

        if self._frames_to_process:
            summary.append("Images: %d to %d" % tuple(self._frames_to_process))
            off = self._imageset.get_scan().get_batch_offset()
            first = self._frames_to_process[0]
            start = self._frames_to_process[0] - first + off
            end = self._frames_to_process[1] - first + 1 + off
            self._imageset = self._imageset[start:end]

        indxr = self._get_indexer()
        if indxr:
            # print the comparative values
            from xia2.Schema.Interfaces.FrameProcessor import get_beam_centre

            imgset = self.get_input_imageset()
            hbeam = get_beam_centre(imgset.get_detector(), imgset.get_beam())
            ibeam = indxr.get_indexer_beam_centre()

            if (
                hbeam
                and ibeam
                and len(hbeam) == 2
                and len(ibeam) == 2
                and all(hbeam)
                and all(ibeam)
            ):
                summary.append(
                    "Beam %.2f %.2f => %.2f %.2f"
                    % (hbeam[0], hbeam[1], ibeam[0], ibeam[1])
                )
            else:
                summary.append("Beam not on detector")

            hdist = imgset.get_detector()[0].get_directed_distance()
            idist = indxr.get_indexer_distance()

            if hdist and idist:
                summary.append(f"Distance {hdist:.2f} => {idist:.2f}")

            summary.append(
                "Date: %s"
                % time.asctime(time.gmtime(imgset.get_scan().get_epochs()[0]))
            )

        return summary

    def get_image(self):
        return self._image

    def get_beam_centre(self):
        return self._beam_centre

    def get_distance(self):
        return self._distance

    def get_gain(self):
        return self._gain

    def set_resolution_high(self, resolution_high):
        self._resolution_high = resolution_high

    def set_resolution_low(self, resolution_low):
        self._resolution_low = resolution_low

    def get_resolution_high(self):
        return self._resolution_high

    def get_resolution_low(self):
        return self._resolution_low

    def get_polarization(self):
        return self._polarization

    def get_name(self):
        return self._name

    def _create_path(self, *args):
        """Create a directory in the project space and return a path object"""

        if not self.get_wavelength():
            base_path = pathlib.Path(".")
        else:
            base_path = self.get_wavelength().get_crystal().get_project().path

        path = base_path.joinpath(*args)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("Set up path %s", path)
        return path

    # Real "action" methods - note though that these should never be
    # run directly, only implicitly...

    # These methods will be delegated down to Indexer and Integrater
    # implementations, through the defined method names. This should
    # make life interesting!

    # Note well - to get this to do things, ask for the
    # integrate_get_reflection() - this will kickstart everything.

    def _get_indexer(self):
        """Get my indexer, if set, else create a new one from the
        factory."""

        if self._indexer is None:
            # set the working directory for this, based on the hierarchy
            # defined herein...

            # that would be CRYSTAL_ID/WAVELENGTH/SWEEP/index &c.
            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"
                project_id = "default"
            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal().get_name()
                project_id = (
                    self.get_wavelength().get_crystal().get_project().get_name()
                )
            working_path = self._create_path(
                crystal_id, wavelength_id, self.get_name(), "index"
            )

            # FIXME the indexer factory should probably be able to
            # take self [this object] as input, to help with deciding
            # the most appropriate indexer to use... this will certainly
            # be the case for the integrater. Maintaining this link
            # will also help the system cope with updates (which
            # was going to be one of the big problems...)
            # 06/SEP/06 no keep these interfaces separate - want to
            # keep "pure" interfaces to the programs for reuse, then
            # wrap in XStyle.
            self._indexer = IndexerFactory.IndexerForXSweep(self)

            # set the user supplied lattice if there is one
            if self._user_lattice:
                self._indexer.set_indexer_input_lattice(self._user_lattice)
                self._indexer.set_indexer_user_input_lattice(True)

                # and also the cell constants - but only if lattice is
                # assigned

                if self._user_cell:
                    self._indexer.set_indexer_input_cell(self._user_cell)

            else:
                if self._user_cell:
                    raise RuntimeError("cannot assign cell without lattice")

            self._indexer.set_working_directory(str(working_path))

            self._indexer.set_indexer_project_info(
                project_id, crystal_id, wavelength_id
            )

            self._indexer.set_indexer_sweep_name(self._name)

        return self._indexer

    def _get_refiner(self):
        if self._refiner is None:
            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"
            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal().get_name()
            working_path = self._create_path(
                crystal_id, wavelength_id, self.get_name(), "refine"
            )
            self._refiner = RefinerFactory.RefinerForXSweep(self)
            self._refiner.set_working_directory(str(working_path))

            epoch = self.get_epoch(self._frames_to_process[0])
            indexer = self._get_indexer()
            self._refiner.add_refiner_indexer(epoch, indexer)

        return self._refiner

    # FIXME make this general - allow multiple intergraters from one indexer to
    # handle multi-lattice cases...

    def _get_integrater(self):
        """Get my integrater, and if it is not set, create one."""

        if self._integrater is None:

            # set the working directory for this, based on the hierarchy
            # defined herein...

            # that would be CRYSTAL_ID/WAVELENGTH/SWEEP/index &c.

            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"
                project_id = "default"
            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal().get_name()
                project_id = (
                    self.get_wavelength().get_crystal().get_project().get_name()
                )
            working_path = self._create_path(
                crystal_id, wavelength_id, self.get_name(), "integrate"
            )

            self._integrater = IntegraterFactory.IntegraterForXSweep(self)

            # configure the integrater with the indexer - unless
            # we don't want to...

            self._integrater.set_integrater_refiner(self._get_refiner())

            logger.debug(
                "Integrater / refiner / indexer for sweep %s: %s/%s/%s"
                % (
                    self._name,
                    self._integrater.__class__.__name__,
                    self._get_refiner().__class__.__name__,
                    self._get_indexer().__class__.__name__,
                )
            )

            # or if we have been told this on the command-line -
            # N.B. should really add a mechanism to specify the ice
            # rings we want removing, #1317.

            if PhilIndex.params.xia2.settings.integration.exclude_ice_regions:
                logger.debug("Ice ring region exclusion ON")
                self._integrater.set_integrater_ice(True)

            # or if we were told about ice or specific excluded resolution
            # ranges via the xinfo file
            if self._ice:
                self._integrater.set_integrater_ice(self._ice)

            if self._excluded_regions:
                self._integrater.set_integrater_excluded_regions(self._excluded_regions)

            self._integrater.set_integrater_project_info(
                project_id, crystal_id, wavelength_id
            )

            self._integrater.set_integrater_sweep_name(self._name)

            # copy across anomalous flags in case it's useful - #871

            self._integrater.set_integrater_anomalous(
                self.get_wavelength().get_crystal().get_anomalous()
            )

            # see if we have any useful detector parameters to pass on

            if self.get_gain():
                self._integrater.set_gain(self.get_gain())

            if self.get_polarization():
                self._integrater.set_polarization(self.get_polarization())

            # look to see if there are any global integration parameters
            # we can set...

            if global_integration_parameters.get_parameters(crystal_id):
                logger.debug("Using integration parameters for crystal %s" % crystal_id)
                self._integrater.set_integrater_parameters(
                    global_integration_parameters.get_parameters(crystal_id)
                )

            # frames to process...

            if self._frames_to_process:
                self._integrater._setup_from_imageset(self.get_imageset())
                # frames = self._frames_to_process
                # self._integrater.set_integrater_wedge(frames[0],
                # frames[1])
                # self._integrater.set_frame_wedge(frames[0],
                # frames[1])
                self._integrater.set_integrater_epoch(
                    self.get_epoch(self._frames_to_process[0])
                )

            self._integrater.set_working_directory(str(working_path))

        return self._integrater

    def get_frames_to_process(self):
        return self._frames_to_process

    def get_indexer_lattice(self):
        return self._get_indexer().get_indexer_lattice()

    def get_indexer_cell(self):
        return self._get_indexer().get_indexer_cell()

    def get_integrater_lattice(self):
        return self._get_integrater().get_integrater_lattice()

    def get_integrater_cell(self):
        return self._get_integrater().get_integrater_cell()

    def get_indexer_distance(self):
        return self._get_indexer().get_indexer_distance()

    def get_indexer_mosaic(self):
        return self._get_indexer().get_indexer_mosaic()

    def get_indexer_beam_centre(self):
        return self._get_indexer().get_indexer_beam_centre()

    def get_wavelength(self):
        return self._wavelength

    def get_wavelength_value(self):
        """Return the wavelength value in Angstroms."""

        try:
            return self.get_wavelength().get_wavelength()
        except Exception:
            return 0.0

    def get_integrater_intensities(self):
        reflections = self._get_integrater().get_integrater_intensities()

        # look to see if there are any global integration parameters
        # we can store...

        try:
            crystal_id = self.get_wavelength().get_crystal().get_name()
            if self._integrater.get_integrater_export_parameters():
                global_integration_parameters.set_parameters(
                    crystal_id, self._integrater.get_integrater_export_parameters()
                )
                logger.debug(
                    "Stored integration parameters for crystal %s" % crystal_id
                )

        except Exception:
            # logger.error('Error storing parameters for crystal %s', crystal_id)
            # logger.error(str(e))
            pass

        return reflections

    def get_crystal_lattice(self):
        """Get the parent crystal lattice pointer."""
        try:
            lattice = self.get_wavelength().get_crystal().get_lattice()
        except Exception:
            lattice = None

        return lattice

    def serialize(self):
        indxr = self._get_indexer()
        intgr = self._get_integrater()

        if indxr.get_indexer_finish_done():
            indxr.as_json(
                filename=os.path.join(indxr.get_working_directory(), "xia2.json")
            )
        if intgr.get_integrater_finish_done():
            intgr.as_json(
                filename=os.path.join(intgr.get_working_directory(), "xia2.json")
            )

    def get_detector_identification(self):
        detector_id = (
            PhilIndex.get_python_object().xia2.settings.developmental.detector_id
        )
        # eg. 'PILATUS 2M, S/N 24-0107 Diamond'
        if not detector_id and self.get_imageset():
            detector_id = self.get_imageset().get_detector()[0].get_identifier()
        if detector_id:
            logger.debug("Detector identified as %s" % detector_id)
            return detector_id
        else:
            logger.debug("Detector could not be identified")
            return None

    def _add_detector_identification_to_cif(self):
        detector_id = self.get_detector_identification()
        if detector_id:
            import dxtbx.data.beamline_defs as ddb

            bl_info = ddb.get_beamline_definition(detector_id)
            logger.debug(
                "Beamline information available for %s: %s"
                % (detector_id, str(bl_info))
            )
            if bl_info:
                from xia2.Handlers.CIF import CIF, mmCIF

                cifblock, mmcifblock = bl_info.CIF_block(), bl_info.mmCIF_block()
                if cifblock:
                    CIF.set_block(bl_info.get_block_name(), cifblock)
                if mmcifblock:
                    mmCIF.set_block(bl_info.get_block_name(), mmcifblock)

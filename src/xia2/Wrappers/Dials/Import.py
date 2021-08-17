import json
import logging
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

logger = logging.getLogger("xia2.Wrappers.Dials.Import")


def Import(DriverType=None):
    """A factory for ImportWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ImportWrapper(DriverInstance.__class__, FrameProcessor):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.import")

            self._images = []
            self._image_range = []

            self._sweep_filename = "imported.expt"
            self._image_to_epoch = None
            self._reference_geometry = None
            self._mosflm_beam_centre = None
            self._wavelength_tolerance = None

        def set_image_range(self, image_range):
            self._image_range = image_range

        def set_sweep_filename(self, sweep_filename):
            self._sweep_filename = sweep_filename

        def get_sweep_filename(self):
            if os.path.abspath(self._sweep_filename):
                return self._sweep_filename
            else:
                return os.path.join(self.get_working_directory(), self._sweep_filename)

        def set_mosflm_beam_centre(self, mosflm_beam_centre):
            self._mosflm_beam_centre = mosflm_beam_centre

        def fix_experiments_import(self):
            experiments_json = self.get_sweep_filename()

            experiments = json.load(open(experiments_json))
            scan = experiments["scan"][0]

            # fix image_range, exposure_time, epochs

            first, last = self._image_range
            offset = self.get_frame_offset()

            exposure_time = scan["exposure_time"][0]
            scan["image_range"] = [first + offset, last + offset]
            scan["epochs"] = []
            scan["exposure_time"] = []
            scan["epochs"] = []
            for image in range(first, last + 1):
                scan["exposure_time"].append(exposure_time)
                scan["epochs"].append(self._image_to_epoch[image + offset])
            experiments["scan"] = [scan]
            with open(experiments_json, "w") as fh:
                json.dump(experiments, fh)

        def run(self, fast_mode=False):
            # fast_mode: read first two image headers then extrapolate the rest
            # from what xia2 read from the image headers...

            if fast_mode:
                if not self._image_to_epoch:
                    raise RuntimeError("fast mode needs image_to_epoch map")
                logger.debug("Running dials.import in fast mode")
            else:
                logger.debug("Running dials.import in slow mode")

            self.clear_command_line()

            for i in range(self._image_range[0], self._image_range[1] + 1):
                self._images.append(self.get_image_name(i))

            if self._wavelength_tolerance is not None:
                self.add_command_line(
                    "input.tolerance.beam.wavelength=%s" % self._wavelength_tolerance
                )

            if self._reference_geometry is not None:
                self.add_command_line(
                    "input.reference_geometry=%s" % self._reference_geometry
                )

            elif self._mosflm_beam_centre is not None:
                assert len(self._mosflm_beam_centre) == 2
                self.add_command_line(
                    "mosflm_beam_centre=%s,%s" % (self._mosflm_beam_centre)
                )

            if fast_mode:
                for image in self._images[:2]:
                    self.add_command_line(image)
            else:
                for image in self._images:
                    self.add_command_line(image)

            self.add_command_line("output.experiments=%s" % self._sweep_filename)
            self.start()
            self.close_wait()
            self.check_for_errors()

            if fast_mode:
                self.fix_experiments_import()

            assert os.path.exists(
                os.path.join(self.get_working_directory(), self._sweep_filename)
            )

    return ImportWrapper()

import logging
import os
import shutil

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import (
    imageset_to_xds,
    template_to_xds,
    xds_check_version_supported,
)

logger = logging.getLogger("xia2.Wrappers.XDS.XDSDefpix")


def XDSDefpix(DriverType=None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSDefpixWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping XDS in defpix mode."""

        def __init__(self):
            super().__init__()

            # now set myself up...

            self.set_executable("xds")

            # generic bits

            self._data_range = (0, 0)
            self._resolution_high = 0.0
            self._resolution_low = 40.0
            # self._VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS
            self._value_range_for_trusted_detector_pixels = None

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = [
                "X-CORRECTIONS.cbf",
                "Y-CORRECTIONS.cbf",
                "BKGINIT.cbf",
                "XPARM.XDS",
            ]

            self._output_data_files_list = ["BKGPIX.cbf", "ABS.cbf"]

        # getter and setter for input / output data

        def set_value_range_for_trusted_detector_pixels(
            self, value_range_for_trusted_detector_pixels
        ):
            self._value_range_for_trusted_detector_pixels = tuple(
                value_range_for_trusted_detector_pixels
            )

        def set_resolution_high(self, resolution_high):
            self._resolution_high = resolution_high

        def set_resolution_low(self, resolution_low):
            self._resolution_low = resolution_low

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            offset = self.get_frame_offset()
            self._data_range = (start - offset, end - offset)

        def run(self):
            """Run defpix."""

            # image_header = self.get_header()

            ## crank through the header dictionary and replace incorrect
            ## information with updated values through the indexer
            ## interface if available...

            ## need to add distance, wavelength - that should be enough...

            # if self.get_distance():
            # image_header['distance'] = self.get_distance()

            # if self.get_wavelength():
            # image_header['wavelength'] = self.get_wavelength()

            # if self.get_two_theta():
            # image_header['two_theta'] = self.get_two_theta()

            header = imageset_to_xds(self.get_imageset())

            xds_inp = open(os.path.join(self.get_working_directory(), "XDS.INP"), "w")

            # what are we doing?
            xds_inp.write("JOB=DEFPIX\n")

            for record in header:
                xds_inp.write("%s\n" % record)

            name_template = template_to_xds(
                os.path.join(self.get_directory(), self.get_template())
            )

            record = "NAME_TEMPLATE_OF_DATA_FRAMES=%s\n" % name_template

            xds_inp.write(record)

            xds_inp.write("DATA_RANGE=%d %d\n" % self._data_range)

            # include the resolution range, perhaps
            if self._resolution_high > 0.0 or self._resolution_low > 0.0:
                xds_inp.write(
                    "INCLUDE_RESOLUTION_RANGE=%.2f %.2f\n"
                    % (self._resolution_low, self._resolution_high)
                )

            if self._value_range_for_trusted_detector_pixels is not None:
                xds_inp.write(
                    "VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS=%i %i"
                    % self._value_range_for_trusted_detector_pixels
                )

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "XDS.INP"),
                os.path.join(
                    self.get_working_directory(), "%d_DEFPIX.INP" % self.get_xpid()
                ),
            )

            # write the input data files...

            for file_name in self._input_data_files_list:
                src = self._input_data_files[file_name]
                dst = os.path.join(self.get_working_directory(), file_name)
                if src != dst:
                    shutil.copyfile(src, dst)

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())

            # copy the LP file
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "DEFPIX.LP"),
                os.path.join(
                    self.get_working_directory(), "%d_DEFPIX.LP" % self.get_xpid()
                ),
            )

            # check the resolution asked for is achievable (if set)
            for record in open(os.path.join(self.get_working_directory(), "DEFPIX.LP")):
                if "RESOLUTION RANGE RECORDED BY DETECTOR" in record:
                    real_high = float(record.split()[-1])
                    if self._resolution_high:
                        if real_high > self._resolution_high + 0.01:
                            logger.warning(
                                "Warning: resolution limited to %.2f", real_high
                            )

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = os.path.join(
                    self.get_working_directory(), file
                )

    return XDSDefpixWrapper()

import os
import shutil

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import (
    find_hdf5_lib,
    imageset_to_xds,
    template_to_xds,
    xds_check_version_supported,
)


def XDSColspot(DriverType=None, params=None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSColspotWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping XDS in colspot mode."""

        def __init__(self, params=None):
            super().__init__()

            # phil parameters

            if not params:
                from xia2.Handlers.Phil import master_phil

                params = master_phil.extract().xds.colspot
            self._params = params

            # now set myself up...

            self._parallel = PhilIndex.params.xia2.settings.multiprocessing.nproc
            self.set_cpu_threads(self._parallel)

            if isinstance(self._parallel, int) and self._parallel <= 1:
                self.set_executable("xds")
            else:
                self.set_executable("xds_par")

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = []
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = [
                "X-CORRECTIONS.cbf",
                "Y-CORRECTIONS.cbf",
                "BLANK.cbf",
                "BKGINIT.cbf",
                "GAIN.cbf",
            ]

            self._output_data_files_list = ["SPOT.XDS"]

        # getter and setter for input / output data

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            offset = self.get_frame_offset()
            self._data_range = (start - offset, end - offset)

        def add_spot_range(self, start, end):
            offset = self.get_frame_offset()
            self._spot_range.append((start - offset, end - offset))

        def set_background_range(self, start, end):
            offset = self.get_frame_offset()
            self._background_range = (start - offset, end - offset)

        def run(self):
            """Run colspot."""
            header = imageset_to_xds(self.get_imageset())

            xds_inp = open(os.path.join(self.get_working_directory(), "XDS.INP"), "w")

            # what are we doing?
            xds_inp.write("JOB=COLSPOT\n")
            xds_inp.write("MAXIMUM_NUMBER_OF_PROCESSORS=%d\n" % self._parallel)
            xds_inp.write("MAXIMUM_NUMBER_OF_JOBS=1\n")

            if self.get_imageset().get_detector()[0].get_type() == "SENSOR_PAD":
                xds_inp.write(
                    "MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT=%d\n"
                    % self._params.minimum_pixels_per_spot
                )

            for record in header:
                xds_inp.write("%s\n" % record)

            name_template = template_to_xds(
                os.path.join(self.get_directory(), self.get_template())
            )

            record = "NAME_TEMPLATE_OF_DATA_FRAMES=%s\n" % name_template

            xds_inp.write(record)

            lib_str = find_hdf5_lib(
                os.path.join(self.get_directory(), self.get_template())
            )
            if lib_str:
                xds_inp.write(lib_str)

            xds_inp.write("DATA_RANGE=%d %d\n" % self._data_range)
            for spot_range in self._spot_range:
                xds_inp.write("SPOT_RANGE=%d %d\n" % spot_range)
            xds_inp.write("BACKGROUND_RANGE=%d %d\n" % self._background_range)

            if PhilIndex.params.xia2.settings.small_molecule:
                xds_inp.write("STRONG_PIXEL=5\n")
                # FIXME should probably be moved to a phil parameter

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "XDS.INP"),
                os.path.join(
                    self.get_working_directory(), "%d_COLSPOT.INP" % self.get_xpid()
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
                os.path.join(self.get_working_directory(), "COLSPOT.LP"),
                os.path.join(
                    self.get_working_directory(), "%d_COLSPOT.LP" % self.get_xpid()
                ),
            )

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = os.path.join(
                    self.get_working_directory(), file
                )

    return XDSColspotWrapper(params)

import os

from libtbx import phil
from xia2.Driver.DriverFactory import DriverFactory

from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

master_params = phil.parse(
    """
"""
)


def ExportSpotXDS(DriverType=None, params=None):
    DriverInstance = DriverFactory.Driver(DriverType)

    class ExportSpotXDSWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping dials.export_spot_xds."""

        def __init__(self, params=None):
            super().__init__()

            # phil parameters

            if not params:
                params = master_params.extract()
            self._params = params

            # now set myself up...

            self.set_executable("dials.export_spot_xds")

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = []
            self._output_data_files_list = []

        # getter and setter for input / output data

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def run(self):
            """Run dials.spotfinder."""

            self.add_command_line(list(self._input_data_files))
            self.start()
            self.close_wait()
            self.check_for_errors()

            self._output_data_files.setdefault(
                "SPOT.XDS",
                open(
                    os.path.join(self.get_working_directory(), "SPOT.XDS"), "rb"
                ).read(),
            )

            output = self.get_all_output()
            print("".join(output))

    return ExportSpotXDSWrapper(params=params)

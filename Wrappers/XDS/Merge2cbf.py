from __future__ import absolute_import, division, print_function

import fileinput
import os
import time

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import xds_check_version_supported


def Merge2cbf(DriverType=None, params=None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class Merge2cbfWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping merge2cbf."""

        def __init__(self, params=None):
            super(Merge2cbfWrapper, self).__init__()

            # phil parameters

            if not params:
                from xia2.Handlers.Phil import master_phil

                params = master_phil.extract().xds.merge2cbf
            self._params = params

            # now set myself up...

            # I don't think there is a parallel version
            self.set_executable("merge2cbf")

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = []
            self._output_data_files_list = []

        @property
        def data_range(self):
            return self._params.data_range

        @data_range.setter
        def data_range(self, value):
            start, end = value
            self._params.data_range = (start, end)

        @property
        def moving_average(self):
            return self._params.moving_average

        @moving_average.setter
        def moving_average(self, value):
            self._params.moving_average = value

        @property
        def merge_n_images(self):
            return self._params.merge_n_images

        @merge_n_images.setter
        def merge_n_images(self, n):
            self._params.merge_n_images = n

        def run_core(self, data_range, moving_average=False):
            """Actually run merge2cbf itself."""

            # merge2cbf only requires mimimal information in the input file

            name_template = os.path.join(
                self.get_directory(), self.get_template().replace("#", "?")
            )

            self._output_template = os.path.join("merge2cbf_averaged_????.cbf")

            with open(
                os.path.join(self.get_working_directory(), "MERGE2CBF.INP"), "w"
            ) as fh:
                fh.write("NAME_TEMPLATE_OF_DATA_FRAMES=%s\n" % name_template)

                fh.write("NAME_TEMPLATE_OF_OUTPUT_FRAMES=%s\n" % self._output_template)

                fh.write(
                    "NUMBER_OF_DATA_FRAMES_COVERED_BY_EACH_OUTPUT_FRAME=%s\n"
                    % self.merge_n_images
                )

                fh.write("DATA_RANGE=%d %d\n" % tuple(data_range))

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())

        def run(self):
            """Run merge2cbf."""

            if self.moving_average:
                i_first, i_last = self.data_range
                n_output_images = (i_last - i_first) - self.merge_n_images + 1
                for i in range(i_first, i_first + n_output_images):
                    data_range = (i, i + self.merge_n_images)
                    self.run_core(data_range, moving_average=False)
                self.update_minicbf_headers(moving_average=True)
                return

            self.run_core(self.data_range, moving_average=False)
            self.update_minicbf_headers(moving_average=False)

        def update_minicbf_headers(self, moving_average=False):
            i_first, i_last = self.data_range
            if moving_average:
                n_output_images = (i_last - i_first) - self.merge_n_images + 1
            else:
                n_output_images = (i_last - i_first + 1) // self.merge_n_images

            for i in range(n_output_images):
                minicbf_header_content = self.get_minicbf_header_contents(
                    i, moving_average=moving_average
                )
                filename = os.path.join(
                    self.get_working_directory(),
                    self._output_template.replace("????", "%04i") % (i + 1),
                )
                assert os.path.isfile(filename)
                f = fileinput.input(filename, mode="rb", inplace=1)
                processing_array_header_contents = False
                printed_array_header_contents = False
                for line in f:
                    if processing_array_header_contents and line.startswith("_"):
                        # we have reached the next data item
                        processing_array_header_contents = False
                    elif line.startswith("_array_data.header_contents"):
                        processing_array_header_contents = True
                    elif processing_array_header_contents:
                        if not printed_array_header_contents:
                            print(""";\n%s\n;\n""" % minicbf_header_content)
                            printed_array_header_contents = True
                        continue
                    print(line, end=" ")
                f.close()

        def get_minicbf_header_contents(self, i_output_image, moving_average=False):
            from xia2.Wrappers.XDS.XDS import beam_centre_mosflm_to_xds

            header_contents = []
            image_header = self.get_header()
            header_contents.append(
                "# Detector: %s" % image_header["detector_class"].upper()
            )

            timestamp = time.strftime(
                "%Y-%m-%dT%H:%M:%S.000", time.gmtime(image_header["epoch"])
            )
            header_contents.append("# %s" % timestamp)
            pixel_size_mm = image_header["pixel"]
            pixel_size_microns = tuple(mm * 1000 for mm in pixel_size_mm)
            header_contents.append(
                "# Pixel_size %.0fe-6 m x %.0fe-6 m" % pixel_size_microns
            )
            if "pilatus" in image_header["detector_class"]:
                header_contents.append("# Silicon sensor, thickness 0.000320 m")
            header_contents.append(
                "# Exposure_period %.7f s" % image_header["exposure_time"]
            )
            # XXX xia2 doesn't keep track of the overload count cutoff value?
            header_contents.append("# Count_cutoff %i counts" % 1e7)
            header_contents.append("# Wavelength %.5f A" % image_header["wavelength"])
            # mm to m
            header_contents.append(
                "# Detector_distance %.5f m" % (image_header["distance"] / 1000)
            )
            beam_x, beam_y = image_header["beam"]
            header_contents.append(
                "# Beam_xy (%.2f, %.2f) pixels"
                % beam_centre_mosflm_to_xds(beam_x, beam_y, image_header)
            )
            input_phi_width = image_header["phi_width"]
            if moving_average:
                output_phi_width = input_phi_width
            else:
                output_phi_width = input_phi_width * self.merge_n_images
            header_contents.append(
                "# Start_angle %.4f deg."
                % (image_header["phi_start"] + output_phi_width * i_output_image)
            )
            header_contents.append("# Angle_increment %.4f deg." % output_phi_width)
            header_contents.append(
                "# Detector_2theta %.4f deg." % image_header["two_theta"]
            )
            return "\n".join(header_contents)

    return Merge2cbfWrapper(params=params)

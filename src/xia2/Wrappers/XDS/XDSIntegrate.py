import copy
import logging
import os
import shutil

from libtbx import Auto

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import (
    _running_xds_version,
    find_hdf5_lib,
    imageset_to_xds,
    template_to_xds,
    xds_check_error,
    xds_check_version_supported,
)

# specific helper stuff
from xia2.Wrappers.XDS.XDSIntegrateHelpers import (
    parse_integrate_lp,
    parse_integrate_lp_updates,
)

logger = logging.getLogger("xia2.Wrappers.XDS.XDSIntegrate")

# For details on reflecting_range, it's E.S.D., and beam divergence etc.
# see:
#
# http://xds.mpimf-heidelberg.mpg.de/html_doc/xds_parameters.html


def XDSIntegrate(DriverType=None, params=None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIntegrateWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping XDS in integrate mode."""

        def __init__(self, params=None):
            super().__init__()

            # phil parameters

            if not params:
                from xia2.Handlers.Phil import master_phil

                params = master_phil.extract().xds.integrate
            self._params = params

            # now set myself up...

            self._parallel = PhilIndex.params.xia2.settings.multiprocessing.nproc
            self.set_cpu_threads(self._parallel)

            if self._parallel != Auto and self._parallel <= 1:
                self.set_executable("xds")
            else:
                self.set_executable("xds_par")

            # generic bits

            self._data_range = (0, 0)

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = [
                "X-CORRECTIONS.cbf",
                "Y-CORRECTIONS.cbf",
                "BLANK.cbf",
                "BKGPIX.cbf",
                "GAIN.cbf",
                "XPARM.XDS",
            ]

            self._output_data_files_list = ["FRAME.cbf"]

            self._refined_xparm = False

            self._updates = {}

            # note well - INTEGRATE.HKL is not included in this list
            # because it is likely to be very large - this is treated
            # separately...

            self._integrate_hkl = None

            # FIXME these will also be wanted by the full integrater
            # interface I guess?

            self._mean_mosaic = None
            self._min_mosaic = None
            self._max_mosaic = None

        # getter and setter for input / output data

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        # this needs setting up from setup_from_image in FrameProcessor

        def set_refined_xparm(self):
            self._refined_xparm = True

        def set_data_range(self, start, end):
            offset = self.get_frame_offset()
            self._data_range = (start - offset, end - offset)

        def set_updates(self, updates):
            self._updates = updates

        def get_updates(self):
            return copy.deepcopy(self._updates)

        def get_mosaic(self):
            return self._min_mosaic, self._mean_mosaic, self._max_mosaic

        def get_per_image_statistics(self):
            return self._per_image_statistics

        def run(self):
            """Run integrate."""

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
            xds_inp.write("JOB=INTEGRATE\n")
            xds_inp.write("MAXIMUM_NUMBER_OF_PROCESSORS=%d\n" % self._parallel)

            from xia2.Handlers.Phil import PhilIndex

            xds_params = PhilIndex.params.xds
            if xds_params.profile_grid_size:
                ab, c = xds_params.profile_grid_size
                assert ab > 0 and ab < 22 and (ab % 2) == 1
                assert c > 0 and c < 22 and (c % 2) == 1
                xds_inp.write(
                    "NUMBER_OF_PROFILE_GRID_POINTS_ALONG_ALPHA/BETA= %d\n" % ab
                )
                xds_inp.write("NUMBER_OF_PROFILE_GRID_POINTS_ALONG_GAMMA= %d\n" % c)

            mp_params = PhilIndex.params.xia2.settings.multiprocessing
            if mp_params.mode == "serial" and mp_params.njob > 1:
                xds_inp.write("MAXIMUM_NUMBER_OF_JOBS=%d\n" % mp_params.njob)

            elif mp_params.mode == "serial" and mp_params.njob == Auto:
                chunk_width = 30.0
                phi_width = self.get_phi_width()
                nchunks = int(
                    (self._data_range[1] - self._data_range[0] + 1)
                    * phi_width
                    / chunk_width
                )

                logger.debug("Xparallel: -1 using %d chunks", nchunks)

                xds_inp.write("MAXIMUM_NUMBER_OF_JOBS=%d\n" % nchunks)
            else:
                xds_inp.write("MAXIMUM_NUMBER_OF_JOBS=1\n")

            profile_fitting = PhilIndex.params.xia2.settings.integration.profile_fitting
            if not profile_fitting:
                xds_inp.write("PROFILE_FITTING=FALSE\n")

            # write out lots of output
            xds_inp.write("TEST=2\n")

            if self._params.delphi:
                xds_inp.write("DELPHI=%.1f\n" % self._params.delphi)
            elif PhilIndex.params.xia2.settings.small_molecule:
                xds_inp.write("DELPHI=%.1f\n" % xds_params.delphi_small)
            else:
                xds_inp.write("DELPHI=%.1f\n" % xds_params.delphi)

            if self._refined_xparm:
                xds_inp.write(
                    "REFINE(INTEGRATE)=%s\n" % " ".join(self._params.refine_final)
                )
            else:
                xds_inp.write("REFINE(INTEGRATE)=%s\n" % " ".join(self._params.refine))

            if self._params.fix_scale:
                if _running_xds_version() >= 20130330:
                    xds_inp.write(
                        "DATA_RANGE_FIXED_SCALE_FACTOR= %d %d 1\n" % self._data_range
                    )
                else:
                    xds_inp.write("FIXED_SCALE_FACTOR=TRUE\n")

            # check for updated input parameters or ones from phil

            if (
                "BEAM_DIVERGENCE" in self._updates
                and "BEAM_DIVERGENCE_E.S.D." in self._updates
            ):
                xds_inp.write(
                    "BEAM_DIVERGENCE=%f BEAM_DIVERGENCE_E.S.D.=%f\n"
                    % (
                        self._updates["BEAM_DIVERGENCE"],
                        self._updates["BEAM_DIVERGENCE_E.S.D."],
                    )
                )
            elif self._params.beam_divergence and self._params.beam_divergence_esd:
                xds_inp.write(
                    "BEAM_DIVERGENCE=%f BEAM_DIVERGENCE_E.S.D.=%f\n"
                    % (self._params.beam_divergence, self._params.beam_divergence_esd)
                )

            if (
                "REFLECTING_RANGE" in self._updates
                and "REFLECTING_RANGE_E.S.D." in self._updates
            ):
                xds_inp.write(
                    "REFLECTING_RANGE=%f REFLECTING_RANGE_E.S.D.=%f\n"
                    % (
                        self._updates["REFLECTING_RANGE"],
                        self._updates["REFLECTING_RANGE_E.S.D."],
                    )
                )
            elif self._params.reflecting_range and self._params.reflecting_range_esd:
                xds_inp.write(
                    "REFLECTING_RANGE=%f REFLECTING_RANGE_E.S.D.=%f\n"
                    % (self._params.reflecting_range, self._params.reflecting_range_esd)
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

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "XDS.INP"),
                os.path.join(
                    self.get_working_directory(), "%d_INTEGRATE.INP" % self.get_xpid()
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
            xds_check_error(self.get_all_output())

            # look for errors
            # like this perhaps - what the hell does this mean?
            #   !!! ERROR !!! "STRONGHKL": ASSERT VIOLATION

            # copy the LP file
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "INTEGRATE.LP"),
                os.path.join(
                    self.get_working_directory(), "%d_INTEGRATE.LP" % self.get_xpid()
                ),
            )

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = os.path.join(
                    self.get_working_directory(), file
                )

            self._integrate_hkl = os.path.join(
                self.get_working_directory(), "INTEGRATE.HKL"
            )

            # look through integrate.lp for some useful information
            # to help with the analysis

            mosaics = []

            for o in open(
                os.path.join(self.get_working_directory(), "INTEGRATE.LP")
            ).readlines():
                if "CRYSTAL MOSAICITY (DEGREES)" in o:
                    mosaic = float(o.split()[-1])
                    mosaics.append(mosaic)

            assert (
                len(mosaics) > 0
            ), "XDS refinement failed (no mosaic spread range reported)"
            self._min_mosaic = min(mosaics)
            self._max_mosaic = max(mosaics)
            self._mean_mosaic = sum(mosaics) / len(mosaics)

            logger.debug(
                "Mosaic spread range: %.3f %.3f %.3f",
                self._min_mosaic,
                self._mean_mosaic,
                self._max_mosaic,
            )

            stats = parse_integrate_lp(
                os.path.join(self.get_working_directory(), "INTEGRATE.LP")
            )

            self._per_image_statistics = stats

            self._updates = parse_integrate_lp_updates(
                os.path.join(self.get_working_directory(), "INTEGRATE.LP")
            )

    return XDSIntegrateWrapper(params)

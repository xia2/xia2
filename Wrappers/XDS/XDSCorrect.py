import logging
import os
import shutil

from cctbx.uctbx import unit_cell
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import (
    imageset_to_xds,
    template_to_xds,
    xds_check_error,
    xds_check_version_supported,
)

# specific helper stuff
from xia2.Wrappers.XDS.XDSCorrectHelpers import _parse_correct_lp

logger = logging.getLogger("xia2.Wrappers.XDS.XDSCorrect")


def XDSCorrect(DriverType=None, params=None):
    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSCorrectWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping XDS in correct mode."""

        def __init__(self, params=None):
            super().__init__()

            # phil parameters

            if not params:
                from xia2.Handlers.Phil import master_phil

                params = master_phil.extract().xds.correct
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
            self._resolution_high = 0.0
            self._resolution_low = 40.0

            # specific information

            self._cell = None
            self._spacegroup_number = None
            self._anomalous = False

            self._polarization = 0.0

            self._reindex_matrix = None
            self._reindex_used = None

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = []

            self._output_data_files_list = ["GXPARM.XDS"]

            self._ice = 0
            self._excluded_regions = []

            # the following input files are also required:
            #
            # INTEGRATE.HKL
            # REMOVE.HKL
            #
            # and XDS_ASCII.HKL is produced.

            # in
            self._integrate_hkl = None
            self._remove_hkl = None

            # out
            self._xds_ascii_hkl = None
            self._results = None
            self._remove = []

        # getter and setter for input / output data

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous

        def get_anomalous(self):
            return self._anomalous

        def set_spacegroup_number(self, spacegroup_number):
            self._spacegroup_number = spacegroup_number

        def set_cell(self, cell):
            self._cell = cell

        def set_ice(self, ice):
            self._ice = ice

        def set_excluded_regions(self, excluded_regions):
            self._excluded_regions = excluded_regions

        def set_polarization(self, polarization):
            if polarization > 1.0 or polarization < 0.0:
                raise RuntimeError("bad value for polarization: %.2f" % polarization)
            self._polarization = polarization

        def set_reindex_matrix(self, reindex_matrix):
            if not len(reindex_matrix) == 12:
                raise RuntimeError("reindex matrix must be 12 numbers")
            self._reindex_matrix = reindex_matrix

        def get_reindex_used(self):
            return self._reindex_used

        def set_resolution_high(self, resolution_high):
            self._resolution_high = resolution_high

        def set_resolution_low(self, resolution_low):
            self._resolution_low = resolution_low

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def set_integrate_hkl(self, integrate_hkl):
            self._integrate_hkl = integrate_hkl

        def get_remove(self):
            return self._remove

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

        def get_result(self, name):
            if not self._results:
                raise RuntimeError("no results")

            if name not in self._results:
                raise RuntimeError('result name "%s" unknown' % name)

            return self._results[name]

        def run(self):
            """Run correct."""

            # this is ok...
            # if not self._cell:
            # raise RuntimeError('cell not set')
            # if not self._spacegroup_number:
            # raise RuntimeError('spacegroup not set')

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
            xds_inp.write("JOB=CORRECT\n")
            xds_inp.write("MAXIMUM_NUMBER_OF_PROCESSORS=%d\n" % self._parallel)

            # check to see if we are excluding ice rings
            if self._ice != 0:
                logger.debug("Excluding ice rings")

                for record in open(
                    os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "..",
                            "Data",
                            "ice-rings.dat",
                        )
                    )
                ).readlines():

                    resol = tuple(map(float, record.split()[:2]))

                    xds_inp.write("EXCLUDE_RESOLUTION_RANGE= %.2f %.2f\n" % resol)

            # exclude requested resolution ranges
            if self._excluded_regions:
                logger.debug("Excluding regions: %s" % repr(self._excluded_regions))

                for upper, lower in self._excluded_regions:
                    xds_inp.write(
                        f"EXCLUDE_RESOLUTION_RANGE= {upper:.2f} {lower:.2f}\n"
                    )

            # postrefine everything to give better values to the
            # next INTEGRATE run
            xds_inp.write("REFINE(CORRECT)=%s\n" % " ".join(self._params.refine))

            if self._polarization > 0.0:
                xds_inp.write("FRACTION_OF_POLARIZATION=%.2f\n" % self._polarization)

            if self._params.air is not None:
                xds_inp.write("AIR=%f" % self._params.air)

            for record in header:
                xds_inp.write("%s\n" % record)

            name_template = template_to_xds(
                os.path.join(self.get_directory(), self.get_template())
            )

            record = "NAME_TEMPLATE_OF_DATA_FRAMES=%s\n" % name_template

            xds_inp.write(record)

            xds_inp.write("DATA_RANGE=%d %d\n" % self._data_range)
            # xds_inp.write('MINIMUM_ZETA=0.1\n')
            # include the resolution range, perhaps
            if self._resolution_high or self._resolution_low:
                xds_inp.write(
                    "INCLUDE_RESOLUTION_RANGE=%.2f %.2f\n"
                    % (self._resolution_low, self._resolution_high)
                )

            if self._anomalous:
                xds_inp.write("FRIEDEL'S_LAW=FALSE\n")
                xds_inp.write("STRICT_ABSORPTION_CORRECTION=TRUE\n")
            else:
                xds_inp.write("FRIEDEL'S_LAW=TRUE\n")

            if self._spacegroup_number:
                if not self._cell:
                    raise RuntimeError("cannot set spacegroup without unit cell")

                xds_inp.write("SPACE_GROUP_NUMBER=%d\n" % self._spacegroup_number)
            if self._cell:
                xds_inp.write("UNIT_CELL_CONSTANTS=")
                xds_inp.write(
                    "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n" % tuple(self._cell)
                )
            if self._reindex_matrix:
                xds_inp.write(
                    "REIDX=%d %d %d %d %d %d %d %d %d %d %d %d"
                    % tuple(map(int, self._reindex_matrix))
                )

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "XDS.INP"),
                os.path.join(
                    self.get_working_directory(), "%d_CORRECT.INP" % self.get_xpid()
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
            # like this perhaps
            #   !!! ERROR !!! ILLEGAL SPACE GROUP NUMBER OR UNIT CELL

            # copy the LP file
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "CORRECT.LP"),
                os.path.join(
                    self.get_working_directory(), "%d_CORRECT.LP" % self.get_xpid()
                ),
            )

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = os.path.join(
                    self.get_working_directory(), file
                )

            self._xds_ascii_hkl = os.path.join(
                self.get_working_directory(), "XDS_ASCII.HKL"
            )

            # do some parsing of the correct output...

            self._results = _parse_correct_lp(
                os.path.join(self.get_working_directory(), "CORRECT.LP")
            )

            # check that the unit cell is comparable to what went in i.e.
            # the volume is the same to within a factor of 10 (which is
            # extremely generous and should only spot gross errors)

            original = unit_cell(self._cell)
            refined = unit_cell(self._results["cell"])

            if original.volume() / refined.volume() > 10:
                raise RuntimeError("catastrophic change in unit cell volume")

            if refined.volume() / original.volume() > 10:
                raise RuntimeError("catastrophic change in unit cell volume")

            # record reindex operation used for future reference... this
            # is to trap trac #419

            if "reindex_op" in self._results:
                format = "XDS applied reindex:" + 12 * " %d"
                logger.debug(format % tuple(self._results["reindex_op"]))
                self._reindex_used = self._results["reindex_op"]

            # get the reflections to remove...
            for line in open(
                os.path.join(self.get_working_directory(), "CORRECT.LP")
            ).readlines():
                if '"alien"' in line:
                    h, k, l = tuple(map(int, line.split()[:3]))
                    z = float(line.split()[4])
                    if not (h, k, l, z) in self._remove:
                        self._remove.append((h, k, l, z))

            return

    return XDSCorrectWrapper()

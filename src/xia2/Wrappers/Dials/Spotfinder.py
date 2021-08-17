import logging
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

logger = logging.getLogger("xia2.Wrappers.Dials.Spotfinder")


def Spotfinder(DriverType=None):
    """A factory for SpotfinderWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class SpotfinderWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.find_spots")

            self._input_sweep_filename = None
            self._output_sweep_filename = None
            self._input_spot_filename = "strong.refl"
            self._scan_ranges = []
            self._nspots = 0
            self._min_spot_size = None
            self._min_local = None
            self._kernel_size = None
            self._global_threshold = None
            self._threshold_algorithm = None
            self._sigma_strong = None
            self._filter_ice_rings = False
            self._phil_file = None
            self._write_hot_mask = False
            self._hot_mask_prefix = None
            self._gain = None

        def set_input_sweep_filename(self, sweep_filename):
            self._input_sweep_filename = sweep_filename

        def set_output_sweep_filename(self, sweep_filename):
            self._output_sweep_filename = sweep_filename

        def set_write_hot_mask(self, write_hot_mask=True):
            self._write_hot_mask = write_hot_mask

        def set_hot_mask_prefix(self, hot_mask_prefix):
            self._hot_mask_prefix = hot_mask_prefix

        def get_output_sweep_filename(self):
            return self._output_sweep_filename

        def set_input_spot_filename(self, spot_filename):
            self._input_spot_filename = spot_filename

        def get_spot_filename(self):
            return os.path.join(self.get_working_directory(), self._input_spot_filename)

        def set_scan_ranges(self, scan_ranges):
            self._scan_ranges = scan_ranges

        def add_scan_range(self, scan_range):
            self._scan_ranges.append(scan_range)

        def set_phil_file(self, phil_file):
            self._phil_file = phil_file

        def set_min_spot_size(self, min_spot_size):
            self._min_spot_size = int(min_spot_size)

        def set_min_local(self, min_local):
            self._min_local = int(min_local)

        def set_kernel_size(self, kernel_size):
            self._kernel_size = int(kernel_size)

        def set_global_threshold(self, global_threshold):
            self._global_threshold = global_threshold

        def set_threshold_algorithm(self, threshold_algorithm):
            self._threshold_algorithm = threshold_algorithm

        def set_sigma_strong(self, sigma_strong):
            self._sigma_strong = sigma_strong

        def set_filter_ice_rings(self, filter_ice_rings):
            self._filter_ice_rings = filter_ice_rings

        def set_gain(self, gain):
            self._gain = gain

        def run(self):
            logger.debug("Running dials.find_spots")

            self.clear_command_line()
            self.add_command_line("input.experiments=%s" % self._input_sweep_filename)
            if self._output_sweep_filename is not None:
                self.add_command_line(
                    "output.experiments=%s" % self._output_sweep_filename
                )
            self.add_command_line("output.reflections=%s" % self._input_spot_filename)
            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            njob = PhilIndex.params.xia2.settings.multiprocessing.njob
            mp_mode = PhilIndex.params.xia2.settings.multiprocessing.mode
            mp_type = PhilIndex.params.xia2.settings.multiprocessing.type
            self.set_cpu_threads(nproc)
            self.add_command_line("nproc=%i" % nproc)
            if mp_mode == "serial" and mp_type == "qsub" and njob > 1:
                self.add_command_line("mp.method=drmaa")
                self.add_command_line("mp.njobs=%i" % njob)
            for scan_range in self._scan_ranges:
                self.add_command_line("spotfinder.scan_range=%d,%d" % scan_range)
            if self._min_spot_size is not None:
                self.add_command_line("min_spot_size=%i" % self._min_spot_size)
            if self._min_local is not None:
                self.add_command_line("dispersion.min_local=%i" % self._min_local)
            if self._kernel_size is not None:
                self.add_command_line(
                    "dispersion.kernel_size=%i %i"
                    % (self._kernel_size, self._kernel_size)
                )
            if self._global_threshold is not None:
                self.add_command_line(
                    "dispersion.global_threshold=%s" % self._global_threshold
                )
            if self._threshold_algorithm is not None:
                self.add_command_line(
                    "threshold.algorithm=%s" % self._threshold_algorithm
                )
            if self._sigma_strong is not None:
                self.add_command_line("dispersion.sigma_strong=%i" % self._sigma_strong)
            if self._filter_ice_rings:
                self.add_command_line("ice_rings.filter=%s" % self._filter_ice_rings)
            if self._phil_file is not None:
                self.add_command_line(self._phil_file)
            if self._write_hot_mask:
                self.add_command_line("write_hot_mask=true")
            if self._hot_mask_prefix:
                self.add_command_line("hot_mask_prefix=%s" % self._hot_mask_prefix)
            if self._gain:
                self.add_command_line("gain=%f" % self._gain)
            self.start()
            self.close_wait()
            self.check_for_errors()

            for record in self.get_all_output():
                if record.startswith("Saved") and "reflections to" in record:
                    self._nspots = int(record.split()[1])

    return SpotfinderWrapper()

import logging
import os

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.XIA.EstimateResolution")


def EstimateResolution(DriverType=None):
    """A factory for EstimateResolutionWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class EstimateResolutionWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.estimate_resolution")

            # inputs
            self._hklin = None
            self._reflections = None
            self._experiments = None
            self._limit_rmerge = None
            self._limit_completeness = None
            self._limit_cc_half = None
            self._cc_half_fit = None
            self._cc_half_significance_level = None
            self._limit_isigma = None
            self._limit_misigma = None
            self._nbins = 100
            self._batch_range = None
            self._labels = None

            # outputs
            self._resolution_rmerge = None
            self._resolution_completeness = None
            self._resolution_cc_half = None
            self._resolution_isigma = None
            self._resolution_misigma = None
            self._html = None
            self._json = None

        def set_reflections(self, filename):
            self._reflections = filename

        def set_experiments(self, filename):
            self._experiments = filename

        def set_hklin(self, hklin):
            self._hklin = hklin

        def set_nbins(self, nbins):
            self._nbins = nbins

        def set_limit_rmerge(self, limit_rmerge):
            self._limit_rmerge = limit_rmerge

        def set_limit_completeness(self, limit_completeness):
            self._limit_completeness = limit_completeness

        def set_limit_cc_half(self, limit_cc_half):
            self._limit_cc_half = limit_cc_half

        def set_cc_half_fit(self, cc_half_fit):
            self._cc_half_fit = cc_half_fit

        def set_cc_half_significance_level(self, cc_half_significance_level):
            self._cc_half_significance_level = cc_half_significance_level

        def set_limit_isigma(self, limit_isigma):
            self._limit_isigma = limit_isigma

        def set_limit_misigma(self, limit_misigma):
            self._limit_misigma = limit_misigma

        def set_batch_range(self, start, end):
            self._batch_range = (start, end)

        def set_labels(self, labels):
            self._labels = labels

        def get_resolution_rmerge(self):
            return self._resolution_rmerge

        def get_resolution_completeness(self):
            return self._resolution_completeness

        def get_resolution_cc_half(self):
            return self._resolution_cc_half

        def get_resolution_isigma(self):
            return self._resolution_isigma

        def get_resolution_misigma(self):
            return self._resolution_misigma

        def get_html(self):
            return self._html

        def get_json(self):
            return self._json

        def run(self):
            assert self._hklin or (self._experiments and self._reflections)
            if self._hklin:
                cl = [self._hklin]
            else:
                cl = [self._experiments, self._reflections]
            cl.append("nbins=%s" % self._nbins)
            cl.append("rmerge=%s" % self._limit_rmerge)
            cl.append("completeness=%s" % self._limit_completeness)
            cl.append("cc_half=%s" % self._limit_cc_half)
            if self._cc_half_fit is not None:
                cl.append("cc_half_fit=%s" % self._cc_half_fit)
            cl.append(
                "cc_half_significance_level=%s" % self._cc_half_significance_level
            )
            cl.append("isigma=%s" % self._limit_isigma)
            cl.append("misigma=%s" % self._limit_misigma)
            if self._batch_range is not None:
                cl.append("batch_range=%i,%i" % self._batch_range)
            if self._labels is not None:
                cl.append("labels=%s" % self._labels)
            for c in cl:
                self.add_command_line(c)
            logger.debug("Resolution analysis: %s", " ".join(cl))

            self._html = os.path.join(
                self.get_working_directory(),
                "%d_dials.estimate_resolution.html" % self.get_xpid(),
            )
            self.add_command_line("output.html=%s" % self._html)

            self._json = os.path.join(
                self.get_working_directory(),
                "%d_dials.estimate_resolution.json" % self.get_xpid(),
            )
            self.add_command_line("output.json=%s" % self._json)

            self.start()
            self.close_wait()
            for record in self.get_all_output():
                if "Resolution rmerge" in record:
                    self._resolution_rmerge = float(record.split()[-1])
                if "Resolution completeness" in record:
                    self._resolution_completeness = float(record.split()[-1])
                if "Resolution cc_half" in record:
                    self._resolution_cc_half = float(record.split()[-1])
                if "Resolution I/sig" in record:
                    self._resolution_isigma = float(record.split()[-1])
                if "Resolution Mn(I/sig)" in record:
                    self._resolution_misigma = float(record.split()[-1])

    return EstimateResolutionWrapper()

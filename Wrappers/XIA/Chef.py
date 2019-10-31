#!/usr/bin/env python
# Chef.py
#   Copyright (C) 2008 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 5th February 2008
#
# A wrapper for the new program "chef". This has been developed for xia2
# to analyse the bulk properties of intensity measurements, particularly
# looking at how well they agree. The idea is that reflection files with
# DOSE columns added in by DOSER may be inspected to determine the
# dose / resolution envelope optimal for given analysis processes, viz:
#
# - substructure determination
# - phase calculation
# - density modification & refinement
#
# This should give "proper" resolution limits...

from __future__ import absolute_import, division, print_function

import math
import sys

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Experts.WedgeExpert import digest_wedges
from xia2.Handlers.Streams import Chatter, Stdout
from xia2.lib.bits import mean_sd, transpose_loggraph
from xia2.Wrappers.CCP4.Mtzdump import Mtzdump


def Chef(DriverType=None, stream=Chatter):
    """A factory for wrappers for the chef."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class ChefWrapper(CCP4DriverInstance.__class__):
        """Provide access to the functionality in chef."""

        def __init__(self):

            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable("pychef")

            self._hklin_list = []
            self._anomalous = False
            self._b_width = 0.0
            self._b_max = 0.0
            self._b_labin = None
            self._resolution = 0.0

            self._p_crd = True

            self._completeness = {}

            # this will be parsed from the Chef program output (which
            # reconstructs this) if available

            self._dose_profile = {}

            self._title = None

            self._stream = stream

            return

        def add_hklin(self, hklin):
            self._hklin_list.append(hklin)
            return

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous
            return

        def set_resolution(self, resolution):
            self._resolution = resolution
            return

        def set_width(self, width):
            self._b_width = width
            return

        def set_max(self, max):
            self._b_max = max
            return

        def set_labin(self, labin):
            self._b_labin = labin
            return

        def set_title(self, title):
            self._title = title
            return

        def get_completeness(self, wavelength):
            return self._completeness[wavelength]

        def get_completeness_datasets(self):
            return list(self._completeness.keys())

        def run(self):
            """Actually run chef..."""

            if not self._hklin_list:
                raise RuntimeError("HKLIN not defined")

            for j in range(len(self._hklin_list)):
                self.add_command_line("HKLIN%d" % (j + 1))
                self.add_command_line(self._hklin_list[j])

            self.start()

            # this is not needed for pychef
            # self.input('print scp comp')

            if self._anomalous:
                self.input("anomalous on")
            if self._b_width > 0.0:
                self.input("range width %f" % self._b_width)
            if self._b_max > 0.0:
                self.input("range max %f" % self._b_max)

            if self._resolution > 0.0:
                self.input("resolution %.2f" % self._resolution)

            if self._b_labin:
                self.input("labin BASE=%s" % self._b_labin)

            if self._title:
                self.input("title %s" % self._title)

            self.close_wait()

            # FIXME should check the status here...

            # read out the completeness curves...

            output = self.get_all_output()

            all_doses = []

            for j in range(len(output)):
                record = output[j]
                if "Completeness vs. BASELINE" in record:
                    dataset = record.split()[-1]
                    completeness = []
                    k = j + 2
                    record = output[k]
                    while not "Expected" in record and not "$TABLE" in record:
                        completeness.append(
                            (float(record.split()[0]), float(record.split()[-1]))
                        )
                        dose = float(record.split()[0])

                        if not dose in all_doses:
                            all_doses.append(dose)

                        k += 1
                        record = output[k]

                    self._completeness[dataset] = completeness

            # now jimmy these..

            for dataset in list(self._completeness.keys()):
                completeness = self._completeness[dataset]
                cmax = completeness[-1][1]
                cnew = []

                # hash this up
                ctable = {}
                for c in completeness:
                    ctable[c[0]] = c[1]

                for dose in all_doses:
                    if dose in ctable:
                        cnew.append((dose, ctable[dose]))
                    else:
                        cnew.append((dose, cmax))

                self._completeness[dataset] = cnew

                # at some point need to figure out how to analyse these
                # results...

            self.parse()

            return

        def digest_rd(self, values):
            """Digest the results of an Rd calculation, working on the
            assumptions that (i) the corresponding dose values are
            meaningless and (ii) we are trying to decide if there is a
            significant gradient there. N.B. does however assume that the
            dose increments are UNIFORM."""

            # FIXME in here, replace the crude comparison with sigma with a
            # distribution comparison - values about the mean, values about
            # a straight line fit: are they drawn from the same distribution.
            # If definately not then the hypothesis of some radiation damage
            # is suggested?

            sx = 0.0
            sy = 0.0

            n = 0

            for j, v in enumerate(values):

                if not v:
                    continue

                sx += j
                sy += v

                n += 1

            mx = sx / n
            my = sy / n

            sxx = 0.0
            sxy = 0.0

            for j, v in enumerate(values):

                if not v:
                    continue

                sxx += (j - mx) * (j - mx)
                sxy += (j - mx) * (v - my)

            if not sxx:
                return 0.0

            m = sxy / sxx
            c = my - m * mx

            # now calculate residual about this line

            ss = 0.0

            for j, v in enumerate(values):

                if not v:
                    continue

                _v = m * j + c

                ss += (v - _v) * (v - _v)

            sd = math.sqrt(ss / (n - 2))

            # then compute the standard deviation of the population

            var = 0.0

            for j, v in enumerate(values):

                if not v:
                    continue

                var += (v - my) * (v - my)

            sigma = math.sqrt(var / (n - 1))

            # return sigma / sd

            return (var / (sd * sd)) / n

        def parse(self):
            """Parse the output of the chef run."""

            results = self.parse_ccp4_loggraph()

            rd_keys = []
            comp_keys = []

            scp_data = None
            comp_data = {}
            rd_data = {}

            datasets_damaged = []

            for key in results:
                if "Completeness vs. " in key:
                    comp_keys.append(key)
                    comp_data[key.split()[-1]] = transpose_loggraph(results[key])

                elif "R vs. " in key:
                    rd_keys.append(key)
                    wavelength = key.split()[-1]
                    rd_data[wavelength] = transpose_loggraph(results[key])

                    values = map(float, rd_data[wavelength]["2_Rd"])
                    digest = self.digest_rd(values)

                    # stream.write('Rd score (%s): %.2f' % \
                    # (wavelength, digest))

                    if digest > 3:
                        datasets_damaged.append((wavelength, digest))

                elif "Normalised radiation" in key:
                    scp_data = transpose_loggraph(results[key])

                elif "Dose vs. BATCH" in key:
                    self._dose_profile = transpose_loggraph(results[key])

            # right, so first work through these to define the limits from
            # where the first set is 50% complete to 90% complete, which
            # will establish the benchmark, then calculate a kinda
            # Z-score for the subsequent Scp values

            lowest_50 = None
            lowest_90 = None

            i_col = "2_I"
            dose_col = "1_DOSE"

            for dataset in comp_data:

                if "5_dI" in comp_data[dataset]:
                    i_col = "4_I"

                if "1_BATCH" in comp_data[dataset]:
                    dose_col = "1_BATCH"

                completeness = comp_data[dataset][i_col]

                local_50 = None
                local_90 = None

                max_comp = max(map(float, completeness))

                for j, dose in enumerate(comp_data[dataset][dose_col]):

                    comp = float(completeness[j])

                    if comp > (0.5 * max_comp) and not local_50:
                        local_50 = float(dose)

                    if comp > (0.9 * max_comp) and not local_90:
                        local_90 = float(dose)

            # check if we have dose profile etc available

            stop_doses = []
            groups = []

            if self._dose_profile:
                wedges = sorted(self.digest_dose_profile())

                # given these and the completeness curves, need to make a
                # choice as to when to stop... will be necessary here
                # to have an indication of the logical wavelength to
                # which the measurements belong

                # wedges is a list of:
                # FIRST_DOSE FIRST_BATCH SIZE EXPOSURE DATASET

                # digest this as follows: if sweeps switch between
                # A and B, or A, B and C then these are tied wedges: aim
                # for uniform total rotation / number of images. if
                # there is the same data set in subsequent chunks,
                # these are tied inverse beams

                # ok, logic. expect at most four wavelengths interleaved,
                # most likely two or three. also assume that the sizes of
                # the wedges should be the same. only want to "block" these.

                # if len(wedges) == 1: can consider any point at which
                # to cut off the data.  N.B. don't forget EDNA strategies...

                # ok, easiest thing is encode a set of rules.

                stop_doses, groups = digest_wedges(wedges)

                for j, g in enumerate(groups):
                    stream.write("Group %d: %s" % (j + 1, g))

            if not lowest_50:
                lowest_50 = local_50
            if local_50 < lowest_50:
                lowest_50 = local_50

            if not lowest_90:
                lowest_90 = local_90
            if local_90 < lowest_90:
                lowest_90 = local_90

            # now build up the reference population

            scp_reference = []

            scp_key = None

            for k in scp_data:
                if "Scp(d)" in k:
                    scp_key = k

            for j, d in enumerate(scp_data[dose_col]):
                dose = float(d)
                if dose >= lowest_50 and dose <= lowest_90:
                    scp_reference.append(float(scp_data[scp_key][j]))

            m, s = mean_sd(scp_reference)

            dose = scp_data[dose_col][0]

            scp_max = 0.0

            if s == 0.0:
                stream.write("Insufficient measurements for analysis")
                return

            for j, d in enumerate(scp_data[dose_col]):

                dose = float(d)
                scp = float(scp_data[scp_key][j])
                z = (scp - m) / s

                if dose < lowest_90:
                    scp_max = max(scp, scp_max)
                    continue

                if z > 3 and scp > scp_max:
                    break

                scp_max = max(scp, scp_max)

            if not datasets_damaged:
                stream.write("No significant radiation damage detected")
                return

            if not groups:
                stop_dose = dose
            elif groups == ["Single wedge"]:
                stop_dose = dose
            else:
                for stop_dose in stop_doses:
                    if stop_dose > dose:
                        break

            stream.write("Significant radiation damage detected:")

            for wavelength, digest in datasets_damaged:
                stream.write("Rd analysis (%s): %.2f" % (wavelength, digest))

            if stop_dose == float(scp_data[dose_col][-1]):
                stream.write("Conclusion: use all data")
            else:
                stream.write(
                    "Conclusion: cut off after %s ~ %.1f"
                    % (dose_col.replace("1_", ""), stop_dose)
                )

            return

        def digest_dose_profile(self):
            """Digest the dose profile to list a range of points where
            we could consider stopping the data collection."""

            # N.B. in the first pass this may not make proper acknowledgement
            # of the wedged structure of the data collection!

            dose_batch = {}
            batch_dose = {}
            batch_dataset = {}

            for j, b in enumerate(self._dose_profile["1_BATCH"]):

                b = int(b)
                d = float(self._dose_profile["2_DOSE"][j])
                ds = self._dose_profile["3_DATASET"][j]

                dose_batch[d] = b
                batch_dose[b] = d
                batch_dataset[b] = ds

            doses = sorted(dose_batch)

            is_monotonic = True

            first_batch = dose_batch[doses[0]]

            start_batches = [first_batch]
            current = first_batch
            wedge_sizes = {first_batch: 1}
            wedge_datasets = {first_batch: batch_dataset[first_batch]}

            for d in doses[1:]:

                b = dose_batch[d]

                if b < first_batch:
                    current = b
                    start_batches.append(current)
                    wedge_sizes[current] = 0
                    wedge_datasets[current] = batch_dataset[current]
                    is_monotonic = False

                if b > first_batch + 1:

                    current = b
                    start_batches.append(current)
                    wedge_sizes[current] = 0
                    wedge_datasets[current] = batch_dataset[current]

                first_batch = b
                wedge_sizes[current] += 1

            result = []

            start_batches.sort()

            for batch in start_batches:

                if not (batch + 1) in batch_dose:
                    continue

                exposure = batch_dose[batch + 1] - batch_dose[batch]
                result.append(
                    (
                        batch_dose[batch],
                        batch,
                        wedge_sizes[batch],
                        exposure,
                        wedge_datasets[batch],
                    )
                )

            return result

    return ChefWrapper()


if __name__ == "__main__":

    # ok, in here (which will be "autoCHEF") this will inspect the MTZ
    # file and run with DOSE if such a column exists, else will run with
    # BATCH. N.B. this will require a fix above.

    chef = Chef(stream=Stdout)

    dose_column = None

    overall_dmin = None

    for argv in sys.argv[1:]:

        md = Mtzdump()
        md.set_hklin(argv)
        md.dump()

        columns = [c[0] for c in md.get_columns()]

        if dose_column:
            assert dose_column in columns
            continue

        if "DOSE" in columns:

            dose_range = md.get_column_range("DOSE")[:2]
            if dose_range[0] != dose_range[1]:
                dose_column = "DOSE"

        if "BATCH" in columns and not dose_column:
            dose_column = "BATCH"

        if not dose_column:
            raise RuntimeError("no DOSE/BATCH column found")

        dmin = min(md.get_resolution_range())

        if overall_dmin is None:
            overall_dmin = dmin
        if dmin > overall_dmin:
            overall_dmin = dmin

    Stdout.write("Selected column: %s" % dose_column)

    for argv in sys.argv[1:]:

        chef.add_hklin(argv)
        chef.set_labin(dose_column)

    chef.set_resolution(overall_dmin)
    chef.write_log_file("chef.log")
    chef.set_anomalous(True)
    chef.run()

#!/usr/bin/env cctbx.python
# PyChef.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A reimplementation of the FORTRAN program CHEF (Winter, PhD thesis)
# into Python, using the CCTBX library. The idea is to analyse scaled
# intensity measurements as a function of cumulative dose, to assess the
# impact of radiation damage.
#

from __future__ import absolute_import, division

import math
import time

from iotbx import mtz
from xia2.Modules.PyChef.PyChefHelpers import (compute_unique_reflections,
                                               get_mtz_column_list)

class PyChef(object):
  '''The main PyChef class.'''

  def __init__(self):

    # assuming that we will be using BATCH by default... unless there is a
    # column named DOSE

    self._base_column = 'BATCH'
    self._base_unique = False

    self._hklin_list = []

    self._reflections = { }
    self._unit_cells = { }
    self._space_groups = { }

    self._range_min = None
    self._range_max = None
    self._range_width = None

    # Dose / batch information for reporting purposes

    self._dose_information = { }

    self._resolution_high = None
    self._resolution_low = None

    self._resolution_bins = 8

    self._anomalous = False

    self._title = None

    self._ncpu = 1

    return

  def set_base_column(self, base_column):
    '''Set the baseline for analysis: note well that this should
    be called before add_hklin, so that add_hklin can check that
    this column is present.'''

    self._base_column = base_column

    return

  def set_base_unique(self, base_unique=True):
    self._base_unique = base_unique
    return

  def add_hklin(self, hklin):
    '''Add a reflection file to the list for analysis... '''

    columns = get_mtz_column_list(hklin)

    assert(self._base_column in columns)

    self._hklin_list.append(hklin)

    return

  def set_range(self, range_min, range_max, range_width):
    '''Set the range of e.g. dose to consider for analysis, with
    binning width set.'''

    assert(range_max > range_min)
    assert(range_max - range_min > range_width)

    self._range_min = range_min
    self._range_max = range_max
    self._range_width = range_width

    return

  def set_resolution(self, resolution_high, resolution_low = None):
    '''Set the resolution range for analysis.'''

    self._resolution_high = resolution_high

    if resolution_low:
      assert(resolution_low > resolution_high)
      self._resolution_low = resolution_low

    return

  def set_anomalous(self, anomalous):
    '''Set the separation of anomalous pairs on or off.'''

    self._anomalous = anomalous
    return

  def set_title(self, title):
    self._title = title
    return

  def set_ncpu(self, ncpu):
    '''Set the number of cpus to be used for parallel processing.'''
    self._ncpu = ncpu
    return

  def init(self):
    '''Initialise the program - this will read all of the reflections
    and so on into memory and set up things like the unit cell objects.'''

    symmetry = None

    overall_dmin = None
    overall_dmax = None

    overall_range_min = None
    overall_range_max = None
    overall_range_width = None

    for hklin in self._hklin_list:

      mtz_obj = mtz.object(hklin)

      mi = mtz_obj.extract_miller_indices()
      dmax, dmin = mtz_obj.max_min_resolution()

      if overall_dmin is None:
        overall_dmin = dmin
      else:
        if dmin > overall_dmin:
          overall_dmin = dmin

      if overall_dmax is None:
        overall_dmax = dmax
      else:
        if dmax < overall_dmax:
          overall_dmax = dmax

      crystal_name = None
      dataset_name = None
      nref = 0
      uc = None

      # chef does not care about systematic absences from e.g.
      # screw axes => patterson group not space group. No,
      # patterson group is always centric?!

      sg = mtz_obj.space_group()

      # .build_derived_patterson_group()

      if not symmetry:
        symmetry = sg
      else:
        assert(symmetry == sg)

      # now have a rummage through to get the columns out that I want

      base_column = None
      misym_column = None
      i_column = None
      sigi_column = None

      batch_column = None
      dose_column = None

      for crystal in mtz_obj.crystals():

        for dataset in crystal.datasets():
          if dataset.name() != 'HKL_base':
            dataset_name = dataset.name()

        if crystal.name() != 'HKL_base':
          crystal_name = crystal.name()

        uc = crystal.unit_cell()

        for dataset in crystal.datasets():

          for column in dataset.columns():

            # for recording purposes for the BATCH / DOSE
            # mapping...

            if column.label() == 'BATCH':
              batch_column = column
            elif column.label() == 'DOSE':
              dose_column = column

            if column.label() == self._base_column:
              base_column = column
            if column.label() == 'M_ISYM':
              misym_column = column
            if column.label() == 'I':
              i_column = column
            if column.label() == 'SIGI':
              sigi_column = column

      assert(base_column is not None)
      assert(misym_column is not None)
      assert(i_column is not None)
      assert(sigi_column is not None)

      if batch_column and dose_column:

        # read, accumulate the dose information - assume that these
        # are correctly structured as per xia2 handling...

        batch_values = batch_column.extract_values(
            not_a_number_substitute = 0.0)
        dose_values = dose_column.extract_values(
            not_a_number_substitute = 0.0)

        assert(len(batch_values) == len(dose_values))

        if min(dose_values) != max(dose_values):

          for j in range(len(batch_values)):
            batch = int(round(batch_values[j]))
            dose = dose_values[j]

            if not batch in self._dose_information:
              self._dose_information[batch] = dose, dataset_name

      print 'Reading in data from %s/%s' % (crystal_name, dataset_name)
      print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
            tuple(uc.parameters())
      print 'Spacegroup: %s' % sg.type(
          ).universal_hermann_mauguin_symbol()
      if self._base_unique:
        print 'Using: %s/%s/%s (unique)' % \
              (i_column.label(), sigi_column.label(), base_column.label())
      else:
        print 'Using: %s/%s/%s' % \
              (i_column.label(), sigi_column.label(), base_column.label())

      if base_column == batch_column and self._base_unique:
        from scitbx.array_family import flex
        batch_values = batch_column.extract_values(
          not_a_number_substitute = 0.0)
        batches = list(set(batch_values))
        lookup = { }
        for j, b in enumerate(sorted(batches)):
          lookup[b] = j
        base_values = flex.double(len(batch_values))
        for j in range(len(batch_values)):
          base_values[j] = lookup[batch_values[j]]

        if not self._range_width:
          self._range_width = 1

      else:
        base_values = base_column.extract_values(
          not_a_number_substitute = 0.0)

      min_base = min(base_values)
      max_base = max(base_values)

      if not self._range_width:
        bases = sorted(set(base_values))
        mean_shift = sum([bases[j + 1] - bases[j] for j in \
                          range(len(bases) - 1)]) / (len(bases) - 1)

        if overall_range_width is None:
          overall_range_width = mean_shift
        if mean_shift < overall_range_width:
          overall_range_width = mean_shift

      if overall_range_min is None:
        overall_range_min = min_base
      else:
        if min_base < overall_range_min:
          overall_range_min = min_base

      if overall_range_max is None:
        overall_range_max = max_base
      else:
        if max_base > overall_range_max:
          overall_range_max = max_base

      misym_values = misym_column.extract_values(
          not_a_number_substitute = 0.0)

      i_values = i_column.extract_values(
          not_a_number_substitute = 0.0)
      i_values_valid = i_column.selection_valid()

      sigi_values = sigi_column.extract_values(
          not_a_number_substitute = 0.0)
      sigi_values_valid = sigi_column.selection_valid()

      reflections = { }

      for j in range(mi.size()):

        if not i_values_valid[j]:
          continue

        if not sigi_values_valid[j]:
          continue

        h, k, l = mi[j]
        base = base_values[j]
        misym = misym_values[j]
        i = i_values[j]
        sigi = sigi_values[j]

        # test whether this is within the range of interest

        if self._range_min is not None:
          if base < self._range_min:
            continue

        if self._range_max is not None:
          if base > self._range_max:
            continue

        if self._resolution_high:
          if uc.d([h, k, l]) < self._resolution_high:
            continue

        if self._resolution_low:
          if uc.d([h, k, l]) > self._resolution_low:
            continue

        if self._anomalous:
          pm = int(round(misym)) % 2
        else:
          pm = 0

        if not (h, k, l) in reflections:
          reflections[(h, k, l)] = []

        reflections[(h, k, l)].append((pm, base, i, sigi))

      # ok, copy the reflections to the class for future analysis

      self._reflections[(crystal_name, dataset_name)] = reflections
      self._unit_cells[(crystal_name, dataset_name)] = uc
      self._space_groups[(crystal_name, dataset_name)] = sg

    if not self._resolution_low:
      print 'Assigning low resolution limit: %.2f' % overall_dmax
      self._resolution_low = overall_dmax

    if not self._resolution_high:
      print 'Assigning high resolution limit: %.2f' % overall_dmin
      self._resolution_high = overall_dmin

    if not self._range_width:
      print 'Assigning baseline width:   %.2f' % \
            overall_range_width
      self._range_width = overall_range_width

    if not self._range_min:
      print 'Assigning baseline minimum: %.2f' % \
            (overall_range_min - self._range_width)
      self._range_min = overall_range_min - self._range_width

    if not self._range_max:
      print 'Assigning baseline maximum: %.2f' % \
            overall_range_max
      self._range_max = overall_range_max

    # if > 1 data set assume that this is anomalous data...

    if len(self._reflections) > 1:
      print 'More than one data set: assume anomalous'
      self._anomalous = True

    # FIXME add warning if measurements don't reach the edge...

    return

  def print_completeness_vs_dose(self):
    '''Print the completeness vs. dose for each input reflection file.
    This will need to read the MTZ file, get the dataset cell constants
    and space group, compute the expected number of reflections, then
    as a function of dose compute what fraction of these are measured.
    For native data this is going to simply write out:

    dose, fraction

    but for MAD data it will need to print out:

    dose, fractionI+, fractionI-, fractionI, fractionI+andI-

    would be nice to have this described a little tidier.'''

    for crystal_name, dataset_name in sorted(self._reflections):

      reflections = self._reflections[(crystal_name, dataset_name)]
      uc = self._unit_cells[(crystal_name, dataset_name)]
      sg = self._space_groups[(crystal_name, dataset_name)]

      nref = len(compute_unique_reflections(uc, sg, self._anomalous,
                                            self._resolution_high,
                                            self._resolution_low))

      nref_n = len(compute_unique_reflections(uc, sg, False,
                                              self._resolution_high,
                                              self._resolution_low))

      print 'Cumulative completeness analysis for %s/%s' % \
            (crystal_name, dataset_name)
      print 'Expecting %d reflections' % nref

      # Right, in here I need to get the lowest dose for a given
      # h, k, l and then add this reflection for completeness to all
      # high dose bins, as it is measured already. So, if it is
      #
      # centric and anomalous, add to I+ and I-
      # centric and not anomalous, add to I
      # acentric and anomalous, add to I+ or I-
      # acentric and not anomalous, add to I
      #
      # To do this the best thing to do is to read through all of the
      # reflections and keep a dictionary of the lowest dose at which
      # a given reflection was recorded. Then iterate through this
      # list to see how many we have as a function of dose...
      #
      # Ok, so after trying to implement this cleanly I think that the
      # only way to do this is to actually read all of the reflections
      # in and store them in e.g. a dictionary. Could be expensive
      # for large data sets, but worry about that ... later. Can at
      # least store this in-memory representation. Accordingly will also
      # need to read in the 'I' column...

      # this will be a dictionary indexed by the Miller indices and
      # containing anomalous flag (1: I+, 0:I- or native) baseline
      # intensity values and the error estimate..

      # now construct the completeness tables for I or I+ & I-,
      # then populate from this list of lowest doses...

      if self._anomalous:

        print '$TABLE : Completeness vs. %s, %s/%s:' % \
              (self._base_column, crystal_name, dataset_name)
        print '$GRAPHS: Completeness:N:1,2,3,4,5: $$'
        print '%8s %5s %5s %5s %5s $$ $$' % \
              (self._base_column, 'I+', 'I-', 'I', 'dI')

        iplus_count = []
        iminus_count = []
        ieither_count = []
        iboth_count = []

        nsteps = 1 + int(
            (self._range_max - self._range_min) / self._range_width)

        for j in range(nsteps):
          iplus_count.append(0)
          iminus_count.append(0)
          ieither_count.append(0)
          iboth_count.append(0)

        for h, k, l in reflections:
          base_min_iplus = self._range_max + self._range_width
          base_min_iminus = self._range_max + self._range_width

          for pm, base, i, sigi in reflections[(h, k, l)]:
            if sg.is_centric((h, k, l)):
              if base < base_min_iplus:
                base_min_iplus = base
              if base < base_min_iminus:
                base_min_iminus = base
            elif pm:
              if base < base_min_iplus:
                base_min_iplus = base
            else:
              if base < base_min_iminus:
                base_min_iminus = base

          start_iplus = int((base_min_iplus - self._range_min)
                            / self._range_width)

          start_iminus = int((base_min_iminus - self._range_min)
                            / self._range_width)

          if start_iplus < nsteps:
            iplus_count[start_iplus] += 1
          if start_iminus < nsteps:
            iminus_count[start_iminus] += 1
          if min(start_iplus, start_iminus) < nsteps:
            ieither_count[min(start_iplus, start_iminus)] += 1
          if max(start_iplus, start_iminus) < nsteps:
            iboth_count[max(start_iplus, start_iminus)] += 1

        # now sum up

        for j in range(1, nsteps):
          iplus_count[j] += iplus_count[j - 1]
          iminus_count[j] += iminus_count[j - 1]
          ieither_count[j] += ieither_count[j - 1]
          iboth_count[j] += iboth_count[j - 1]

        for j in range(nsteps):
          iplus = iplus_count[j] / float(nref_n)
          iminus = iminus_count[j] / float(nref_n)
          ieither = ieither_count[j] / float(nref_n)
          iboth = iboth_count[j] / float(nref_n)

          print '%8.1f %5.3f %5.3f %5.3f %5.3f' % \
                (self._range_min + j * self._range_width,
                 iplus, iminus, ieither, iboth)

        print '$$'

      else:

        print '$TABLE : Completeness vs. %s, %s/%s:' % \
              (self._base_column, crystal_name, dataset_name)
        print '$GRAPHS: Completeness:N:1, 2: $$'
        print '%8s %5s $$ $$' % (self._base_column, 'I')

        i_count = []

        nsteps = 1 + int(
            (self._range_max - self._range_min) / self._range_width)

        for j in range(nsteps):
          i_count.append(0)

        for h, k, l in reflections:
          base_min = self._range_max + self._range_width

          for pm, base, i, sigi in reflections[(h, k, l)]:
            if base < base_min:
              base_min = base

          start = int((base_min - self._range_min)
                      / self._range_width)

          # for j in range(start, nsteps):
          i_count[start] += 1

        for j in range(1, nsteps):
          i_count[j] += i_count[j - 1]

        for j in range(nsteps):
          i = i_count[j] / float(nref)

          print '%8.1f %5.3f' % \
                (self._range_min + j * self._range_width, i)

        print '$$'

    return

  def rd(self):
    '''Calculate Rd (Diederichs, 2006) for the data in the individual
    wavelengths. This will obviously result in one plot for each of the
    input data sets.'''

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    for crystal_name, dataset_name in sorted(self._reflections):

      rd_top = [0.0 for j in range(nsteps)]
      rd_bottom = [0.0 for j in range(nsteps)]

      reflections = self._reflections[(crystal_name, dataset_name)]

      if self._anomalous:

        for hkl in reflections:

          observations = self._reflections[
              (crystal_name, dataset_name)][hkl]

          iplus = []
          iminus = []

          for pm, base, i, sigi in observations:
            if pm:
              iplus.append((base, i, sigi))
            else:
              iminus.append((base, i, sigi))

          for n, (base, i, sigi) in enumerate(iplus):
            for _base, _i, _sigi in iplus[n + 1:]:
              d = int(round(math.fabs(base - _base) /
                            self._range_width))
              rd_top[d] += math.fabs(i - _i)
              rd_bottom[d] += 0.5 * (i + _i)

          for n, (base, i, sigi) in enumerate(iminus):
            for _base, _i, _sigi in iminus[n + 1:]:
              d = int(round(math.fabs(base - _base) /
                            self._range_width))
              rd_top[d] += math.fabs(i - _i)
              rd_bottom[d] += 0.5 * (i + _i)

      else:

        for hkl in reflections:

          observations = self._reflections[
              (crystal_name, dataset_name)][hkl]


          for n, (pm, base, i, sigi) in enumerate(observations):
            for _pm, _base, _i, _sigi in observations[n + 1:]:
              d = int(round(math.fabs(base - _base) /
                            self._range_width))
              rd_top[d] += math.fabs(i - _i)
              rd_bottom[d] += 0.5 * (i + _i)

      # print the report...

      print '$TABLE : R vs. %s difference, %s/%s:' % \
            (self._base_column, crystal_name, dataset_name)
      print '$GRAPHS: Rd:N:1, 2: $$'
      print '%8s %5s $$ $$' % (self._base_column, 'Rd')

      for j in range(nsteps):
        d = self._range_width * j
        if rd_bottom[j]:
          r = rd_top[j] / rd_bottom[j]
        else:
          r = 0.0
        print '%8.1f %5.3f' % (d, r)

      print '$$'

    return

  def scp(self):
    '''Perform the scp = rcp / ercp calculation as a function of
    assumulated dose across a number of resolution bins, from
    measurements already cached in memory.'''

    rcp_top = { }
    rcp_bottom = { }
    isigma = { }
    count = { }

    if self._resolution_low:
      smin = 1.0 / (self._resolution_low * self._resolution_low)
    else:
      smin = 0.0

    smax = 1.0 / (self._resolution_high * self._resolution_high)

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    # lay out the storage

    for j in range(self._resolution_bins + 1):

      rcp_top[j] = []
      rcp_bottom[j] = []
      isigma[j] = []
      count[j] = []

      for k in range(nsteps):
        rcp_top[j].append(0.0)
        rcp_bottom[j].append(0.0)
        isigma[j].append(0.0)
        count[j].append(0)

    # then populate

    for xname, dname in sorted(self._reflections):

      print 'Accumulating from %s %s' % (xname, dname)

      for h, k, l in self._reflections[(xname, dname)]:

        d = self._unit_cells[(xname, dname)].d([h, k, l])

        s = 1.0 / (d * d)

        bin = int(self._resolution_bins * (s - smin) / (smax - smin))

        observations = self._reflections[(xname, dname)][(h, k, l)]

        iplus = []
        iminus = []

        for pm, base, i, sigi in observations:
          if pm:
            iplus.append((base, i, sigi))
          else:
            iminus.append((base, i, sigi))

        # compute contributions

        for n, (base, i, sigi) in enumerate(iplus):

          for _base, _i, _sigi in iplus[n + 1:]:
            start = int((max(base, _base) - self._range_min) /
                        self._range_width)

            ra = math.fabs(i - _i)
            rb = 0.5 * (i + _i)

            rcp_top[bin][start] += ra
            rcp_bottom[bin][start] += rb

            isigma[bin][start] += (i / sigi) + (_i / _sigi)
            count[bin][start] += 2

        for n, (base, i, sigi) in enumerate(iminus):

          for _base, _i, _sigi in iminus[n + 1:]:
            start = int((max(base, _base) - self._range_min) /
                        self._range_width)

            ra = math.fabs(i - _i)
            rb = 0.5 * (i + _i)

            rcp_top[bin][start] += ra
            rcp_bottom[bin][start] += rb

            isigma[bin][start] += (i / sigi) + (_i / _sigi)
            count[bin][start] += 2

    # now accumulate as a funtion of time...

    for k in range(self._resolution_bins):
      for j in range(1, nsteps):
        rcp_top[k][j] += rcp_top[k][j - 1]
        rcp_bottom[k][j] += rcp_bottom[k][j - 1]
        isigma[k][j] += isigma[k][j - 1]
        count[k][j] += count[k][j - 1]

    # now digest the results - as a function of dose and resolution...

    if self._title:
      print '$TABLE : Normalised radiation damage analysis (%s):' % \
            self._title

    else:
      print '$TABLE : Normalised radiation damage analysis:'

    print '$GRAPHS: Scp(d):N:1,%d: $$' % (self._resolution_bins + 2)

    columns = ''
    for j in range(self._resolution_bins):
      columns += ' S%d' % j

    print '%s %s Scp(d) $$ $$' % (self._base_column, columns)
    format = '%8.1f %6.4f'
    for k in range(self._resolution_bins):
      format += ' %6.4f'

    for j in range(nsteps):
      base = j * self._range_width + self._range_min
      values = [base]

      for k in range(self._resolution_bins):

        if rcp_bottom[k][j] and count[k][j] > 100:
          rcp = rcp_top[k][j] / rcp_bottom[k][j]
          isig = isigma[k][j] / count[k][j]
          scp = rcp / (1.1284 / isig)
        else:
          scp = 0.0
          rcp = 0.0
          isig = 0.0

        values.append(scp)

      values.append((sum(values[1:]) / self._resolution_bins))

      print format % tuple(values)

    print '$$'

    return

  def rcp(self):
    '''Perform the rcp calculation as a function of
    assumulated dose across a number of resolution bins, from
    measurements already cached in memory.'''

    rcp_top = { }
    rcp_bottom = { }

    if self._resolution_low:
      smin = 1.0 / (self._resolution_low * self._resolution_low)
    else:
      smin = 0.0

    smax = 1.0 / (self._resolution_high * self._resolution_high)

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    # lay out the storage

    for j in range(self._resolution_bins + 1):

      rcp_top[j] = []
      rcp_bottom[j] = []

      for k in range(nsteps):
        rcp_top[j].append(0.0)
        rcp_bottom[j].append(0.0)

    # then populate

    for xname, dname in sorted(self._reflections):

      print 'Accumulating from %s %s' % (xname, dname)

      for h, k, l in self._reflections[(xname, dname)]:

        d = self._unit_cells[(xname, dname)].d([h, k, l])

        s = 1.0 / (d * d)

        bin = int(self._resolution_bins * (s - smin) / (smax - smin))

        observations = self._reflections[(xname, dname)][(h, k, l)]

        iplus = []
        iminus = []

        for pm, base, i, sigi in observations:
          if pm:
            iplus.append((base, i, sigi))
          else:
            iminus.append((base, i, sigi))

        # compute contributions

        for n, (base, i, sigi) in enumerate(iplus):

          for _base, _i, _sigi in iplus[n + 1:]:
            start = int((max(base, _base) - self._range_min) /
                        self._range_width)

            ra = math.fabs(i - _i)
            rb = 0.5 * (i + _i)

            rcp_top[bin][start] += ra
            rcp_bottom[bin][start] += rb

        for n, (base, i, sigi) in enumerate(iminus):

          for _base, _i, _sigi in iminus[n + 1:]:
            start = int((max(base, _base) - self._range_min) /
                        self._range_width)

            ra = math.fabs(i - _i)
            rb = 0.5 * (i + _i)

            rcp_top[bin][start] += ra
            rcp_bottom[bin][start] += rb

    # now accumulate as a funtion of time...

    for k in range(self._resolution_bins):
      for j in range(1, nsteps):
        rcp_top[k][j] += rcp_top[k][j - 1]
        rcp_bottom[k][j] += rcp_bottom[k][j - 1]

    # now digest the results - as a function of dose and resolution...

    if self._title:
      print '$TABLE : Cumulative radiation damage analysis (%s):' % \
            self._title

    else:
      print '$TABLE : Cumulative radiation damage analysis:'

    print '$GRAPHS: Rcp(d):N:1,%d: $$' % (self._resolution_bins + 2)

    columns = ''
    for j in range(self._resolution_bins):
      columns += ' S%d' % j

    print '%s %s Rcp(d) $$ $$' % (self._base_column, columns)
    format = '%8.1f %6.4f'
    for k in range(self._resolution_bins):
      format += ' %6.4f'

    for j in range(nsteps):
      base = j * self._range_width + self._range_min
      values = [base]

      for k in range(self._resolution_bins):

        if rcp_bottom[k][j]:
          rcp = rcp_top[k][j] / rcp_bottom[k][j]
        else:
          rcp = 0.0

        values.append(rcp)

      ot = sum([rcp_top[k][j] for k in range(self._resolution_bins)])
      ob = sum([rcp_bottom[k][j] for k in range(self._resolution_bins)])

      if ob:
        overall = ot / ob
      else:
        overall = 0.0

      values.append(overall)

      print format % tuple(values)

    print '$$'

    return

  def print_dose_profile(self):

    if not self._dose_information:
      return

    print '$TABLE: Dose vs. BATCH:'
    print '$GRAPHS: Dose Profile:N:1,2: $$'
    print 'BATCH DOSE DATASET $$ $$'

    for j in sorted(self._dose_information):
      d, n = self._dose_information[j]
      print '%d %f %s' % (j, d, n)

    print '$$'

    return

  # threaded functions to improve speed of above calculations

  def calculate_completeness_vs_dose_anomalous(self, reflections, hkls):
    '''Compute arrays of number vs. dose for anomalous data for
    these named reflections.'''

    iplus_count = []
    iminus_count = []
    ieither_count = []
    iboth_count = []

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    for j in range(nsteps):
      iplus_count.append(0)
      iminus_count.append(0)
      ieither_count.append(0)
      iboth_count.append(0)

    for hkl in hkls:
      base_min_iplus = self._range_max + self._range_width
      base_min_iminus = self._range_max + self._range_width

      for pm, base, i, sigi in reflections[hkl]:
        if sg.is_centric(hkl):
          if base < base_min_iplus:
            base_min_iplus = base
          if base < base_min_iminus:
            base_min_iminus = base
        elif pm:
          if base < base_min_iplus:
            base_min_iplus = base
        else:
          if base < base_min_iminus:
            base_min_iminus = base

      start_iplus = int((base_min_iplus - self._range_min)
                        / self._range_width)

      start_iminus = int((base_min_iminus - self._range_min)
                         / self._range_width)

      if start_iplus < nsteps:
        iplus_count[start_iplus] += 1
      if start_iminus < nsteps:
        iminus_count[start_iminus] += 1
      if min(start_iplus, start_iminus) < nsteps:
        ieither_count[min(start_iplus, start_iminus)] += 1
      if max(start_iplus, start_iminus) < nsteps:
        iboth_count[max(start_iplus, start_iminus)] += 1

    for j in range(1, nsteps):
      iplus_count[j] += iplus_count[j - 1]
      iminus_count[j] += iminus_count[j - 1]
      ieither_count[j] += ieither_count[j - 1]
      iboth_count[j] += iboth_count[j - 1]

    return iplus_count, iminus_count, iboth_count, ieither_count

  def parallel_calculate_completeness_vs_dose_anomalous(self, reflections):
    '''Compute arrays of completeness vs. dose for anomalous data for
    these reflections. This version will split the reflections into
    different chunks and accumulate afterwards.'''

    uc = self._unit_cells[(crystal_name, dataset_name)]
    sg = self._space_groups[(crystal_name, dataset_name)]

    nref = len(compute_unique_reflections(uc, sg, self._anomalous,
                                          self._resolution_high,
                                          self._resolution_low))

    nref_n = len(compute_unique_reflections(uc, sg, False,
                                            self._resolution_high,
                                            self._resolution_low))

    iplus_count = []
    iminus_count = []
    ieither_count = []
    iboth_count = []

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    for j in range(nsteps):
      iplus_count.append(0)
      iminus_count.append(0)
      ieither_count.append(0)
      iboth_count.append(0)

    hkls = list(reflections)

    chunk_size = len(hkls) / self._ncpu

    chunks = [hkls[j: j + chunk_size] \
              for j in range(0, len(hkls), chunk_size)]

    # here need to spawn parallel threads

    for hkl in reflections:
      base_min_iplus = self._range_max + self._range_width
      base_min_iminus = self._range_max + self._range_width

      for pm, base, i, sigi in reflections[hkl]:
        if sg.is_centric(hkl):
          if base < base_min_iplus:
            base_min_iplus = base
          if base < base_min_iminus:
            base_min_iminus = base
        elif pm:
          if base < base_min_iplus:
            base_min_iplus = base
        else:
          if base < base_min_iminus:
            base_min_iminus = base

      start_iplus = int((base_min_iplus - self._range_min)
                        / self._range_width)

      start_iminus = int((base_min_iminus - self._range_min)
                         / self._range_width)

      if start_iplus < nsteps:
        iplus_count[start_iplus] += 1
      if start_iminus < nsteps:
        iminus_count[start_iminus] += 1
      if min(start_iplus, start_iminus) < nsteps:
        ieither_count[min(start_iplus, start_iminus)] += 1
      if max(start_iplus, start_iminus) < nsteps:
        iboth_count[max(start_iplus, start_iminus)] += 1

    # now sum up

    for j in range(1, nsteps):
      iplus_count[j] += iplus_count[j - 1]
      iminus_count[j] += iminus_count[j - 1]
      ieither_count[j] += ieither_count[j - 1]
      iboth_count[j] += iboth_count[j - 1]

    # now compute this as fractions

    comp_iplus = [ip / float(nref_n) for ip in iplus_count]
    comp_iminus = [im / float(nref_n) for im in iminus_count]
    comp_ieither = [ie / float(nref_n) for ie in iplus_count]
    comp_iboth = [ib / float(nref_n) for ib in iplus_count]

    # and return

    return comp_iplus, comp_iminus, comp_ieither, comp_iboth

  def help_calculate_completeness_vs_dose_anomalous(self, reflections, hkls):

    iplus_count = []
    iminus_count = []
    ieither_count = []
    iboth_count = []

    nsteps = 1 + int(
        (self._range_max - self._range_min) / self._range_width)

    for j in range(nsteps):
      iplus_count.append(0)
      iminus_count.append(0)
      ieither_count.append(0)
      iboth_count.append(0)

    for hkl in hkls:
      base_min_iplus = self._range_max + self._range_width
      base_min_iminus = self._range_max + self._range_width

      for pm, base, i, sigi in reflections[hkl]:
        if sg.is_centric(hkl):
          if base < base_min_iplus:
            base_min_iplus = base
          if base < base_min_iminus:
            base_min_iminus = base
        elif pm:
          if base < base_min_iplus:
            base_min_iplus = base
        else:
          if base < base_min_iminus:
            base_min_iminus = base

      start_iplus = int((base_min_iplus - self._range_min)
                        / self._range_width)

      start_iminus = int((base_min_iminus - self._range_min)
                         / self._range_width)

      if start_iplus < nsteps:
        iplus_count[start_iplus] += 1
      if start_iminus < nsteps:
        iminus_count[start_iminus] += 1
      if min(start_iplus, start_iminus) < nsteps:
        ieither_count[min(start_iplus, start_iminus)] += 1
      if max(start_iplus, start_iminus) < nsteps:
        iboth_count[max(start_iplus, start_iminus)] += 1

    return iplus_count, iminus_count, iboth_count, ieither_count

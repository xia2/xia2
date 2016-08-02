#!/usr/bin/env python
# XCrystal.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A versioning object representation of the toplevel crystal object,
# which presents much of the overall interface of xia2dpa to the
# outside world.
#
# This will contain some information about the sequence, some information
# about heavy atoms, some stuff about wavelengths. This will also, most
# substantially, contain some really important stuff to do with
# managing the crystal lattice, for instance computing the correct
# "average" value and also handling lattice changes during the data
# reduction.
#
# This latter function is delegated to a lower level object, the
# lattice manager which is contained in this module.
#
# This depends on:
#
# DPA/Wrappers/CCP4/Othercell
#
# FIXME 05/SEP/06 question - do I want to maintain a link to the unit cells
#                 of am I better off just handling the possible lattices and
#                 treating the unit cells as a separate problem? Maintaining
#                 the actual unit cell during processing may be complex -
#                 perhaps I am better off doing this after the event?
#
# FIXME 11/SEP/06 This needs to represent:
#
#  BEGIN CRYSTAL 12847
#
#  BEGIN AA_SEQUENCE
#
#  MKVKKWVTQDFPMVEESATVRECLHRMRQYQTNECIVKDREGHFRGVVNKEDLLDLDLDSSVFNKVSLPD
#  FFVHEEDNITHALLLFLEHQEPYLPVVDEEMRLKGAVSLHDFLEALIEALAMDVPGIRFSVLLEDKPGEL
#  RKVVDALALSNINILSVITTRSGDGKREVLIKVDAVDEGTLIKLFESLGIKIESIEKEEGF
#
#  END AA_SEQUENCE
#
#  BEGIN WAVELENGTH NATIVE
#  WAVELENGTH 0.99187
#  END WAVELENGTH NATIVE
#
#  BEGIN SWEEP NATIVE_HR
#  WAVELENGTH NATIVE
#
#  ... &c. ...
#
# FIXME 20/NOV/06 want to be able to use this to calculate the likely number
#                 of molecules per ASU and also the solvent content, to
#                 help with the links to the experimental phasing. Should
#                 also pass back the spacegroup generated in data reduction
#                 to this. Finally, should provide a user input to allow the
#                 spacegroup to be assigned (and perhaps number of molecules
#                 in the ASU?) from the .xinfo file...
#
# FIXME 28/JUN/07 need to be able to pass in a reference reflection file
#                 for determining the correct setting and also to provide
#                 the FreeR column. This should probably be enforced as an
#                 MTZ file.

import os
import sys
import math

from xia2.Wrappers.CCP4.Othercell import Othercell
from xia2.Handlers.Environment import Environment
from xia2.Modules.Scaler.ScalerFactory import Scaler
from xia2.Modules.Refiner.RefinerFactory import Refiner
from xia2.Handlers.Syminfo import Syminfo
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.lib.NMolLib import compute_nmol, compute_solvent

# Generation of Crystallographic Information Files (CIF)
from xia2.Handlers.CIF import CIF

def sort_o_dict(dict, metric):
  '''A generic sorter for dictionaries - will return the keys in
  the correct order for sorting by the input metric.'''
  result = []
  jiffy = []

  class sort_o_thing(object):
    def __init__(self, tag, guff):
      self.tag = tag
      for key in guff.keys():
        setattr(self, key, guff[key])

    def __cmp__(self, other):
      return getattr(self, metric) < getattr(other, metric)

  for key in dict.keys():
    jiffy.append(sort_o_thing(key, dict[key]))

  jiffy.sort()

  for j in jiffy:
    result.append(j.tag)

  return result

class _lattice_manager(object):
  '''A class to manage lattice representations.'''

  def __init__(self, index_lattice, index_cell):
    '''Initialise the whole system from the original indexing
    results.'''

    self._allowed_lattices = { }
    self._allowed_lattice_order = []

    o = Othercell()
    o.set_cell(index_cell)
    o.set_lattice(index_lattice)

    o.generate()

    self._allowed_lattices = o.get_possible_lattices()
    self._allowed_lattice_order = sort_o_dict(self._allowed_lattices,
                                              'number')
    self._allowed_lattice_order.reverse()

  def get_lattice(self):
    return self._allowed_lattices[self._allowed_lattice_order[0]]

  def kill_lattice(self):
    # remove the top one from the list

    if len(self._allowed_lattice_order) == 1:
      raise RuntimeError, 'out of lattices'

    self._allowed_lattice_order = self._allowed_lattice_order[1:]

class _aa_sequence(object):
  '''An object to represent the amino acid sequence.'''

  def __init__(self, sequence):
    self._sequence = sequence
    return

  def set_sequence(self, sequence):
    self._sequence = sequence
    return

  def get_sequence(self):
    return self._sequence

  # serialization functions

  def to_dict(self):
    obj = {}
    obj['__id__'] = 'aa_sequence'
    import inspect
    attributes = inspect.getmembers(self, lambda m:not(inspect.isroutine(m)))
    for a in attributes:
      if a[0].startswith('__'):
        continue
      else:
        obj[a[0]] = a[1]
    return obj

  @classmethod
  def from_dict(cls, obj):
    assert obj['__id__'] == 'aa_sequence'
    return_obj = cls(obj['_sequence'])
    for k, v in obj.iteritems():
      setattr(return_obj, k, v)
    return return_obj

class _ha_info(object):
  '''A versioned class to represent the heavy atom information.'''

  # FIXME in theory we could have > 1 of these to represent e.g. different
  # metal ions naturally present in the molecule, but for the moment
  # just think in terms of a single one (though couldn't hurt to
  # keep them in a list.)

  def __init__(self, atom, number_per_monomer = 0, number_total = 0):
    self._atom = atom
    self._number_per_monomer = number_per_monomer
    self._number_total = number_total
    return

  def set_number_per_monomer(self, number_per_monomer):
    self._number_per_monomer = number_per_monomer
    return

  def set_number_total(self, number_total):
    self._number_total = number_total
    return

  def get_atom(self):
    return self._atom

  def get_number_per_monomer(self):
    return self._number_per_monomer

  def get_number_total(self):
    return self._number_total

  def to_dict(self):
    obj = {}
    obj['__id__'] = 'ha_info'
    import inspect
    attributes = inspect.getmembers(self, lambda m:not(inspect.isroutine(m)))
    for a in attributes:
      if a[0].startswith('__'):
        continue
      else:
        obj[a[0]] = a[1]
    return obj

  @classmethod
  def from_dict(cls, obj):
    assert obj['__id__'] == 'ha_info'
    return_obj = cls(obj['_atom'])
    for k, v in obj.iteritems():
      setattr(return_obj, k, v)
    return return_obj


def _print_lattice(lattice):
  print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % lattice['cell']
  print 'Number: %s     Lattice: %s' % (lattice['number'],
                                        lattice['lattice'])


from libtbx.containers import OrderedDict
formats = OrderedDict([
  ('High resolution limit', ' %7.2f %7.2f %7.2f'),
  ('Low resolution limit', ' %7.2f %7.2f %7.2f'),
  ('Completeness', '%7.1f %7.1f %7.1f'),
  ('Multiplicity', '%7.1f %7.1f %7.1f'),
  ('I/sigma', '%7.1f %7.1f %7.1f'),
  ('Rmerge(I)', '%7.3f %7.3f %7.3f'),
  ('Rmerge(I+/-)', '%7.3f %7.3f %7.3f'),
  ('Rmeas(I)', '%7.3f %7.3f %7.3f'),
  ('Rmeas(I+/-)', '%7.3f %7.3f %7.3f'),
  ('Rpim(I)', '%7.3f %7.3f %7.3f'),
  ('Rpim(I+/-)', '%7.3f %7.3f %7.3f'),
  ('CC half', '%7.3f %7.3f %7.3f'),
  ('Wilson B factor', '%7.3f'),
  ('Partial bias', '%7.3f %7.3f %7.3f'),
  ('Anomalous completeness', '%7.1f %7.1f %7.1f'),
  ('Anomalous multiplicity', '%7.1f %7.1f %7.1f'),
  ('Anomalous correlation', '%7.3f %7.3f %7.3f'),
  ('Anomalous slope', '%7.3f %7.3f %7.3f'),
  ('dF/F', '%7.3f'),
  ('dI/s(dI)', '%7.3f'),
  ('Total observations', '%7d %7d %7d'),
  ('Total unique', '%7d %7d %7d')
])


def format_statistics(statistics):
  '''Format for printing statistics from data processing, removing from
  the main XCrystal __repr__ method. See DLS #1291'''

  available = statistics.keys()

  result = ''

  for k, format_str in formats.iteritems():
    if k in available:
      try:
        formatted = format_str % tuple(statistics[k])
      except TypeError:
        formatted = '(error)'
      result += k.ljust(44) + formatted + '\n'

  return result

class XCrystal(object):
  '''An object to maintain all of the information about a crystal. This
  will contain the experimental information in XWavelength objects,
  and also amino acid sequence, heavy atom information.'''

  def __init__(self, name, project):

    self._name = name

    # separate out the anomalous pairs or merge them together?
    self._anomalous = False

    # FIXME check that project is an XProject
    self._project = project

    # these should be populated with the objects defined above
    self._aa_sequence = None

    # note that I am making allowances for > 1 heavy atom class...
    # FIXME 18/SEP/06 these should be in a dictionary which is keyed
    # by the element name...
    self._ha_info = {}
    self._wavelengths = {}
    self._samples = {}
    self._lattice_manager = None

    # hooks to dangle command interfaces from

    self._scaler = None

    self._refiner = None

    # things to store input reflections which are used to define
    # the setting... this will be passed into the Scaler if
    # defined... likewise the FreeR column file
    self._reference_reflection_file = None
    self._freer_file = None
    self._user_spacegroup = None

    # things to help the great passing on of information
    self._scaled_merged_reflections = None

    # derived information
    self._nmol = 1

    return

  # serialization functions

  def to_dict(self):
    obj = {}
    obj['__id__'] = 'XCrystal'
    import inspect
    attributes = inspect.getmembers(self, lambda m:not(inspect.isroutine(m)))
    for a in attributes:
      if a[0] == '_scaler' and a[1] is not None:
        obj[a[0]] = a[1].to_dict()
      elif a[0] == '_wavelengths':
        wavs = {}
        for wname, wav in a[1].iteritems():
          wavs[wname] = wav.to_dict()
        obj[a[0]] = wavs
      elif a[0] == '_samples':
        samples = {}
        for sname, sample in a[1].iteritems():
          samples[sname] = sample.to_dict()
        obj[a[0]] = samples
      elif a[0] == '_project':
        # don't serialize this since the parent xproject *should* contain
        # the pointer to the child xcrystal
        continue
      elif a[0] == '_aa_sequence' and a[1] is not None:
        obj[a[0]] = a[1].to_dict()
      elif a[0] == '_ha_info' and a[1] is not None:
        d = {}
        for k, v in a[1].iteritems():
          d[k] = v.to_dict()
        obj[a[0]] = d
      elif a[0].startswith('__'):
        continue
      else:
        obj[a[0]] = a[1]
    return obj

  @classmethod
  def from_dict(cls, obj):
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSample import XSample
    assert obj['__id__'] == 'XCrystal'
    return_obj = cls(name=None, project=None)
    for k, v in obj.iteritems():
      if k == '_scaler' and v is not None:
        from libtbx.utils import import_python_object
        cls = import_python_object(
          import_path=".".join((v['__module__'], v['__name__'])),
          error_prefix='', target_must_be='', where_str='').object
        v = cls.from_dict(v)
        v._scalr_xcrystal = return_obj
      elif k == '_wavelengths':
        v_ = {}
        for wname, wdict in v.iteritems():
          wav = XWavelength.from_dict(wdict)
          wav._crystal = return_obj
          v_[wname] = wav
        v = v_
      elif k == '_samples':
        v_ = {}
        for sname, sdict in v.iteritems():
          sample = XSample.from_dict(sdict)
          sample._crystal = return_obj
          v_[sname] = sample
        v = v_
      elif k == '_aa_sequence' and v is not None:
        v = _aa_sequence.from_dict(v)
      elif k == '_ha_info' and v is not None:
        for k_, v_ in v.iteritems():
          v[k_] = _ha_info.from_dict(v_)
      setattr(return_obj, k, v)
    sweep_dict = {}
    for sample in return_obj._samples.values():
      for i, sname in enumerate(sample._sweeps):
        found_sweep = False
        for wav in return_obj._wavelengths.values():
          if found_sweep: break
          for sweep in wav._sweeps:
            if sweep.get_name() == sname:
              sample._sweeps[i] = sweep
              sweep._sample = sample
              found_sweep = True
              break
      for s in sample._sweeps: assert not isinstance(s, basestring)
    if return_obj._scaler is not None:
      for intgr in return_obj._get_integraters():
        return_obj._scaler._scalr_integraters[intgr.get_integrater_epoch()] \
          = intgr
        if (hasattr(return_obj._scaler, '_sweep_handler') and
            return_obj._scaler._sweep_handler is not None):
          if intgr.get_integrater_epoch() in \
             return_obj._scaler._sweep_handler._sweep_information:
            return_obj._scaler._sweep_handler._sweep_information[
              intgr.get_integrater_epoch()]._integrater = intgr
    return return_obj

  def get_output(self):

    result = 'Crystal: %s\n' % self._name

    if self._aa_sequence:
      result += 'Sequence: %s\n' % self._aa_sequence.get_sequence()
    for wavelength in self._wavelengths.keys():
      result += self._wavelengths[wavelength].get_output()

    scaler = self._get_scaler()
    if scaler.get_scaler_finish_done():
      for wname, xwav in self._wavelengths.iteritems():
        for xsweep in xwav.get_sweeps():
          idxr = xsweep._get_indexer()
          if PhilIndex.params.xia2.settings.show_template:
            result += '%s\n' %banner('Autoindexing %s (%s)' %(
              idxr.get_indexer_sweep_name(), idxr.get_template()))
          else:
            result += '%s\n' %banner(
              'Autoindexing %s' %idxr.get_indexer_sweep_name())
          result += '%s\n' %idxr.show_indexer_solutions()

          intgr = xsweep._get_integrater()
          if PhilIndex.params.xia2.settings.show_template:
            result += '%s\n' %banner('Integrating %s (%s)' %(
              intgr.get_integrater_sweep_name(), intgr.get_template()))
          else:
            result += '%s\n' %banner(
              'Integrating %s' %intgr.get_integrater_sweep_name())
          result += '%s\n' % intgr.show_per_image_statistics()

      result += '%s\n' %banner('Scaling %s' %self.get_name())

      for (dname, sname), limit in scaler.get_scaler_resolution_limits().iteritems():
        result += 'Resolution limit for %s/%s: %5.2f\n' %(dname, sname, limit)

    # this is now deprecated - be explicit in what you are
    # asking for...
    reflections_all = self.get_scaled_merged_reflections()
    statistics_all = self._get_scaler().get_scaler_statistics()

    # print some of these statistics, perhaps?

    for key in statistics_all.keys():
      result += 'For %s/%s/%s\n' % key
      result += format_statistics(statistics_all[key])

    # then print out some "derived" information based on the
    # scaling - this is presented through the Scaler interface
    # explicitly...

    cell = self._get_scaler().get_scaler_cell()
    cell_esd = self._get_scaler().get_scaler_cell_esd()
    spacegroups = self._get_scaler().get_scaler_likely_spacegroups()

    spacegroup = spacegroups[0]
    resolution = self._get_scaler().get_scaler_highest_resolution()

    from cctbx import sgtbx
    sg = sgtbx.space_group_type(str(spacegroup))
    spacegroup = sg.lookup_symbol()
    CIF.set_spacegroup(sg)

    result += 'Assuming spacegroup: %s\n' % spacegroup
    if len(spacegroups) > 1:
      result += 'Other likely alternatives are:\n'
      for sg in spacegroups[1:]:
        result += '%s\n' % sg

    if cell_esd:
      def format_value_with_esd(value, esd, decimal_places):
        value = "%%.%df" % decimal_places % value
        esd_value = round(esd * (10 ** decimal_places))
        if esd_value == 0:
          return value, ""
        else:
          return value, "(%d)" % esd_value
      formatted_cell_esds = tuple(format_value_with_esd(v, sd, 4) for v, sd in zip(cell, cell_esd))
      alignment = tuple(max(len(i) for i in s) for s in zip(*formatted_cell_esds))
      formatted_cell_esds = tuple("%%%ds%%-%ds" % alignment % param for param in formatted_cell_esds)
      result += 'Unit cell (with estimated std devs):\n'
      result += '%s %s %s\n%s %s %s\n' % formatted_cell_esds
    else:
      result += 'Unit cell:\n'
      result += '%7.3f %7.3f %7.3f\n%7.3f %7.3f %7.3f\n' % tuple(cell)

    # now, use this information and the sequence (if provided)
    # and also matthews_coef (should I be using this directly, here?)
    # to compute a likely number of molecules in the ASU and also
    # the solvent content...

    if self._aa_sequence:
      residues = self._aa_sequence.get_sequence()
      if residues:
        nres = len(residues)

        # first compute the number of molecules using the K&R
        # method

        nmol = compute_nmol(cell[0], cell[1], cell[2],
                            cell[3], cell[4], cell[5],
                            spacegroup, resolution, nres)

        # then compute the solvent fraction

        solvent = compute_solvent(cell[0], cell[1], cell[2],
                                  cell[3], cell[4], cell[5],
                                  spacegroup, nmol, nres)

        result += 'Likely number of molecules in ASU: %d\n' % nmol
        result += 'Giving solvent fraction:        %4.2f\n' % solvent

        self._nmol = nmol

    if type(reflections_all) == type({}):
      for format in reflections_all.keys():
        result += '%s format:\n' % format
        reflections = reflections_all[format]

        if type(reflections) == type({}):
          for wavelength in reflections.keys():
            target = FileHandler.get_data_file(
                reflections[wavelength])
            result += 'Scaled reflections (%s): %s\n' % \
                      (wavelength, target)

        else:
          target = FileHandler.get_data_file(
              reflections)
          result += 'Scaled reflections: %s\n' % target

    CIF.write_cif()

    return result

  #def __str__(self):
    #return self.__repr__()

  def summarise(self):
    '''Produce a short summary of this crystal.'''

    summary = ['Crystal: %s' % self._name]

    if self._aa_sequence:
      summary.append('Sequence length: %d' % \
                     len(self._aa_sequence.get_sequence()))

    for wavelength in self._wavelengths.keys():
      for record in self._wavelengths[wavelength].summarise():
        summary.append(record)

    statistics_all = self._get_scaler().get_scaler_statistics()

    for key in statistics_all:
      pname, xname, dname = key

      summary.append('For %s/%s/%s:' % key)
      available = statistics_all[key].keys()

      stats = []
      keys = [
        'High resolution limit',
        'Low resolution limit',
        'Completeness',
        'Multiplicity',
        'I/sigma',
        'Rmerge(I+/-)',
        'CC half',
        'Anomalous completeness',
        'Anomalous multiplicity']

      for k in keys:
        if k in available:
          stats.append(k)

      for s in stats:
        format_str = formats[s]
        if isinstance(statistics_all[key][s], float):
          summary.append(
            '%s: ' %(s.ljust(40)) + format_str % (statistics_all[key][s]))
        elif isinstance(statistics_all[key][s], basestring):
          summary.append(
            '%s: %s' % (s.ljust(40), statistics_all[key][s]))
        else:
          summary.append(
            '%s ' % s.ljust(43) + format_str % tuple(statistics_all[key][s]))

    cell = self._get_scaler().get_scaler_cell()
    spacegroup = self._get_scaler().get_scaler_likely_spacegroups()[0]

    summary.append('Cell: %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
                   tuple(cell))
    summary.append('Spacegroup: %s' % spacegroup)

    return summary

  def set_reference_reflection_file(self, reference_reflection_file):
    '''Set a reference reflection file to use to standardise the
    setting, FreeR etc.'''

    # check here it is an MTZ file

    self._reference_reflection_file = reference_reflection_file
    return

  def set_freer_file(self, freer_file):
    '''Set a FreeR column file to use to standardise the FreeR column.'''

    self._freer_file = freer_file
    return

  def set_user_spacegroup(self, user_spacegroup):
    '''Set a user assigned spacegroup - which needs to be propogated.'''

    self._user_spacegroup = user_spacegroup
    return

  def get_user_spacegroup(self):
    return self._user_spacegroup

  def get_reference_reflection_file(self):
    return self._reference_reflection_file

  def get_freer_file(self):
    return self._freer_file

  def set_scaled_merged_reflections(self, scaled_merged_reflections):
    self._scaled_merged_reflections = scaled_merged_reflections
    return

  def get_project(self):
    return self._project

  def get_name(self):
    return self._name

  def get_aa_sequence(self):
    return self._aa_sequence

  def set_aa_sequence(self, aa_sequence):
    if not self._aa_sequence:
      self._aa_sequence = _aa_sequence(aa_sequence)
    else:
      self._aa_sequence.set_sequence(aa_sequence)

    return

  def get_ha_info(self):
    return self._ha_info

  def set_ha_info(self, ha_info_dict):
    # FIXED I need to decide how to implement this...
    # do so from the dictionary...

    # bug # 2326 - need to decide when we're anomalous
    self._anomalous = True

    atom = ha_info_dict['atom']

    if atom in self._ha_info:
      # update this description
      if 'number_per_monomer' in ha_info_dict:
        self._ha_info[atom].set_number_per_monomer(
            ha_info_dict['number_per_monomer'])
      if 'number_total' in ha_info_dict:
        self._ha_info[atom].set_number_total(
            ha_info_dict['number_total'])

    else:
      # implant a new atom
      self._ha_info[atom] = _ha_info(atom)
      if 'number_per_monomer' in ha_info_dict:
        self._ha_info[atom].set_number_per_monomer(
            ha_info_dict['number_per_monomer'])
      if 'number_total' in ha_info_dict:
        self._ha_info[atom].set_number_total(
            ha_info_dict['number_total'])

    return

  def get_wavelength_names(self):
    '''Get a list of wavelengths belonging to this crystal.'''
    return sorted(self._wavelengths)

  def get_xwavelength(self, wavelength_name):
    '''Get a named xwavelength object back.'''
    return self._wavelengths[wavelength_name]

  def add_wavelength(self, xwavelength):

    if xwavelength.__class__.__name__ != 'XWavelength':
      raise RuntimeError, 'input should be an XWavelength object'

    if xwavelength.get_name() in self._wavelengths.keys():
      raise RuntimeError, 'XWavelength with name %s already exists' % \
            xwavelength.get_name()

    self._wavelengths[xwavelength.get_name()] = xwavelength

    # bug # 2326 - need to decide when we're anomalous
    if len(self._wavelengths.keys()) > 1:
      self._anomalous = True

    if xwavelength.get_f_pr() != 0.0 or xwavelength.get_f_prpr() != 0.0:
      self._anomalous = True

    return

  def get_xsample(self, sample_name):
    '''Get a named xsample object back.'''
    return self._samples[sample_name]

  def add_sample(self, xsample):

    if xsample.__class__.__name__ != 'XSample':
      raise RuntimeError, 'input should be an XSample object'

    if xsample.get_name() in self._samples.keys():
      raise RuntimeError, 'XSample with name %s already exists' % \
            xsample.get_name()

    self._samples[xsample.get_name()] = xsample

    return

  def remove_sweep(self, s):
    '''Find and remove the sweep s from this crystal.'''

    for wave in self._wavelengths.keys():
      self._wavelengths[wave].remove_sweep(s)

    return

  def _get_integraters(self):
    integraters = []

    for wave in self._wavelengths.keys():
      for i in self._wavelengths[wave]._get_integraters():
        integraters.append(i)

    return integraters

  def _get_indexers(self):
    indexers = []

    for wave in self._wavelengths.keys():
      for i in self._wavelengths[wave]._get_indexers():
        indexers.append(i)

    return indexers

  def get_all_image_names(self):
    '''Get a full list of all images from this crystal...'''

    # for RD analysis ...

    result = []
    for wavelength in self._wavelengths.keys():
      result.extend(self._wavelengths[wavelength].get_all_image_names())
    return result

  def set_lattice(self, lattice, cell):
    '''Configure the cell - if it is already set, then manage this
    carefully...'''

    # FIXME this should also verify that the cell for the provided
    # lattice exactly matches the limitations provided in IUCR
    # tables A.

    if self._lattice_manager:
      self._update_lattice(lattice, cell)
    else:
      self._lattice_manager = _lattice_manager(lattice, cell)

    return

  def _update_lattice(self, lattice, cell):
    '''Inspect the available lattices and see if this matches
    one of them...'''

    # FIXME need to think in here in terms of the lattice
    # being higher than the current one...
    # though that shouldn't happen, because if this is the
    # next processing, this should have taken the top
    # lattice supplied earler as input...

    while lattice != self._lattice_manager.get_lattice()['lattice']:
      self._lattice_manager.kill_lattice()

    # this should now point to the correct lattice class...
    # check that the unit cell matches reasonably well...

    cell_orig = self._lattice_manager.get_lattice()['cell']

    dist = 0.0

    for j in range(6):
      dist += math.fabs(cell_orig[j] - cell[j])

    # allow average of 1 degree, 1 angstrom
    if dist > 6.0:
      raise RuntimeError, 'new lattice incompatible: %s vs. %s' % \
            ('[%6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f]' % \
             tuple(cell),
             '[%6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f]' % \
             tuple(cell_orig))

    # if we reach here we're satisfied that the new lattice matches...
    # FIXME write out some messages here to Chatter.

    return

  def get_lattice(self):
    if self._lattice_manager:
      return self._lattice_manager.get_lattice()

    return None

  def set_anomalous(self, anomalous=True):
    self._anomalous = anomalous

  def get_anomalous(self):
    return self._anomalous

  # "power" methods - now where these actually perform some real calculations
  # to get some real information out - beware, this will actually run
  # programs...

  def get_scaled_merged_reflections(self):
    '''Return a reflection file (or files) containing all of the
    merged reflections for this XCrystal.'''

    return self._get_scaler().get_scaled_merged_reflections()

  def get_scaled_reflections(self, format):
    '''Get specific reflection files.'''

    return self._get_scaler().get_scaled_reflections(format)

  def get_cell(self):
    '''Get the final unit cell from scaling.'''
    return self._get_scaler().get_scaler_cell()

  def get_likely_spacegroups(self):
    '''Get the list if likely spacegroups from the scaling.'''
    return self._get_scaler().get_scaler_likely_spacegroups()

  def get_statistics(self):
    '''Get the scaling statistics for this sample.'''
    return self._get_scaler().get_scaler_statistics()

  def _get_scaler(self):
    if self._scaler is None:

      # in here check if
      #
      # (1) self._scaled_merged_reflections is set and
      # (2) there is no sweep information
      #
      # if both of these are true then produce a null scaler
      # which will wrap this information

      from libtbx import Auto
      scale_dir = PhilIndex.params.xia2.settings.scale.directory
      if scale_dir is Auto:
        scale_dir = 'scale'
      working_directory = Environment.generate_directory([self._name, scale_dir])

      self._scaler = Scaler()

      # put an inverse link in place... to support RD analysis
      # involved change to Scaler interface definition

      self._scaler.set_scaler_xcrystal(self)

      if self._anomalous:
        self._scaler.set_scaler_anomalous(True)

      # set up a sensible working directory
      self._scaler.set_working_directory(working_directory)

      # set the reference reflection file, if we have one...
      if self._reference_reflection_file:
        self._scaler.set_scaler_reference_reflection_file(
            self._reference_reflection_file)

      # and FreeR file
      if self._freer_file:
        self._scaler.set_scaler_freer_file(self._freer_file)

      # and spacegroup information
      if self._user_spacegroup:
        # compute the lattice and pointgroup from this...

        pointgroup = Syminfo.get_pointgroup(self._user_spacegroup)

        self._scaler.set_scaler_input_spacegroup(
            self._user_spacegroup)
        self._scaler.set_scaler_input_pointgroup(pointgroup)

      integraters = self._get_integraters()

      # then feed them to the scaler

      for i in integraters:
        self._scaler.add_scaler_integrater(i)

    return self._scaler

  def serialize(self):
    scaler = self._get_scaler()
    if scaler.get_scaler_finish_done():
      scaler.as_json(
        filename=os.path.join(scaler.get_working_directory(), "xia2.json"))


if __name__ == '__main__':
  # lm = _lattice_manager('aP', (43.62, 52.27, 116.4, 103, 100.7, 90.03))
  # _print_lattice(lm.get_lattice())
  # lm.kill_lattice()
  # _print_lattice(lm.get_lattice())

  xc = XCrystal('DEMO', None)

  # this should configure with all possible lattices, though
  # I think going through an explicit "init lattices" would help...
  xc.set_lattice('aP', (43.62, 52.27, 116.4, 103, 100.7, 90.03))
  _print_lattice(xc.get_lattice())

  # this should "drop" the lattice by one - the idea here is
  # that this is the output from e.g. pointless updating the lattice
  # used for processing
  xc.set_lattice('mC', (228.70, 43.62, 52.27, 90.00, 103.20, 90.00))
  _print_lattice(xc.get_lattice())

  # this should raise an exception - the unit cell is not compatible
  xc.set_lattice('mC', (221.0, 44.0, 57.0, 90.0, 106.0, 90.0))

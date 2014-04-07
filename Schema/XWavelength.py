#!/usr/bin/env python
# XWavelength.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A versioning object representing the wavelength level in the .xinfo
# hierarchy. This will include all of the methods for performing operations
# on a wavelength as well as stuff for integration with the rest of the
# .xinfo hierarchy.
#
# The following are properties defined for an XWavelength object:
#
# wavelength
# f_pr
# f_prpr
#
# However, these objects are not versioned, since they do not (in the current
# implementation) impact on the data reduction process. These are mostly
# passed through.
#
# FIXME 05/SEP/06 this also needs to be able to handle the information
#                 pertaining to the lattice, because it is critcial that
#                 all of the sweeps for a wavelength share the same
#                 lattice.
#
# FIXME 05/SEP/06 also don't forget about ordering the sweeps in collection
#                 order for the data reduction, to make sure that we
#                 reduce the least damaged data first.

from XSweep import XSweep
from Handlers.Flags import Flags
from Handlers.Streams import Chatter

class XWavelength(object):
  '''An object representation of a wavelength, which will after data
  reduction correspond to an MTZ hierarchy dataset.'''

  def __init__(self, name, crystal, wavelength,
               f_pr = 0.0, f_prpr = 0.0, dmin = 0.0, dmax = 0.0):
    '''Create a new wavelength named name, belonging to XCrystal object
    crystal, with wavelength and optionally f_pr, f_prpr assigned.'''

    # check that the crystal is an XCrystal

    if not crystal.__class__.__name__ == 'XCrystal':
      pass

    # set up this object

    self._name = name
    self._crystal = crystal
    self._wavelength = wavelength
    self._f_pr = f_pr
    self._f_prpr = f_prpr
    self._resolution_high = dmin
    self._resolution_low = dmax

    # then create space to store things which are contained
    # in here - the sweeps

    self._sweeps = []

    return

  def __repr__(self):
    result = 'Wavelength name: %s\n' % self._name
    result += 'Wavelength %7.5f\n' % self._wavelength
    if self._f_pr != 0.0 and self._f_prpr != 0.0:
      result += 'F\', F\'\' = (%5.2f, %5.2f)\n' % (self._f_pr,
                                                   self._f_prpr)

    result += 'Sweeps:\n'

    remove = []

    def run_one_sweep(args):
      assert len(args) == 2
      s, failover = args
      if failover:
        try:
          s.get_integrater_intensities()
          #import pickle
          #p = pickle.dumps(s)
          return s
        except Exception, e:
          Chatter.write('Processing sweep %s failed: %s' % \
                        (s.get_name(), str(e)))
          #remove.append(s)
          #return ''
      else:
        return s

    args = [(s, Flags.get_failover()) for s in self._sweeps]

    from libtbx import easy_mp
    from libtbx import Auto
    from Handlers.Phil import PhilIndex
    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    if mp_params.mode == 'serial':
      nproc = 1
    else:
      #assert
      nproc = mp_params.nproc
      if nproc is Auto:
        from Handlers.Environment import get_number_cpus
        nproc = get_number_cpus()

    results_list = easy_mp.parallel_map(
      run_one_sweep, args, params=None,
      processes=nproc,
      method="multiprocessing",
      asynchronous=True,
      callback=None,
      preserve_order=True,
      preserve_exception_message=True)

    self._sweeps = [s for s in results_list if s is not None]
    result += "\n".join(str(s) for s in results_list)

    #remove = [s for s, r in zip(self._sweeps, results_list) if r is None]

    #result += '\n'.join(r for r in results_list if r is not None)

    #for s in self._sweeps:

      ## would be nice to put this somewhere else in the hierarchy - not
      ## sure how to do that though (should be handled in Interfaces?)

      ## would also be nice to put some parallelism in here - though is
      ## this the right place to do that? would seem kind-of messy...

      #if Flags.get_failover():
        #try:
          #result += '%s\n' % str(s)
        #except Exception, e:
          #Chatter.write('Processing sweep %s failed: %s' % \
                        #(s.get_name(), str(e)))
          #remove.append(s)
      #else:
        #result += '%s\n' % str(s)

    #for s in remove:
      #self._sweeps.remove(s)

    return result[:-1]

  def summarise(self):

    summary = ['Wavelength: %s (%7.5f)' % (self._name, self._wavelength)]

    for s in self._sweeps:
      for record in s.summarise():
        summary.append(record)

    return summary

  def __str__(self):
    return self.__repr__()

  def get_wavelength(self):
    return self._wavelength

  def set_wavelength(self, wavelength):
    # FIXME 29/NOV/06 provide a facility to update this when it is
    # not provided in the .xinfo file - this will come from the
    # image header
    if self._wavelength != 0.0:
      raise RuntimeError, 'setting wavelength when already set'
    self._wavelength = wavelength
    return

  def set_resolution_high(self, resolution_high):
    self._resolution_high = resolution_high
    return

  def set_resolution_low(self, resolution_low):
    self._resolution_low = resolution_low
    return

  def get_resolution_high(self):
    return self._resolution_high

  def get_resolution_low(self):
    return self._resolution_low

  def get_f_pr(self):
    return self._f_pr

  def get_f_prpr(self):
    return self._f_prpr

  def get_crystal(self):
    return self._crystal

  def get_name(self):
    return self._name

  def get_all_image_names(self):
    '''Get a full list of all images in this wavelength...'''

    # for RD analysis ...

    result = []
    for sweep in self._sweeps:
      result.extend(sweep.get_all_image_names())
    return result

  def add_sweep(self, name, directory = None, image = None,
                beam = None, reversephi = False, distance = None,
                gain = 0.0, dmin = 0.0, dmax = 0.0, polarization = 0.0,
                frames_to_process = None, user_lattice = None,
                user_cell = None, epoch = 0, ice = False, excluded_regions = []):
    '''Add a sweep to this wavelength.'''

    self._sweeps.append(XSweep(name, self,
                               directory = directory,
                               image = image,
                               beam = beam,
                               reversephi = reversephi,
                               distance = distance,
                               gain = gain,
                               dmin = dmin,
                               dmax = dmax,
                               polarization = polarization,
                               frames_to_process = frames_to_process,
                               user_lattice = user_lattice,
                               user_cell = user_cell,
                               epoch = epoch,
                               ice = ice,
                               excluded_regions = excluded_regions))

    return

  def get_sweeps(self):
    return self._sweeps

  def remove_sweep(self, sweep):
    '''Remove a sweep object from this wavelength.'''

    try:
      self._sweeps.remove(sweep)
    except ValueError, e:
      pass

    return

  def _get_integraters(self):
    integraters = []
    for s in self._sweeps:
      integraters.append(s._get_integrater())

    return integraters

  def _get_indexers(self):
    indexers = []
    for s in self._sweeps:
      indexers.append(s._get_indexer())

    return indexers

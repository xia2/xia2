#!/usr/bin/env python
# XSample.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.

from __future__ import absolute_import, division

class XSample(object):
  '''An object representation of a sample.'''

  def __init__(self, name, crystal):
    '''Create a new sample named name, belonging to XCrystal object crystal.'''

    # check that the crystal is an XCrystal

    if not crystal.__class__.__name__ == 'XCrystal':
      pass

    # set up this object

    self._name = name
    self._crystal = crystal

    # then create space to store things which are contained
    # in here - the sweeps

    self._sweeps = []

    self._multi_indexer = None

    return

  def get_epoch_to_dose(self):

    from xia2.Modules.DoseAccumulate import accumulate_dose
    epoch_to_dose = accumulate_dose(
      [sweep.get_imageset() for sweep in self._sweeps])
    return epoch_to_dose

    #from matplotlib import pyplot
    #for i, sweep in enumerate(self._sweeps):
      #epochs = sweep.get_imageset().get_scan().get_epochs()
      #pyplot.scatter(
        #list(epochs), [epoch_to_dose[e] for e in epochs],
        #marker='+', color='bg'[i])
    #pyplot.show()

  # serialization functions

  def to_dict(self):
    obj = {}
    obj['__id__'] = 'XSample'
    import inspect
    attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
    for a in attributes:
      if a[0] == '_sweeps':
        sweeps = []
        for sweep in a[1]:
          sweeps.append(sweep.to_dict())
        obj[a[0]] = sweeps
      elif a[0] == '_crystal':
        # don't serialize this since the parent xsample *should* contain
        # the reference to the child xsweep
        continue
      elif a[0] == '_multi_indexer' and a[1] is not None:
        obj[a[0]] = a[1].to_dict()
      elif a[0].startswith('__'):
        continue
      else:
        obj[a[0]] = a[1]
    return obj

  @classmethod
  def from_dict(cls, obj):
    assert obj['__id__'] == 'XSample'
    return_obj = cls(name=None, crystal=None)
    for k, v in obj.iteritems():
      if k == '_sweeps':
        v = [s_dict['_name'] for s_dict in v]
      elif k == '_multi_indexer' and v is not None:
        from libtbx.utils import import_python_object
        cls = import_python_object(
          import_path=".".join((v['__module__'], v['__name__'])),
          error_prefix='', target_must_be='', where_str='').object
        v = cls.from_dict(v)
      setattr(return_obj, k, v)
    return return_obj

  def get_output(self):
    result = 'Sample name: %s\n' % self._name
    result += 'Sweeps:\n'
    return result[:-1]

  def get_crystal(self):
    return self._crystal

  def get_name(self):
    return self._name

  def add_sweep(self, sweep):
    self._sweeps.append(sweep)

  def get_sweeps(self):
    return self._sweeps

  def set_multi_indexer(self, multi_indexer):
    self._multi_indexer = multi_indexer

  def get_multi_indexer(self):
    return self._multi_indexer

  def remove_sweep(self, sweep):
    '''Remove a sweep object from this wavelength.'''

    try:
      self._sweeps.remove(sweep)
    except ValueError:
      pass

    return

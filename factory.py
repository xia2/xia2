from __future__ import absolute_import, division, print_function

import importlib

class FactoryMixIn():
  def _get_data_area(self, module, classname):
    '''Helper function to instantiate a data area or return a cached instance.'''
    if hasattr(self, '_cache_' + module):
      return getattr(self, '_cache_' + module)
    da_mod = importlib.import_module('%s.%s' % (self.get_data_area_package(), module))
    DAClass = getattr(da_mod, classname)
    da = DAClass()
    da.set_connection(self)
    setattr(self, '_cache_' + module, da)
    return da

  @property
  def core(self):
    '''Core part of the database schema'''
    return self._get_data_area('core', 'Core')

  @property
  def mx_acquisition(self):
    '''MX acquisition tables'''
    return self._get_data_area('mxacquisition', 'MXAcquisition')

  @property
  def em_acquisition(self):
    '''EM acquisition tables'''
    return self._get_data_area('emacquisition', 'EMAcquisition')

  @property
  def mx_processing(self):
    '''MX processing tables'''
    return self._get_data_area('mxprocessing', 'MXProcessing')

  @property
  def mx_screening(self):
    '''MX screening tables'''
    return self._get_data_area('mxscreening', 'MXScreening')

  @property
  def shipping(self):
    '''Shipping tables'''
    return self._get_data_area('shipping', 'Shipping')

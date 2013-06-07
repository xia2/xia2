#!/usr/bin/env python
# Phil.py
#   Copyright (C) 2012 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Phil parameter setting - to get a single place where complex parameters to
# set for individual programs can be found. Initially this will be just a 
# couple for XDS.

import os

from libtbx.phil import parse

class _Phil:
    def __init__(self):
        self._working_phil = parse("""
xds {
  integrate {
    include scope Wrappers.XDS.XDSIntegrate.master_params
  }
  index {
    include scope Wrappers.XDS.XDSIdxref.master_params
  }
}
deprecated_xds.parameter {
  delphi = 5
    .type = float
  delphi_small = 30
    .type = float
  untrusted_ellipse = None
    .type = ints(size = 4)
  untrusted_rectangle = None
    .type = ints(size = 4)
  xscale_min_isigma = 3.0
    .type = float
  trusted_region = None
    .type = floats(size = 2)
  profile_grid_size = None
    .type = ints(size = 2)
}
ccp4.reindex {
  program = 'pointless'
    .type = str
}
ccp4.truncate {
  program = 'ctruncate'
    .type = str
}
xia2.settings {
  show_template = False
    .type = bool
  untrusted_rectangle_indexing = None
    .type = ints(size = 4)
  xds_cell_deviation = 0.05, 5.0
    .type = floats(size = 2)
}
""", process_includes = True)
        self._parameters = self._working_phil.extract()
        return

    def add(self, source):
        
        if not os.path.exists(source):
            raise RuntimeError, 'phil file missing: %s' % source

        source_phil = parse(open(source).read())
        self._working_phil = self._working_phil.fetch(source = source_phil)
        self._parameters = self._working_phil.extract()
        return

    def show(self):
        self._working_phil.show()
        return

    def get_xds_parameter_delphi(self):
        return self._parameters.deprecated_xds.parameter.delphi

    def get_xds_parameter_untrusted_ellipse(self):
        return self._parameters.deprecated_xds.parameter.untrusted_ellipse
    
    def get_xds_parameter_untrusted_rectangle(self):
        return self._parameters.deprecated_xds.parameter.untrusted_rectangle

    def get_xds_parameter_trusted_region(self):
        return self._parameters.deprecated_xds.parameter.trusted_region

    def get_xds_parameter_profile_grid_size(self):
        return self._parameters.deprecated_xds.parameter.profile_grid_size

    def get_xds_parameter_delphi_small(self):
        return self._parameters.deprecated_xds.parameter.delphi_small

    def get_xds_parameter_xscale_min_isigma(self):
        return self._parameters.deprecated_xds.parameter.xscale_min_isigma

    def get_ccp4_reindex_program(self):
        return self._parameters.ccp4.reindex.program

    def get_ccp4_truncate_program(self):
        return self._parameters.ccp4.truncate.program

    def get_xia2_settings_show_template(self):
        return self._parameters.xia2.settings.show_template

    def get_xia2_settings_xds_cell_deviation(self):
        return self._parameters.xia2.settings.xds_cell_deviation

    def get_xia2_settings_untrusted_rectangle_indexing(self):
        return self._parameters.xia2.settings.untrusted_rectangle_indexing

Phil = _Phil()

if __name__ == '__main__':
    print Phil.get_xds_parameter_delphi()

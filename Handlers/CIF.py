#!/usr/bin/env python
# CIFHandler.py
#   Copyright (C) 2016 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler to manage the data ending up in CIF output file

from __future__ import division
import datetime
import iotbx.cif.model
import xia2.XIA2Version
import xia2.Handlers.Citations

class _CIFHandler(object):
  def __init__(self):
    self._cif = iotbx.cif.model.cif()
    self._block = iotbx.cif.model.block()
    self._cif['xia2'] = self._block

  def add_xcrystal(self, xcrystal):
#   print "CIF: Adding crystal", xcrystal
    pass

  def write_cif(self):
    self.collate_audit_information(self._block)
    with open('xia2.cif', 'w') as fh:
      self._cif.show(out=fh)

  def collate_audit_information(self, block):
    block["_audit_creation_method"] = xia2.XIA2Version.Version
    block["_audit_creation_date"] = datetime.date.today().isoformat()
    block["_computing_data_reduction"] = ', '.join(xia2.Handlers.Citations.Citations.get_programs())
    block["_publ_section_references"] = '\n'.join(xia2.Handlers.Citations.Citations.get_citations_acta())

CIF = _CIFHandler()

if __name__ == '__main__':
  CIF.write_cif()

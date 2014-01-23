#!/usr/bin/env python
# DialsIndexer.py
#   Copyright (C) 2014 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An indexer compatible with XDS but using the DIALS methods.

import os
import sys
import math
import shutil

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs: XDS

from Wrappers.XDS.XDSXycorr import XDSXycorr as _Xycorr
from Wrappers.XDS.XDSInit import XDSInit as _Init
from Wrappers.XDS.XDSColspot import XDSColspot as _Colspot
from Wrappers.XDS.XDSIdxref import XDSIdxref as _Idxref

# wrappers for programs that this needs: DIALS

from Wrappers.Dials.Import import Import as _Import
from Wrappers.Dials.Spotfinder import Spotfinder as _Spotfinder
from Wrappers.Dials.Index import Index as _Index
from Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings as \
     _RefineBravaisSettings
from Wrappers.Dials.ExportXDS import ExportXDS as _ExportXDS

from Wrappers.XIA.Diffdump import Diffdump

# interfaces that this must implement to be an indexer

from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.FrameProcessor import FrameProcessor

# odds and sods that are needed

from lib.bits import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Files import FileHandler

class DialsIndexer(FrameProcessor,
                   Indexer):
  def __init__(self):

    # set up the inherited objects

    FrameProcessor.__init__(self)
    Indexer.__init__(self)

    self._working_directory = os.getcwd()

    self._background_images = None
    
    # place to store working data
    
    self._data_files = { }

    return

  # admin functions

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    return

  def get_working_directory(self):
    return self._working_directory

  # factory functions

  def Xycorr(self):
    xycorr = _Xycorr()
    xycorr.set_working_directory(self.get_working_directory())

    xycorr.setup_from_image(self.get_image_name(
        self._indxr_images[0][0]))

    if self.get_distance():
      xycorr.set_distance(self.get_distance())

    if self.get_wavelength():
      xycorr.set_wavelength(self.get_wavelength())

    auto_logfiler(xycorr, 'XYCORR')

    return xycorr

  def Init(self):
    from Handlers.Phil import PhilIndex
    init = _Init(params=PhilIndex.params.xds.init)
    init.set_working_directory(self.get_working_directory())

    init.setup_from_image(self.get_image_name(
        self._indxr_images[0][0]))

    if self.get_distance():
      init.set_distance(self.get_distance())

    if self.get_wavelength():
      init.set_wavelength(self.get_wavelength())

    auto_logfiler(init, 'INIT')

    return init

  def Import(self):
    importer = _Import()
    importer.set_working_directory(self.get_working_directory())
    importer.setup_from_image(self.get_image_name(
      self._indxr_images[0][0]))
    auto_logfiler(importer)
    return importer

  def Spotfinder(self):
    spotfinder = _Spotfinder()
    spotfinder.set_working_directory(self.get_working_directory())
    auto_logfiler(spotfinder)
    return spotfinder

  def Index(self):
    index = _Index()
    index.set_working_directory(self.get_working_directory())
    auto_logfiler(index)
    return index

  def ExportXDS(self):
    export_xds = _ExportXDS()
    export_xds.set_working_directory(self.get_working_directory())
    auto_logfiler(export_xds)
    return export_xds

  def RefineBravaisSettings(self):
    rbs = _RefineBravaisSettings()
    rms.set_working_directory(self.get_working_directory())
    auto_logfiler(rbs)
    return rbs

  ##########################################

  def _index_prepare(self):
    
    all_images = self.get_matching_images()
    first = min(all_images)
    last = max(all_images)

    self._indxr_images = [(first, last)]
    
    dd = Diffdump()
    dd.set_image(self.get_image_name(first))
    header = dd.readheader()
    last_background = int(round(5.0 / header['phi_width'])) - 1 + first
    
    # next start to process these - first xycorr
    # FIXME run these *afterwards* as then we have a refined detector geometry 
    # so the parallax correction etc. should be slightly better.

    xycorr = self.Xycorr()
    xycorr.set_data_range(first, last)
    xycorr.set_background_range(first, last_background)
    xycorr.run()

    for file in ['X-CORRECTIONS.cbf',
                 'Y-CORRECTIONS.cbf']:
      self._data_files[file] = xycorr.get_output_data_file(file)

    # next start to process these - then init

    init = self.Init()

    for file in ['X-CORRECTIONS.cbf',
                 'Y-CORRECTIONS.cbf']:
      init.set_input_data_file(file, self._data_files[file])

    init.set_data_range(first, last)
    init.set_background_range(first, last_background)
    init.run()

    for file in ['BLANK.cbf',
                 'BKGINIT.cbf',
                 'GAIN.cbf']:
      self._data_files[file] = init.get_output_data_file(file)

    # at this stage, break out to run the DIALS code: this sets itself up

    importer = self.Import()
    importer.run()

    # FIXME this should really use the assigned spot finding regions
    spotfinder = self.Spotfinder()
    spotfinder.set_sweep_filename(importer.get_sweep_filename())
    spotfinder.set_scan_ranges([(first, last)])
    spotfinder.run()

    self._spot_filename = spotfinder.get_spot_filename()
    self._sweep_filename = importer.get_sweep_filename()

    return

  def _index(self):
    # FIXME allow humans to set the indexing method from whatever list...
    # FIXME respect input unit cell / symmetry if set - or if decided from 
    # previous indexing cycle
    indexer = self.Index()
    indexer.set_spot_filename(self._spot_filename)
    indexer.set_sweep_filename(self._sweep_filename)
    indexer.run('fft3d')

    self._indexer = indexer

    rbs = self.RefineBravaisSettings()
    rbs.set_crystal_filename(indexer.get_crystal_filename())
    rbs.set_sweep_filename(indexer.get_sweep_filename())
    rbs.set_indexed_filename(indexer.get_indexed_filename())
    rbs.run()

    
    # FIXME set_indexer_done(False) and recycle perhaps if we select a 
    # non-P1 solution...
    # FIXME Richard now writing a tool to do this...

    from Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry
    ls = LatticeSymmetry()
    ls.set_lattice('aP')
    ls.set_cell(indexer.get_p1_cell())
    ls.generate()
    
    allowed_lattices = ls.get_lattices()
    for al in allowed_lattices:
      print al, '%8.3f %8.3f %8.3f %8.3f %8.3f %8.3f' % tuple(ls.get_cell(al))
    
    return

  def _index_finish(self):
    exporter = self.ExportXDS()
    exporter.set_crystal_filename(indexer.get_crystal_filename())
    exporter.set_sweep_filename(indexer.get_sweep_filename())
    exporter.run()

    for file in ['XPARM.XDS']:
      self._data_files[file] = open(os.path.join(
        self.get_working_directory(), file), 'rb').read()
    
    self._indxr_payload['xds_files'] = self._data_files

    from Wrappers.XDS.XDS import xds_read_xparm
    xparm_dict = xds_read_xparm(os.path.join(self.get_working_directory(),
                                             'XPARM.XDS'))

    distance = xparm_dict['distance']
    wavelength = xparm_dict['wavelength']
    pixel = xparm_dict['px'], xparm_dict['py']
    beam = xparm_dict['ox'], xparm_dict['oy']

    return

  

  
  

  
    
    

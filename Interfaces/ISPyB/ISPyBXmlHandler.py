#!/usr/bin/env python
# ISPyBXmlHandler.py
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler to manage the data which needs to end up in the ISPyB xml out
# file.
#
# 11th November 2009

import time
import os
import sys

from xia2.Handlers.Files import FileHandler

def sanitize(path):
  '''Replace double path separators with single ones.'''

  import os
  double = os.sep * 2
  return path.replace(double, os.sep)

class _ISPyBXmlHandler(object):

  def __init__(self):
    self._crystals = { }
    self._per_crystal_data = {}
    self._project = None

    self._name_map = {
        'High resolution limit':'resolutionLimitHigh',
        'Low resolution limit':'resolutionLimitLow',
        'Completeness':'completeness',
        'Multiplicity':'multiplicity',
        'CC half':'ccHalf',
        'Anomalous completeness':'anomalousCompleteness',
        'Anomalous correlation':'ccAnomalous',
        'Anomalous multiplicity':'anomalousMultiplicity',
        'Total observations':'nTotalObservations',
        'Total unique':'nTotalUniqueObservations',
        'Rmerge(I+/-)':'rMerge',
        'Rmeas(I)':'rMeasAllIPlusIMinus',
        'Rmeas(I+/-)':'rMeasWithinIPlusIMinus',
        'Rpim(I)':'rPimAllIPlusIMinus',
        'Rpim(I+/-)':'rPimWithinIPlusIMinus',
        'Partial Bias':'fractionalPartialBias',
        'I/sigma':'meanIOverSigI',
        }

    return

  def add_xcrystal(self, xcrystal):
    if not xcrystal.get_name() in self._crystals:
      self._crystals[xcrystal.get_name()] = xcrystal

    # should ideally drill down and get the refined cell constants for
    # each sweep and the scaling statistics for low resolution, high
    # resolution and overall...

    return

  def add_crystal_log_file(self, crystal, log_file):
    if not log_file in self._per_crystal_data[crystal][
        'log_files']:
      self._per_crystal_data[crystal]['log_files'].append(
          log_file)

    return

  def write_date(self, fout):
    '''Write the current date and time out as XML.'''

    fout.write('<recordTimeStamp>%s</recordTimeStamp>\n' % \
               time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

    return

  def write_cell(self, fout, cell):
    '''Write out a UNIT CELL as XML...'''

    fout.write('<cell_a>%f</cell_a>' % cell[0])
    fout.write('<cell_b>%f</cell_b>' % cell[1])
    fout.write('<cell_c>%f</cell_c>' % cell[2])
    fout.write('<cell_alpha>%f</cell_alpha>' % cell[3])
    fout.write('<cell_beta>%f</cell_beta>' % cell[4])
    fout.write('<cell_gamma>%f</cell_gamma>' % cell[5])

    return

  def write_refined_cell(self, fout, cell):
    '''Write out a REFINED UNIT CELL as XML...'''

    fout.write('<refinedCell_a>%f</refinedCell_a>' % cell[0])
    fout.write('<refinedCell_b>%f</refinedCell_b>' % cell[1])
    fout.write('<refinedCell_c>%f</refinedCell_c>' % cell[2])
    fout.write('<refinedCell_alpha>%f</refinedCell_alpha>' % cell[3])
    fout.write('<refinedCell_beta>%f</refinedCell_beta>' % cell[4])
    fout.write('<refinedCell_gamma>%f</refinedCell_gamma>' % cell[5])

    return

  def write_scaling_statistics(self, fout, scaling_stats_type, stats_dict):
    '''Write out the SCALING STATISTICS block...'''

    fout.write('<AutoProcScalingStatistics>\n')

    fout.write('<scalingStatisticsType>%s</scalingStatisticsType>\n' % \
               scaling_stats_type)

    for name in stats_dict:
      if not name in self._name_map:
        continue

      out_name = self._name_map[name]

      if out_name in ['nTotalObservations', 'nTotalUniqueObservations']:
        fout.write('<%s>%d</%s>' % \
                   (out_name, int(stats_dict[name]), out_name))
      else:
        fout.write('<%s>%s</%s>' % \
                   (out_name, stats_dict[name], out_name))

    fout.write('</AutoProcScalingStatistics>\n')

    return

  def write_xml(self, file):

    fout = open(file, 'w')

    fout.write('<?xml version="1.0"?>')
    fout.write('<AutoProcContainer>\n')

    for crystal in sorted(self._crystals):
      xcrystal = self._crystals[crystal]

      cell = xcrystal.get_cell()
      spacegroup = xcrystal.get_likely_spacegroups()[0]

      fout.write('<AutoProc><spaceGroup>%s</spaceGroup>' % spacegroup)
      self.write_refined_cell(fout, cell)
      fout.write('</AutoProc>')

      fout.write('<AutoProcScalingContainer>')
      fout.write('<AutoProcScaling>')
      self.write_date(fout)
      fout.write('</AutoProcScaling>')

      statistics_all = xcrystal.get_statistics()
      reflection_files = xcrystal.get_scaled_merged_reflections()

      wavelength_names = xcrystal.get_wavelength_names()

      for key in statistics_all.keys():
        pname, xname, dname = key

        # FIXME should assert that the dname is a
        # valid wavelength name

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
            'Anomalous correlation',
            'Anomalous multiplicity',
            'Total observations',
            'Total unique',
            'Rmeas(I)',
            'Rmeas(I+/-)',
            'Rpim(I)',
            'Rpim(I+/-)',
            'Partial Bias'
            ]

        for k in keys:
          if k in available:
            stats.append(k)

        xwavelength = xcrystal.get_xwavelength(dname)
        sweeps = xwavelength.get_sweeps()

        for j, name in enumerate(
            ['overall', 'innerShell', 'outerShell']):
          statistics_cache = { }

          for s in stats:
            if type(statistics_all[key][s]) == type([]):
              statistics_cache[s] = statistics_all[key][s][j]
            elif type(statistics_all[key][s]) == type(()):
              statistics_cache[s] = statistics_all[key][s][j]

          # send these to be written out
          self.write_scaling_statistics(fout, name,
                                        statistics_cache)

        for sweep in sweeps:
          fout.write('<AutoProcIntegrationContainer>\n')
          image_name = sweep.get_all_image_names()[0]
          fout.write('<Image><fileName>%s</fileName>' % \
                     os.path.split(image_name)[-1])
          fout.write('<fileLocation>%s</fileLocation></Image>' %
                     sanitize(os.path.split(image_name)[0]))
          fout.write('<AutoProcIntegration>\n')
          cell = sweep.get_integrater_cell()
          self.write_cell(fout, cell)

          # FIXME this is naughty
          intgr = sweep._get_integrater()

          start, end = intgr.get_integrater_wedge()

          fout.write('<startImageNumber>%d</startImageNumber>' % \
                     start)

          fout.write('<endImageNumber>%d</endImageNumber>' % \
                     end)

          # FIXME this is naughty
          indxr = sweep._get_indexer()

          fout.write(
              '<refinedDetectorDistance>%f</refinedDetectorDistance>' % \
              indxr.get_indexer_distance())

          beam = indxr.get_indexer_beam_centre()

          fout.write('<refinedXBeam>%f</refinedXBeam>' % beam[0])
          fout.write('<refinedYBeam>%f</refinedYBeam>' % beam[1])

          fout.write('</AutoProcIntegration>\n')
          fout.write('</AutoProcIntegrationContainer>\n')

      fout.write('</AutoProcScalingContainer>')

      # file unpacking nonsense

      from xia2.Handlers.CommandLine import CommandLine

      fout.write('<AutoProcProgramContainer><AutoProcProgram>')
      fout.write('<processingCommandLine>%s</processingCommandLine>' \
                 % sanitize(CommandLine.get_command_line()))
      fout.write('<processingPrograms>xia2</processingPrograms>')
      fout.write('</AutoProcProgram>')

      for k in reflection_files:

        reflection_file = reflection_files[k]

        if not type(reflection_file) == type(''):
          continue

        reflection_file = FileHandler.get_data_file(reflection_file)

        fout.write(
            '<AutoProcProgramAttachment><fileType>Result')
        fout.write('</fileType><fileName>%s</fileName>' % \
                   os.path.split(reflection_file)[-1])
        fout.write('<filePath>%s</filePath>' % \
                   sanitize(os.path.split(reflection_file)[0]))
        fout.write('</AutoProcProgramAttachment>\n')


      # add the xia2.txt file...

      fout.write('<AutoProcProgramAttachment><fileType>Log')
      fout.write('</fileType><fileName>xia2.txt</fileName>')
      fout.write('<filePath>%s</filePath>' % sanitize(os.getcwd()))
      fout.write('</AutoProcProgramAttachment>\n')

      fout.write('</AutoProcProgramContainer>')

    fout.write('</AutoProcContainer>\n')
    fout.close()

    return

ISPyBXmlHandler = _ISPyBXmlHandler()

if __name__ == '__main__':
  ISPyBXmlHandler.set_project('test')
  ISPyBXmlHandler.write_xml('test.xml')

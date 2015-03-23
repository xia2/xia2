# LIBTBX_SET_DISPATCHER_NAME dev.xia2.html

import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Handlers.Streams import Chatter, Debug

from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment, df

from Applications.xia2 import get_command_line, write_citations, help


# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

def run():
  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')
  rst = get_xproject_rst(xinfo)

  with open('xia2.new.html', 'wb') as f:
    print >> f, rst2html(rst)

  with open('xia2.tex', 'wb') as f:
    print >> f, rst2latex(rst)


def rst2html(rst):
  from docutils.core import publish_string
  from docutils.writers.html4css1 import Writer,HTMLTranslator

  w = Writer()

  return publish_string(rst, writer=w)

def rst2latex(rst):
  from docutils.core import publish_string
  from docutils.writers.latex2e import Writer

  w = Writer()

  return publish_string(rst, writer=w)

def get_xproject_rst(xproject):

  lines = []

  lines.append('Detailed statistics for each dataset')
  lines.append('=' * len(lines[-1]))

  for cname, xcryst in xproject.get_crystals().iteritems():
    statistics_all = xcryst.get_statistics()

    from lib.tabulate import tabulate
    from collections import OrderedDict

    for key, statistics in statistics_all.iteritems():

      pname, xname, dname = key

      lines.append('Dataset %s' %dname)
      lines.append('_' * len(lines[-1]))

      table = []

      headers = [' ', 'Overall', 'Low', 'High']

      available = statistics.keys()

      formats = OrderedDict([
        ('High resolution limit', '%6.2f'),
        ('Low resolution limit', '%6.2f'),
        ('Completeness', '%5.1f'),
        ('Multiplicity', '%5.1f'),
        ('I/sigma', '%5.1f'),
        ('Rmerge', '%5.3f'),
        ('Rmeas(I)', '%5.3f'),
        ('Rmeas(I+/-)', '%5.3f'),
        ('Rpim(I)', '%5.3f'),
        ('Rpim(I+/-)', '%5.3f'),
        ('CC half', '%5.3f'),
        ('Wilson B factor', '%.3f'),
        ('Partial bias', '%5.3f'),
        ('Anomalous completeness', '%5.1f'),
        ('Anomalous multiplicity', '%5.1f'),
        ('Anomalous correlation', '%6.3f'),
        ('Anomalous slope', '%5.3f'),
        ('dF/F', '%.3f'),
        ('dI/s(dI)', '%.3f'),
        ('Total observations', '%d'),
        ('Total unique', '%d')
      ])

      for k in formats.keys():
        if k in available:
          values = [formats[k] % v for v in statistics[k]]
          if len(values) == 1:
            values = [values[0], '', '']
          assert len(values) == 3
          table.append([k] + values)


      lines.append('\n')
      lines.append(tabulate(table, headers, tablefmt='grid'))
      lines.append('\n')

  lines.append('Integration status per image')
  lines.append('=' * len(lines[-1]))
  lines.append(
    'The following sections show the status of each image from the final '
    'integration run performed on each sweep within each dataset. The table '
    'below summarises the image status for each dataset and sweep.')

  overall_table = []
  headers = ['Dataset', 'Sweep', 'Good', 'Ok', 'Bad rmsd', 'Overloaded',
             'Many bad', 'Weak', 'Abandoned', 'Total']

  good = 'o'
  ok = '%'
  bad_rmsd = '!'
  overloaded = 'O'
  many_bad = '#'
  weak = '.'
  abandoned = '@'

  status_lines = []

  for cname, xcryst in xproject.get_crystals().iteritems():
    for wname in xcryst.get_wavelength_names():
      xwav = xcryst.get_xwavelength(wname)
      for xsweep in xwav.get_sweeps():
        intgr = xsweep._get_integrater()
        stats = intgr.show_per_image_statistics()
        status = stats.split('Integration status per image:')[1].split(
          '"o" => good')[0].strip()

        overall_table.append([
          wname, xsweep.get_name(),
          status.count(good), status.count(ok), status.count(bad_rmsd),
          status.count(overloaded), status.count(many_bad), status.count(weak),
          status.count(abandoned), len(status)])

        status_lines.append('\n')
        status_lines.append('Dataset %s' %wname)
        status_lines.append('_' * len(status_lines[-1]))
        status_lines.append('\n')
        batches = xsweep.get_image_range()
        status_lines.append(
          '%s: batches %d to %d' %(xsweep.get_name(), batches[0], batches[1]))
        status_lines.append('\n%s\n' %status)

  lines.append('\n')
  lines.append(tabulate(overall_table, headers, tablefmt='rst'))
  lines.append('\n')

  lines.extend(status_lines)

  return '\n'.join(lines)


if __name__ == '__main__':
  run()


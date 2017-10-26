#!/usr/bin/env python
# PyChef.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Main program for PyChef, using the PyChef class. Here is some example input:
#
# labin BASE=DOSE
# range width 5 max 605
# anomalous on
# resolution 1.9
#
# This is the same program interface as used to come from the program CHEF.
#

from __future__ import absolute_import, division

import os
import subprocess
import sys
import time

from xia2.Modules.PyChef.PyChef import PyChef

def banner():
  version = '1.0'
  user = os.environ.get('USER', '')
  now = time.asctime()

  print '#' * 60
  print '#' * 60
  print '#' * 60
  print '### PyCHEF                                           %s ###' % \
        version
  print '#' * 60
  print 'User: %s                  Run at: %s' % (user, now)

def get_hklin_files():
  '''From the command-line, get the list of hklin files. Set up thus
  as it may be useful externally. Assumes that the list of reflection
  files is passed in as HKLIN1 infl.mtz etc. N.B. could well be the case
  that HKLIN infl.mtz HKLIN lrem.mtz works just as well, though thats
  just a side-effect.'''

  hklin_files = []

  for j in range(1, len(sys.argv)):
    if 'HKLIN' in sys.argv[j].upper()[:5]:
      hklin = sys.argv[j + 1]

      if not os.path.abspath(hklin):
        hklin = os.path.join(os.getcwd(), hklin)

      if not os.path.exists(hklin):
        raise RuntimeError('hklin %s does not exist' % hklin)

      hklin_files.append(hklin)

  for hklin in hklin_files:
    print 'HKLIN: %s' % hklin

  return hklin_files

def get_number_cpus():
  '''Portably get the number of processor cores available.'''

  # Windows NT derived platforms

  if os.name == 'nt':
    return int(os.environ['NUMBER_OF_PROCESSORS'])

  # linux

  if os.path.exists('/proc/cpuinfo'):
    n_cpu = 0

    for record in open('/proc/cpuinfo', 'r').readlines():
      if not record.strip():
        continue
      if 'processor' in record.split()[0]:
        n_cpu += 1

    return n_cpu

  # os X

  output = subprocess.Popen(['system_profiler', 'SPHardwareDataType'],
                            stdout = subprocess.PIPE).communicate()[0]
  for record in output.split('\n'):
    if 'Total Number Of Cores' in record:
      return int(record.split()[-1])

  return -1

def parse_standard_input():
  '''Read and parse the standard input. Return as a dictionary.'''

  range_min = 0.0
  range_max = None
  range_width = None

  anomalous = False

  resolution_low = None
  resolution_high = None

  base_column = None
  base_unique = False

  title = None

  ncpu = get_number_cpus()

  for record in sys.stdin.readlines():

    record = record.split('!')[0].split('#')[0].strip()

    if not record:
      continue

    print '> %s' % record

    key = record[:4].upper()
    tokens = record.split()

    #### KEYWORD RESOLUTION ####

    if key == 'RESO':
      assert(len(tokens) < 4)
      assert(len(tokens) > 1)

      if len(tokens) == 2:
        resolution_high = float(tokens[1])

      elif len(tokens) == 3:
        resolution_a = float(tokens[1])
        resolution_b = float(tokens[2])
        resolution_high = min(resolution_a, resolution_b)
        resolution_low = max(resolution_a, resolution_b)

    #### KEYWORD RANGE ####

    elif key == 'RANG':
      assert(len(tokens) < 8)
      assert(len(tokens) > 2)

      for j in range(1, len(tokens)):
        subkey = tokens[j][:4].upper()
        if subkey == 'MIN':
          range_min = float(tokens[j + 1])
        elif subkey == 'MAX':
          range_max = float(tokens[j + 1])
        if subkey == 'WIDT':
          range_width = float(tokens[j + 1])

    #### KEYWORD ANOMALOUS ####

    elif key == 'ANOM':
      assert(len(tokens) < 3)

      anomalous = True

      if len(tokens) > 1:
        if tokens[1].upper() == 'OFF' or \
           tokens[1].upper() == 'FALSE' or \
           tokens[1].upper() == 'NO':
          anomalous = False

    #### KEYWORD LABIN ####

    elif key == 'LABI':
      assert(len(tokens) == 2)
      assert('BASE=' in tokens[1])

      base_column = tokens[1].replace('BASE=', '')

    #### KEYWORD TITLE ####

    elif key == 'TITL':
      keyword = tokens[0]
      title = record[len(keyword):].strip()

    #### KEYWORD NCPU

    elif key == 'NCPU':
      ncpu = int(record.split()[-1])

    #### KEYWORD UNIQ

    elif key == 'UNIQ':
      base_unique = True


  # check that these values are sound - where they are needed...
  # assert(base_column)

  # if we have BATCH we can guess the limit and range...
  # assert(range_max)
  # assert(range_width)

  # now drop this lot to a dictionary

  results = {
    'range_min':range_min,
    'range_max':range_max,
    'range_width':range_width,
    'anomalous':anomalous,
    'resolution_high':resolution_high,
    'resolution_low':resolution_low,
    'base_column':base_column,
    'title':title,
    'ncpu':ncpu,
    'base_unique':base_unique
    }

  return results

def main():
  '''Create and run a PyChef, reading the traditional format input from
  the command-line.'''

  banner()

  start_time = time.time()

  hklin_list = get_hklin_files()
  standard_input = parse_standard_input()

  pychef = PyChef()

  # copy the information across from the standard input dictionary to
  # the PyChef instance.

  pychef.set_ncpu(standard_input['ncpu'])

  print 'Using %d threads' % standard_input['ncpu']

  if standard_input['base_column']:
    pychef.set_base_column(standard_input['base_column'])

  if standard_input['base_unique']:
    pychef.set_base_unique(standard_input['base_unique'])

  if standard_input['range_max']:
    pychef.set_range(standard_input['range_min'],
                     standard_input['range_max'],
                     standard_input['range_width'])

  pychef.set_resolution(standard_input['resolution_high'],
                        standard_input['resolution_low'])
  pychef.set_anomalous(standard_input['anomalous'])

  if standard_input['title']:
    pychef.set_title(standard_input['title'])

  for hklin in hklin_list:
    pychef.add_hklin(hklin)

  # right, all set up - let's run some analysis - first the completeness
  # vs. dose for each input reflection file

  pychef.init()
  pychef.print_completeness_vs_dose()
  pychef.rcp()
  pychef.scp()
  pychef.rd()
  pychef.print_dose_profile()

  print ' PyChef: ** Normal termination **'
  print ' Times: Elapsed: %.1f' % (time.time() - start_time)

  return

if __name__ == '__main__':

  if False:

    import profile
    profile.run('main()')

  else:
    main()

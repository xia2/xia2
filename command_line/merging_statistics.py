from __future__ import absolute_import, division, print_function

import sys

import iotbx.phil
from iotbx.command_line import merging_statistics

master_params = iotbx.phil.parse(
  merging_statistics.master_phil, process_includes=True)

# override default parameters
master_params = master_params.fetch(source=iotbx.phil.parse(
  """\
use_internal_variance = False
eliminate_sys_absent = False
"""))

def run(args):
  merging_statistics.run(args, master_params=master_params)

if (__name__ == "__main__") :
  run(sys.argv[1:])

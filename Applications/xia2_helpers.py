
import os
import sys

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")


from Handlers.Streams import Chatter, Debug

import Handlers.Flags
import Handlers.Phil
import Handlers.CommandLine

def process_one_sweep(args):

  assert len(args) == 1
  args = args[0]
  sweep = args.sweep
  stop_after = args.stop_after
  cache = args.cache_output

  Handlers.Flags.Flags = args.flags
  Handlers.Phil.PhilIndex = args.phil_index
  Handlers.CommandLine.CommandLine = args.command_line

  from Handlers.Flags import Flags
  from Handlers.Phil import PhilIndex
  from Driver.DriverFactory import DriverFactory

  if cache:
    Chatter.cache()
    Debug.cache()

  params = PhilIndex.get_python_object()
  mp_params = params.xia2.settings.multiprocessing

  try:
    if stop_after == 'index':
      sweep.get_indexer_cell()
    else:
      sweep.get_integrater_intensities()
    sweep.serialize()
  except Exception, e:
    if Flags.get_failover():
      Chatter.write('Processing sweep %s failed: %s' % \
                    (sweep.get_name(), str(e)))
    else:
      raise
  finally:
    if cache:
      Chatter.uncache()
      Debug.uncache()

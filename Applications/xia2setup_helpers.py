#
# 03/MAR/16
# To resolve the naming conflict between this file and the entire xia2 module
# any xia2.* imports in this directory must instead be imported as ..*


# this must be defined in a separate file from xia2setup.py to be
# compatible with easy_mp.parallel_map with method="sge" when
# xia2setup.py is run as the __main__ program.
def get_sweep(args):
  import os
  from ..Schema.Sweep import SweepFactory

  assert len(args) == 1
  directory, template = os.path.split(args[0])

  try:
    sweeplist = SweepFactory(template, directory)

  except Exception, e:
    from ..Handlers.Streams import Debug
    Debug.write('Exception: %s (%s)' % (str(e), args[0]))
    return None

  return sweeplist


from __future__ import division
# LIBTBX_SET_DISPATCHER_NAME dev.xia2.rogues_gallery

import exceptions
import json
import os
import sys

# Needed to make xia2 imports work correctly FIXME we should make these go away
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2", optional=False)
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

def munch_rogues(rogues):
  rogue_reflections = []
  for record in open(rogues):
    if not record.strip():
      continue
    tokens = record.split()
    if not tokens[-1] == '*':
      continue
    x = float(tokens[15])
    y = float(tokens[16])
    b = int(tokens[6])
    h, k, l = map(int, tokens[3:6]) # don't forget these are probably reindexed
    rogue_reflections.append((b, x, y, h, k, l))

  return rogue_reflections

def magic_code():
  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  from dxtbx.model.experiment.experiment_list import ExperimentListFactory
  import cPickle as pickle
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1

  for xname in crystals:
    crystal = crystals[xname]

  scaler = crystal._get_scaler()

  epochs = scaler._sweep_handler.get_epochs()

  rogues = os.path.join(scaler.get_working_directory(),
                        xname, 'scale', 'ROGUES')

  munch_rogues(rogues)

  for epoch in epochs:
    si = scaler._sweep_handler.get_sweep_information(epoch)
    intgr = si.get_integrater()
    experiments_filename = intgr.get_integrated_experiments()
    reflections_filename = intgr.get_integrated_reflections()

if __name__ == '__main__':
  magic_code()

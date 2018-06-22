from __future__ import division, print_function

# some dev.xia2 hidden command-line option so muggles don't start to
# run this - also need a real major health warning...

# LIBTBX_SET_DISPATCHER_NAME dev.xia2.magic_scaling_doohicky

# wrap dials.symmetry and dials.scale with simple and rather dumb wrappers
# from xia2 droppings extract pickle and json files from integration
# plumb together all this stuff \o/

def find_pickle_and_json():
  import sys
  import os
  import json

  jsons = []
  for xia2 in sys.argv[1:]:
    assert os.path.exists(os.path.join(xia2, 'xia2.json')), xia2
    jsons.append(json.load(open(os.path.join(xia2, 'xia2.json'), 'r')))

  # extract out the information needed - for the moment just the merging
  # statistics though could later extract data collection statistics from
  # the image headers :TODO:

  integrate_pickles = []
  integrate_jsons = []

  for _j, j in enumerate(jsons):
    for x in j['_crystals']:
      s = j['_crystals'][x]['_scaler']['_scalr_integraters']
      for k in s:
        p = s[k]['_intgr_integrated_pickle']
        integrate_pickles.append(p)
        integrate_jsons.append(p.replace('.pickle', '_experiments.json'))

  for p, j in zip(integrate_pickles, integrate_jsons):
    assert(os.path.exists(p))
    assert(os.path.exists(j))

  args = integrate_pickles + integrate_jsons
  from dials.command_line.symmetry import run as symmetry_run
  sys.argv = [sys.argv[0]] + args
  symmetry_run([])

  from dials.command_line.scale import Script, phil_scope

  from dxtbx.serialize import load as load_experiment
  from dials.array_family import flex

  experiments = load_experiment.experiment_list('reindexed_experiments.json',
                                                check_format=False)
  reflections = flex.reflection_table.from_pickle(
    'reindexed_reflections.pickle')

  spells = ['unmerged_mtz=dials_unmerged.mtz',
            'optimise_errors=true']

  interp = phil_scope.command_line_argument_interpreter()
  for s in spells:
    phil_scope = phil_scope.fetch(interp.process_arg(s))
  params = phil_scope.extract()

  phil_scope.show()
  Script(params, experiments=experiments, reflections=[reflections]).run()

if __name__ == '__main__':
  find_pickle_and_json()

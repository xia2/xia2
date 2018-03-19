from __future__ import absolute_import, division, print_function

import json
import os
import sys

# LIBTBX_SET_DISPATCHER_NAME xia2.rogues_gallery


def munch_rogues(rogues):
  rogue_reflections = []
  for record in open(rogues):
    if not record.strip():
      continue
    tokens = record.split()
    if not tokens[-1] == '*':
      continue
    x, y, z = map(float, tokens[15:18])
    b = int(tokens[6])
    h, k, l = map(int, tokens[3:6]) # don't forget these are probably reindexed
    rogue_reflections.append((b, x, y, z, h, k, l))

  return rogue_reflections

def reconstruct_rogues(params):
  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  from dxtbx.model.experiment_list import ExperimentListFactory
  import cPickle as pickle
  import dials # because WARNING:root:No profile class gaussian_rs registered
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1

  for xname in crystals:
    crystal = crystals[xname]

  scaler = crystal._get_scaler()

  epochs = scaler._sweep_handler.get_epochs()

  rogues = os.path.join(scaler.get_working_directory(),
                        xname, 'scale', 'ROGUES')

  rogue_reflections = munch_rogues(rogues)

  batched_reflections = { }

  for epoch in epochs:
    si = scaler._sweep_handler.get_sweep_information(epoch)
    intgr = si.get_integrater()
    experiments = ExperimentListFactory.from_json_file(
      intgr.get_integrated_experiments())
    reflections = pickle.load(open(intgr.get_integrated_reflections()))
    batched_reflections[si.get_batch_range()] = (experiments, reflections,
                                                 si.get_sweep_name())

  # - look up reflection in reflection list, get bounding box
  # - pull pixels given from image set, flatten these, write out

  from dials.array_family import flex
  from annlib_ext import AnnAdaptor as ann_adaptor

  reflections_run = { }
  for run in batched_reflections:
    reflections_run[run] = []

  for rogue in rogue_reflections:
    b = rogue[0]
    for run in batched_reflections:
      if b >= run[0] and b <= run[1]:
        reflections_run[run].append(rogue)
        break

  for run_no, run in enumerate(reflections_run):
    experiment = batched_reflections[run][0]
    reflections = batched_reflections[run][1]
    name = batched_reflections[run][2]
    rogues = reflections_run[run]
    reference = flex.double()
    scan = experiment.scans()[0]
    images = experiment.imagesets()[0]
    for xyz in reflections['xyzcal.px']:
      reference.append(xyz[0])
      reference.append(xyz[1])
      reference.append(xyz[2])

    search = flex.double()
    for rogue in rogues:
      search.append(rogue[1])
      search.append(rogue[2])
      search.append(scan.get_array_index_from_angle(rogue[3]))

    ann = ann_adaptor(data=reference, dim=3, k=1)
    ann.query(search)

    keep = flex.bool(len(reflections), False)

    for j, rogue in enumerate(rogues):
      keep[ann.nn[j]] = True

    reflections = reflections.select(keep==True)

    if params.extract:
      reflections["shoebox"] = flex.shoebox(
        reflections["panel"],
        reflections["bbox"],
        allocate=True)
      reflections.extract_shoeboxes(images, verbose=False)

    if len(reflections_run) > 1:
      output = params.output.reflections.replace(
          '.pickle', '-%s.pickle' % name)
      print('Extracted %d rogue reflections for %s to %s' % \
        (len(reflections), name, output))
      reflections.as_pickle(output)
    else:
      output = params.output.reflections
      print('Extracted %d rogue reflections to %s' % \
        (len(reflections), output))
      reflections.as_pickle(output)


if __name__ == '__main__':
  from libtbx.phil import parse
  phil_scope = parse('''
rogues {
  extract = False
    .type = bool
    .help = "Extract shoebox pixels"

  output {
    reflections = 'xia2-rogues.pickle'
      .type = str
      .help = "The integrated output filename"
  }
}
  ''')
  interp = phil_scope.command_line_argument_interpreter(home_scope='rogues')
  for arg in sys.argv[1:]:
    cl_phil = interp.process(arg)
    phil_scope = phil_scope.fetch(cl_phil)
  params = phil_scope.extract()
  reconstruct_rogues(params.rogues)

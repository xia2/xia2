from __future__ import absolute_import, division

import math
import os
import sys

# LIBTBX_SET_DISPATCHER_NAME dev.xia2.pea_in_box


def reconstruct_peabox(params):
  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  from dxtbx.model.experiment_list import ExperimentListFactory
  import cPickle as pickle
  import dials # because WARNING:root:No profile class gaussian_rs registered
  from dials.array_family import flex
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1

  for xname in crystals:
    crystal = crystals[xname]

  scaler = crystal._get_scaler()

  epochs = scaler._sweep_handler.get_epochs()

  from xia2.command_line.rogues_gallery import munch_rogues
  from pprint import pprint

  batched_reflections = { }

  for epoch in epochs:
    si = scaler._sweep_handler.get_sweep_information(epoch)
    intgr = si.get_integrater()
    experiments = ExperimentListFactory.from_json_file(
      intgr.get_integrated_experiments())
    reflections = pickle.load(open(intgr.get_integrated_reflections()))
    batched_reflections[si.get_batch_range()] = (experiments, reflections,
                                                 si.get_sweep_name())
    from dials.util import debug_console
#   debug_console()

    good = reflections.get_flags(reflections.flags.integrated)
#   bad  = reflections.get_flags(reflections.flags.bad_spot)
    reflections = reflections.select(good)

    for r in reflections:
      flags = r['flags']
      r['flags'] = []
      for v, f in reflections.flags.values.iteritems():
        if flags & f:
          r['flags'].append(str(f))
      r['flags'] = ', '.join(r['flags'])
#     pprint(r)

    print "Collecting shoeboxes for %d reflections" % len(reflections)

    reflections["shoebox"] = flex.shoebox(reflections["panel"],reflections["bbox"],allocate=True)
    reflections.extract_shoeboxes(experiments.imagesets()[0], verbose=True)
    print "Consolidating..."

    sizes = {}
    for r in reflections:
      s = r['shoebox']
      a = s.size()
      if a not in sizes:
        sizes[a] = { 'sum': flex.float([0] * a[0] * a[1] * a[2]),
                     'weights': flex.int([0] * a[0] * a[1] * a[2]),
                     'count': 0 }
      s.mask.set_selected(s.data<0, 0)
      s.data.set_selected(s.mask==0, 0)
      s.background.set_selected(s.mask==0, 0)
      sizes[a]['sum'] += s.data - s.background
      sizes[a]['weights'] += s.mask
      sizes[a]['count'] += 1

    print len(sizes), "shoebox sizes extracted"

    for s, c in sizes.iteritems():
      print "%dx %s" % (c['count'], str(s))
      sdat = iter(c['sum'])
      wdat = iter(c['weights'])
      for z in range(s[0]):
        for y in range(s[1]):
          count = [ next(sdat) for x in range(s[2]) ]
          weight = [ next(wdat) for x in range(s[2]) ]
          truecount = ( 0 if w == 0 else 10 * c / w for c, w in zip(count, weight) )
          visualize = ( "X" if c < 0 else ("." if c < 10 else str(int(math.log10(c)))) for c in truecount )
          print "".join(visualize)
        print ""
      print ""
#   debug_console()

  # - look up reflection in reflection list, get bounding box
  # - pull pixels given from image set, flatten these, write out


if __name__ == '__main__':
  from libtbx.phil import parse
  phil_scope = parse('''
peabox {
  extract = False
    .type = bool
    .help = "Extract shoebox pixels"

  output {
    reflections = 'xia2-peabox.pickle'
      .type = str
      .help = "The integrated output filename"
  }
}
  ''')
  interp = phil_scope.command_line_argument_interpreter(home_scope='peabox')
  for arg in sys.argv[1:]:
    cl_phil = interp.process(arg)
    phil_scope = phil_scope.fetch(cl_phil)
  params = phil_scope.extract()
  reconstruct_peabox(params.peabox)

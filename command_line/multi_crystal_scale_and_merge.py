#!/usr/bin/env dials.python
from __future__ import absolute_import, division, print_function

from collections import OrderedDict
import logging


from libtbx.utils import Sorry

from dials.array_family import flex
from dials.util.options import OptionParser
from dials.util import log
from dials.util.options import flatten_experiments, flatten_reflections

from xia2.Modules.MultiCrystal import ScaleAndMerge

logger = logging.getLogger('xia2.multi_crystal_scale_and_merge')

help_message = '''
'''


def run():

  # The script usage
  usage  = "usage: xia2.multi_crystal_scale_and_merge [options] [param.phil] " \
           "experiments1.json experiments2.json reflections1.pickle " \
           "reflections2.pickle..."

  # Create the parser
  parser = OptionParser(
    usage=usage,
    phil=ScaleAndMerge.phil_scope,
    read_reflections=True,
    read_experiments=True,
    check_format=False,
    epilog=help_message)

  # Parse the command line
  params, options = parser.parse_args(show_diff_phil=True)

  # Configure the logging

  for name in ('xia2', 'dials'):
    log.config(
      info='multi_crystal_scale_and_merge.log',
      #debug=params.output.debug_log
      name=name)
  from dials.util.version import dials_version
  logger.info(dials_version())

  # Try to load the models and data
  if len(params.input.experiments) == 0:
    logger.info("No Experiments found in the input")
    parser.print_help()
    return
  if len(params.input.reflections) == 0:
    logger.info("No reflection data found in the input")
    parser.print_help()
    return
  try:
    assert len(params.input.reflections) == len(params.input.experiments)
  except AssertionError:
    raise Sorry("The number of input reflections files does not match the "
      "number of input experiments")

  expt_filenames = OrderedDict((e.filename, e.data) for e in params.input.experiments)
  refl_filenames = OrderedDict((r.filename, r.data) for r in params.input.reflections)

  experiments = flatten_experiments(params.input.experiments)
  reflections = flatten_reflections(params.input.reflections)

  reflections_all = flex.reflection_table()
  assert len(reflections) == 1 or len(reflections) == len(experiments)
  if len(reflections) > 1:
    for i, (expt, refl) in enumerate(zip(experiments, reflections)):
      expt.identifier = '%i' % i
      refl['identifier'] = flex.std_string(refl.size(), expt.identifier)
      refl['id'] = flex.int(refl.size(), i)
      reflections_all.extend(refl)
      reflections_all.experiment_identifiers()[i] = expt.identifier
  else:
    reflections_all = reflections[0]
    assert 'identifier' in reflections_all
    assert len(set(reflections_all['identifier'])) == len(experiments)

  assert reflections_all.are_experiment_identifiers_consistent(experiments)

  if params.identifiers is not None:
    identifiers = []
    for identifier in params.identifiers:
      identifiers.extend(identifier.split(','))
    params.identifiers = identifiers
  scaled = ScaleAndMerge.MultiCrystalScale(experiments, reflections_all, params)

if __name__ == '__main__':
  run()

from __future__ import division
import sys

import iotbx.phil
from libtbx.phil import command_line
from scitbx.array_family import flex

from xia2.Handlers.Streams import Chatter, Debug

master_phil_scope = iotbx.phil.parse("""\
hklout = truncate.mtz
  .type = path
include scope cctbx.french_wilson.master_phil
""", process_includes=True)


class french_wilson(object):

  def __init__(self, mtz_file, params=None):

    from iotbx.reflection_file_reader import any_reflection_file
    result = any_reflection_file(mtz_file)
    assert result.file_type() == 'ccp4_mtz'
    mtz_object = result.file_content()

    i_plus_minus = None
    i_mean = None

    for ma in result.as_miller_arrays(merge_equivalents=False):
      print ma.info().labels
      if ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
        assert ma.anomalous_flag()
        i_plus_minus = ma
      elif ma.info().labels == ['IMEAN', 'SIGIMEAN']:
        assert not ma.anomalous_flag()
        i_mean = ma

    assert i_mean.is_xray_intensity_array()
    f_mean = i_mean.french_wilson(params=params)
    assert f_mean.is_xray_amplitude_array()

    mtz_dataset = mtz_object.crystals()[1].datasets()[0]

    matches = i_mean.match_indices(f_mean)
    nan = float('nan')
    f_double = flex.double(i_mean.size(), nan)
    sigf_double = flex.double(i_mean.size(), nan)

    sel = matches.pair_selection(0)
    f_double.set_selected(sel, f_mean.data())
    sigf_double.set_selected(sel, f_mean.sigmas())
    mtz_dataset.add_column('F', 'F').set_values(f_double.as_float())
    mtz_dataset.add_column('SIGF', 'F').set_values(sigf_double.as_float())
    mtz_object.add_history('cctbx.french_wilson analysis')
    mtz_object.write(params.hklout)


def run(args):

  cmd_line = command_line.argument_interpreter(master_params=master_phil_scope)
  working_phil, args = cmd_line.process_and_fetch(
    args=args, custom_processor="collect_remaining")
  working_phil.show()
  params = working_phil.extract()
  assert len(args) == 1

  french_wilson(args[0], params=params)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])

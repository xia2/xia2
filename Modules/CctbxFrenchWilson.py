from __future__ import absolute_import, division, print_function

import sys

import iotbx.phil
from iotbx.reflection_file_reader import any_reflection_file
from libtbx.phil import command_line
from mmtbx.scaling import data_statistics

master_phil_scope = iotbx.phil.parse(
    """\
hklout = truncate.mtz
  .type = path
anomalous = False
  .type = bool
include scope cctbx.french_wilson.master_phil
""",
    process_includes=True,
)


class french_wilson(object):
    def __init__(self, mtz_file, params=None):
        print("Reading reflections from %s" % mtz_file)

        result = any_reflection_file(mtz_file)
        assert result.file_type() == "ccp4_mtz"
        mtz_object = result.file_content()
        mtz_object.show_summary()

        mtz_dataset = mtz_object.crystals()[1].datasets()[0]

        intensities = None
        for ma in result.as_miller_arrays(merge_equivalents=False):
            if params.anomalous and ma.info().labels == [
                "I(+)",
                "SIGI(+)",
                "I(-)",
                "SIGI(-)",
            ]:
                assert ma.anomalous_flag()
                intensities = (
                    ma.merge_equivalents().array()
                )  # XXX why is this necessary?
                break
            elif ma.info().labels == ["IMEAN", "SIGIMEAN"]:
                assert not ma.anomalous_flag()
                intensities = ma
                break

        assert intensities is not None, "No intensities found in input mtz file"

        assert intensities.is_xray_intensity_array()
        amplitudes = intensities.french_wilson(params=params)
        assert amplitudes.is_xray_amplitude_array()

        if not intensities.space_group().is_centric():
            merged_intensities = intensities.merge_equivalents().array()
            wilson_scaling = data_statistics.wilson_scaling(
                miller_array=merged_intensities, n_residues=200
            )  # XXX default n_residues?
            wilson_scaling.show()
            print()

            mtz_dataset = mtz_object.crystals()[1].datasets()[0]
            if "F" in mtz_dataset.column_labels():
                assert (
                    "SIGF" in mtz_dataset.column_labels()
                ), "Input file contains F but no SIGF column"
                F = mtz_dataset.columns()[mtz_dataset.column_labels().index("F")]
                SIGF = mtz_dataset.columns()[mtz_dataset.column_labels().index("SIGF")]
                F.set_reals(miller_indices=amplitudes.indices(), data=amplitudes.data())
                SIGF.set_reals(
                    miller_indices=amplitudes.indices(), data=amplitudes.sigmas()
                )
            else:
                mtz_dataset.add_miller_array(amplitudes, column_root_label="F")

        mtz_object.add_history("cctbx.french_wilson analysis")
        print("Writing reflections to %s" % (params.hklout))
        mtz_object.show_summary()
        mtz_object.write(params.hklout)


def run(args):
    cmd_line = command_line.argument_interpreter(master_params=master_phil_scope)
    working_phil, args = cmd_line.process_and_fetch(
        args=args, custom_processor="collect_remaining"
    )
    working_phil.show()
    params = working_phil.extract()
    assert len(args) == 1

    french_wilson(args[0], params=params)


if __name__ == "__main__":
    run(sys.argv[1:])

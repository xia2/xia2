import io
import logging

from iotbx.reflection_file_reader import any_reflection_file
from mmtbx.scaling import data_statistics

logger = logging.getLogger("xia2.Modules.CctbxFrenchWilson")


def do_french_wilson(mtz_file, hklout, anomalous=False):
    logger.debug("Reading reflections from %s", mtz_file)

    result = any_reflection_file(mtz_file)
    assert result.file_type() == "ccp4_mtz"

    mtz_object = result.file_content()
    output = io.StringIO()
    mtz_object.show_summary(out=output)

    for ma in result.as_miller_arrays(merge_equivalents=False):
        if anomalous and ma.info().labels == ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"]:
            assert ma.anomalous_flag()
            intensities = ma.merge_equivalents().array()  # XXX why is this necessary?
        elif ma.info().labels == ["IMEAN", "SIGIMEAN"]:
            assert not ma.anomalous_flag()
            intensities = ma
        else:
            intensities = None

        if intensities:
            assert intensities.is_xray_intensity_array()
            amplitudes = intensities.french_wilson(log=output)
            assert amplitudes.is_xray_amplitude_array()

            dano = None
            if amplitudes.anomalous_flag():
                dano = amplitudes.anomalous_differences()

            if not intensities.space_group().is_centric():
                merged_intensities = intensities.merge_equivalents().array()
                try:
                    wilson_scaling = data_statistics.wilson_scaling(
                        miller_array=merged_intensities, n_residues=200
                    )  # XXX default n_residues?
                except (IndexError, RuntimeError) as e:
                    logger.error(
                        "\n"
                        "Error encountered during Wilson statistics calculation:\n"
                        "Perhaps there are too few unique reflections.\n"
                        "%s",
                        e,
                        exc_info=True,
                    )
                else:
                    wilson_scaling.show(out=output)

            mtz_dataset = mtz_object.crystals()[1].datasets()[0]
            mtz_dataset.add_miller_array(amplitudes, column_root_label="F")
            if dano is not None:
                mtz_dataset.add_miller_array(
                    dano, column_root_label="DANO", column_types="DQ"
                )
    mtz_object.add_history("cctbx.french_wilson analysis")
    mtz_object.show_summary(out=output)
    logger.debug("Writing reflections to %s", hklout)
    mtz_object.write(hklout)
    return output.getvalue()

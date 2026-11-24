from __future__ import annotations

import iotbx.mtz
import pytest
from cctbx import crystal, miller
from cctbx.array_family import flex

from xia2.Modules import MtzUtils

SYMMETRY = crystal.symmetry((50, 60, 70, 90, 90, 90), "P212121")


def _make_merged_mtz(path, dataset_name, wavelength, d_min, fraction=1.0):
    """Write a merged MTZ file resembling the xia2 per-wavelength output."""
    flex.set_random_seed(0)
    miller_set = miller.build_set(SYMMETRY, anomalous_flag=True, d_min=d_min)
    if fraction < 1:
        miller_set = miller_set.select(flex.random_bool(miller_set.size(), fraction))
    intensities = miller_set.array(
        data=flex.random_double(miller_set.size()) * 100,
        sigmas=flex.double(miller_set.size(), 1),
    ).set_observation_type_xray_intensity()
    mtz_dataset = intensities.as_mtz_dataset(
        column_root_label="I", wavelength=wavelength
    )
    mtz_dataset.mtz_crystal().set_name("bar")
    mtz_dataset.mtz_crystal().set_project_name("foo")
    mtz_dataset.set_name(dataset_name)
    mtz_dataset.add_miller_array(
        intensities.average_bijvoet_mates(), column_root_label="IMEAN"
    )
    amplitudes = intensities.as_amplitude_array()
    mtz_dataset.add_miller_array(amplitudes, column_root_label="F")
    mtz_dataset.add_miller_array(
        amplitudes.anomalous_differences(),
        column_root_label="DANO",
        column_types="DQ",
    )
    mtz_dataset.mtz_object().write(str(path))
    return str(path)


def _free_flags(path):
    (flags,) = [
        ma
        for ma in iotbx.mtz.object(str(path)).as_miller_arrays()
        if ma.info().labels == ["FreeR_flag"]
    ]
    return flags


def test_add_free_flags(tmp_path):
    hklin = _make_merged_mtz(tmp_path / "scaled.mtz", "NATIVE", 0.98, 2.0)
    hklout = tmp_path / "free.mtz"
    MtzUtils.add_free_flags(hklin, str(hklout), free_fraction=0.05)

    mtz_obj = iotbx.mtz.object(str(hklout))
    assert mtz_obj.n_reflections() == iotbx.mtz.object(hklin).n_reflections()
    assert mtz_obj.get_column("FreeR_flag").type() == "I"
    flags = _free_flags(hklout)
    # every reflection has a flag, with CCP4 conventions (0..19, 0 = free)
    assert flags.size() == mtz_obj.n_reflections()
    assert flex.min(flags.data()) == 0
    assert flex.max(flags.data()) == 19
    assert (flags.data() == 0).count(True) / flags.size() == pytest.approx(
        0.05, abs=0.01
    )
    # FreeR_flag goes in the HKL_base dataset, as with CCP4 freerflag
    hkl_base = mtz_obj.crystals()[0]
    assert hkl_base.name() == "HKL_base"
    assert "FreeR_flag" in [c.label() for c in hkl_base.datasets()[0].columns()]
    # the original data are unchanged
    assert "IMEAN" in mtz_obj.column_labels()
    assert mtz_obj.crystals()[1].name() == "bar"

    with pytest.raises(RuntimeError, match="already contains a FreeR_flag"):
        MtzUtils.add_free_flags(str(hklout), str(tmp_path / "again.mtz"))


def test_copy_free_flags(tmp_path):
    # reference flags at lower resolution than the data, with 10% free
    # (flags 0..9) rather than the default 5%
    reference = _make_merged_mtz(tmp_path / "ref_data.mtz", "REF", 1.0, 2.5)
    freein = tmp_path / "ref.mtz"
    MtzUtils.add_free_flags(reference, str(freein), free_fraction=0.1)

    hklin = _make_merged_mtz(tmp_path / "scaled.mtz", "NATIVE", 0.98, 2.0)
    hklout = tmp_path / "free.mtz"
    MtzUtils.copy_free_flags(str(freein), hklin, str(hklout))

    reference_flags = _free_flags(freein)
    flags = _free_flags(hklout)
    assert flags.size() == iotbx.mtz.object(str(hklout)).n_reflections()
    # existing flags are preserved...
    common_reference, common = reference_flags.common_sets(flags)
    assert common.size() == reference_flags.size()
    assert (common_reference.data() == common.data()).all_eq(True)
    # ... and extended to the higher resolution reflections, with the same
    # range of flag values as the reference
    assert flags.d_min() == pytest.approx(2.0, abs=0.01)
    extension = flags.lone_set(reference_flags)
    assert extension.size() > 0
    assert flex.min(extension.data()) == 0
    assert flex.max(extension.data()) == 9
    assert (flags.data() == 0).count(True) / flags.size() == pytest.approx(
        0.1, abs=0.015
    )


def test_merge_wavelength_files(tmp_path):
    hklin = {
        "WAVE1": _make_merged_mtz(tmp_path / "w1.mtz", "WAVE1", 0.97, 2.0, 0.9),
        "WAVE2": _make_merged_mtz(tmp_path / "w2.mtz", "WAVE2", 0.98, 2.2, 0.95),
    }
    hklout = tmp_path / "merged.mtz"
    MtzUtils.merge_wavelength_files(hklin, str(hklout))

    mtz_obj = iotbx.mtz.object(str(hklout))
    assert mtz_obj.crystals()[0].name() == "HKL_base"
    crystal = mtz_obj.crystals()[1]
    assert (crystal.project_name(), crystal.name()) == ("foo", "bar")
    datasets = {d.name(): d for d in crystal.datasets()}
    assert set(datasets) == {"WAVE1", "WAVE2"}
    assert datasets["WAVE1"].wavelength() == pytest.approx(0.97)
    assert datasets["WAVE2"].wavelength() == pytest.approx(0.98)

    for wave, path in hklin.items():
        # columns are renamed <label>_<wavelength name>, as CCP4 cad would
        input_columns = {
            c.label(): c.type()
            for c in iotbx.mtz.object(path).columns()
            if c.type() != "H"
        }
        for label, column_type in input_columns.items():
            assert mtz_obj.get_column(f"{label}_{wave}").type() == column_type

        # and the data are unchanged
        input_arrays = {
            tuple(ma.info().labels): ma
            for ma in iotbx.mtz.object(path).as_miller_arrays()
        }
        output_arrays = {
            tuple(ma.info().labels): ma for ma in mtz_obj.as_miller_arrays()
        }
        expected = input_arrays[("IMEAN", "SIGIMEAN")]
        actual = output_arrays[(f"IMEAN_{wave}", f"SIGIMEAN_{wave}")]
        assert actual.size() == expected.size()
        expected, actual = expected.common_sets(actual)
        assert actual.data() == pytest.approx(expected.data(), abs=1e-3)

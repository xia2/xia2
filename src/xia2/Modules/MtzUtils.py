from __future__ import annotations

import logging
import os

import iotbx.mtz
from cctbx import miller, r_free_utils, sgtbx

from xia2.lib.SymmetryLib import clean_reindex_operator

logger = logging.getLogger("xia2.Modules.MtzUtils")


def space_group_from_mtz(file_name):
    mtz_obj = iotbx.mtz.object(file_name=file_name)
    return mtz_obj.space_group()


def space_group_name_from_mtz(file_name):
    return space_group_from_mtz(file_name).type().lookup_symbol()


def space_group_number_from_mtz(file_name):
    return space_group_from_mtz(file_name).type().number()


def batches_from_mtz(file_name):
    mtz_obj = iotbx.mtz.object(file_name=file_name)
    return [batch.num() for batch in mtz_obj.batches()]


def nref_from_mtz(file_name):
    mtz_obj = iotbx.mtz.object(file_name=file_name)
    return mtz_obj.n_reflections()


def reindex(hklin, hklout, change_of_basis_op, space_group=None):
    if not isinstance(change_of_basis_op, sgtbx.change_of_basis_op):
        change_of_basis_op = sgtbx.change_of_basis_op(
            str(clean_reindex_operator(change_of_basis_op))
        )
    if space_group is not None and not isinstance(space_group, sgtbx.space_group):
        space_group = sgtbx.space_group_info(str(space_group)).group()

    mtz_obj = iotbx.mtz.object(file_name=hklin)
    original_index_miller_indices = mtz_obj.extract_original_index_miller_indices()
    reindexed_miller_indices = change_of_basis_op.apply(original_index_miller_indices)
    if space_group is not None:
        mtz_obj.set_space_group(space_group)
    mtz_obj.replace_original_index_miller_indices(reindexed_miller_indices)
    mtz_obj.write(hklout)


def _first_dataset(mtz_obj):
    """Return the first dataset that is not in the HKL_base crystal."""
    for crystal in mtz_obj.crystals():
        if crystal.name() == "HKL_base":
            continue
        for dataset in crystal.datasets():
            return dataset
    raise RuntimeError("No datasets found in MTZ file")


def _miller_set_from_mtz(mtz_obj):
    return miller.set(
        crystal_symmetry=_first_dataset(mtz_obj).mtz_crystal().crystal_symmetry(),
        indices=mtz_obj.extract_miller_indices(),
        anomalous_flag=False,
    )


def _generate_ccp4_free_flags(miller_set, free_fraction):
    """Generate CCP4-style R-free flags (integers 0..N-1, 0 = free) for
    every reflection in miller_set, keeping lattice-symmetry related
    reflections in the same set."""
    return miller_set.generate_r_free_flags(
        fraction=free_fraction,
        max_free=None,
        use_lattice_symmetry=True,
        format="ccp4",
    )


def _write_free_flags(mtz_obj, flags, hklout, history):
    # CCP4 freerflag puts FreeR_flag in the HKL_base dataset
    crystals = mtz_obj.crystals()
    if crystals[0].name() == "HKL_base" and crystals[0].datasets():
        dataset = crystals[0].datasets()[0]
    else:
        dataset = _first_dataset(mtz_obj)
    dataset.add_miller_array(flags, column_root_label="FreeR_flag")
    mtz_obj.add_history(history)
    mtz_obj.write(hklout)


def add_free_flags(hklin, hklout, free_fraction=0.05):
    """Add a FreeR_flag column to hklin -> hklout, assigning a flag to every
    reflection in the file. A replacement for CCP4 freerflag."""
    mtz_obj = iotbx.mtz.object(file_name=hklin)
    if "FreeR_flag" in mtz_obj.column_labels():
        raise RuntimeError(f"{hklin} already contains a FreeR_flag column")
    flags = _generate_ccp4_free_flags(_miller_set_from_mtz(mtz_obj), free_fraction)
    _write_free_flags(
        mtz_obj, flags, hklout, f"xia2: added FreeR_flag (fraction {free_fraction})"
    )
    return hklout


def copy_free_flags(freein, hklin, hklout):
    """Copy the free-R flags from the reference file freein into hklin ->
    hklout, as a FreeR_flag column. Reflections in hklin with no flag in the
    reference are given new flags, with the same range of flag values as the
    reference (as CCP4 freerflag complete would). A replacement for CCP4
    cad + freerflag."""
    from xia2.Modules.FindFreeFlag import FindFreeFlag

    free_column = FindFreeFlag(freein)
    reference = [
        ma
        for ma in iotbx.mtz.object(file_name=freein).as_miller_arrays()
        if ma.info().labels == [free_column]
    ]
    if len(reference) != 1:
        raise RuntimeError(f"Could not read {free_column} from {freein}")
    reference = reference[0]
    if not r_free_utils.looks_like_ccp4_flags(reference):
        raise RuntimeError(
            f"{free_column} in {freein} does not look like CCP4-style flags"
        )

    mtz_obj = iotbx.mtz.object(file_name=hklin)
    if "FreeR_flag" in mtz_obj.column_labels():
        raise RuntimeError(f"{hklin} already contains a FreeR_flag column")
    miller_set = _miller_set_from_mtz(mtz_obj)

    if miller_set.space_group() != reference.space_group():
        logger.warning(
            "Space group in %s (%s) differs from %s (%s)",
            freein,
            reference.space_group_info(),
            hklin,
            miller_set.space_group_info(),
        )
    reference = reference.customized_copy(
        crystal_symmetry=miller_set.crystal_symmetry()
    ).map_to_asu()

    matches = miller.match_indices(miller_set.indices(), reference.indices())
    pairs = matches.pairs()
    copied = reference.select(pairs.column(1)).customized_copy(
        indices=miller_set.indices().select(pairs.column(0))
    )

    missing = miller_set.select(matches.singles(0))
    n_missing = missing.size()
    if n_missing:
        # match the free fraction of the reference: flags 0..N-1, 0 = free
        free_fraction = 1.0 / (max(reference.data()) + 1)
        new_flags = _generate_ccp4_free_flags(missing, free_fraction)
        flags = copied.concatenate(new_flags)
    else:
        flags = copied

    logger.debug(
        "Copied %d FreeR flags from %s; generated %d new flags",
        copied.size(),
        freein,
        n_missing,
    )
    _write_free_flags(
        mtz_obj,
        flags.customized_copy(info=None),
        hklout,
        f"xia2: FreeR_flag copied from {os.path.basename(freein)}",
    )
    return hklout


def merge_wavelength_files(hklin_dict, hklout):
    """Combine several merged MTZ files (one per wavelength) into a single
    multi-dataset MTZ file. Each column is renamed as <column>_<suffix>,
    where suffix is the key in hklin_dict. A replacement for CCP4 cad."""
    combined = None
    crystal = None
    for suffix, hklin in hklin_dict.items():
        mtz_in = iotbx.mtz.object(file_name=hklin)
        source_dataset = _first_dataset(mtz_in)
        source_crystal = source_dataset.mtz_crystal()
        if combined is None:
            combined = iotbx.mtz.object()
            combined.set_title(mtz_in.title())
            combined.set_space_group_info(mtz_in.space_group_info())
            # as CCP4 cad would, with an HKL_base crystal for the indices
            hkl_base = combined.add_crystal(
                name="HKL_base",
                project_name="HKL_base",
                unit_cell=source_crystal.unit_cell(),
            )
            hkl_base.add_dataset(name="HKL_base", wavelength=0)
            crystal = combined.add_crystal(
                name=source_crystal.name(),
                project_name=source_crystal.project_name(),
                unit_cell=source_crystal.unit_cell(),
            )
        dataset = crystal.add_dataset(
            name=source_dataset.name(), wavelength=source_dataset.wavelength()
        )

        miller_set = miller.set(
            crystal_symmetry=source_crystal.crystal_symmetry(),
            indices=mtz_in.extract_miller_indices(),
            anomalous_flag=False,
        )
        for column in source_dataset.columns():
            if column.type() == "H":
                continue
            values, selection_valid = column.extract_values_and_selection_valid(
                -1
            ).as_tuple()
            values = values.as_double()
            if column.type() in ("I", "B", "Y"):
                values = values.iround()
            ma = miller_set.array(data=values).select(selection_valid)
            dataset.add_miller_array(
                ma,
                column_root_label=f"{column.label()}_{suffix}",
                column_types=column.type(),
            )
    combined.add_history("xia2: combined wavelengths " + " ".join(hklin_dict))
    combined.write(hklout)
    return hklout

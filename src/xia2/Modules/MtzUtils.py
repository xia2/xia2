import iotbx.mtz
from cctbx import sgtbx
from xia2.lib.SymmetryLib import clean_reindex_operator


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

import iotbx.mtz


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
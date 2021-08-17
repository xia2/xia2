# Replacement for CCP4 program rebatch, using cctbx Python.


import itertools

from cctbx.array_family import flex
from iotbx import mtz


def compact_batches(batches):
    """Pack down batches to lists of continuous batches."""

    return [
        [x[1] for x in g]
        for k, g in itertools.groupby(enumerate(batches), lambda i_x: i_x[0] - i_x[1])
    ]


def rebatch(
    hklin,
    hklout,
    first_batch=None,
    add_batch=None,
    include_range=None,
    exclude_range=None,
    exclude_batches=None,
    pname=None,
    xname=None,
    dname=None,
):
    """Need to implement: include batch range, exclude batches, add N to
    batches, start batches at N."""
    if include_range is None:
        include_range = []
    if exclude_range is None:
        exclude_range = []

    if first_batch is not None and add_batch is not None:
        raise RuntimeError("both first and add specified")

    assert not (len(include_range) and len(exclude_range))
    assert not (len(exclude_range) and len(exclude_batches))
    assert not (len(include_range) and first_batch)
    assert not (len(exclude_range) and first_batch)

    if exclude_batches:
        exclude_range = [(b[0], b[-1]) for b in compact_batches(exclude_batches)]

    mtz_obj = mtz.object(file_name=hklin)

    batch_column = None

    for crystal in mtz_obj.crystals():
        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == "BATCH":
                    batch_column = column

    if not batch_column:
        raise RuntimeError("no BATCH column found in %s" % hklin)

    batches = [b.num() for b in mtz_obj.batches()]
    batch_column_values = batch_column.extract_values(not_a_number_substitute=-1)

    valid = flex.bool()
    offset = 0

    if exclude_range:
        exclude_sel = flex.bool(batch_column_values.size(), False)
        for (start, end) in exclude_range:
            exclude_sel.set_selected(
                (batch_column_values >= start) & (batch_column_values <= end), True
            )
        mtz_obj.delete_reflections(exclude_sel.iselection())

    elif include_range:
        exclude_sel = flex.bool(batch_column_values.size(), True)
        for (start, end) in include_range:
            exclude_sel.set_selected(
                (batch_column_values >= start) & (batch_column_values <= end), False
            )
        mtz_obj.delete_reflections(exclude_sel.iselection())

    # modify batch columns, and also the batch headers

    elif first_batch is not None or add_batch is not None:
        if first_batch is not None:
            offset = first_batch - min(batches)
        else:
            offset = add_batch

        batch_column_values = batch_column_values + offset

        for batch in mtz_obj.batches():
            batch.set_num(int(batch.num() + offset))

        # done modifying

        batch_column.set_values(values=batch_column_values, selection_valid=valid)

    if pname and xname and dname:
        for c in mtz_obj.crystals():
            for d in c.datasets():
                d.set_name(dname)
            if c.name() == "HKL_base":
                continue
            c.set_project_name(pname)
            c.set_name(xname)

    # and write this lot out as hklout

    mtz_obj.write(file_name=hklout)

    new_batches = (min(batches) + offset, max(batches) + offset)

    return new_batches

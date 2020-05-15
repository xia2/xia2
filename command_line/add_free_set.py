import sys
import random

from iotbx import mtz
from scitbx.array_family import flex


def random_selection(fraction, list):
    selected = set()

    while len(selected) < fraction * len(list):
        selected.add(random.choice(list))

    return selected


def add_free_set(hklin, fraction, hklout_work, hklout_free):
    # open up the reflection file

    mtz_obj = mtz.object(hklin)
    mi = mtz_obj.extract_miller_indices()

    # the calculate the list of unique miller indices I want to assign
    # as "free"

    free_set = random_selection(fraction, list(set(mi)))

    # now read through and assign those as free by adding 50 to FLAG

    flag_column = None

    for crystal in mtz_obj.crystals():
        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == "FLAG":
                    flag_column = column

    if flag_column:
        flag_values = flag_column.extract_values(not_a_number_substitute=0.0)
    else:
        flag_values = flex.double(len(mi), 0)

    free = 0
    for j, hkl in enumerate(mi):
        if hkl in free_set:
            flag_values[j] += 50
            free += 1
    print("%d observations / %d free" % (len(mi), free))

    # now write this back out to a test reflection file

    if flag_column:
        flag_column.set_values(flag_values)
    else:
        flag_column = dataset.add_column("FLAG", "I")
        flag_column.set_values(flag_values.as_float())

    mtz_obj.write(hklout_work)

    # now write out the test set

    for j, hkl in enumerate(mi):
        if hkl in free_set:
            flag_values[j] -= 50
        else:
            flag_values[j] += 50

    flag_column.set_values(flag_values.as_float())

    mtz_obj.write(hklout_free)


if __name__ == "__main__":
    add_free_set(sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4])

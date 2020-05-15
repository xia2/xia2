import sys

from iotbx.reflection_file_reader import any_reflection_file
from scitbx.array_family import flex

# LIBTBX_SET_DISPATCHER_NAME dev.xia2.file_statistics


m = any_reflection_file(sys.argv[1]).file_content()
sg = m.space_group()
mi = m.extract_miller_indices()
mas = m.as_miller_arrays()

absent = flex.bool([sg.is_sys_absent(indx) for indx in mi])

intensities = None
for ma in mas:
    if ma.is_xray_intensity_array():
        intensities = ma
        break

assert intensities, "intensity data not found in %s" % sys.argv[1]

print("Removing %d absent reflections" % absent.count(True))
intensities = intensities.select(~absent)

i_over_sig = intensities.data() / intensities.sigmas()
hist = flex.histogram(i_over_sig, n_slots=50)

print("I/sig(I)  N")

for centre, value in zip(hist.slot_centers(), hist.slots()):
    print("%5.1f %d" % (centre, value))

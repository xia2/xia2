# cbfdump.py 
# 
# A little jiffy to read a cbf file and tell us what it finds...
# 
# Based on pycbf from the CBFlib distribution.
# 

import sys
import pycbf
import math

cbf_handle = pycbf.cbf_handle_struct()
cbf_handle.read_file(sys.argv[1], pycbf.MSG_DIGEST)
cbf_handle.rewind_datablock()

# help(cbf_handle)

# first rummage through the cbf and find the block which is marked
# diffrn_data_frame

num_categories = cbf_handle.count_categories()

ddframe = -1

for j in range(num_categories):
    cbf_handle.select_category(j)
    if cbf_handle.category_name()== 'diffrn_data_frame':
        ddframe = j

assert(ddframe >= 0)

# help(cbf_handle)

detector = cbf_handle.construct_detector(0)

beam = detector.get_beam_center()
beam_pixel = tuple(beam[:2])
beam_mm = tuple(beam[2:])
detector_normal = tuple(detector.get_detector_normal())
distance = detector.get_detector_distance()
pixel = (detector.get_inferred_pixel_size(1),
         detector.get_inferred_pixel_size(2))

gonio = cbf_handle.construct_goniometer()

# help(gonio)

axis = tuple(gonio.get_rotation_axis())
angles = tuple(gonio.get_rotation_range())

date = cbf_handle.get_datestamp()
time = cbf_handle.get_timestamp()
size = tuple(cbf_handle.get_image_size(0))
exposure = cbf_handle.get_integration_time()
overload = cbf_handle.get_overload(0)
wavelength = cbf_handle.get_wavelength()

print 'Detector information:'
print 'Dimensions: %d %d' % size
print 'Pixel size: %.3f %.3f' % pixel
print 'Distance:   %.1f' % distance
print 'Normal:     %.2f %.2f %.2f' % detector_normal
print 'Exposure:   %.2f' % exposure
print 'Overload:   %d' % int(overload)
print 'Beam:       %.2f %.2f' % beam_mm

print 'Goniometer:'
print 'Axis:       %.2f %.2f %.2f' % axis
print 'Angles:     %.2f %.2f' % angles

print 'Experiment:'
print 'Wavelength: %.5f' % wavelength

# now need to dig out the detector axes

# help(cbf_handle)

# perhaps bodge this by looking at the displacements of pixels in the
# fast and slow directions?

origin = detector.get_pixel_coordinates(0, 0)
fast = detector.get_pixel_coordinates(1, 0)
slow = detector.get_pixel_coordinates(0, 1)

dfast = [fast[j] - origin[j] for j in range(3)]
dslow = [slow[j] - origin[j] for j in range(3)]

lfast = math.sqrt(sum([dfast[j] * dfast[j] for j in range(3)]))
lslow = math.sqrt(sum([dslow[j] * dslow[j] for j in range(3)]))

fast = tuple([dfast[j] / lfast for j in range(3)])
slow = tuple([dslow[j] / lslow for j in range(3)])

print 'Fast direction: %.2f %.2f %.2f' % fast
print 'Slow direction: %.2f %.2f %.2f' % slow

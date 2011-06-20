# cbfdump.py 
# 
# A little jiffy to read a cbf file and tell us what it finds...
# 
# Based on pycbf from the CBFlib distribution.
# 

import sys
import pycbf
import math

def cbfdump(cbf_image, do_print = False):

    cbf_handle = pycbf.cbf_handle_struct()
    cbf_handle.read_file(cbf_image, pycbf.MSG_DIGEST)

    cbf_handle.rewind_datablock()
    
    detector = cbf_handle.construct_detector(0)

    beam = detector.get_beam_center()
    beam_pixel = tuple(beam[:2])
    beam_mm = tuple(beam[2:])
    detector_normal = tuple(detector.get_detector_normal())
    distance = detector.get_detector_distance()
    pixel = (detector.get_inferred_pixel_size(1),
             detector.get_inferred_pixel_size(2))
    
    gonio = cbf_handle.construct_goniometer()
    
    axis = tuple(gonio.get_rotation_axis())
    angles = tuple(gonio.get_rotation_range())
    
    date = cbf_handle.get_datestamp()
    time = cbf_handle.get_timestamp()
    size = tuple(cbf_handle.get_image_size(0))
    exposure = cbf_handle.get_integration_time()
    overload = cbf_handle.get_overload(0)
    wavelength = cbf_handle.get_wavelength()
    
    if do_print: print 'Detector information:'
    if do_print: print 'Dimensions: %d %d' % size
    if do_print: print 'Pixel size: %.3f %.3f' % pixel
    if do_print: print 'Distance:   %.1f' % distance
    if do_print: print 'Normal:     %.2f %.2f %.2f' % detector_normal
    if do_print: print 'Exposure:   %.2f' % exposure
    if do_print: print 'Overload:   %d' % int(overload)
    if do_print: print 'Beam:       %.2f %.2f' % beam_mm
    
    if do_print: print 'Goniometer:'
    if do_print: print 'Axis:       %.2f %.2f %.2f' % axis
    if do_print: print 'Angles:     %.2f %.2f' % angles
    
    if do_print: print 'Experiment:'
    if do_print: print 'Wavelength: %.5f' % wavelength
    
    # now need to dig out the detector axes
    # perhaps bodge this by looking at the displacements of pixels in the
    # fast and slow directions?
    
    origin = detector.get_pixel_coordinates(0, 0)
    fast = detector.get_pixel_coordinates(0, 1)
    slow = detector.get_pixel_coordinates(1, 0)

    if do_print: print 'Origin:     %.2f %.2f %.2f' % tuple(origin)
    
    dfast = [fast[j] - origin[j] for j in range(3)]
    dslow = [slow[j] - origin[j] for j in range(3)]
    
    lfast = math.sqrt(sum([dfast[j] * dfast[j] for j in range(3)]))
    lslow = math.sqrt(sum([dslow[j] * dslow[j] for j in range(3)]))
    
    fast = tuple([dfast[j] / lfast for j in range(3)])
    slow = tuple([dslow[j] / lslow for j in range(3)])
    
    if do_print: print 'Fast direction: %.2f %.2f %.2f' % fast
    if do_print: print 'Slow direction: %.2f %.2f %.2f' % slow

    if hasattr(detector, 'get_detector_axis_fast'):

        if do_print: print 'CBF fast: %.2f %.2f %.2f' % \
           tuple(detector.get_detector_axis_fast())
        if do_print: print 'CBF slow: %.2f %.2f %.2f' % \
           tuple(detector.get_detector_axis_slow())
        
    detector.__swig_destroy__(detector)
    del(detector)

    gonio.__swig_destroy__(gonio)
    del(gonio)

    return

if __name__ == '__main__':
    import time

    start = time.time()

    j = 0
    for image in sys.argv[1:]:
         print image
         cbfdump(image, do_print = True)
         j += 1

    end = time.time()

    print 'Reading %d headers took %.1fs' % (j, end - start)


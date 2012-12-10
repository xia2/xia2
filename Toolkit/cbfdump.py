# cbfdump.py
#
# A little jiffy to read a cbf file and tell us what it finds...
#
# Based on pycbf from the CBFlib distribution.
#

import sys
import pycbf
import math
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

def find_detector_id(cbf_handle):

    detector_id = ''

    cbf_handle.rewind_datablock()
    nblocks = cbf_handle.count_datablocks()

    for j in range(nblocks):
        cbf_handle.select_datablock(0)

    ncat = cbf_handle.count_categories()

    for j in range(ncat):
        cbf_handle.select_category(j)

        if not cbf_handle.category_name() == 'diffrn_detector':
            continue

        nrows = cbf_handle.count_rows()
        ncols = cbf_handle.count_columns()

        cbf_handle.rewind_column()
        cbf_handle.rewind_row()

        while True:
            if cbf_handle.column_name() == 'id':
                detector_id = cbf_handle.get_value()
                break
            try:
                cbf_handle.next_column()
            except:
                break

    return detector_id

def find_undefined_value(cbf_handle):
    cbf_handle.find_category('array_intensities')
    cbf_handle.find_column('undefined_value')
    return cbf_handle.get_doublevalue()

def determine_effective_scan_axis(gonio):
    x = gonio.rotate_vector(0.0, 1, 0, 0)
    y = gonio.rotate_vector(0.0, 0, 1, 0)
    z = gonio.rotate_vector(0.0, 0, 0, 1)

    R = matrix.rec(x + y + z, (3, 3)).transpose()

    x1 = gonio.rotate_vector(1.0, 1, 0, 0)
    y1 = gonio.rotate_vector(1.0, 0, 1, 0)
    z1 = gonio.rotate_vector(1.0, 0, 0, 1)

    R1 = matrix.rec(x1 + y1 + z1, (3, 3)).transpose()

    RA = R1 * R.inverse()

    rot = r3_rotation_axis_and_angle_from_matrix(RA)

    return rot.axis, rot.angle(deg = True)

def cbfdump(cbf_image, do_print = False):

    cbf_handle = pycbf.cbf_handle_struct()
    cbf_handle.read_file(cbf_image, pycbf.MSG_DIGEST)

    detector_id = find_detector_id(cbf_handle)

    # find the direct beam vector - takes a few steps
    cbf_handle.find_category('axis')

    # find record with equipment = source
    cbf_handle.find_column('equipment')
    cbf_handle.find_row('source')

    # then get the vector and offset from this

    beam_direction = []

    for j in range(3):
        cbf_handle.find_column('vector[%d]' % (j + 1))
        beam_direction.append(cbf_handle.get_doublevalue())

    # and calculate the polarization plane normal vector, which is
    # presumed to be in the x / y plane? it is certainly given as an angle
    # from +y

    polarization_ratio, polarization_norm = cbf_handle.get_polarization()
    polarization_plane_normal = (math.sin(polarization_norm * math.pi / 180.0),
                                 math.cos(polarization_norm * math.pi / 180.0),
                                 0.0)

    detector = cbf_handle.construct_detector(0)

    # this returns slow fast slow fast pixels pixels mm mm

    beam = detector.get_beam_center()

    beam_pixel = tuple(reversed(beam[:2]))
    beam_mm = tuple(reversed(beam[2:]))
    detector_normal = tuple(detector.get_detector_normal())
    distance = detector.get_detector_distance()
    pixel = (detector.get_inferred_pixel_size(1),
             detector.get_inferred_pixel_size(2))

    gonio = cbf_handle.construct_goniometer()

    real_axis, real_angle = determine_effective_scan_axis(gonio)

    axis = tuple(gonio.get_rotation_axis())
    angles = tuple(gonio.get_rotation_range())

    date = cbf_handle.get_datestamp()

    time = cbf_handle.get_timestamp()

    # this method returns slow then fast dimensions i.e. (y, x)

    size = tuple(reversed(cbf_handle.get_image_size(0)))
    exposure = cbf_handle.get_integration_time()
    overload = cbf_handle.get_overload(0)
    underload = find_undefined_value(cbf_handle)
    wavelength = cbf_handle.get_wavelength()

    if do_print: print 'Detector information:'
    if do_print: print 'Dimensions: %d %d' % size
    if do_print: print 'Pixel size: %.3f %.3f' % pixel
    if do_print: print 'Distance:   %.1f' % distance
    if do_print: print 'Normal:     %.2f %.2f %.2f' % detector_normal
    if do_print: print 'Exposure:   %.2f' % exposure
    if do_print: print 'Overload:   %d' % int(overload)
    if do_print: print 'Underload:  %d' % int(underload)
    if do_print: print 'Beam:       %.2f %.2f' % beam_mm
    if do_print: print 'Beam:       %.2f %.2f %.2f' % tuple(beam_direction)
    if do_print: print 'Polariz.:   %.2f %.2f %.2f' % \
       tuple(polarization_plane_normal)

    if do_print: print 'Goniometer:'
    if do_print: print 'Axis:       %.2f %.2f %.2f' % axis
    if do_print: print 'Real axis:  %.2f %.2f %.2f' % real_axis
    if do_print: print 'Angles:     %.2f %.2f' % angles
    if do_print: print 'Real angle: %.2f' % real_angle

    if do_print: print 'Experiment:'
    if do_print: print 'Wavelength: %.5f' % wavelength

    # now need to dig out the detector axes
    # perhaps bodge this by looking at the displacements of pixels in the
    # fast and slow directions?

    origin = matrix.col(detector.get_pixel_coordinates(0, 0))
    pfast = matrix.col(detector.get_pixel_coordinates(0, 1))
    pslow = matrix.col(detector.get_pixel_coordinates(1, 0))

    if do_print: print 'Origin:     %.2f %.2f %.2f' % origin.elems

    dfast = pfast - origin
    dslow = pslow - origin

    fast = dfast.normalize()
    slow = dslow.normalize()

    if do_print: print 'Fast direction: %.2f %.2f %.2f' % fast.elems
    if do_print: print 'Slow direction: %.2f %.2f %.2f' % slow.elems

    if hasattr(detector, 'get_detector_axis_fast'):

        if do_print: print 'CBF fast: %.2f %.2f %.2f' % \
           tuple(detector.get_detector_axis_fast())
        if do_print: print 'CBF slow: %.2f %.2f %.2f' % \
           tuple(detector.get_detector_axis_slow())

    # now also compute the position on the detector where the beam will
    # actually strike the detector - this will be the intersection of the
    # source vector with the plane defined by fast and slow passing through
    # the detector origin. Then return this position on the detector in mm.
    #
    # unit vectors -
    # _b - beam
    # _n - detector normal
    # _f, _s - fast and slow directions on the detector
    #
    # full vectors -
    # _O - displacement of origin
    # _D - displacement to intersection of beam with detector plane
    # _B - displacement from origin to said intersection

    _b = matrix.col(beam_direction) / math.sqrt(
        matrix.col(beam_direction).dot())
    _n = matrix.col(detector_normal) / math.sqrt(
        matrix.col(detector_normal).dot())
    
    _f = fast
    _s = slow

    _O = origin
    _D = _b * (_O.dot(_n) / _b.dot(_n))

    _B = _D - _O

    x = _B.dot(_f)
    y = _B.dot(_s)

    if do_print: print 'Computed:   %.2f %.2f' % (x, y)

    if do_print: print 'Pixels:     %.2f %.2f' % (x / pixel[0],
                                                  y / pixel[1])
    
    if do_print: print 'Size:       %.2f %.2f' % (size[0] * pixel[0],
                                                  size[1] * pixel[1])
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

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XIA.Diffdump import Diffdump

def test_image_header(image):
    d = Diffdump()
    d.set_image(image)
    header = d.readheader()

    print image

    print 'Frame %s collected at: %s' % \
          (os.path.split(image)[-1], header['date'])
    print 'Phi:  %6.2f %6.2f' % \
          (header['phi_start'], header['phi_end'])
    print 'Wavelength: %6.4f    Distance:   %6.2f' % \
          (header['wavelength'], header['distance'])
    print 'Pixel size:    %f %f' % header['pixel']
    print 'Size:          %d %d' % tuple(header['size'])
    print 'Beam centre:   %f %f' % tuple(header['beam'])
    print 'Detector class: %s' % header['detector_class']
    print 'Epoch:         %.3f' % header['epoch']
    print 'Exposure time: %.3f' % header['exposure_time']
    print 'Two theta:     %.3f' % header['two_theta']

    return

if __name__ == '__main__':

    for image in sys.argv[1:]:
        test_image_header(image)

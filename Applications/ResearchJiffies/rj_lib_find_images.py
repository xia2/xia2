# odds and sods for finding matching images

import os, sys

if not 'XIA2_ROOT' in os.environ:
    raise RuntimeError, 'XIA2_ROOT undefined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Experts.FindImages import find_matching_images, \
     image2template_directory, \
     template_directory_number2image

from Wrappers.XIA.Diffdump import Diffdump

def rj_get_template_directory(image):
    template, directory = image2template_directory(image)    
    return template, directory

def rj_find_matching_images(image):
    template, directory = image2template_directory(image)
    images = find_matching_images(template, directory)
    return images

def rj_get_phi(image):
    dd = Diffdump()
    dd.set_image(image)
    header = dd.readheader()
    phi = header['phi_end'] - header['phi_start']
    if phi < 0.0:
        phi += 360.0
    if phi > 360.0:
        phi -= 360.0
    return phi

def rj_image_name(template, directory, number):
    return template_directory_number2image(template, directory, number)

if __name__ == '__main__':
    image = sys.argv[1]
    template, directory = rj_get_template_directory(image)
    phi = rj_get_phi(image)
    images = rj_find_matching_images(image)

    for i in [images[0], images[-1]]:
        print i, (i - images[0]) * phi, (i - images[0] + 1) * phi
        print rj_image_name(template, directory, i)

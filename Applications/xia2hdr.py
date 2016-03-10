#
# 03/MAR/16
# To resolve the naming conflict between this file and the entire xia2 module
# any xia2.* imports in this directory must instead be imported as ..*

import os
import sys

def xia2hdr(filename, image_range):

  # diamantle the filename into template, directory, image numbers

  from ..Experts.FindImages import image2template_directory, image2image

  template, directory = image2template_directory(filename)
  image_number = image2image(filename)

  assert(image_number == image_range[0])

  # read the first image header to get the starting point

  from ..Wrappers.XIA.Diffdump import Diffdump

  d = Diffdump()

  d.set_image(filename)
  header = d.readheader()

  # now regenerate the rest of the image headers for image range...

  from ..Experts.FindImages import template_directory_number2image
  import copy
  import datetime
  import time

  fake_header_cache = { }

  for j in range(image_range[0], image_range[1] + 1):
    offset = j - image_range[0]
    fake_header = copy.deepcopy(header)
    fake_header['epoch'] = (header['epoch'] +
                            offset * header['exposure_time'])
    fake_header['date'] = time.asctime(datetime.datetime.fromtimestamp(
        fake_header['epoch']).timetuple())
    fake_header['phi_start'] = (header['phi_start'] +
                                offset * header['phi_width'])
    fake_header['phi_end'] = (header['phi_end'] +
                              offset * header['phi_width'])

    fake_header_cache[template_directory_number2image(
        template, directory, j)] = fake_header

  import json
  return json.dumps(fake_header_cache)

if __name__ == '__main__':
  print xia2hdr(os.path.abspath(sys.argv[1]),
      (int(sys.argv[2]), int(sys.argv[3])))

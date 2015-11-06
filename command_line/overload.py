from __future__ import division

def read_cbf_image(cbf_image):
  from cbflib_adaptbx import uncompress
  import binascii

  start_tag = binascii.unhexlify('0c1a04d5')

  data = open(cbf_image, 'rb').read()
  data_offset = data.find(start_tag) + 4
  cbf_header = data[:data_offset - 4]

  fast = 0
  slow = 0
  length = 0

  for record in cbf_header.split('\n'):
    if 'X-Binary-Size-Fastest-Dimension' in record:
      fast = int(record.split()[-1])
    elif 'X-Binary-Size-Second-Dimension' in record:
      slow = int(record.split()[-1])
    elif 'X-Binary-Number-of-Elements' in record:
      length = int(record.split()[-1])
    elif 'X-Binary-Size:' in record:
      size = int(record.split()[-1])

  assert(length == fast * slow)

  pixel_values = uncompress(packed = data[data_offset:data_offset + size],
                            fast = fast, slow = slow)

  return pixel_values

def get_overload(cbf_file):
  for record in open(cbf_file):
    if 'Count_cutoff' in record:
      return int(record.split()[-2])

def build_hist():
  import sys
  from scitbx.array_family import flex

  thresh = 100
  scale = thresh / get_overload(sys.argv[1])

  hist = flex.histogram(flex.double(), data_min=0.0, data_max=(5.0*thresh),
                        n_slots=500)

  for image in sys.argv[1:]:
    data = read_cbf_image(image)
    scaled = scale * data.as_double()
    tmp_hist = flex.histogram(scaled.as_1d(), data_min=0.0, data_max=(5.0*thresh),
                              n_slots=500)
    hist.update(tmp_hist)

  hist.show()

if __name__ == '__main__':
  build_hist()

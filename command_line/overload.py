from __future__ import division
import binascii
import json
import sys
import timeit

def read_cbf_image(cbf_image):
  from cbflib_adaptbx import uncompress

  start_tag = binascii.unhexlify('0c1a04d5')

  with open(cbf_image, 'rb') as fh:
    data = fh.read()

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
  with open(cbf_file, 'rb') as fh:
    for record in fh:
      if 'Count_cutoff' in record:
        return int(record.split()[-2])

def build_hist():
  from scitbx.array_family import flex

  if len(sys.argv) == 2 and sys.argv[1].endswith('.json'):
    from dxtbx import datablock
    db = datablock.DataBlockFactory.from_json_file(sys.argv[1])[0]
    image_list = db.extract_imagesets()[0].paths()
  else:
    image_list = sys.argv[1:]
  image_count = len(image_list)

  # Faster, yet still less than ideal and wasting a lot of resources.
  limit = get_overload(image_list[0])
  binfactor = 5 # register up to 500% counts
  histmax = (limit * binfactor) + 0.0
  histbins = (limit * binfactor) + 1
  hist = flex.histogram(flex.double(), data_min=0.0, data_max=histmax, n_slots=histbins)

  print "Processing %d images" % image_count
  start = timeit.default_timer()
  last_update = start

#  image_maxima = [None] * image_count

  for i in range(image_count):
    data = read_cbf_image(image_list[i])
    tmp_hist = flex.histogram(data.as_double().as_1d(), data_min=0.0, data_max=histmax, n_slots=histbins)
#    image_max = histmax
#    for b in reversed(tmp_hist.slots()):
#      if b != 0:
#        image_maxima[i] = int(image_max)
#        break
#      image_max -= 1
    hist.update(tmp_hist)
    if timeit.default_timer() > (last_update + 3):
      last_update = timeit.default_timer()
      if sys.stdout.isatty():
        sys.stdout.write('\033[A')
      print 'Processed %d of %d images (%d seconds remain)    ' % (i+1, image_count, round((image_count - i) * (last_update - start) / (i+1)))
#  print image_maxima
  results = { 'scale_factor': 1 / limit,
              'bin_count': histbins,
              'bins': list(hist.slots()),
              'image_files': image_list }

  print "Writing results to overload.json"
  with open('overload.json', 'w') as fh:
    json.dump(results, fh)

if __name__ == '__main__':
  build_hist()

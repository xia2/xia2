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
        return float(record.split()[-2])

def build_hist(nproc=1):
  from scitbx.array_family import flex
  from libtbx import easy_mp
  from collections import Counter

  # FIXME use proper optionparser here. This works for now
  if len(sys.argv) >= 2 and sys.argv[1].startswith('nproc='):
    nproc=int(sys.argv[1][6:])
    sys.argv = sys.argv[1:]
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
  histbins = int(limit * binfactor) + 1
  use_python_counter = histbins > 90000000 # empirically determined

  print "Processing %d images in %d processes using %s\n" % (image_count, nproc, \
    "python Counter" if use_python_counter else "flex arrays")

  def process_image(process):
    import sys
    last_update = start = timeit.default_timer()

    i = process
    if use_python_counter:
      local_hist = Counter()
    else:
      local_hist = flex.histogram(flex.double(), data_min=0.0, data_max=histmax, n_slots=histbins)

    max_images = image_count // nproc
    if process >= image_count % nproc:
      max_images += 1
    while i < image_count:
      data = read_cbf_image(image_list[i])
      if not use_python_counter:
        data = flex.histogram(data.as_double().as_1d(), data_min=0.0, data_max=histmax, n_slots=histbins)
      local_hist.update(data)
      i = i + nproc
      if process == 0:
        if timeit.default_timer() > (last_update + 3):
          last_update = timeit.default_timer()
          if sys.stdout.isatty():
            sys.stdout.write('\033[A')
          print 'Processed %d%% (%d seconds remain)    ' % (100 * i // image_count, round((image_count - i) * (last_update - start) / (i+1)))
    return local_hist

  results = easy_mp.parallel_map(
    func=process_image,
    iterable=range(nproc),
    processes=nproc,
    preserve_exception_message=True)

  print "Merging results"
  result_hist = None
  for hist in results:
    if result_hist is None:
      result_hist = hist
    else:
      result_hist.update(hist)

  if not use_python_counter:
    # reformat histogram into dictionary
    result = list(result_hist.slots())
    result_hist = { b: count for b, count in enumerate(result) if count > 0 }

  results = { 'scale_factor': 1 / limit,
              'overload_limit': limit,
              'counts': result_hist }

  print "Writing results to overload.json"
  with open('overload.json', 'w') as fh:
    json.dump(results, fh, indent=1, sort_keys=True)

if __name__ == '__main__':
  build_hist()

from __future__ import absolute_import, division, print_function

def read_image(image_name):
  import dxtbx
  from scitbx.array_family import flex
  data = dxtbx.load(image_name).get_raw_data()
  data.reshape(flex.grid(2527, 2463))
  subset = data[1055:1473,984:1478]
  return subset

def cc(a, b):
  _a = a - (sum(a) / len(a))
  _b = b - (sum(b) / len(b))
  import math
  return sum(_a * _b) / math.sqrt(sum(_a * _a) * sum(_b * _b))

if __name__ == '__main__':
  import sys
  results = { }
  for i, frame in enumerate(sys.argv[1:]):
    a = read_image(frame).as_double()
    for j, other in enumerate(sys.argv[i + 1:]):
      b = read_image(other).as_double()
      c = cc(a, b)
      results[(i, j + i)] = c
      results[(j + i, i)] = c

  for k in sorted(results):
    print('%4d %4d %.6e %.6e' % (k[0] + 1, k[1] + 1, results[k],
                                 1.0 - results[k]))

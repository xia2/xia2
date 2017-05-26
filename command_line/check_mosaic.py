# LIBTBX_SET_DISPATCHER_NAME dev.xia2.check_mosaic
from __future__ import absolute_import, division
from dials.array_family import flex
import cPickle as pickle

def mosaic_profile(profile):
  nz, ny, nx = profile.focus()
  z = flex.double(nz, 0.0)

  for j in range(nz):
    z[j] = flex.sum(profile[j:j+1,:,:])

  return z

def go(filename):
  allprof = pickle.load(open(filename))
  for prof in allprof:
    z = mosaic_profile(prof[0])
    for profile in prof[1:]:
      z += mosaic_profile(profile)
    z /= flex.max(z)
    data = (100 * z).iround()

    fmt = '%3d ' * z.size()

    print fmt % tuple(data)

if __name__ == '__main__':
  import sys
  go(sys.argv[1])

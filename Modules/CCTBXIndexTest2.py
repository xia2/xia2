from rstbx.diffraction import rotation_angles
from cctbx.crystal_orientation import crystal_orientation,basis_type
import math

rtod = 180.0 / math.pi

def inspect(o):
  for m in dir(o):
    if not '__' in m[:2]:
      print m

def read_xparm(xparm_file):
  '''Parse the XPARM file to a dictionary.'''

  records = open(xparm_file, 'r').readlines()

  data = map(float, open(xparm_file, 'r').read().split())

  if not len(data) == 42:
    raise RuntimeError, 'error parsing %s' % xparm_file

  starting_frame = int(data[0])
  phi_start = data[1]
  phi_width = data[2]
  axis = data[3:6]

  wavelength = data[6]
  beam = data[7:10]

  nx = int(data[10])
  ny = int(data[11])
  px = data[12]
  py = data[13]

  distance = data[14]
  ox = data[15]
  oy = data[16]

  x = data[17:20]
  y = data[20:23]
  normal = data[23:26]

  spacegroup = int(data[26])
  cell = data[27:33]

  a = data[33:36]
  b = data[36:39]
  c = data[39:42]

  results = {
      'starting_frame':starting_frame,
      'phi_start':phi_start,
      'phi_width':phi_width,
      'axis':axis,
      'wavelength':wavelength,
      'beam':beam,
      'nx':nx,
      'ny':ny,
      'px':px,
      'py':py,
      'distance':distance,
      'ox':ox,
      'oy':oy,
      'x':x,
      'y':y,
      'normal':normal,
      'spacegroup':spacegroup,
      'cell':cell,
      'a':a,
      'b':b,
      'c':c
      }

  return results

def nint(a):
  i = int(a)
  if a - i > 0.5:
    i += 1
  return i

if __name__ == '__main__':

  results = read_xparm('XPARM.XDS')

  A = results['a']
  B = results['b']
  C = results['c']

  cell = results['cell']
  axis = results['axis']
  wavelength = results['wavelength']

  start = results['starting_frame'] - 1
  phi_start = results['phi_start']
  phi_width = results['phi_width']

  # FIXME really need to rotate the reference frame to put the
  # direct beam vector along (0,0,1)

  resolution = 1.8

  orientation = A + B + C

  co = crystal_orientation(orientation, basis_type.direct)
  mm = co.unit_cell().max_miller_indices(resolution)
  ra = rotation_angles(resolution, co.reciprocal_matrix(), wavelength, axis)

  for record in open('SPOT.XDS', 'r').readlines():
    lst = record.split()
    hkl = tuple(map(int, lst[-3:]))
    if hkl == (0, 0, 0):
      continue
    image = nint(float(lst[2]))

    if ra(hkl):
      phi1, phi2 = ra.get_intersection_angles()
      i = nint(start + (rtod * phi1 - phi_start) / phi_width)
      j = nint(start + (rtod * phi2 - phi_start) / phi_width)
      if abs(i - image) <= abs(j - image):
        print '%4d %4d' % (image, i)
      else:
        print '%4d %4d' % (image, j)

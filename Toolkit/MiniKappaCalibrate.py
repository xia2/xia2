import os
import sys

def xds_read_xparm(xparm_file):
  '''Parse the new-style or old-style XPARM file.'''

  if 'XPARM' in open(xparm_file, 'r').readline():
    return xds_read_xparm_new_style(xparm_file)
  else:
    return xds_read_xparm_old_style(xparm_file)

def xds_read_xparm_old_style(xparm_file):
  '''Parse the XPARM file to a dictionary.'''

  data = map(float, open(xparm_file, 'r').read().split())

  assert(len(data) == 42)

  starting_frame = int(data[0])
  phi_start, phi_width = data[1:3]
  axis = data[3:6]

  wavelength = data[6]
  beam = data[7:10]

  nx, ny = map(int, data[10:12])
  px, py = data[12:14]

  distance = data[14]
  ox, oy = data[15:17]

  x, y = data[17:20], data[20:23]
  normal = data[23:26]

  spacegroup = int(data[26])
  cell = data[27:33]

  a, b, c = data[33:36], data[36:39], data[39:42]

  results = {
      'starting_frame':starting_frame,
      'phi_start':phi_start, 'phi_width':phi_width,
      'axis':axis, 'wavelength':wavelength, 'beam':beam,
      'nx':nx, 'ny':ny, 'px':px, 'py':py, 'distance':distance,
      'ox':ox, 'oy':oy, 'x':x, 'y':y, 'normal':normal,
      'spacegroup':spacegroup, 'cell':cell, 'a':a, 'b':b, 'c':c
      }

  return results

def xds_read_xparm_new_style(xparm_file):
  '''Parse the XPARM file to a dictionary.'''

  data = map(float, ' '.join(open(xparm_file, 'r').readlines()[1:]).split())

  starting_frame = int(data[0])
  phi_start, phi_width = data[1:3]
  axis = data[3:6]

  wavelength = data[6]
  beam = data[7:10]

  spacegroup = int(data[10])
  cell = data[11:17]
  a, b, c = data[17:20], data[20:23], data[23:26]
  assert(int(data[26]) == 1)
  nx, ny = map(int, data[27:29])
  px, py = data[29:31]
  ox, oy = data[31:33]
  distance = data[33]
  x, y = data[34:37], data[37:40]
  normal = data[40:43]

  results = {
      'starting_frame':starting_frame,
      'phi_start':phi_start, 'phi_width':phi_width,
      'axis':axis, 'wavelength':wavelength, 'beam':beam,
      'nx':nx, 'ny':ny, 'px':px, 'py':py, 'distance':distance,
      'ox':ox, 'oy':oy, 'x':x, 'y':y, 'normal':normal,
      'spacegroup':spacegroup, 'cell':cell, 'a':a, 'b':b, 'c':c
      }

  return results

def xparm_to_ub(xparm_file):
  from scitbx import matrix
  xparm_data = xds_read_xparm(xparm_file)
  RS_ub = matrix.sqr(xparm_data['a'] + xparm_data['b'] + xparm_data['c'])
  return RS_ub.inverse()

def xparm_to_beam_fast_slow(xparm_file):
  from scitbx import matrix
  xparm_data = xds_read_xparm(xparm_file)

  return tuple(xparm_data['beam']), tuple(xparm_data['x']), \
         tuple(xparm_data['y'])

def find_xparm(xparm_location):
  assert(os.path.exists(xparm_location))
  if os.path.split(xparm_location)[-1] == 'GXPARM.XDS':
    return xparm_location
  assert(os.path.isdir(xparm_location))
  if os.path.exists(os.path.join(xparm_location, 'GXPARM.XDS')):
    return os.path.join(xparm_location, 'GXPARM.XDS')

  raise RuntimeError, 'no GXPARM.XDS found in %s' % xparm_location

def derive_axis_angle(xparm0, xparm1):
  xparm0 = find_xparm(xparm0)
  xparm1 = find_xparm(xparm1)
  from scitbx.math import r3_rotation_axis_and_angle_from_matrix
  import math
  ub0 = xparm_to_ub(xparm0)
  ub1 = xparm_to_ub(xparm1)
  R = ub1 * ub0.inverse()
  axis_angle = r3_rotation_axis_and_angle_from_matrix(R)
  axis = axis_angle.axis
  angle = axis_angle.angle() * 180.0 / math.pi
  return axis, angle, R

def main(args):

  from scitbx import matrix

  prefix = os.path.commonprefix(args)

  from rstbx.cftbx.coordinate_frame_converter import \
   coordinate_frame_converter

  cfc = coordinate_frame_converter(find_xparm(args[0]))

  for j in range(len(args) - 1):
    print '%s => %s' % (args[j].replace(prefix, ''),
                        args[j + 1].replace(prefix, ''))
    axis, angle, R = derive_axis_angle(args[j], args[j + 1])
    print 'Axis:'
    print '%6.3f %6.3f %6.3f' % cfc.move(axis, convention = cfc.MOSFLM)
    print 'Angle:'
    print '%6.3f' % angle

if __name__ == '__main__':
  main(sys.argv[1:])

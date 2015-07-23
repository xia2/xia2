from __future__ import division

def parse_compound(compound):
  import string
  result = { }
  element = ''
  number = ''
  compound += 'X'
  for c in compound:
    if c in string.uppercase:
      if not element:
        element += c
        continue
      if number == '':
        count = 1
      else:
        count = int(number)
      if not element in result:
        result[element] = 0
      result[element] += count
      element = '' + c
      number = ''
      if c == 'X':
        break
    elif c in string.lowercase:
      element += c
    elif c in string.digits:
      number += c
  return result

def to_shelx(hklin, prefix, compound=''):
  '''Read hklin (unmerged reflection file) and generate SHELXT input file
  and HKL file'''

  from iotbx.reflection_file_reader import any_reflection_file
  from iotbx.shelx import writer
  from cctbx.xray.structure import structure
  from cctbx.xray import scatterer

  reader = any_reflection_file(hklin)
  intensities = [ma for ma in reader.as_miller_arrays(merge_equivalents=False)
                 if ma.info().labels == ['I', 'SIGI']][0]
  with open('%s.hkl' % prefix, 'wb') as f:
    intensities.export_as_shelx_hklf(f)

  crystal_symm = intensities.crystal_symmetry()
  xray_structure = structure(crystal_symmetry=crystal_symm)
  if compound:
    result = parse_compound(compound)
    for element in result:
      xray_structure.add_scatterer(scatterer(label=element,
                                             occupancy=result[element]))
  open('%s.ins' % prefix, 'w').write(''.join(writer.generator(xray_structure,
                            full_matrix_least_squares_cycles=0,
                            title=prefix)))

if __name__ == '__main__':
  import sys

  # FIXME concatenate argv[3:] to merge C2 H5 OH into H2H5OH
  if len(sys.argv) == 4:
    to_shelx(sys.argv[1], sys.argv[2], sys.argv[3])
  else:
    to_shelx(sys.argv[1], sys.argv[2])

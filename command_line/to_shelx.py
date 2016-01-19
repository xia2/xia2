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

def mtz_to_hklf4(hklin, out):
  from iotbx import mtz
  mtz_obj = mtz.object(hklin)
  miller_indices = mtz_obj.extract_original_index_miller_indices()
  i = mtz_obj.get_column('I').extract_values()
  sigi = mtz_obj.get_column('SIGI').extract_values()
  f = open(out, 'wb')
  for j, mi in enumerate(miller_indices):
    f.write('%4d%4d%4d' % mi)
    f.write('%8.2f%8.2f\n' % (i[j], sigi[j]))
  f.close()
  return

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

  # FIXME do I need to reindex to a conventional setting here

  mtz_to_hklf4(hklin, '%s.hkl' % prefix)

  crystal_symm = intensities.crystal_symmetry()

  cb_op = crystal_symm.change_of_basis_op_to_reference_setting()

  assert(cb_op.c().r().as_hkl() == 'h,k,l')

  print 'Change of basis to reference setting: %s' % cb_op

  crystal_symm = crystal_symm.change_basis(cb_op)

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

  if len(sys.argv) > 3:
    atoms = ''.join(sys.argv[3:])
    print 'Atoms: %s' % atoms
    to_shelx(sys.argv[1], sys.argv[2], atoms)
  else:
    to_shelx(sys.argv[1], sys.argv[2])

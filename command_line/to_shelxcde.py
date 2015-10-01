from __future__ import division

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

def to_shelxcde(hklin, prefix, sites=0):
  '''Read hklin (unmerged reflection file) and generate SHELXC input file
  and HKL file'''

  from iotbx.reflection_file_reader import any_reflection_file
  reader = any_reflection_file(hklin)
  intensities = [ma for ma in reader.as_miller_arrays(merge_equivalents=False)
                 if ma.info().labels == ['I', 'SIGI']][0]
  mtz_to_hklf4(hklin, '%s.hkl' % prefix)
  uc = intensities.unit_cell().parameters()
  sg = intensities.space_group().type().lookup_symbol().replace(' ', '')
  open('%s.sh' % prefix, 'w').write('\n'.join([
    'shelxc %s << eof' % prefix,
    'cell %f %f %f %f %f %f' % uc,
    'spag %s' % sg,
    'sad %s.hkl' % prefix,
    'find %d' % sites,
    'eof']))

if __name__ == '__main__':
  import sys

  if len(sys.argv) > 3:
    sites = int(sys.argv[3])
    to_shelxcde(sys.argv[1], sys.argv[2], sites)
  else:
    to_shelxcde(sys.argv[1], sys.argv[2])

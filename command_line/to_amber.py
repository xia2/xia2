from __future__ import absolute_import, division, print_function

# LIBTBX_SET_DISPATCHER_NAME dev.xia2.to_amber
# hacky amber wants this ersatz hkl thing *** do not use ***

def to_amber(hklin, prefix):
  '''Read hklin (unmerged reflection file) HKL file containing
  H K L I sqrt(|I|)'''

  from iotbx.reflection_file_reader import any_reflection_file
  from iotbx.shelx import writer
  from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf

  reader = any_reflection_file(hklin)
  mtz_object = reader.file_content()
  ma = reader.as_miller_arrays(merge_equivalents=False)
  labels = [c.info().labels for c in ma]
  if ['I', 'SIGI'] not in labels:
    if ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)'] in labels:
      print("Error: xia2.to_amber must be run on unmerged data.")
    else:
      print("Error: columns I / SIGI not found.")
    sys.exit(1)

  intensities = [c for c in ma if c.info().labels == ['I', 'SIGI']][0]

  indices = reader.file_content().extract_original_index_miller_indices()
  intensities = intensities.customized_copy(indices=indices, info=intensities.info())

  from scitbx.array_family import flex
  abs_intensities = flex.sqrt(flex.abs(intensities.data()))
  intensities.set_sigmas(abs_intensities)

  with open('%s.hkl' % prefix, 'wb') as hkl_file_handle:
    miller_array_export_as_shelx_hklf(intensities, hkl_file_handle,
      scale_range=(-9999., 9999.), normalise_if_format_overflow=True)

  return

if __name__ == '__main__':
  import sys
  args = sys.argv[1:]
  to_amber(args[0], args[1])

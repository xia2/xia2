def npp(hklin):
  from iotbx.reflection_file_reader import any_reflection_file
  from xia2.Toolkit.NPP import npp_ify, mean_variance
  reader = any_reflection_file(hklin)
  mtz_object = reader.file_content()
  intensities = [ma for ma in reader.as_miller_arrays(merge_equivalents=False)
                 if ma.info().labels == ['I', 'SIGI']][0]
  indices = intensities.indices()

  merger = intensities.merge_equivalents(use_internal_variance=False)
  mult = merger.redundancies().data()
  imean = merger.array()
  unique = imean.indices()
  iobs = imean.data()
  variobs = (imean.sigmas() ** 2) * mult.as_double()

  for hkl, i, v in zip(unique, iobs, variobs):
    sel = indices == hkl
    data = intensities.select(sel).data()
    _x, _y = npp_ify(data, input_mean_variance=(i,v))
    for x, y in zip(_x, _y):
      print x, y

if __name__ == '__main__':
  import sys
  npp(sys.argv[1])

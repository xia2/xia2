import os

def run():
  from xia2.Handlers.XInfo import XInfo

  import libtbx.load_env
  xinfo_dir = os.path.join(libtbx.env.dist_path('xia2'), 'Test', 'Handlers')

  xinfo = XInfo(os.path.join(xinfo_dir, 'insulin.xinfo'))
  assert xinfo.get_crystals().keys() == ['DEFAULT']
  assert xinfo.get_crystals()['DEFAULT']['wavelengths'] == {
    'NATIVE': {'wavelength': 0.979}}
  assert xinfo.get_crystals()['DEFAULT']['sweeps'] ==  {
    'SWEEP1': {
      'excluded_regions': [], 'IMAGE': 'insulin_1_001.img',
      'beam': [94.34, 94.5], 'start_end': [1, 45],
      'DIRECTORY': '/path/to/build/xia2_regression/test_data/insulin',
      'wavelength': 'NATIVE'}}

  xinfo = XInfo(os.path.join(xinfo_dir, 'multi.xinfo'))
  assert xinfo.get_crystals().keys() == ['DEFAULT']
  assert xinfo.get_crystals()['DEFAULT']['wavelengths'] == {
    'NATIVE': {'wavelength': 1.77}}
  assert xinfo.get_crystals()['DEFAULT']['sweeps'] == {
    'SWEEP4': {'DIRECTORY': '/path/to/data/dir2', 'wavelength': 'NATIVE',
               'IMAGE': 'sweep_4_0001.cbf', 'start_end': [1, 900],
               'excluded_regions': []},
    'SWEEP2': {'DIRECTORY': '/path/to/data/dir1', 'wavelength': 'NATIVE',
               'IMAGE': 'sweep_2_0001.cbf', 'start_end': [1, 900],
               'excluded_regions': []},
    'SWEEP3': {'DIRECTORY': '/path/to/data/dir2', 'wavelength': 'NATIVE',
               'IMAGE': 'sweep_3_0001.cbf', 'start_end': [1, 900],
               'excluded_regions': []},
    'SWEEP1': {'DIRECTORY': '/path/to/data/dir1', 'wavelength': 'NATIVE',
               'IMAGE': 'sweep_1_0001.cbf', 'start_end': [1, 900],
               'excluded_regions': []}}

  xinfo = XInfo(os.path.join(xinfo_dir, 'multi.xinfo'),
                sweep_ids=['SWEEP1', 'swEEp4'])
  assert xinfo.get_crystals()['DEFAULT']['sweeps'] == {
  'SWEEP4': {'DIRECTORY': '/path/to/data/dir2', 'wavelength': 'NATIVE',
             'IMAGE': 'sweep_4_0001.cbf', 'start_end': [1, 900],
             'excluded_regions': []},
  'SWEEP1': {'DIRECTORY': '/path/to/data/dir1', 'wavelength': 'NATIVE',
             'IMAGE': 'sweep_1_0001.cbf', 'start_end': [1, 900],
             'excluded_regions': []}}


if __name__ == '__main__':
  run()
  print 'OK'

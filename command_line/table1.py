from __future__ import division, print_function

def table1_tex(crystal_params, merging_stats):
  # based on table1 from
  #
  # http://journals.iucr.org/d/issues/2018/02/00/di5011/index.html

  assert len(crystal_params) == len(merging_stats)
  
  # first iterate through and work out how many columns we will be needing
  columns = [len(ms) for ms in merging_stats]

  if max(columns) > 1:
    raise RuntimeError(':TODO: make this work for multiwavelength data sets')
  
  ncols = sum(columns)

  print('\\begin{tabular}{%s}' % ('l' * (ncols + 1)))

  name_str = ['']
  for ms in merging_stats:
    for name in ms:
      _name = eval(name)
      name_str.append('%s/%s/%s' % tuple(_name))

  print(' & '.join(name_str) + ' \\\\')
  print('Crystal parameters' + ' & ' * ncols + '\\\\')
  print('Space group & ' + 
          ' & '.join([cp['space_group'] for cp in crystal_params]) + ' \\\\')
  print('Unit-cell parameters (\\AA) & ' + ' & '.join(
          ['$a=%.5f b=%.5f c=%.5f \\alpha=%.5f \\beta=%.5f \\gamma=%.5f$'
             % tuple(cp['cell']) for cp in crystal_params]) + ' \\\\')
  print('Data statistics' + ' & ' * ncols + '\\\\')

  # resolution ranges, shells

  resolution_str = ['Resolution range (\\AA)']
  
  for ms in merging_stats:
    for name in ms:
      low = ms[name]['Low resolution limit']
      high = ms[name]['High resolution limit']
      resolution_str.append('%.2f-%.2f (%.2f-%.2f)' %
                              (low[0], high[0], low[2], high[2]))
  
  print(' & '.join(resolution_str) + ' \\\\')
  

def table1():
  import sys
  import os
  import json
  import pprint
  
  jsons = []
  for xia2 in sys.argv[1:]:
    assert os.path.exists(os.path.join(xia2, 'xia2.json')), xia2
    jsons.append(json.load(open(os.path.join(xia2, 'xia2.json'), 'r')))

  # extract out the information needed - for the moment just the merging
  # statistics though could later extract data collection statistics from
  # the image headers :TODO:

  merging_stats = []
  crystal_params = []
    
  for j in jsons:
    for x in j['_crystals']:
      s = j['_crystals'][x]['_scaler']
      crystal_param = {
        'space_group':s['_scalr_likely_spacegroups'][0],
        'cell':s['_scalr_cell'],
        'cell_esd':s['_scalr_cell_esd']
        }
          
      merging_stats.append(s['_scalr_statistics'])
      crystal_params.append(crystal_param)

  table1_tex(crystal_params, merging_stats)
      
if __name__ == '__main__':
  table1()

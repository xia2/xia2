from __future__ import division, print_function

def table1_tex(merging_stats):
  # based on table1 from
  #
  # http://journals.iucr.org/d/issues/2018/02/00/di5011/index.html
  
  # first iterate through and work out how many columns we will be needing
  columns = [len(ms) for ms in merging_stats]
  ncols = sum(columns)

  print('\\begin{tabular}{%s}' % ('l' * (ncols + 1)))

  name_str = ['']
  for ms in merging_stats:
    for name in ms:
      _name = eval(name)
      name_str.append('%s/%s/%s' % tuple(_name))

  print(' & '.join(name_str) + ' \\\\')
  print('Crystal parameters' + ' & ' * ncols + '\\\\')
  
  print('\\end{tabular}')
  

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
    
  for j in jsons:
    for x in j['_crystals']:
      merging_stats.append(j['_crystals'][x]['_scaler']['_scalr_statistics'])

  table1_tex(merging_stats)
      
if __name__ == '__main__':
  table1()

import sys
import os

input_file = os.path.join(os.environ['X2TD_ROOT'],
                          'Test', 'UnitTest', 'Interfaces',
                          'Scaler', 'Merged', 'TS00_13185_merged_free.mtz')

input_dict = {'cell':(57.746, 76.931, 86.582, 90.00, 90.00, 90.00),
              'spacegroup':'P 21 21 21',
              'INFL':{'fp':-12.0,
                      'fpp':5.8},
              'LREM':{'fp':-2.5,
                      'fpp':0.5},
              'PEAK':{'fp':-10.0,
                      'fpp':6.9},
              'n_sites':5,
              'atom':'se',
              'solvent':0.49}


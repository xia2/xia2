import sys
import os

input_file = os.path.join(os.environ['X2TD_ROOT'],
                          'Test', 'UnitTest', 'Interfaces',
                          'Scaler', 'Merged', 'TS00_13185_merged_free.mtz')

input_dict = {'INFL':{'wavelength':0.97950,
                      'fp':-12.0,
                      'fpp':5.8},
              'LREM':{'wavelength':1.00000,
                      'fp':-2.5,
                      'fpp':0.5},
              'PEAK':{'wavelength':0.97934,
                      'fp':-10.0,
                      'fpp':6.9},
              'n_sites':5,
              'nres':360,
              'atom':'se',
              'solvent':0.49}


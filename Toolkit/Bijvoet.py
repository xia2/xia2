import sys
import math
import os
from iotbx import mtz

def bijvoet(hklin):
    '''Compute bijvoet differences between I+/I- and F+/F- averaged over
    some resolution bins.'''

    mtz_obj = mtz.object(hklin)
    mi = mtz_obj.extract_miller_indices()

    mas = mtz_obj.as_miller_arrays()

    for ma in mas:
        columns = ma.info().label_string()
        if '+' in columns and '-' in columns:
            print columns, ma.anomalous_signal()

if __name__ == '__main__':

    bijvoet(sys.argv[1])

#!/usr/bin/env python
# WedgeExpert.py
# 
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# Some code to help figure out how the experiment was performed and tell
# Chef where we could consider cutting the data at... N.B. this will now 
# take the digested wedges from the Chef wrapper.

import math
import sys
import pickle

def digest_wedges(wedges):
    '''Digest the wedges defined as a list of

    FIRST_DOSE FIRST_BATCH SIZE EXPOSURE DATASET
    
    to a set of potential "stop" points, in terms of the doses. This will
    return a list of DOSE values which should be treated as LIMITS (i.e.
    d:d < DOSE ok).'''

    # first digest to logical sweeps, keyed by the last image in the set
    # and the wavelength name, and containing the start and end dose.

    doses = { }

    belonging_wedges = { }

    for w in wedges:
        dose, batch, size, exposure, dataset = w
        if (dataset, batch) in doses:
            k_old = (dataset, batch)
            k_new = (dataset, batch + size)
            
            sweep = doses[k_old]
            doses[k_new] = (sweep[0], sweep[1] + exposure * size)

            belonging_wedges[k_new] = belonging_wedges[k_old]
            belonging_wedges[k_new].append(w)
            
            del(doses[k_old])
            del(belonging_wedges[k_old])

        else:
            end_dose = dose + exposure * (size - 1)
            
            doses[(dataset, batch + size)] = (dose, end_dose)
            belonging_wedges[(dataset, batch + size)] = [w]
            
    # now invert

    sweeps = { }

    for k in doses:
        sweeps[doses[k]] = k

    # now try to figure the sweeps which are overlapping - these will be
    # added to a list named "groups"

    groups = []

    

    

    
    


if __name__ == '__main__':


    wedges = pickle.loads(open('test.pkl').read())
    
    digest_wedges(wedges)

    

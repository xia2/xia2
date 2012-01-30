#!/usr/bin/env python
# ChefHelpers.py
#   Copyright (C) 2008 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 27th March, 2008
#
# Helper functions and definitions for things to help chef.
#
#

import math
import os

# completeness handling functions - take as input dictionary
# completeness[dose]

def completeness_dose(cd_dict):
    '''Find the doses where the data reach 100, 98, 95 and 90% the
    maximum completeness.'''

    doses = cd_dict.keys()
    doses.sort()

    cmax = cd_dict[doses[-1]]

    dc100 = None
    dc98 = None
    dc95 = None
    dc90 = None

    for d in doses:
        comp = cd_dict[d]

        if dc100 is None and comp >= 1.0 * cmax:
            dc100 = d

        if dc98 is None and comp >= 0.98 * cmax:
            dc98 = d

        if dc95 is None and comp >= 0.95 * cmax:
            dc95 = d

        if dc90 is None and comp >= 0.9 * cmax:
            dc90 = d

    return dc100, dc98, dc95, dc90

if __name__ == '__main__':

    cd_dict = { }

    src = os.path.join(os.environ['X2TD_ROOT'], 'Test', 'Chef', 'Helpers',
                       'ChefHelpers.dat')

    src2 = os.path.join(os.environ['X2TD_ROOT'], 'Test', 'Chef', 'Helpers',
                       'ChefHelpers2.dat')

    for record in open(src, 'r').readlines():
        lst = map(float, record.split())

        if not lst:
            break

        cd_dict[lst[0]] = lst[3]

    print 'INFL'
    print completeness_dose(cd_dict)

    cd_dict = { }

    for record in open(src2, 'r').readlines():
        lst = map(float, record.split())

        if not lst:
            break

        cd_dict[lst[0]] = lst[3]

    print 'LREM'
    print completeness_dose(cd_dict)

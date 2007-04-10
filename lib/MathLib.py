#!/usr/bin/env python
# MathLib.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 5th April 2007
# 
# A library of generally useful mathematical functions.
# 

import math
import random

def linear_fit_ml(X, Y, S):
    '''Find a solution to the best fit equation for y = a + bx to the
    provided data with errors in the y coordinates. These should be
    lists or arrays.'''

    if len(X) != len(Y) or len(Y) != len(S):
        raise RuntimeError, 'input data not uniform lengths'

    if len(X) == 0:
        return 0.0, 0.0

    if len(X) == 1:
        return Y[0], 0.0

    # Find a best-fit straight line based on equations from P104 of
    # "Data reduction and error analysis in the physical sciences"
    # 0-07-911243-9.

    num = range(len(X))

    # for j in num:
    if False:
        print X[j], Y[j], S[j]
    
    inv_s_sq = sum([1.0 / (S[j] * S[j]) for j in num])
    x_sq_over_s_sq = sum([(X[j] * X[j]) / (S[j] * S[j]) for j in num])
    x_over_s_sq = sum([X[j] / (S[j] * S[j]) for j in num])
    y_over_s_sq = sum([Y[j] / (S[j] * S[j]) for j in num])
    xy_over_s_sq = sum([(X[j] * Y[j]) / (S[j] * S[j]) for j in num])

    _a = x_sq_over_s_sq * y_over_s_sq - x_over_s_sq * xy_over_s_sq
    _b = inv_s_sq * xy_over_s_sq - x_over_s_sq * y_over_s_sq
    _d = inv_s_sq * x_sq_over_s_sq - x_over_s_sq * x_over_s_sq

    a = _a / _d
    b = _b / _d

    return a, b

if __name__ == '__main__':

    X = [0.1 * j for j in range(100)]
    Y = [0.1 * j * 0.5 + (0.1 * (random.random() - 0.5)) for j in range(100)]
    S = [0.1 for j in range(100)]

    print linear_fit_ml(X, Y, S)

    

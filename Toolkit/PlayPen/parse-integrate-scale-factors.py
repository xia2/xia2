import math
import sys
import os

def parse_integrate_scale_factors(integrate_lp = 'INTEGRATE.LP'):

    scale_factors = { }

    collect_scale_factors = False

    for record in open(integrate_lp):
        if 'IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ' in record:
            collect_scale_factors = True
            continue

        if collect_scale_factors:
            if not record.strip():
                collect_scale_factors = False
                continue

            values = map(float, record.split())

            scale_factors[int(values[0])] = values[2]

    return scale_factors

def print_scale_factors(scale_factors):
    for j in sorted(scale_factors):
        print '%5d %.3f' % (j, scale_factors[j])

    return

if __name__ == '__main__':

    if len(sys.argv) > 1:
        print_scale_factors(parse_integrate_scale_factors(sys.argv[1]))
    else:
        print_scale_factors(parse_integrate_scale_factors())

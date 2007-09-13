#!/usr/bin/env python
# 
# A jiffy application to parse an unmerged scalepack file from Scala and then
# estimate error correction factors to apply based on observed spread and 
# error estimates.
# 

import math
import sys

def parse_scalepack(scalepack_file):
    '''Parse the scalepack file into a dictionary keyed by
    (h_r, k_r, l_r, J) where h_r, k_r, l_r are the reduced miller
    indices and J is the type of reflection (centric, I+, I-).
    The dictionary will contain a list of tuples ((h,k,l), batch, I, s(I)).'''

    results = { }

    for record in open(scalepack_file, 'r').readlines():

        # is header guff?
        if len(record) < 40:
            continue

        # nope
        h, k, l, hr, kr, lr = map(int, [record[4 * j:4 * (j + 1)].strip()
                                        for j in range(6)])

        batch = int(record[24:30].strip())

        J = int(record[31])

        I, sig_I = map(float, record[37:].split())

        key = ((hr, kr, lr), J)

        if not results.has_key(key):
            results[key] = []

        results[key].append(((h, k, l), batch, I, sig_I))

    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise RuntimeError, '%s reflections.sca' % sys.argv[0]
    
    reflections = parse_scalepack(sys.argv[1])

    indices = reflections.keys()

    chi_mean = 0.0
    chi_count = 0

    chi_min = 1000
    best_sdadd = 0.0
    best_sdfac = 0.0

    for sdfac_counter in range(10, 20):
        sdfac = 0.1 * sdfac_counter
        for sdadd_counter in range(0, 10):
            sdadd = 0.01 * sdadd_counter

            for i in indices:

                # this calculation is meaningless with fewer than
                # two reflections...

                if len(reflections[i]) < 2:
                    continue
                
                I_mean = 0.0
                sig_I_mean = 0.0
                sum_w = 0.0
                for r in reflections[i]:
                    I = r[2]
                    sig_I = sdfac * math.sqrt(r[3] * r[3] +
                                              sdadd * sdadd * I * I)
                    w = 1.0 / sig_I
                    sum_w += w
                    I_mean += I * w
                    sig_I_mean += w * w
                    
                I_mean /= sum_w
                sig_I_mean = math.sqrt(1.0 / sig_I_mean)

                chi_sq = 0.0
                N = 0

                for r in reflections[i]:
                    I = r[2]
                    sig_I = sdfac * math.sqrt(r[3] * r[3] +
                                              sdadd * sdadd * I * I)

                    I_others = 0.0
                    sum_w = 0.0
                    
                    for s in reflections[i]:
                        if id(r) is id(s):
                            continue
                        
                        Is = s[2]
                        sig_Is = sdfac * math.sqrt(s[3] * s[3] +
                                                   sdadd * sdadd * Is * Is)
                        w = 1.0 / sig_Is
                        sum_w += w
                        I_others += Is * w

                    I_others /= sum_w

                    # chi_sq = (I - I_others) * (I - I_others) / \
                    # (sig_I * sig_I + sig_I_mean * sig_I_mean)

                    chi_sq += (I - I_mean) * (I - I_mean) / \
                              (sig_I_mean * sig_I_mean + sig_I * sig_I)
                    N += 1

                chi_sq /= N
                        
                if chi_sq > 0:
                    chi_mean += math.fabs(chi_sq - 1.0)
                    chi_count += 1

            if (chi_mean / chi_count) < chi_min:
                best_sdadd = sdadd
                best_sdfac = sdfac
                chi_min = chi_mean / chi_count

            print sdfac, sdadd, chi_mean / chi_count

    print 'Best sdadd: %f' % best_sdadd
    print 'Best sdfac: %f' % best_sdfac
    

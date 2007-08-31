#!/usr/bin/env python

import sys

def get_mosflm_commands(lines_of_input):
    '''Get the commands which were sent to Mosflm.'''

    result = []

    for line in lines_of_input:
        if '===>' in line:
            result.append(line.replace('===>', '').strip())
        if 'MOSFLM =>' in line:
            result.append(line.replace('MOSFLM =>', '').strip())

    return result

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError, '%s mosflm.lp' % sys.argv[0]

    for line in get_mosflm_commands(open(sys.argv[1], 'r').readlines()):
        print line


                                                      

        
                          

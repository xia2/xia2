#!/usr/bin/env python

import sys

def get_ccp4_commands(lines_of_input):
    '''Get the commands which were sent to a CCP4 program.'''

    result = []

    for line in lines_of_input:
        if 'Data line---' in line:
            result.append(line.replace('Data line---', '').strip())

    return result

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError, '%s ccp4_program.log' % sys.argv[0]

    for line in get_ccp4_commands(open(sys.argv[1], 'r').readlines()):
        print line


                                                      

        
                          

#!/usr/bin/env python

import sys

def get_ccp4_commands(lines_of_input):
    '''Get the commands which were sent to a CCP4 program.'''

    # first look through for hklin / hklout

    logicals = { }

    for line in lines_of_input:
        if 'Logical Name:' in line:
            token = line.split(':')[1].split()[0]
            value = line.split(':')[-1].strip()
            logicals[token] = value

    # then look for standard input commands

    script = []

    for line in lines_of_input:
        if 'Data line---' in line:
            script.append(line.replace('Data line---', '').strip())

    return script, logicals

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError, '%s ccp4_program.log' % sys.argv[0]

    script, logicals = get_ccp4_commands(open(sys.argv[1], 'r').readlines())

    for token in logicals.keys():
        print token, logicals[token]

    for line in script:
        print line

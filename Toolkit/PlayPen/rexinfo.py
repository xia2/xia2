#!/usr/bin/env python

import sys

def parse_x1335_out(x1335_out):

    ds_to_sweep = { }
    
    for record in open(x1335_out):
        values = record.split()
        if not values:
            continue
        ds_to_sweep[int(values[0])] = values[-1].split('.')[0]

    return ds_to_sweep

def parse_xinfo(xinfo_file):
    # FIXME need to have a think about how to do this?!

    preamble = ''
    sweeps = { } 
    postamble = ''

    records = open(xinfo_file).readlines()

    for record in records:
        if 'BEGIN SWEEP' in record:
            break
        preamble += record

    saving = None

    for record in records:
        if 'BEGIN SWEEP' in record:
            saving = record.split()[-1]
            sweeps[saving] = record
            continue
        if 'END SWEEP' in record:
            sweeps[saving] += record
            sweeps[saving] += '\n'
            saving = None
            continue
        if saving:
            sweeps[saving] += record

    for record in records:
        if 'END CRYSTAL' in record:
            postamble = record
            continue
        if postamble:
            postamble += record

    return preamble, sweeps, postamble

def rexinfo(xinfo, x1335, x1335_keep):
    
    ds_to_sweep = parse_x1335_out(x1335)

    keep_sweeps = [ds_to_sweep[int(j)] for j in x1335_keep]

    preamble, sweeps, postamble = parse_xinfo(xinfo)

    prefix = None

    for record in preamble.split('\n'):
        if 'BEGIN WAVELENGTH' in record:
            prefix = record.split()[-1]

    if not prefix:
        raise RuntimeError, 'missed prefix'
    
    sys.stdout.write(preamble)

    for sweep in sweeps:
        sweep_id = '%s_%s' % (prefix, sweep)
        if sweep_id in keep_sweeps:
            sys.stdout.write(sweeps[sweep])

    sys.stdout.write(postamble)

    return

if __name__ == '__main__':
    rexinfo(sys.argv[1], sys.argv[2], sys.argv[3].split(','))

    

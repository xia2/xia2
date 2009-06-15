from rj_lib_parse_xds import rj_parse_idxref_xds_inp, rj_parse_idxref_lp, \
     rj_parse_integrate_lp, rj_parse_xds_correct_lp

from rj_lib_run_job import rj_run_job

from rj_lib_lattice_symmetry import lattice_symmetry, sort_lattices, \
     lattice_spacegroup

import shutil
import sys
import os
import time
import math

def nint(a):
    i = int(a)
    if (a - i) > 0.5:
        i += 1
    return i

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def lattice_test(integrate_lp, xds_inp_file):
    images, phi, cell, records = rj_parse_integrate_lp(
        open(integrate_lp).readlines())

    # next work through the XDS.INP file to get the proper name template
    # out...

    nt = None
    distance = None

    for record in open(xds_inp_file, 'r').readlines():
        if 'NAME_TEMPLATE_OF_DATA_FRAMES' in record:
            nt = record.strip()
        if 'DETECTOR_DISTANCE' in record:
            distance = record.strip()

    if not nt:
        raise RuntimeError, 'filename template not found in %s' % xds_inp_file

    if not distance:
        raise RuntimeError, 'distance not found in %s' % xds_inp_file
        
    r_new = [distance]

    for r in records:
        if not 'NAME_TEMPLATE_OF_DATA_FRAMES' in r:
            r_new.append(r)
        else:
            r_new.append(nt)

    records = r_new

    # ok, in here need to rerun XDS with all of the data from all of
    # the images and the triclinic target cell, then parse out the
    # solutions from the CORRECT.LP file (applying the cell constants -
    # done in the parser) and then use *these* as the target, as the
    # lattice symmetry code (interestingly) does not always give the
    # right answer...

    standard = [
        'JOB=CORRECT',
        'MAXIMUM_NUMBER_OF_PROCESSORS=4',
        'CORRECTIONS=!',
        'REFINE(CORRECT)=CELL',
        'OVERLOAD=65000',
        'DIRECTION_OF_DETECTOR_X-AXIS=1.0 0.0 0.0',
        'DIRECTION_OF_DETECTOR_Y-AXIS=0.0 1.0 0.0',
        'TRUSTED_REGION=0.0 1.41'
        ]

    # first get the list of possible lattices - do this by running CORRECT
    # with all of the images, then looking at the favourite settings for the
    # P1 result (or something) - meh.

    fout = open('XDS.INP', 'w')
    
    for record in standard:
        fout.write('%s\n' % record)
        
    for record in records:
        fout.write('%s\n' % record)
        
    fout.write('DATA_RANGE= %d %d\n' % images)
    fout.write('OSCILLATION_RANGE= %.2f\n' % phi)
    fout.write(
        'UNIT_CELL_CONSTANTS= %.2f %.2f %.2f %.2f %.2f %.2f\n' % tuple(cell))
    fout.write('SPACE_GROUP_NUMBER=%d\n' % 1)
    
    fout.close()
    
    output = rj_run_job('xds_par', [], [])    

    # read CORRECT.LP to get the right solutions...

    result = rj_parse_xds_correct_lp(open('CORRECT.LP', 'r').readlines())

    for lattice in result:
        cp = '%.2f %.2f %.2f %.2f %.2f %.2f' % result[lattice]['cell']
        # print '%s %s' % (lattice, cp)

    # result = lattice_symmetry(cell)
    lattices = sort_lattices(result)

    # then iterate through them...

    data = { }

    for l in lattices:

        data[l] = { }
        
        c = result[l]['cell']

        fout = open('XDS.INP', 'w')
            
        for record in standard:
            fout.write('%s\n' % record)
                
        for record in records:
            fout.write('%s\n' % record)
                
        fout.write('DATA_RANGE= %d %d\n' % (images))
        fout.write('OSCILLATION_RANGE= %.2f\n' % phi)
        fout.write(
            'UNIT_CELL_CONSTANTS= %.2f %.2f %.2f %.2f %.2f %.2f\n' % tuple(c))
        fout.write('SPACE_GROUP_NUMBER=%d\n' % lattice_spacegroup(l))

        fout.close()
            
        output = rj_run_job('xds_par', [], [])

        # now read out the records I want from CORRECT.LP...
            
        rmsd = None
        rmsp = None
        
        for record in open('CORRECT.LP').readlines():
            if 'STANDARD DEVIATION OF SPOT    POSITION' in record:
                rmsd = float(record.split()[-1])

            if 'STANDARD DEVIATION OF SPINDLE POSITION' in record:
                rmsp = float(record.split()[-1])
                    
        if not rmsp or not rmsd:
            raise RuntimeError, 'refinement failed'
        
        print '%s rmsd %f rmsp %f' % (l, rmsd, rmsp)
    
if __name__ == '__main__':
    lattice_test('INTEGRATE.LP', 'integrate/XDS.INP')

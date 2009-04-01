from rj_lib_parse_xds import rj_parse_idxref_xds_inp, rj_parse_idxref_lp, \
     rj_parse_integrate_lp

from rj_lib_run_job import rj_run_job

from rj_lib_lattice_symmetry import lattice_symmetry, sort_lattices, \
     lattice_spacegroup

import shutil
import sys
import os
import time

def nint(a):
    i = int(a)
    if (a - i) > 0.5:
        i += 1
    return i

def lattice_test(integrate_lp, xds_inp_file):
    images, phi, cell, records = rj_parse_integrate_lp(
        open(integrate_lp).readlines())

    # next work through the XDS.INP file to get the proper name template
    # out...

    nt = None

    for record in open(xds_inp_file, 'r').readlines():
        if 'NAME_TEMPLATE_OF_DATA_FRAMES' in record:
            nt = record

    if not nt:
        raise RuntimeError, 'filename template not found in %s' % xds_inp_file

    r_new = []

    for r in records:
        if not 'NAME_TEMPLATE_OF_DATA_FRAMES' in record:
            r_new.append(record)
        else:
            r_new.append(nt)

    records = r_new

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

    # first get the list of possible lattices

    result = lattice_symmetry(cell)
    lattices = sort_lattices(result)

    # then iterate through them...

    data = { }

    for l in lattices:

        data[l] = { }
        
        c = result[l]['cell']

        # then iterate through the image ranges

        w = nint(10.0/phi)
        m = nint((images[1] - images[0] + 1) / w)

        for j in range(m):
            start = j * w + 1
            end = j * w + w

            data[l][j] = { }

            fout = open('XDS.INP', 'w')
            
            for record in standard:
                fout.write('%s\n' % record)
                
            for record in records:
                fout.write('%s\n' % record)
                
            fout.write('DATA_RANGE= %d %d\n' % (start, end))
            fout.write('OSCILLATION_RANGE= %.2f\n' % phi)
            fout.write(
                'UNIT_CELL_CONSTANTS= %.2f %.2f %.2f %.2f %.2f %.2f\n' % tuple(c))
            fout.write('SPACE_GROUP_NUMBER=%d\n' % lattice_spacegroup(l))

            fout.close()
            
            output = rj_run_job('xds_par', [], [])

            for record in output:
                print record[:-1]
            
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
        
            data[l][j] = {'d':rmsd,
                          'p':rmsp}

    # now tabulate the results

    for j in range(m):
        record = '%d' % j
        for l in lattices[1:]:
            record += ' %.3f %.3f' % (data[l][j]['d'] / data['aP'][j]['d'],
                                      data[l][j]['p'] / data['aP'][j]['p'])

        print record


                        
    
if __name__ == '__main__':
    lattice_test('INTEGRATE.LP', 'integrate/XDS.INP')

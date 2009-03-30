from rj_lib_parse_xds import rj_parse_idxref_xds_inp, rj_parse_idxref_lp

from rj_lib_run_job import rj_run_job

from rj_lib_lattice_symmetry import lattice_symmetry, sort_lattices

import shutil
import sys
import os
import time

def nint(a):
    i = int(a)
    if (a - i) > 0.5:
        i += 1
    return i

# ok then, what happens here is to first parse the start of an INTEGRATE.LP
# file to get the guts of what I need, then take the unit cell and pass
# it over to iotbx.lattice_symmetry. Then for each of the "good" results
# run correct to get the rmsd and rmsphi for 10 degree wedges, allowing for
# the refinement of the cell constants. Store these and write
# the whole lot to a log file - wedge #, rmsd p1...
# 
# 


'''

NAME_TEMPLATE_OF_DATA_FRAMES=/home/gw56/mx-scratch/data/jcsg/1vr9/data/jcsg/als
1/8.2.1/20050121/collection/TM0892/12847/12847_4_???
DATA_RANGE=       1     180
NX=  2048 NY=  2048 QX= 0.10240 QY= 0.10240
MINIMUM_VALID_PIXEL_VALUE=     0    OVERLOAD=     65000
BACKGROUND_PIXEL=    6.00      SIGNAL_PIXEL=    3.00
MAXIMUM_ERROR_OF_SPOT_POSITION=   3.0
MINPK=   75.00
STARTING_ANGLE= 161.000 STARTING_FRAME=       1
OSCILLATION_RANGE=  0.500000 DEGREES
ROTATION_AXIS= 0.99999-0.00271 0.00336
X-RAY_WAVELENGTH=   0.99187 ANGSTROM
INCIDENT_BEAM_DIRECTION= -0.006465  0.003637  1.008170
SPACE_GROUP_NUMBER=    1
UNIT_CELL_CONSTANTS=    44.05    52.52   116.72  77.064  79.742  89.838
RESOLUTION RANGE RECORDED BY DETECTOR (ANGSTROM)    19.999     1.285
NUMBER OF TRUSTED DETECTOR PIXELS    4127643
MEAN CONTENTS OF TRUSTED PIXELS IN BACKGROUND TABLE  24800.535
MEAN VALUE OF NON-XRAY BACKGROUND (OFFSET)=    0.00
NUMBER OF X-RAY COUNTS EQUIVALENT TO PIXEL CONTENTS IN A DATA IMAGE
(PIXEL VALUE - OFFSET)/GAIN ,    WITH GAIN=    0.13

parse as far as *****

'''

JOB=CORRECT
MAXIMUM_NUMBER_OF_PROCESSORS=4
CORRECTIONS=!
REFINE(CORRECT)=CELL
DETECTOR=ADSC MINIMUM_VALID_PIXEL_VALUE=0 OVERLOAD=65000
DIRECTION_OF_DETECTOR_X-AXIS=1.0 0.0 0.0
DIRECTION_OF_DETECTOR_Y-AXIS=0.0 1.0 0.0
TRUSTED_REGION=0.0 1.41
NX=2048 NY=2048 QX=0.102400 QY=0.102400
DETECTOR_DISTANCE=150.100
OSCILLATION_RANGE=0.50
X-RAY_WAVELENGTH=0.991870
ROTATION_AXIS= 1.0 0.0 0.0
INCIDENT_BEAM_DIRECTION=0.0 0.0 1.0
FRACTION_OF_POLARIZATION=0.95
POLARIZATION_PLANE_NORMAL=0.0 1.0 0.0
AIR=0.001
NAME_TEMPLATE_OF_DATA_FRAMES=/home/gw56/mx-scratch/data/jcsg/1vr9/data/jcsg/als1/8.2.1/20050121/collection/TM0892/12847/12847_4_???.img
DATA_RANGE=1 180
SPACE_GROUP_NUMBER=5
UNIT_CELL_CONSTANTS=228.00  52.63  44.11  90.00 100.49  90.00


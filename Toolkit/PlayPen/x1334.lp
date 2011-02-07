 
 ***** INTEGRATE *****  (VERSION  December 6, 2010)             7-Feb-2011
 
 PROFILE_FITTING= TRUE
 NAME_TEMPLATE_OF_DATA_FRAMES=/data2/gw56/jcsg/12287_2L/12287_1_E1_???.img SMV
 DATA_RANGE=       1      60
 NX=  2048 NY=  2048 QX= 0.10240 QY= 0.10240
 MINIMUM_VALID_PIXEL_VALUE=     1    OVERLOAD=     65000
 BACKGROUND_PIXEL=    6.00      SIGNAL_PIXEL=    3.00
 MAXIMUM_ERROR_OF_SPOT_POSITION=   3.0
 MAXIMUM_ERROR_OF_SPINDLE_POSITION=   2.0
 MINPK=   75.00
 STARTING_ANGLE= 290.000 STARTING_FRAME=       1
 OSCILLATION_RANGE=  1.000000 DEGREES
 ROTATION_AXIS=  0.99999 -0.00017  0.00421
 X-RAY_WAVELENGTH=   0.97966 ANGSTROM
 INCIDENT_BEAM_DIRECTION= -0.004496  0.003443  1.020747
 SPACE_GROUP_NUMBER=   75
 UNIT_CELL_CONSTANTS=    51.55    51.55   157.56  90.000  90.000  90.000
 RESOLUTION RANGE RECORDED BY DETECTOR (ANGSTROM)    42.956     1.375
 NUMBER OF TRUSTED DETECTOR PIXELS    4122081
 MEAN CONTENTS OF TRUSTED PIXELS IN BACKGROUND TABLE  14292.678
 MEAN VALUE OF NON-XRAY BACKGROUND (OFFSET)=    0.00
 NUMBER OF X-RAY COUNTS EQUIVALENT TO PIXEL CONTENTS IN A DATA IMAGE
 (PIXEL VALUE - OFFSET)/GAIN ,    WITH GAIN=    0.12
 
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES        1 ...       5
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
     1   0  1.005  3908841    2   6186    1684     5  0.0545  0.2156
     2   0  1.034  3917703    1   6153    1629     5  0.0544  0.2073
     3   0  1.009  3921212    1   6124    1587     6  0.0543  0.2069
     4   0  1.004  3918169    1   6120    1593     5  0.0553  0.2084
     5   0  0.999  3912799    1   6132    1651    14  0.0544  0.2085
 
  3324 OUT OF   3443 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.52
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.26   1064.93
 DETECTOR ORIGIN (PIXELS) AT                     1034.55   1059.36
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.837   -19.415    46.900
 COORDINATES OF UNIT CELL B-AXIS     9.386    47.410    17.857
 COORDINATES OF UNIT CELL C-AXIS  -152.471    16.753    35.663
 REC. CELL PARAMETERS   0.019409  0.019409  0.006350  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.523    51.523   157.480  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3317 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  409    250    361    452    437    244    339    412    413
 SIGMAB (degree)       0.063  0.066  0.067  0.066  0.064  0.064  0.067  0.067  0.065
 SIGMAR (degree)       0.164  0.151  0.163  0.172  0.163  0.147  0.161  0.171  0.167
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3317 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  2  2  1  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  2  1  0  0  0     0  0  1  6 13  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  1  2  4  2  0  0  0    -1  0  1 10 24 11  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  7 14  7  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  1  0  0  0     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0
    -1 -1  1  4  7  4  1 -1  0    -1 -1  1  6 10  5  1 -1  0    -1 -1  1  4  8  4  1 -1  0
    -1  0  2 16 37 18  2  0 -1    -1  0  3 25 55 25  3  0 -1    -1  0  3 19 40 17  2  0 -1
    -1  0  3 29 69 29  3  0 -1    -1  0  5 45100 39  4  0 -1    -1  0  4 34 71 26  3  0 -1
    -1  0  2 19 39 17  2  0 -1    -1  0  3 27 54 23  3  0 -1    -1  0  2 20 38 16  2  0 -1
     0  0  1  4  8  4  1 -1 -1     0 -1  1  5 10  6  1 -1 -1     0  0  1  4  8  4  1  0 -1
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0 -1  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  7 16  7  1  0  0     0  0  0  1  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 13 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 14  6  1  0 -1     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14731 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES        6 ...      10
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
     6   0  0.999  3908180    2   6161    1657     9  0.0556  0.2032
     7   0  1.003  3904541    1   6140    1726    16  0.0549  0.2070
     8   0  0.998  3908593    2   6126    1633    14  0.0559  0.2072
     9   0  0.998  3903153    0   6198    1691     7  0.0547  0.2076
    10   0  1.001  3917540    0   6137    1654     5  0.0530  0.2135
 
  3478 OUT OF   3610 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.51
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.27   1064.94
 DETECTOR ORIGIN (PIXELS) AT                     1034.56   1059.36
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.837   -19.416    46.905
 COORDINATES OF UNIT CELL B-AXIS     9.391    47.414    17.857
 COORDINATES OF UNIT CELL C-AXIS  -152.480    16.767    35.668
 REC. CELL PARAMETERS   0.019407  0.019407  0.006350  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.529    51.529   157.491  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3468 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  454    254    382    486    430    243    363    440    415
 SIGMAB (degree)       0.063  0.065  0.066  0.066  0.064  0.064  0.066  0.066  0.065
 SIGMAR (degree)       0.164  0.149  0.163  0.175  0.165  0.147  0.159  0.169  0.165
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3468 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  1  2  1  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  2  1  0  0  0     0  0  1  6 13  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  4  2  0  0  0     0  0  1 10 24 11  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  7 14  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0
     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0
    -1 -1  1  4  7  4  1 -1  0    -1 -1  1  6 10  5  1 -1  0    -1 -1  1  4  7  4  1  0  0
    -1  0  2 16 37 18  2  0 -1    -1  0  3 25 54 24  3  0 -1    -1  0  3 19 40 17  2  0 -1
    -1  0  3 29 69 29  3  0 -1    -1  0  5 45100 39  4  0 -1    -1  0  4 35 71 25  3  0 -1
    -1  0  3 19 39 17  2  0 -1    -1  0  4 27 54 23  3  0 -1    -1  0  3 20 38 15  2  0 -1
     0  0  1  4  8  4  1 -1 -1     0  0  1  6 10  6  1 -1 -1     0  0  1  4  7  4  1  0  0
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0 -1  0  0 -1  0  0     0  0  0 -1  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  2  3  2  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 15  6  1  0  0     0  0  1  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  0  1  0  0  0  0
    -1  0  1  8 14  5  1  0 -1     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14750 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       11 ...      15
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    11   0  1.000  3915025    0   6135    1658     9  0.0540  0.2034
    12   0  1.006  3921539    1   6073    1555    10  0.0543  0.2006
    13   0  1.006  3918661    0   6123    1624    14  0.0543  0.2009
    14   0  1.008  3909456    0   6226    1714    12  0.0550  0.2055
    15   0  1.008  3912797    1   6194    1642     8  0.0558  0.2068
 
  3380 OUT OF   3505 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.52
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.28   1064.91
 DETECTOR ORIGIN (PIXELS) AT                     1034.57   1059.34
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.838   -19.421    46.907
 COORDINATES OF UNIT CELL B-AXIS     9.394    47.416    17.862
 COORDINATES OF UNIT CELL C-AXIS  -152.488    16.771    35.676
 REC. CELL PARAMETERS   0.019405  0.019405  0.006349  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.533    51.533   157.501  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3369 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  421    256    365    468    433    245    344    409    429
 SIGMAB (degree)       0.063  0.065  0.068  0.066  0.064  0.064  0.066  0.066  0.065
 SIGMAR (degree)       0.163  0.152  0.165  0.174  0.165  0.146  0.160  0.168  0.166
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3369 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  1  2  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  2  1  0  0  0     0  0  1  5 13  7  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  4  2  0  0  0     0  0  1  9 23 11  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  7 14  6  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  1  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0
     0 -1  0  1  1  1  0  0  0     0 -1  0  1  2  1  0  0  0     0 -1  0  1  1  1  0  0  0
    -1  0  1  4  7  4  1  0  0    -1 -1  1  5 10  5  1  0  0    -1 -1  1  4  7  4  1  0  0
    -1  0  2 16 37 18  2  0 -1    -1  0  4 25 54 25  3  0 -1    -1  0  3 19 40 18  2  0 -1
    -1  0  3 30 69 29  3  0 -1    -1  0  5 45100 40  4  0 -1    -1  0  4 35 71 26  3  0 -1
    -1  0  2 19 39 17  2  0 -1    -1  0  3 27 54 23  3  0 -1    -1  0  2 20 37 15  2  0 -1
     0  0  1  4  8  4  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  7  4  1  0  0
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  1  1  0 -1  0
     0  0  0  0  0 -1  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0 -1  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  0  0  0  0     0 -1  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  0  2  3  2  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 16  6  1  0  0     0  0  1  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1  8 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14683 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       16 ...      20
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    16   0  1.011  3918594    1   6085    1558    12  0.0551  0.2076
    17   0  1.012  3923608    1   6128    1562    13  0.0545  0.1952
    18   0  1.013  3912999    0   6165    1643    15  0.0548  0.1995
    19   0  1.014  3922874    2   6147    1585    11  0.0540  0.1963
    20   0  1.016  3920886    1   6131    1569    11  0.0551  0.2198
 
  3310 OUT OF   3420 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.53
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.33   1064.89
 DETECTOR ORIGIN (PIXELS) AT                     1034.61   1059.31
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.841   -19.428    46.908
 COORDINATES OF UNIT CELL B-AXIS     9.394    47.418    17.869
 COORDINATES OF UNIT CELL C-AXIS  -152.498    16.764    35.684
 REC. CELL PARAMETERS   0.019404  0.019404  0.006349  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.537    51.537   157.512  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3303 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  416    253    362    454    417    242    341    403    416
 SIGMAB (degree)       0.062  0.066  0.067  0.066  0.064  0.064  0.066  0.066  0.064
 SIGMAR (degree)       0.164  0.152  0.164  0.172  0.166  0.147  0.160  0.170  0.166
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3303 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  5 13  7  1  0  0
     0  0  0  0  1  1  0  0  0     0  0  0  2  5  2  1  0  0     0  0  1  9 24 11  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  2  1  0  0  0     0  0  1  7 14  6  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  1  0  0  0     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0
     0  0  1  4  7  4  1 -1  0    -1 -1  1  5 10  6  1 -1  0    -1 -1  1  4  8  4  1  0  0
    -1  0  2 16 37 18  2  0 -1    -1  0  3 24 53 25  3  0 -1    -1  0  2 19 39 17  2  0 -1
    -1  0  3 29 69 29  3  0 -1    -1  0  5 45100 40  4  0 -1    -1  0  4 35 70 26  3  0 -1
    -1  0  2 19 38 16  2  0 -1    -1  0  4 27 53 22  3  0 -1    -1  0  3 20 37 15  2  0 -1
     0  0  1  4  7  4  0 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  7  4  1  0 -1
     0  0 -1  1  1  1  0 -1  0     0  0 -1  1  2  1  0 -1  0     0  0  0  1  1  0  0  0  0
     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  0  0 -1  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  0  2  3  2  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 15  7  1  0 -1     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  0  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1  8 14  5  1  0  0    -1  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0 -1  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14677 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       21 ...      25
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    21   0  1.015  3908232    2   6217    1659    13  0.0564  0.2120
    22   0  1.012  3923739    2   6126    1527    18  0.0554  0.2022
    23   0  1.004  3914239    0   6117    1605     6  0.0557  0.2159
    24   0  1.001  3918799    1   6186    1595     9  0.0540  0.2131
    25   0  1.007  3919349    1   6132    1561    18  0.0547  0.2064
 
  3284 OUT OF   3386 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.54
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.15
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.35   1064.86
 DETECTOR ORIGIN (PIXELS) AT                     1034.63   1059.28
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.838   -19.429    46.912
 COORDINATES OF UNIT CELL B-AXIS     9.396    47.421    17.870
 COORDINATES OF UNIT CELL C-AXIS  -152.504    16.772    35.678
 REC. CELL PARAMETERS   0.019403  0.019403  0.006349  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.540    51.540   157.517  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3273 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  423    246    362    449    421    242    328    393    409
 SIGMAB (degree)       0.062  0.064  0.067  0.067  0.065  0.065  0.066  0.066  0.064
 SIGMAR (degree)       0.164  0.149  0.163  0.173  0.167  0.147  0.159  0.169  0.165
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3273 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  5 13  7  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  2  4  2  1  0  0     0  0  1 10 24 11  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  7 14  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0 -1  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0     0 -1  0  1  1  1  0  0  0
     0  0  1  4  7  4  1  0  0    -1 -1  1  6 10  5  1  0  0    -1 -1  1  4  8  4  1  0  0
    -1  0  2 16 37 18  2  0  0    -1  0  3 24 54 24  3  0 -1    -1  0  2 18 39 17  2  0 -1
     0  0  3 30 70 29  3  0 -1    -1  0  5 45100 39  4  0 -1    -1  0  4 34 70 25  2  0 -1
    -1  0  2 19 38 16  2  0 -1    -1  0  3 27 53 21  2  0 -1    -1  0  2 20 37 14  2  0 -1
     0  0  1  4  7  4  1 -1 -1     0  0  1  6 10  5  1 -1 -1     0 -1  1  4  7  4  1  0 -1
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  1  1  0  0  0
     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  0  2  3  2  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  7 15  6  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14713 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       26 ...      30
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    26   0  1.001  3916761    0   6166    1555    12  0.0555  0.2164
    27   0  0.993  3908093    1   6193    1638     5  0.0556  0.1987
    28   0  0.990  3923435    0   6155    1532    12  0.0550  0.2199
    29   0  0.985  3917593    0   6081    1547    10  0.0561  0.2167
    30   0  0.981  3911139    0   6254    1638    16  0.0550  0.2208
 
  3238 OUT OF   3354 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.55
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.33   1064.82
 DETECTOR ORIGIN (PIXELS) AT                     1034.62   1059.24
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.836   -19.436    46.914
 COORDINATES OF UNIT CELL B-AXIS     9.398    47.422    17.876
 COORDINATES OF UNIT CELL C-AXIS  -152.518    16.778    35.675
 REC. CELL PARAMETERS   0.019401  0.019401  0.006348  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.543    51.543   157.531  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3231 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  425    246    357    436    386    236    334    403    409
 SIGMAB (degree)       0.063  0.066  0.068  0.068  0.065  0.065  0.066  0.066  0.065
 SIGMAR (degree)       0.164  0.153  0.166  0.176  0.165  0.147  0.160  0.170  0.165
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3231 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  6 13  7  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 10 25 11  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  3  1  0  0  0     0  0  1  7 14  6  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  1  1  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  1  0  0  0     0 -1  0  1  2  1  0  0  0     0 -1  0  1  1  1  0  0  0
     0  0  1  4  7  4  1 -1  0     0 -1  1  6 10  6  1 -1  0     0  0  1  4  8  4  1  0  0
    -1  0  2 16 37 18  3  0 -1    -1  0  3 25 53 24  3  0 -1    -1  0  3 19 38 17  2  0 -1
    -1  0  3 30 69 29  3  0 -1    -1  0  5 46100 39  4  0 -1    -1  0  4 35 70 25  3  0 -1
    -1  0  2 19 38 16  2  0 -1    -1  0  3 28 54 22  3  0 -1    -1  0  3 21 38 15  2  0 -1
     0  0  1  4  7  4  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0  0  1  4  8  4  1 -1 -1
     0  0  0  1  2  1  0 -1  0     0  0 -1  1  2  1  0 -1  0     0  0 -1  1  2  1  0  0  0
     0  0  0 -1  0  0 -1  0  0     0  0  0 -1  0  0 -1  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  0  2  3  2  0  0  0    -1  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  8 15  6  1  0  0     0  0  0  2  3  1  0  0 -1     0  0  0  1  1  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1  9 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14776 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       31 ...      35
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    31   0  0.962  3917517    0   6104    1554     8  0.0553  0.2282
    32   0  0.978  3928505    1   6112    1428    12  0.0555  0.2287
    33   0  0.977  3922357    0   6153    1505    11  0.0550  0.2158
    34   0  0.965  3915183    0   6179    1555    11  0.0563  0.2352
    35   0  0.964  3908275    0   6244    1583    20  0.0561  0.2182
 
  3078 OUT OF   3187 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.57
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.14
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.37   1064.79
 DETECTOR ORIGIN (PIXELS) AT                     1034.65   1059.21
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.851   -19.445    46.924
 COORDINATES OF UNIT CELL B-AXIS     9.396    47.436    17.885
 COORDINATES OF UNIT CELL C-AXIS  -152.561    16.753    35.720
 REC. CELL PARAMETERS   0.019395  0.019395  0.006346  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.559    51.559   157.580  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    3068 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  420    241    334    404    367    229    317    373    383
 SIGMAB (degree)       0.063  0.065  0.068  0.067  0.065  0.065  0.066  0.066  0.064
 SIGMAR (degree)       0.165  0.153  0.165  0.176  0.168  0.148  0.158  0.168  0.168
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   3068 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  1  1  0  0  0  0     0  0  0  1  3  1  0  0  0     0  0  1  6 13  7  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 10 24 11  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  1  1  3  1  0  0  0     0  0  1  7 14  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  2  3  2  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0 -1  0 -1  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0 -1  0  0  0  0  0
     0 -1  0  0  1  1  0  0  0     0 -1  0  1  1  1  0  0  0     0 -1  0  0  1  1  0  0  0
     0 -1  1  4  7  5  1 -1  0    -1 -1  1  6 10  6  1 -1  0    -1 -1  1  4  8  5  1  0  0
    -1  0  2 17 38 19  3  0 -1    -1  0  3 25 54 25  3  0 -1    -1  0  2 19 39 17  2  0 -1
    -1  0  3 31 69 29  3  0 -1    -1  0  5 47100 39  4  0 -1    -1  0  4 36 70 26  3  0 -1
     0  0  3 20 38 16  2  0 -1    -1  0  4 28 54 22  2  0 -1    -1  0  3 21 38 15  2  0 -1
     0 -1  1  4  7  4  0 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  8  3  1  0 -1
     0  0  0  1  1  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  0  0  0  0
     0  0  0 -1  0 -1 -1  0  0     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0 -1 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  0  2  3  2  1  0  0    -1  0  0  1  1  0  0  0  0    -1  0  0  0  0  0  0  0  0
    -1  0  1  8 15  6  1  0  0    -1  0  0  2  3  1  0  0  0    -1  0  0  0  1  0  0  0  0
    -1  0  2 14 26  9  1  0  0     0  0  0  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1  8 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
     0 -1  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14752 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       36 ...      40
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    36   0  0.965  3933158    0   6126    1431    11  0.0547  0.2433
    37   0  0.966  3932430    1   6057    1412    12  0.0550  0.2176
    38   0  0.966  3926505    0   6152    1477     9  0.0546  0.2369
    39   0  0.966  3922417    1   6220    1467    13  0.0553  0.2308
    40   0  0.969  3920119    0   6220    1534    11  0.0555  0.2311
 
  2921 OUT OF   3032 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.54
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.15
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.42   1064.73
 DETECTOR ORIGIN (PIXELS) AT                     1034.71   1059.15
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.849   -19.451    46.927
 COORDINATES OF UNIT CELL B-AXIS     9.397    47.438    17.891
 COORDINATES OF UNIT CELL C-AXIS  -152.580    16.753    35.716
 REC. CELL PARAMETERS   0.019394  0.019394  0.006345  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.563    51.563   157.598  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    2915 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  398    227    287    377    362    221    314    364    366
 SIGMAB (degree)       0.063  0.065  0.068  0.067  0.065  0.065  0.067  0.067  0.065
 SIGMAR (degree)       0.165  0.148  0.164  0.174  0.166  0.148  0.162  0.171  0.165
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   2915 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  1  3  2  1 -1  0
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  6 14  7  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 10 24 11  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  3  1  0  0  0     0  0  1  7 14  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0 -1 -1  0  0
 
 
     0  0  0 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0
     0 -1  0  1  1  1  0  0  0     0 -1  0  1  2  1  0 -1  0     0 -1  0  1  1  1  0  0  0
     0 -1  1  4  7  5  1 -1  0     0 -1  1  5 10  6  2 -1  0    -1 -1  1  4  8  5  1  0  0
    -1  0  2 16 37 19  3  0 -1    -1  0  3 24 53 25  4  0 -1    -1  0  3 18 38 17  2  0 -1
    -1  0  3 30 69 29  3  0 -1    -1  0  5 46100 40  4  0 -1    -1  0  4 35 69 25  3  0 -1
    -1  0  2 19 37 15  2  0 -1    -1  0  3 28 53 21  3  0 -1    -1  0  3 21 37 14  2  0  0
     0  0  1  4  7  4  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  7  3  1 -1  0
     0  0  0  1  1  1  0 -1  0     0  0 -1  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0 -1  0 -1 -1  0  0     0  0  0  0  0 -1 -1  0  0     0  0  0  0  0 -1 -1  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0 -1  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  1  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  2  3  2  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  7 15  6  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0
     0  0  1 14 25  9  1  0  0     0  0  0  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1  9 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  2  3  1  0 -1  0     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14725 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       41 ...      45
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    41   0  0.965  3914247    0   6293    1549    12  0.0565  0.2339
    42   0  0.966  3916450    0   6261    1533    21  0.0552  0.2353
    43   0  0.967  3923304    0   6148    1515    22  0.0539  0.2212
    44   0  0.966  3935123    1   6123    1408    11  0.0553  0.2558
    45   0  0.965  3940424    0   6118    1388    18  0.0556  0.2185
 
  2977 OUT OF   3097 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.58
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.16
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.44   1064.69
 DETECTOR ORIGIN (PIXELS) AT                     1034.72   1059.11
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.846   -19.449    46.933
 COORDINATES OF UNIT CELL B-AXIS     9.394    47.444    17.890
 COORDINATES OF UNIT CELL C-AXIS  -152.596    16.753    35.703
 REC. CELL PARAMETERS   0.019392  0.019392  0.006345  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.567    51.567   157.610  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    2971 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  413    237    310    392    357    218    302    365    376
 SIGMAB (degree)       0.063  0.065  0.068  0.068  0.065  0.065  0.067  0.066  0.064
 SIGMAR (degree)       0.165  0.151  0.164  0.174  0.164  0.148  0.162  0.171  0.167
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   2971 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  0  1  1  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  6 14  8  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 11 25 11  2  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  1  0  0  0    -1  0  1  7 14  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  2  3  2  0 -1 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0 -1  0     0  0  0  0  1  0  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0 -1  0  0  0  0  0     0  0  0 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  1  1  1  0  0  0     0 -1  0  1  2  1  0 -1  0     0 -1 -1  1  1  1  0  0  0
     0 -1  1  4  7  5  1 -1  0     0 -1  1  5 10  6  2 -1  0     0 -1  1  4  8  5  1  0  0
    -1  0  2 16 37 19  3  0 -1    -1  0  3 24 51 25  3  0 -1    -1  0  2 18 36 17  2  0 -1
    -1  0  3 31 70 29  3  0 -1    -1  0  5 47100 39  4  0 -1    -1  0  4 35 69 25  3  0 -1
    -1  0  3 19 38 16  2  0 -1    -1  0  4 28 54 21  3  0 -1    -1  0  3 21 38 14  2  0 -1
     0 -1  1  4  7  4  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  7  4  1 -1 -1
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0  0  0 -1  0  0  0     0  0  0  0  0 -1 -1  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  7 14  6  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
    -1  0  2 14 25  9  1  0  0     0  0  0  3  5  1  0  0  0     0  0  0  0  1  0  0  0  0
    -1  0  1  8 14  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14798 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       46 ...      50
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    46   0  0.958  3938227    0   6094    1386    13  0.0551  0.2363
    47   0  0.964  3933969    0   6090    1407    12  0.0548  0.2219
    48   0  0.964  3931614    0   6077    1394    16  0.0563  0.2166
    49   0  0.964  3934196    1   6124    1389    15  0.0543  0.2205
    50   0  0.959  3939357    0   6068    1391    10  0.0558  0.2217
 
  2874 OUT OF   2998 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.59
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.15
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.45   1064.65
 DETECTOR ORIGIN (PIXELS) AT                     1034.74   1059.07
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.848   -19.454    46.937
 COORDINATES OF UNIT CELL B-AXIS     9.397    47.448    17.895
 COORDINATES OF UNIT CELL C-AXIS  -152.609    16.754    35.711
 REC. CELL PARAMETERS   0.019390  0.019390  0.006344  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.574    51.574   157.625  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    2865 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  392    220    311    375    360    220    296    338    355
 SIGMAB (degree)       0.063  0.066  0.068  0.068  0.066  0.065  0.067  0.066  0.064
 SIGMAR (degree)       0.166  0.152  0.162  0.173  0.167  0.149  0.161  0.170  0.166
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   2865 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0 -1  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  1  0  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  6 15  8  1  0 -1
     0  0  0  1  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 10 25 11  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  7 14  6  1  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  2  3  2  0  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0 -1  0     0  0  0  0  1  0  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  1  0  0  0     0 -1  0  1  2  1  0 -1  0     0 -1  0  1  1  1  0  0  0
     0  0  0  4  8  5  1 -1  0     0 -1  1  6 11  7  2 -1  0     0 -1  1  4  8  5  1  0  0
    -1  0  2 16 39 20  3  0 -1    -1  0  3 24 53 26  4  0 -1    -1  0  2 17 37 17  3  0 -1
    -1  0  3 31 71 30  3  0 -1    -1  0  4 46100 40  4  0 -1    -1  0  3 34 69 25  3  0 -1
    -1  0  2 19 38 16  2  0 -1    -1  0  3 28 54 22  3  0 -1    -1  0  2 21 38 14  2  0 -1
     0  0  1  4  7  4  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  5  8  3  1 -1 -1
     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0  0  0 -1 -1  0  0     0  0  0  0  0 -1 -1  0  0     0  0  0  0  0 -1  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  1  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  1  0  0     0  0  0  0  1  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  1  7 14  6  1  0  0     0  0  0  2  3  2  0  0  0     0  0  0  0  1  0  0  0  0
    -1  0  1 13 26  9  1  0 -1     0  0  0  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
     0  0  1  8 15  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0
     0  0  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14637 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       51 ...      55
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    51   0  0.956  3935373    1   6102    1376    17  0.0552  0.2360
    52   0  0.951  3930827    0   6132    1419    11  0.0558  0.2609
    53   0  0.949  3925012    1   6214    1465    15  0.0552  0.2418
    54   0  0.944  3923110    0   6250    1518    14  0.0547  0.2500
    55   0  0.940  3925312    0   6271    1504    24  0.0551  0.2417
 
  2882 OUT OF   2986 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.57
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.16
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.49   1064.60
 DETECTOR ORIGIN (PIXELS) AT                     1034.77   1059.03
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.842   -19.475    46.934
 COORDINATES OF UNIT CELL B-AXIS     9.393    47.445    17.918
 COORDINATES OF UNIT CELL C-AXIS  -152.630    16.735    35.697
 REC. CELL PARAMETERS   0.019388  0.019388  0.006344  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.578    51.578   157.639  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    2874 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  419    236    322    368    334    216    283    340    356
 SIGMAB (degree)       0.062  0.066  0.068  0.067  0.067  0.065  0.066  0.066  0.064
 SIGMAR (degree)       0.163  0.152  0.161  0.170  0.165  0.147  0.162  0.172  0.168
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   2874 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0 -1  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  1  0  0  0     0 -1  0  1  3  2  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  5 13  7  1  0  0
     0  0  0  1  1  1  0  0  0     0  0  1  2  5  2  0  0  0     0  0  1 11 24 10  1  0  0
     0  0  0  0  1  0  0  0  0     0  0  1  2  3  1  0  0  0    -1  0  1  7 13  5  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  2  3  1  0  0 -1
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0 -1  0     0  0  0  0  1  1  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0 -1 -1  0  0
 
 
     0  0  0 -1  0  0  0  0  0     0  0  0 -1  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1 -1  0  1  1  0  0  0     0 -1 -1  0  2  1  0  0  0     0 -1 -1  0  2  1  0  0  0
     0 -1  0  3  8  5  1  0  0     0 -1  1  5 10  7  2  0  0     0 -1  1  4  8  5  1  0  0
    -1  0  2 15 37 19  3  0 -1    -1  0  3 23 52 25  4  0 -1    -1  0  2 17 37 17  2  0  0
     0  0  4 31 68 28  3  0 -1    -1  0  5 47100 39  4  0 -1    -1  0  4 36 70 26  3  0 -1
    -1  0  3 19 36 15  2  0 -1    -1  0  4 28 53 21  2  0 -1    -1  0  3 22 39 14  2  0 -1
     0  0  1  4  7  3  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  4  8  4  1 -1 -1
     0 -1  0  1  1  1  0 -1  0     0  0  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0  0  0  0 -1  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  1  1  1  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  1  7 14  6  1  0  0     0  0  0  1  3  1  1  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 14 26  9  1  0  0     0  0  0  3  5  2  0  0  0     0  0  0  1  1  1  0  0  0
    -1  0  1  9 15  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  1  1  1  0  0  0
     0 -1  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14793 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING
 
 
 ******************************************************************************
                     PROCESSING OF IMAGES       56 ...      60
 ******************************************************************************
 
 USING   5 PROCESSORS
 
 *** DEFINITION OF SYMBOLS ***
 IER     = ERROR CODE AFTER ACCESSING DATA IMAGE
              0: NO ERROR
             -1: CANNOT OPEN OR READ IMAGE FILE
             -3: WRONG DATA FORMAT
 SCALE   = SCALING FACTOR FOR THIS DATA IMAGE
 NBKG    = NUMBER OF BACKGROUND PIXELS ON DATA IMAGE
 NOVL    = NUMBER OF OVERLOADED REFLECTIONS ON DATA IMAGE
 NEWALD  = NUMBER OF REFLECTIONS CLOSE TO THE EWALD SPHERE
 NSTRONG = NUMBER OF STRONG REFLECTIONS ON DATA IMAGE
 NREJ    = NUMBER OF UNEXPECTED REFLECTIONS
 SIGMAB  = BEAM_DIVERGENCE_E.S.D.=SIGMAB
 SIGMAR  = REFLECTING_RANGE_E.S.D.=SIGMAR (MOSAICITY)
 
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ  SIGMAB  SIGMAR
    56   0  0.936  3932535    0   6255    1418    12  0.0553  0.2228
    57   0  0.935  3936402    1   6154    1420    20  0.0550  0.2349
    58   0  0.934  3939395    1   6087    1385    13  0.0536  0.2278
    59   0  0.938  3950441    0   6055    1278    15  0.0541  0.2196
    60   0  0.944  3936008    0   6127    1396    18  0.0553  0.2307
 
  2720 OUT OF   2825 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.57
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.15
 CRYSTAL MOSAICITY (DEGREES)     0.185
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004496  0.003443  1.020747
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.57   1064.56
 DETECTOR ORIGIN (PIXELS) AT                     1034.85   1058.98
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.37
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999991 -0.000172  0.004214
 COORDINATES OF UNIT CELL A-AXIS     8.848   -19.478    46.938
 COORDINATES OF UNIT CELL B-AXIS     9.391    47.451    17.920
 COORDINATES OF UNIT CELL C-AXIS  -152.631    16.722    35.709
 REC. CELL PARAMETERS   0.019386  0.019386  0.006343  90.000  90.000  90.000
 UNIT CELL PARAMETERS     51.584    51.584   157.643  90.000  90.000  90.000
 SPACE GROUP NUMBER     75
 
 
 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    2714 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3
 NUMBER                  376    209    318    373    325    210    291    313    298
 SIGMAB (degree)       0.063  0.066  0.069  0.068  0.066  0.065  0.066  0.066  0.064
 SIGMAR (degree)       0.167  0.152  0.163  0.172  0.164  0.151  0.164  0.172  0.168
 
 
 ***** AVERAGE THREE-DIMENSIONAL PROFILE OF   2714 STRONG REFLECTIONS *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0 -1  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  2  0  0  0     0  0  1  6 14  8  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  1 11 25 10  1  0 -1
     0  0  0  0  1  0  0  0  0     0  0  0  1  3  1  0  0  0    -1  0  1  7 13  6  1  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0  0  0     0  0  0  2  3  1  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  1  0  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0 -1  0 -1  0  0  0     0  0  0 -1  0 -1  0  0  0     0  0  0  0  0  0  0  0  0
     0 -1  0  0  1  1  0 -1  0     0 -1 -1  1  2  1  0  0  0     0 -1  0  1  2  1  0  0  0
     0 -1  1  4  8  5  1 -1  0     0 -1  1  5 10  7  2 -1  0     0  0  1  4  7  5  1  0  0
    -1  0  2 16 38 19  3  0 -1    -1  0  3 23 52 25  4  0 -1    -1  0  2 17 36 17  3  0 -1
    -1  0  3 31 69 28  3  0 -1    -1  0  5 47100 39  4  0 -1    -1  0  4 36 70 26  3  0 -1
    -1  0  3 19 37 15  2 -1 -1    -1  0  4 28 54 21  3 -1 -1    -1  0  3 22 40 15  2 -1 -1
     0 -1  1  4  7  3  1 -1 -1     0 -1  1  6 10  5  1 -1 -1     0 -1  1  5  8  3  1 -1 -1
     0 -1  0  1  1  1  0 -1  0     0 -1  0  1  2  1  0 -1  0     0  0  0  1  2  1  0 -1  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  1  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  1  0  0     0  0  0  0  1  1  0  0  0     0  0  0  0  0  0  0  0  0
    -1  0  1  7 14  6  1  0  0     0  0  0  1  3  1  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  2 14 26  9  1  0  0     0  0  1  3  5  2  0  0  0     0  0  0  1  1  0  0  0  0
    -1  0  1 10 16  5  1  0  0     0  0  0  2  3  1  0  0  0     0  0  0  0  1  0  0  0  0
     0  0  0  2  3  1  0  0  0     0  0  0  1  1  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  1  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
  14785 REFLECTION INTENSITIES INTEGRATED BY PROFILE FITTING


 ******************************************************************************
  REFERENCE PROFILES AS FUNCTION OF DETECTOR POSITION
 ******************************************************************************

 PROFILES ARE DETERMINED AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 1024.0 1787.2 1563.7 1024.0  484.3  260.8  484.3 1024.0 1563.7
 Y-COORDINATE (pixel) 1024.0 1024.0 1563.7 1787.2 1563.7 1024.0  484.3  260.8  484.3




 ***** RUN-AVERAGE OF PROFILE #  1 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  5 13  6  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  0 11 25  9  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  7 14  5  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  3  6  3  0  0  0     0  0  0  4  8  4  0  0  0     0  0  0  3  6  3  0  0  0
     0  0  2 16 35 15  2  0  0     0  0  3 24 50 19  3  0  0     0  0  2 18 36 13  0  0  0
     0  0  3 31 70 24  2  0  0     0  0  5 47100 32  3  0  0     0  0  3 36 71 21  2  0  0
     0  0  2 19 37 13  0  0  0     0  0  3 27 51 18  2  0  0     0  0  2 20 37 13  0  0  0
     0  0  0  4  6  3  0  0  0     0  0  0  5  8  4  0  0  0     0  0  0  4  6  3  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  7 14  5  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 14 27  8  0  0  0     0  0  0  3  5  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  8 14  5  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  2 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  3  8  4  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0 10 18  7  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  2  0  0  0  0     0  0  0  9 13  5  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  3  4  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  3  5  3  0  0  0     0  0  0  6  8  5  0  0  0     0  0  0  5  7  4  0  0  0
     0  0  2 12 25 12  2  0  0     0  0  3 23 43 22  3  0  0     0  0  3 19 33 18  2  0  0
     0  0  4 33 62 23  2  0  0     0  0  6 54100 37  3  0  0     0  0  4 37 67 25  2  0  0
     0  0  3 26 40 15  0  0  0     0  0  4 35 57 21  2  0  0     0  0  3 21 36 13  0  0  0
     0  0  0  6  9  4  0  0  0     0  0  0  6 11  5  0  0  0     0  0  0  4  7  3  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  6 12  6  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 12 21  7  0  0  0     0  0  0  2  4  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  7 11  4  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  3 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  6 12  6  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  4  2  0  0  0     0  0  0  9 22 11  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  2  0  0  0     0  0  0  6 15  8  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  4  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  3  2  0  0  0     0  0  0  2  2  0  0  0  0
     0  0  0  5  8  4  0  0  0     0  0  2  8 13  6  0  0  0     0  0  2  7 10  5  0  0  0
     0  0  2 18 35 15  2  0  0     0  0  4 30 53 21  3  0  0     0  0  3 24 38 14  2  0  0
     0  0  3 30 66 29  3  0  0     0  0  5 51100 40  4  0  0     0  0  4 43 72 26  3  0  0
     0  0  2 16 44 22  3  0  0     0  0  3 26 67 31  3  0  0     0  0  3 23 51 21  2  0  0
     0  0  0  4  9  6  0  0  0     0  0  0  6 14  8  0  0  0     0  0  0  5 11  5  0  0  0
     0  0  0  0  2  2  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  3  4  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 10 15  5  0  0  0     0  0  0  3  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  3 18 28  9  0  0  0     0  0  0  4  6  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 10 20  7  0  0  0     0  0  0  3  4  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  4  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  4 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  3  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  3  0  0  0     0  0  0  5 15 10  2  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  6  3  0  0  0     0  0  0 10 27 13  2  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  4  2  0  0  0     0  0  0  7 17  8  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  2  4  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  2  0  0  0     0  0  0  0  2  2  0  0  0
     0  0  0  3  8  7  2  0  0     0  0  0  5 11  8  2  0  0     0  0  0  4  8  6  2  0  0
     0  0  2 14 40 24  4  0  0     0  0  3 21 55 30  5  0  0     0  0  3 17 40 20  3  0  0
     0  0  3 29 72 33  4  0  0     0  0  4 44100 41  5  0  0     0  0  4 38 74 27  3  0  0
     0  0  2 19 44 19  2  0  0     0  0  3 29 62 24  3  0  0     0  0  3 24 47 16  2  0  0
     0  0  0  4  9  5  0  0  0     0  0  0  6 12  6  0  0  0     0  0  0  5  9  4  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  4  3  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  8 16  7  0  0  0     0  0  0  3  4  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 18 31 10  0  0  0     0  0  0  4  7  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 12 20  6  0  0  0     0  0  0  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  4  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  5 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  3  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  3  0  0  0     0  0  0  4 14 12  2  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  5  3  0  0  0     0  0  0 10 25 13  2  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  7 13  5  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  3  6  6  2  0  0     0  0  0  3  8  7  3  0  0     0  0  0  2  5  5  2  0  0
     0  0  0 11 37 29  5  0  0     0  0  2 16 50 34  6  0  0     0  0  2 12 35 21  3  0  0
     0  0  3 29 70 33  4  0  0     0  0  4 46100 43  5  0  0     0  0  3 36 71 26  3  0  0
     0  0  2 20 35 12  2  0  0     0  0  4 32 50 16  2  0  0     0  0  3 26 36 10  0  0  0
     0  0  0  4  6  3  0  0  0     0  0  2  6  9  4  0  0  0     0  0  0  5  7  3  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  5 13  7  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 14 26  9  0  0  0     0  0  0  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 10 14  4  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  6 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  6 11  7  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  2  0  0  0     0  0  0  9 19  9  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  4  8  4  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  4  6  4  0  0  0     0  0  0  5  7  5  0  0  0     0  0  0  3  4  3  0  0  0
     0  0  3 19 34 19  3  0  0     0  0  4 27 46 23  4  0  0     0  0  2 16 27 12  2  0  0
     0  0  3 30 63 29  3  0  0     0  0  5 49100 43  5  0  0     0  0  4 33 64 25  3  0  0
     0  0  2 14 26 13  2  0  0     0  0  4 26 47 23  3  0  0     0  0  3 20 34 16  2  0  0
     0  0  0  3  5  3  0  0  0     0  0  0  5  9  5  0  0  0     0  0  0  5  7  4  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  5  8  4  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 10 19  7  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  7 11  5  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  7 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  3  0  0  0  0     0  0  2 10 15  5  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  4  2  0  0  0     0  0  2 10 24 11  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  4 11  7  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  2  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  6  8  3  0  0  0     0  0  2  8 10  5  0  0  0     0  0  0  6  7  3  0  0  0
     0  0  4 27 42 13  2  0  0     0  0  5 38 57 18  3  0  0     0  0  4 26 38 12  2  0  0
     0  0  4 31 70 29  3  0  0     0  0  6 46100 41  4  0  0     0  0  5 33 68 27  3  0  0
     0  0  2 12 31 19  3  0  0     0  0  3 19 47 28  4  0  0     0  0  3 15 34 19  3  0  0
     0  0  0  3  6  4  0  0  0     0  0  0  5  9  6  0  0  0     0  0  0  4  7  4  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 10 14  4  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  2 12 24  9  0  0  0     0  0  0  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  6 13  7  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  8 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  2  4  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  4  2  0  0  0     0  0  2  7 18  7  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  6  3  0  0  0     0  0  0 10 28 12  2  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  3  2  0  0  0     0  0  0  7 15  7  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  2  3  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  5 10  5  0  0  0     0  0  0  7 14  6  0  0  0     0  0  0  6 11  5  0  0  0
     0  0  3 19 48 19  2  0  0     0  0  3 27 66 26  3  0  0     0  0  3 21 50 18  2  0  0
     0  0  3 27 74 31  3  0  0     0  0  5 39100 40  4  0  0     0  0  4 30 71 27  3  0  0
     0  0  2 17 38 18  3  0  0     0  0  3 22 49 22  3  0  0     0  0  2 16 33 15  2  0  0
     0  0  0  4  7  4  0  0  0     0  0  0  5  9  5  0  0  0     0  0  0  4  7  4  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  3  0  0  0  0     0  0  0  0  2  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  3  5  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  9 20  7  0  0  0     0  0  0  2  4  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 12 27 10  0  0  0     0  0  0  3  6  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  6 13  6  0  0  0     0  0  0  2  3  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  2  3  2  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 ***** RUN-AVERAGE OF PROFILE #  9 *****
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  2  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  4 12  6  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  5  2  0  0  0     0  0  0 11 25 10  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  2  4  0  0  0  0     0  0  0 11 16  5  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  3  4  2  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  3  7  4  0  0  0     0  0  0  4 10  6  0  0  0     0  0  0  3  8  5  0  0  0
     0  0  0 11 35 18  2  0  0     0  0  2 16 53 28  3  0  0     0  0  2 12 41 22  2  0  0
     0  0  3 31 71 26  2  0  0     0  0  4 43100 37  3  0  0     0  0  3 30 70 25  2  0  0
     0  0  3 27 41 13  0  0  0     0  0  4 33 51 16  2  0  0     0  0  3 21 32 10  0  0  0
     0  0  0  6  8  3  0  0  0     0  0  0  7  9  4  0  0  0     0  0  0  4  6  3  0  0  0
     0  0  0  0  2  0  0  0  0     0  0  0  0  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
 
 
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  4  3  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  5 17  9  0  0  0     0  0  0  0  3  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0 11 25  9  0  0  0     0  0  0  2  5  2  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  7 11  4  0  0  0     0  0  0  2  2  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  3  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0
     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0     0  0  0  0  0  0  0  0  0


 STANDARD DEVIATION (DEGREES) OF BEAM DIVERGENCE
 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1    0.044  0.047  0.047  0.047  0.045  0.046  0.047  0.048  0.046
     2    0.044  0.046  0.047  0.047  0.045  0.045  0.047  0.047  0.046
     3    0.044  0.046  0.048  0.047  0.045  0.045  0.047  0.047  0.046
     4    0.044  0.046  0.047  0.047  0.045  0.046  0.047  0.047  0.046
     5    0.044  0.046  0.048  0.047  0.046  0.046  0.047  0.047  0.045
     6    0.044  0.047  0.048  0.048  0.046  0.046  0.047  0.047  0.046
     7    0.045  0.046  0.048  0.048  0.046  0.046  0.047  0.047  0.045
     8    0.044  0.046  0.048  0.048  0.046  0.046  0.047  0.047  0.046
     9    0.044  0.046  0.048  0.048  0.046  0.046  0.047  0.047  0.045
    10    0.045  0.047  0.048  0.048  0.047  0.046  0.047  0.047  0.045
    11    0.044  0.047  0.048  0.048  0.047  0.046  0.046  0.047  0.046
    12    0.044  0.047  0.048  0.048  0.047  0.046  0.047  0.047  0.045


 STANDARD DEVIATION (DEGREES) OF REFLECTING RANGE
 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1    0.164  0.151  0.163  0.172  0.163  0.147  0.161  0.171  0.167
     2    0.164  0.149  0.163  0.175  0.165  0.147  0.159  0.169  0.165
     3    0.163  0.152  0.165  0.174  0.165  0.146  0.160  0.168  0.166
     4    0.164  0.152  0.164  0.172  0.166  0.147  0.160  0.170  0.166
     5    0.164  0.149  0.163  0.173  0.167  0.147  0.159  0.169  0.165
     6    0.164  0.153  0.166  0.176  0.165  0.147  0.160  0.170  0.165
     7    0.165  0.153  0.165  0.176  0.168  0.148  0.158  0.168  0.168
     8    0.165  0.148  0.164  0.174  0.166  0.148  0.162  0.171  0.165
     9    0.165  0.151  0.164  0.174  0.164  0.148  0.162  0.171  0.167
    10    0.166  0.152  0.162  0.173  0.167  0.149  0.161  0.170  0.166
    11    0.163  0.152  0.161  0.170  0.165  0.147  0.162  0.172  0.168
    12    0.167  0.152  0.163  0.172  0.164  0.151  0.164  0.172  0.168


 ***** SUGGESTED VALUES FOR INPUT PARAMETERS *****
 BEAM_DIVERGENCE=   0.464  BEAM_DIVERGENCE_E.S.D.=   0.046
 REFLECTING_RANGE=  1.138  REFLECTING_RANGE_E.S.D.=  0.163



 NUMBER OF STRONG REFLECTIONS USED FOR LEARNING REFERENCE PROFILES

 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1      409    250    361    452    437    244    339    412    413
     2      454    254    382    486    430    243    363    440    415
     3      421    256    365    468    433    245    344    409    429
     4      416    253    362    454    417    242    341    403    416
     5      423    246    362    449    421    242    328    393    409
     6      425    246    357    436    386    236    334    403    409
     7      420    241    334    404    367    229    317    373    383
     8      398    227    287    377    362    221    314    364    366
     9      413    237    310    392    357    218    302    365    376
    10      392    220    311    375    360    220    296    338    355
    11      419    236    322    368    334    216    283    340    356
    12      376    209    318    373    325    210    291    313    298
 margin    4967   2874   4072   5033   4628   2767   3851   4552   4624



 NUMBER OF GRID POINTS IN REFERENCE PROFILES WITH  SIGNAL >   2.% OF MAXIMUM

 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1       87     90     97    100     90     82     97    101     91
     2       87     85     97    102     90     82     94     95     89
     3       86     87    107    101     93     81     95     98     90
     4       85     87     99    102     91     82     90     95     88
     5       86     81    101    104     95     83     95     99     86
     6       85     89    103    110     93     86     95     97     88
     7       89     86    103    107     96     86     91     95     88
     8       89     85    104    106     98     85     96    100     89
     9       88     84     99    107     95     87    100     97     87
    10       88     90     98    107     96     87     98    102     88
    11       86     88     97    103     99     86     97    103     92
    12       90     91    101    106     96     89     96    102     92
 margin      92     97    118    120    105     93    111    113    102

 MINIMUM INTEGRATION VOLUME IS   81 GRID POINTS



 CORRELATIONS BETWEEN REFERENCE PROFILES WITH CENTRAL PROFILE #1

 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1     1.00   0.98   0.98   0.99   0.98   0.98   0.98   0.98   0.99
     2     1.00   0.98   0.99   0.99   0.98   0.98   0.98   0.98   0.99
     3     1.00   0.98   0.98   0.99   0.98   0.98   0.98   0.98   0.98
     4     1.00   0.98   0.99   0.99   0.98   0.98   0.98   0.98   0.99
     5     1.00   0.98   0.98   0.99   0.98   0.98   0.98   0.98   0.98
     6     1.00   0.99   0.98   0.99   0.98   0.98   0.98   0.98   0.99
     7     1.00   0.98   0.98   0.99   0.98   0.98   0.98   0.98   0.99
     8     1.00   0.98   0.98   0.99   0.98   0.98   0.98   0.98   0.99
     9     1.00   0.99   0.98   0.99   0.98   0.98   0.98   0.98   0.99
    10     1.00   0.99   0.98   0.99   0.98   0.98   0.98   0.99   0.99
    11     1.00   0.99   0.98   0.99   0.99   0.98   0.98   0.98   0.99
    12     1.00   0.99   0.98   0.99   0.99   0.99   0.99   0.99   0.99
 margin    1.00   0.99   0.98   0.99   0.98   0.98   0.98   0.98   0.99



 CORRELATIONS BETWEEN REFERENCE PROFILES WITH RUN-AVERAGED PROFILES

 BATCH-                           PROFILE NUMBER
 NUMBER      1      2      3      4      5      6      7      8      9
     1     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     2     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     3     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     4     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     5     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     6     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     7     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     8     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
     9     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
    10     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
    11     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
    12     1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00
 margin    1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00   1.00



      CORRELATION BETWEEN OBSERVED AND EXPECTED PROFILES

  I/Sigma  = mean of intensity/Sigma, where
  Sigma^2  =  4.0*[variance(I; from counting statistics)
                   + 0.00010*I^2]
  CORR     = mean correlation factor between observed and
             expected reflection profiles.
  E.S.D.   = estimated standard deviation of CORR.
  <I>      = mean LP-corrected reflection intensity,
             assuming unpolarized incident beam.
  NUMBER   = number of accepted reflections used to calculate
             I/Sigma, CORR, E.S.D., and <I>.

       I/Sigma        CORR      E.S.D.      <I>      NUMBER

       -3...-2      -0.258      0.092      -258.        444
       -2...-1      -0.178      0.050       -45.       2410
       -1... 0      -0.117      0.065       -14.       8991
        0... 1       0.135      0.075        17.      15619
        1... 2       0.229      0.080        47.      14742
        2... 3       0.346      0.087        77.      10516
        3... 6       0.533      0.113       132.      17644
        6... 9       0.723      0.089       220.       9642
        9...12       0.809      0.077       307.       6862
       12...15       0.851      0.067       395.       5226
       15...18       0.869      0.063       485.       4143
       18...21       0.880      0.068       578.       3378
       21...24       0.882      0.071       682.       2974
       24...27       0.886      0.066       802.       2768
       27...30       0.886      0.063       928.       2497
       30...33       0.885      0.060      1091.       2266
       33...36       0.879      0.066      1268.       2296
       36...39       0.878      0.056      1521.       2368
       39...42       0.868      0.058      1875.       2549
       42...45       0.858      0.057      2396.       2955
       45...48       0.844      0.055      3714.       4135
       48...51       0.805      0.058      7488.       3450

  127875 REFLECTIONS SAVED ON FILE "INTEGRATE.HKL"


 Time spent in the multi-tasking/processing part of INTEGRATE

     job #  cpu-time  wall-clock time (sec)
        1      158.0      33.3


 Time spent in the final, sequential part of INTEGRATE
            cpu-time  wall-clock time (sec)
                 2.1       1.8

 total cpu time used                160.0 sec
 total elapsed wall-clock time       35.1 sec

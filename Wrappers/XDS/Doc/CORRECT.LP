
 ***** CORRECT *****  (XDS VERSION  June 2006)               17-Oct-2006

 INPUT PARAMETER VALUES
 ----------------------
 SPACE_GROUP_NUMBER=    1
 UNIT_CELL_CONSTANTS=    51.49    51.52   157.35  90.040  90.017  90.137
 FRIEDEL'S_LAW=FALSE
 PROFILE_FITTING= TRUE 
 OVERLOAD=   65000     MINPK=  75.0    WFAC1=   1.0
 INCLUDE_RESOLUTION_RANGE=   100.000     1.650
 NAME_TEMPLATE_OF_DATA_FRAMES=/data/graeme/12287/12287_1_E1_???.img SMV DIRECT  
 DATA_RANGE=       1      60
 ROTATION_AXIS=  0.999988 -0.000083  0.004992
 OSCILLATION_RANGE=  1.000000
 STARTING_ANGLE=     0.000     STARTING_FRAME=       1
 X-RAY_WAVELENGTH=  0.979660
 INCIDENT_BEAM_DIRECTION= -0.005143  0.003602  1.020743
 FRACTION_OF_POLARIZATION=   0.950
 POLARIZATION_PLANE_NORMAL=  0.000000  1.000000  0.000000
 AIR=   0.00100
 DETECTOR=ADSC                                              
 DIRECTION_OF_DETECTOR_X-AXIS=   1.00000   0.00000   0.00000
 DIRECTION_OF_DETECTOR_Y-AXIS=   0.00000   1.00000   0.00000
 DETECTOR_DISTANCE=   169.077
 ORGX=   1035.66  ORGY=   1059.02
 NX=  2048  NY=  2048    QX=  0.102400  QY=  0.102400
 BEAM_DIVERGENCE_E.S.D.=   0.051
 REFLECTING_RANGE_E.S.D.=   0.188
 MAXIMUM_ERROR_OF_SPOT_POSITION=   3.0
 REFERENCE_DATA_SET=                                                  

 *****  1 EQUIVALENT POSITIONS IN SPACE GROUP #  1 *****

    If x',y',z' is an equivalent position to x,y,z, then
        x'=x*ML(1)+y*ML( 2)+z*ML( 3)+ML( 4)/12.0
        y'=x*ML(5)+y*ML( 6)+z*ML( 7)+ML( 8)/12.0
        z'=x*ML(9)+y*ML(10)+z*ML(11)+ML(12)/12.0

    #    1  2  3  4    5  6  7  8    9 10 11 12 
    1    1  0  0  0    0  1  0  0    0  0  1  0

  112443 REFLECTIONS ON FILE "INTEGRATE.HKL"
       0 REFLECTIONS INCOMPLETE OR OUTSIDE IMAGE RANGE       1 ...      60
      39 OVERLOADED REFLECTIONS (IGNORED)
       3 REFLECTIONS OUTSIDE ACCEPTED RESOLUTION RANGES (IGNORED)
       0 REFLECTIONS REJECTED AS REQUESTED FROM FILE "REMOVE.HKL"
  112401 REFLECTIONS ACCEPTED



 ******************************************************************************
  REFINEMENT OF DIFFRACTION PARAMETERS USING ALL IMAGES
 ******************************************************************************


 REFINED PARAMETERS:  DISTANCE BEAM ORIENTATION CELL AXIS                   
 USING   73664 INDEXED SPOTS
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.61
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.13
 CRYSTAL MOSAICITY (DEGREES)     0.188
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.004840  0.003798  1.020744
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    1027.34   1064.89
 DETECTOR ORIGIN (PIXELS) AT                     1035.19   1058.74
 CRYSTAL TO DETECTOR DISTANCE (mm)       169.43
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000
 LAB COORDINATES OF ROTATION AXIS  0.999988 -0.000284  0.004813
 COORDINATES OF UNIT CELL A-AXIS    -9.652   -32.946    38.513
 COORDINATES OF UNIT CELL B-AXIS    -8.920   -37.430   -34.367
 COORDINATES OF UNIT CELL C-AXIS   152.425   -39.827     4.107
 REC. CELL PARAMETERS   0.019383  0.019383  0.006345  89.929  89.994  89.907
 UNIT CELL PARAMETERS     51.593    51.591   157.596  90.071  90.006  90.093
 E.S.D. OF CELL PARAMETERS  3.4E-02 2.4E-02 5.6E-02 1.6E-02 3.1E-02 2.3E-02
 SPACE GROUP NUMBER      1


 THE DATA COLLECTION STATISTICS REPORTED BELOW ASSUMES:
 SPACE_GROUP_NUMBER=    1
 UNIT_CELL_CONSTANTS=    51.59    51.59   157.60  90.071  90.006  90.093


 ******************************************************************************
        MEAN INTENSITY AS FUNCTION OF SPINDLE POSITION WITHIN DATA IMAGE
 ******************************************************************************

 This statistics could serve as a diagnostic tool for detecting
 shutter problems (suggested by Kay Diederichs).
 Data are corrected for this effect if PATCH_SHUTTER_PROBLEM=TRUE in XDS.INP.
 ===> Selected : PATCH_SHUTTER_PROBLEM=FALSE

 INTERVAL = Angular interval in units of the oscillation range
            covered by a data image.
 NUMBER   = Number of reflections in each interval
 INTENSITY= Mean intensity of the reflections in each interval
 FACTOR   = Correction factor applied to intensities;
            INTENSITY(overall)/INTENSITY(interval)

  INTERVAL    NUMBER      INTENSITY      FACTOR
  0.0  0.1     11327        781.210       1.014
  0.1  0.2     11102        813.719       0.973
  0.2  0.3     11188        790.581       1.002
  0.3  0.4     11283        816.338       0.970
  0.4  0.5     11193        753.717       1.051
  0.5  0.6     11263        754.494       1.050
  0.6  0.7     11332        790.909       1.001
  0.7  0.8     11188        773.537       1.024
  0.8  0.9     11320        807.781       0.980
  0.9  1.0     11205        836.990       0.946
 
  0.0  1.0    112401        791.916       1.000
 

 ******************************************************************************
                INITIAL CORRECTIONS FOR BULK RADIATION DAMAGE
 ******************************************************************************

 The correction factor applied to a reflection intensity is

 D      = exp{[IFRAME-FFRAME]*SS*B},        where

 IFRAME = running number of image containing reflection peak
 FFRAME = running number of the first image in the data set
 LFRAME = running number of the last  image in the data set
 SS     = (2*sin(theta)/lambda)^2
 B      = decay constant of data set (enforced non-negative)
 Dmax(low_res)  correction factor applied to reflections recorded
                on the last image (LFRAME) at low resolution
 Dmax(high_res) correction factor applied to reflections recorded
                on the last image (LFRAME) at high resolution

 NOTE, that values D>1 compensate for intensity loss of the
          reflection due to radiation damage.

 DATA  FFRAME  LFRAME      B     Dmax(low_res)  Dmax(high_res)
 SET#

    1     0.1    59.9   0.0184  1.000(  78.80)  1.497(   1.65)

 ************************************************************************
      INITIAL SCALING, CRYSTAL DISORDER, AND ABSORPTION CORRECTIONS
 ************************************************************************

      The correction factor applied to the intensities is determined
      by 8 parameters for each data set as:

      K*EXP(B*SS+SUM(i<=j){a(i,j)*[S0(i)*S0(j)+S1(i)*S1(j)]})

      K      factor to scale each data set to the reference data set
      B      xtal disorder (B-factor relative to reference data set)
      SS     (2*sin(theta)/lambda)^2
      a(i,j) describes crystal absorption by the 6 components of a
             symmetric matrix (0<i<=j<=3)
      S0(i), are the x,y,z direction cosines of the incident
      S1(i)  and diffracted beam for each reflection with respect
             to a crystal-fixed orthonormal coordinate system.
             Note, that a11+a22+a33=0.
      N      number of parameters describing crystal absorption.
             (6 :: normal case; 1 :: if S0 and S1 are not available)

 DATA    K        B      a11      a12      a22      a13      a23      a33    N
 SET#

   1   1.0000   0.000   0.0078   0.0479   0.1046   0.0172  -0.0583  -0.1125  6

 ******************************************************************************
  RECIPROCAL SCALING FACTORS AS FUNCTION OF DETECTOR POSITION AND IMAGE NUMBER
 ******************************************************************************

 RECIPROCAL SCALING FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     


 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW=FALSE
 TOTAL NUMBER OF SCALING FACTORS DEFINED         156
 RANK OF NORMAL MATRIX                           156
 NUMBER OF CYCLES CARRIED OUT                      3
 ACCURACY OF SCALING FACTORS                0.000000

 REC. SCALING FACTORS FOR DATA SET INTEGRATE.HKL                                     
 FRAME-                     X,Y-DETECTOR POSITION (pixel) 
 NUMBER   1024  1370   677   677  1370  1808  1349   699   240   240   699  1349  1808
          1025  1371  1371   678   678  1350  1809  1809  1350   700   240   240   700
    2.6  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
    7.6  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   12.6  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   17.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   22.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   27.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   32.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   37.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   42.5  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   47.4  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   52.4  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0
   57.4  1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
             0     0     0     0     0     0     0     0     0     0     0     0     0

 ******************************************************************************
    CORRECTION PARAMETERS FOR THE STANDARD ERROR OF REFLECTION INTENSITIES
 ******************************************************************************

 The initial estimate v0(I) for the variance of the reflection intensity I
 is replaced by v(I)=a*(v0(I)+b*I^2). The two constants a and b are chosen
 for each input data set to minimize the discrepancies between v(I) and the
 variance estimated from sample statistics of symmetry related reflections.

      a          b              INPUT DATA SET
  1.000E+00  0.000E+00  INTEGRATE.HKL                                     
 

 ******************************************************************************
      STANDARD ERROR OF REFLECTION INTENSITIES AS FUNCTION OF RESOLUTION
      FOR DATA SET  XDS_ASCII.HKL                                     
 ******************************************************************************

  I/Sigma  = mean intensity/Sigma of a reflection in shell
  Chi^2    = goodness of fit between sample variances of
             symmetry-related intensities and their errors
             (Chi^2 = 1 for perfect agreement)
  R-FACTOR
  observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
  expected = expected R-FACTOR derived from Sigma(I)

   NUMBER  = number of reflections in resolution shell
             used for calculation of R-FACTOR
  ACCEPTED = number of accepted reflections
  REJECTED = number of rejected reflections (MISFITS),
             recognized by comparison with symmetry-related
             reflections.

 RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR  NUMBER ACCEPTED REJECTED
                                   observed  expected

   78.798  16.182    36.45   0.00    -99.90    -99.90       0     133       0
   16.182  11.565    37.85   0.00    -99.90    -99.90       0     230       0
   11.565   9.477    37.64   0.00    -99.90    -99.90       0     289       0
    9.477   8.222    35.89   0.00    -99.90    -99.90       0     319       0
    8.222   7.362    38.57   0.00    -99.90    -99.90       0     393       0
    7.362   6.725    38.66   0.00    -99.90    -99.90       0     457       0
    6.725   6.230    33.74   0.00    -99.90    -99.90       0     504       0
    6.230   5.830    36.06   0.00    -99.90    -99.90       0     494       0
    5.830   5.498    34.19   0.00    -99.90    -99.90       0     570       0
    5.498   5.217    37.41   0.00    -99.90    -99.90       0     549       0
    5.217   4.975    36.69   0.00    -99.90    -99.90       0     643       0
    4.975   4.764    36.59   0.00    -99.90    -99.90       0     632       0
    4.764   4.578    39.16   0.00    -99.90    -99.90       0     656       0
    4.578   4.412    37.18   0.00    -99.90    -99.90       0     706       0
    4.412   4.263    38.69   0.00    -99.90    -99.90       0     663       0
    4.263   4.128    36.58   0.00    -99.90    -99.90       0     776       0
    4.128   4.005    37.70   0.00    -99.90    -99.90       0     735       0
    4.005   3.892    34.15   0.00    -99.90    -99.90       0     807       0
    3.892   3.789    33.15   0.00    -99.90    -99.90       0     831       0
    3.789   3.693    36.51   0.00    -99.90    -99.90       0     760       0
    3.693   3.604    34.05   0.00    -99.90    -99.90       0     889       0
    3.604   3.522    31.66   0.00    -99.90    -99.90       0     893       0
    3.522   3.444    32.49   0.00    -99.90    -99.90       0     848       0
    3.444   3.372    31.28   0.00    -99.90    -99.90       0     954       0
    3.372   3.304    29.24   0.00    -99.90    -99.90       0     920       0
    3.304   3.240    30.93   0.00    -99.90    -99.90       0     956       0
    3.240   3.179    28.28   0.00    -99.90    -99.90       0     964       0
    3.179   3.122    27.92   0.00    -99.90    -99.90       0    1020       0
    3.122   3.068    24.70   0.00    -99.90    -99.90       0     944       0
    3.068   3.017    25.58   0.00    -99.90    -99.90       0     993       0
    3.017   2.968    23.89   0.00    -99.90    -99.90       0    1124       0
    2.968   2.921    21.70   0.00    -99.90    -99.90       0    1022       0
    2.921   2.876    21.95   0.00    -99.90    -99.90       0    1015       0
    2.876   2.834    20.50   0.00    -99.90    -99.90       0    1110       0
    2.834   2.793    20.39   0.00    -99.90    -99.90       0    1114       0
    2.793   2.754    19.44   0.00    -99.90    -99.90       0    1095       0
    2.754   2.717    18.52   0.00    -99.90    -99.90       0    1081       0
    2.717   2.681    18.51   0.00    -99.90    -99.90       0    1170       0
    2.681   2.646    18.58   0.00    -99.90    -99.90       0    1210       0
    2.646   2.613    16.29   0.00    -99.90    -99.90       0    1166       0
    2.613   2.581    16.28   0.00    -99.90    -99.90       0    1111       0
    2.581   2.550    15.79   0.00    -99.90    -99.90       0    1246       0
    2.550   2.520    14.66   0.00    -99.90    -99.90       0    1251       0
    2.520   2.491    15.96   0.00    -99.90    -99.90       0    1251       0
    2.491   2.464    14.93   0.00    -99.90    -99.90       0    1214       0
    2.464   2.437    14.42   0.00    -99.90    -99.90       0    1191       0
    2.437   2.411    13.69   0.00    -99.90    -99.90       0    1322       0
    2.411   2.385    14.25   0.00    -99.90    -99.90       0    1291       0
    2.385   2.361    14.75   0.00    -99.90    -99.90       0    1275       0
    2.361   2.337    13.62   0.00    -99.90    -99.90       0    1321       0
    2.337   2.314    13.25   0.00    -99.90    -99.90       0    1371       0
    2.314   2.292    12.25   0.00    -99.90    -99.90       0    1332       0
    2.292   2.270    11.93   0.00    -99.90    -99.90       0    1305       0
    2.270   2.249    12.23   0.00    -99.90    -99.90       0    1370       0
    2.249   2.229    12.32   0.00    -99.90    -99.90       0    1409       0
    2.229   2.209    11.37   0.00    -99.90    -99.90       0    1359       0
    2.209   2.189    10.98   0.00    -99.90    -99.90       0    1437       0
    2.189   2.170     9.98   0.00    -99.90    -99.90       0    1345       0
    2.170   2.152    10.88   0.00    -99.90    -99.90       0    1420       0
    2.152   2.134     9.09   0.00    -99.90    -99.90       0    1441       0
    2.134   2.116     8.61   0.00    -99.90    -99.90       0    1498       0
    2.116   2.099     8.82   0.00    -99.90    -99.90       0    1379       0
    2.099   2.082     8.93   0.00    -99.90    -99.90       0    1494       0
    2.082   2.066     7.93   0.00    -99.90    -99.90       0    1420       0
    2.066   2.050     8.16   0.00    -99.90    -99.90       0    1574       0
    2.050   2.035     7.30   0.00    -99.90    -99.90       0    1512       0
    2.035   2.019     7.09   0.00    -99.90    -99.90       0    1466       0
    2.019   2.004     6.46   0.00    -99.90    -99.90       0    1581       0
    2.004   1.990     6.65   0.00    -99.90    -99.90       0    1407       0
    1.990   1.976     6.19   0.00    -99.90    -99.90       0    1565       0
    1.976   1.962     6.24   0.00    -99.90    -99.90       0    1579       0
    1.962   1.948     5.11   0.00    -99.90    -99.90       0    1603       0
    1.948   1.935     5.47   0.00    -99.90    -99.90       0    1567       0
    1.935   1.922     5.24   0.00    -99.90    -99.90       0    1487       0
    1.922   1.909     5.39   0.00    -99.90    -99.90       0    1583       0
    1.909   1.896     4.14   0.00    -99.90    -99.90       0    1645       0
    1.896   1.884     3.95   0.00    -99.90    -99.90       0    1661       0
    1.884   1.872     4.41   0.00    -99.90    -99.90       0    1607       0
    1.872   1.860     3.83   0.00    -99.90    -99.90       0    1502       0
    1.860   1.848     3.72   0.00    -99.90    -99.90       0    1508       0
    1.848   1.837     3.34   0.00    -99.90    -99.90       0    1480       0
    1.837   1.825     3.42   0.00    -99.90    -99.90       0    1423       0
    1.825   1.814     3.49   0.00    -99.90    -99.90       0    1505       0
    1.814   1.804     2.94   0.00    -99.90    -99.90       0    1434       0
    1.804   1.793     2.99   0.00    -99.90    -99.90       0    1413       0
    1.793   1.782     2.89   0.00    -99.90    -99.90       0    1457       0
    1.782   1.772     2.76   0.00    -99.90    -99.90       0    1324       0
    1.772   1.762     2.51   0.00    -99.90    -99.90       0    1448       0
    1.762   1.752     2.62   0.00    -99.90    -99.90       0    1340       0
    1.752   1.742     2.31   0.00    -99.90    -99.90       0    1205       0
    1.742   1.733     2.11   0.00    -99.90    -99.90       0    1227       0
    1.733   1.723     2.01   0.00    -99.90    -99.90       0    1146       0
    1.723   1.714     2.41   0.00    -99.90    -99.90       0    1106       0
    1.714   1.705     2.03   0.00    -99.90    -99.90       0     991       0
    1.705   1.696     1.93   0.00    -99.90    -99.90       0    1029       0
    1.696   1.687     1.96   0.00    -99.90    -99.90       0    1009       0
    1.687   1.678     1.68   0.00    -99.90    -99.90       0     938       0
    1.678   1.670     1.83   0.00    -99.90    -99.90       0     887       0
    1.670   1.661     1.66   0.00    -99.90    -99.90       0     896       0
    1.661   1.653     1.54   0.00    -99.90    -99.90       0     608       0
   --------------------------------------------------------------------------
   78.798   1.653    13.30   0.00    -99.90    -99.90       0  112401       0
 


 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR VARIOUS SUBSETS OF INCLUDED DATA IMAGES
 ******************************************************************************

 Data set statistics is reported below several times, each with a different
 upper limit on the number of images included. This provides the user with
 the information for deciding which data images should be excluded from the
 final data set because of radiation damage or other defects. If the user
 decides for a subset of "good" images that differs from the specification
 as given by the input parameter (see DATA_RANGE= in XDS.INP) the CORRECT-
 step of XDS must be repeated with the new parameter values for DATA_RANGE=.


 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1      11
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95         855     855     14516        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        1556    1556     26362        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        1993    1993     33980        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        2356    2356     40484        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        2637    2637     45710        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        2961    2961     50658        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        3158    3158     55252        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        2903    2903     59146        4.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        2039    2039     62822        3.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       20458   20458    388930        5.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95         855     855     14516        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        1553    1553     26362        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        1992    1992     33980        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        2343    2343     40484        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        2603    2603     45710        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        2910    2910     50658        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        3020    3020     55252        5.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        2647    2647     59146        4.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        1816    1816     62822        2.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       19739   19739    388930        5.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95         838     838     14516        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        1530    1530     26362        5.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        1921    1921     33980        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        2154    2154     40484        5.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        2268    2268     45710        5.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        2330    2330     50658        4.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        2034    2034     55252        3.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1289    1289     59146        2.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         632     632     62822        1.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       14996   14996    388930        3.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95         821     821     14516        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        1495    1495     26362        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        1826    1826     33980        5.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        1947    1947     40484        4.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        1927    1927     45710        4.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        1809    1809     50658        3.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        1197    1197     55252        2.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75         557     557     59146        0.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         188     188     62822        0.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       11767   11767    388930        3.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95         812     812     14516        5.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        1465    1465     26362        5.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        1741    1741     33980        5.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        1747    1747     40484        4.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        1614    1614     45710        3.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        1394    1394     50658        2.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87         756     756     55252        1.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75         257     257     59146        0.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65          59      59     62822        0.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total        9845    9845    388930        2.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   20459
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                      20459
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                20459



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1      21
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        1619    1619     14516       11.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        2973    2973     26362       11.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        3831    3831     33980       11.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        4540    4540     40484       11.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        5081    5081     45710       11.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        5636    5636     50658       11.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        6063    6063     55252       11.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        5618    5618     59146        9.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        3913    3913     62822        6.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       39274   39274    388930       10.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        1618    1618     14516       11.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        2968    2968     26362       11.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        3826    3826     33980       11.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        4502    4502     40484       11.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        5011    5011     45710       11.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        5524    5524     50658       10.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        5775    5775     55252       10.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        5128    5128     59146        8.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        3458    3458     62822        5.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       37810   37810    388930        9.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        1586    1586     14516       10.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        2924    2924     26362       11.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        3699    3699     33980       10.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        4106    4106     40484       10.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        4373    4373     45710        9.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        4374    4374     50658        8.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        3769    3769     55252        6.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        2376    2376     59146        4.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        1165    1165     62822        1.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       28372   28372    388930        7.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        1554    1554     14516       10.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        2859    2859     26362       10.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        3499    3499     33980       10.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        3688    3688     40484        9.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        3692    3692     45710        8.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        3327    3327     50658        6.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        2258    2258     55252        4.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1034    1034     59146        1.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         357     357     62822        0.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       22268   22268    388930        5.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        1528    1528     14516       10.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        2804    2804     26362       10.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        3330    3330     33980        9.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        3297    3297     40484        8.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        3090    3090     45710        6.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        2503    2503     50658        4.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        1426    1426     55252        2.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75         489     489     59146        0.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         123     123     62822        0.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       18590   18590    388930        4.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   39276
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                      39276
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                39276



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1      31
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2396    2396     14516       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        4389    4389     26362       16.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        5697    5697     33980       16.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        6715    6715     40484       16.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        7535    7535     45710       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        8339    8339     50658       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        9018    9018     55252       16.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        8340    8340     59146       14.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        5780    5780     62822        9.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       58209   58209    388930       15.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2394    2394     14516       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        4382    4382     26362       16.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        5686    5686     33980       16.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        6660    6660     40484       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        7428    7428     45710       16.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        8156    8156     50658       16.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        8560    8560     55252       15.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        7613    7613     59146       12.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        5080    5080     62822        8.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       55959   55959    388930       14.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2347    2347     14516       16.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        4320    4320     26362       16.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        5487    5487     33980       16.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        6066    6066     40484       15.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        6454    6454     45710       14.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        6400    6400     50658       12.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        5443    5443     55252        9.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        3495    3495     59146        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        1644    1644     62822        2.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       41656   41656    388930       10.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2304    2304     14516       15.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        4228    4228     26362       16.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        5211    5211     33980       15.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        5439    5439     40484       13.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        5397    5397     45710       11.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        4792    4792     50658        9.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        3258    3258     55252        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1510    1510     59146        2.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         491     491     62822        0.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       32630   32630    388930        8.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2258    2258     14516       15.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        4148    4148     26362       15.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        4957    4957     33980       14.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        4850    4850     40484       12.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        4508    4508     45710        9.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        3560    3560     50658        7.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        2036    2036     55252        3.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75         735     735     59146        1.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         166     166     62822        0.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       27218   27218    388930        7.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   58211
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                      58211
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                58211



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1      40
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3106    3106     14516       21.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        5652    5652     26362       21.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        7326    7326     33980       21.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        8665    8665     40484       21.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        9735    9735     45710       21.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       10764   10764     50658       21.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       11643   11643     55252       21.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75       10719   10719     59146       18.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        7487    7487     62822       11.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       75097   75097    388930       19.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3104    3104     14516       21.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        5643    5643     26362       21.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        7314    7314     33980       21.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        8587    8587     40484       21.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        9587    9587     45710       21.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       10493   10493     50658       20.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       11007   11007     55252       19.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        9732    9732     59146       16.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        6540    6540     62822       10.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       72007   72007    388930       18.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3045    3045     14516       21.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        5558    5558     26362       21.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        7030    7030     33980       20.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        7780    7780     40484       19.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        8296    8296     45710       18.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        8135    8135     50658       16.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        6866    6866     55252       12.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        4326    4326     59146        7.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        2003    2003     62822        3.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       53039   53039    388930       13.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2979    2979     14516       20.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        5446    5446     26362       20.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        6673    6673     33980       19.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        6947    6947     40484       17.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        6876    6876     45710       15.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        5995    5995     50658       11.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        4014    4014     55252        7.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1808    1808     59146        3.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         569     569     62822        0.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       41307   41307    388930       10.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        2920    2920     14516       20.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        5337    5337     26362       20.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        6349    6349     33980       18.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        6154    6154     40484       15.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        5718    5718     45710       12.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        4414    4414     50658        8.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        2453    2453     55252        4.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75         876     876     59146        1.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         180     180     62822        0.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       34401   34401    388930        8.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   75099
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                      75099
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                75099



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1      50
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3866    3866     14516       26.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        7093    7093     26362       26.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        9136    9136     33980       26.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       10828   10828     40484       26.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       12190   12190     45710       26.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       13466   13466     50658       26.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       14560   14560     55252       26.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75       13418   13418     59146       22.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        9381    9381     62822       14.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       93938   93938    388930       24.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3862    3862     14516       26.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        7081    7081     26362       26.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        9113    9113     33980       26.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       10712   10712     40484       26.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       12016   12016     45710       26.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       13117   13117     50658       25.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       13731   13731     55252       24.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75       12126   12126     59146       20.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        8145    8145     62822       13.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       89903   89903    388930       23.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3779    3779     14516       26.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        6973    6973     26362       26.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        8747    8747     33980       25.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        9656    9656     40484       23.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       10316   10316     45710       22.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       10060   10060     50658       19.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        8339    8339     55252       15.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        5170    5170     59146        8.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        2326    2326     62822        3.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       65366   65366    388930       16.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3699    3699     14516       25.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        6824    6824     26362       25.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        8288    8288     33980       24.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        8562    8562     40484       21.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        8508    8508     45710       18.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        7281    7281     50658       14.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        4775    4775     55252        8.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        2092    2092     59146        3.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         620     620     62822        1.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       50649   50649    388930       13.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        3621    3621     14516       24.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        6686    6686     26362       25.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        7861    7861     33980       23.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        7548    7548     40484       18.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        7009    7009     45710       15.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        5304    5304     50658       10.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        2885    2885     55252        5.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1005    1005     59146        1.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         194     194     62822        0.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       42113   42113    388930       10.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   93940
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                      93940
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                93940



 ******************************************************************************
  STATISTICS OF SAVED DATA SET "XDS_ASCII.HKL" (DATA_RANGE=       1      60)
 FILE TYPE:         XDS_ASCII      MERGE=FALSE          FRIEDEL'S_LAW=FALSE
 ******************************************************************************

   REFLECTIONS OF TYPE H,0,0  0,K,0  0,0,L OR EXPECTED TO BE ABSENT (*)
   --------------------------------------------------------------------

   H    K    L  RESOLUTION  INTENSITY     SIGMA    INTENSITY/SIGMA  #OBSERVED

    0    0    2    78.798   0.1884E+01  0.7868E+00         2.40           2 
    0    0    3    52.532   0.3847E+02  0.4661E+01         8.25           1 
    0    0    5    31.519   0.4427E+02  0.6392E+01         6.93           1 
    0    0    6    26.266   0.1354E+01  0.1010E+01         1.34           1 
    0    0    7    22.514   0.1669E+01  0.1092E+01         1.53           1 
    0    0    8    19.700   0.4467E+03  0.9733E+01        45.90           1 
    0    0    9    17.511   0.3209E+01  0.1344E+01         2.39           1 
    0    0   10    15.760   0.5714E+01  0.1723E+01         3.32           1 
    0    0   11    14.327   0.1137E+02  0.1807E+01         6.30           1 
    0    0   12    13.133   0.1490E+03  0.4334E+01        34.38           1 
    0    0   13    12.123   0.4902E+01  0.2434E+01         2.01           1 
    0    0   14    11.257   0.7636E+01  0.2703E+01         2.83           1 
    0    0   17     9.270   0.6893E+01  0.3610E+01         1.91           1 
    0    0   18     8.755   0.2253E+00  0.2819E+01         0.08           1 
    0    0   19     8.295   0.1444E+02  0.3512E+01         4.11           1 
    0    0   21     7.505   0.3451E+01  0.3737E+01         0.92           1 
    0    0   22     7.163   0.6044E+01  0.3155E+01         1.92           1 
    0    0   23     6.852   0.3009E+01  0.3807E+01         0.79           1 
    0    0   25     6.304   0.1193E+02  0.3988E+01         2.99           1 
    0    0   26     6.061   0.1074E+02  0.3526E+01         3.05           1 
    0    0   27     5.837   0.1102E+02  0.4810E+01         2.29           1 
    0    0   29     5.434   0.1973E+01  0.4259E+01         0.46           1 
    0    0   30     5.253   0.8175E+01  0.4398E+01         1.86           1 
    0    0   31     5.084   0.8116E+01  0.5979E+01         1.36           1 
    0    0   32     4.925   0.2620E+04  0.5644E+02        46.43           1 
    0    0   33     4.776   0.1289E+02  0.5269E+01         2.45           1 
    0    0   34     4.635  -0.5925E+01  0.4923E+01        -1.20           1 
    0    0   35     4.503   0.8523E+01  0.5859E+01         1.45           1 
    0    0   36     4.378   0.9470E+03  0.2055E+02        46.08           1 
    0    0   37     4.259   0.4633E+01  0.5929E+01         0.78           1 
    0    0   38     4.147   0.1554E+02  0.6465E+01         2.40           1 
    0    0   39     4.041  -0.2530E+01  0.6460E+01        -0.39           1 
    0    0   40     3.940   0.1058E+05  0.2203E+03        48.01           1 
    0    0   41     3.844   0.1511E+01  0.7519E+01         0.20           1 
    0    0   42     3.752   0.8105E+01  0.8499E+01         0.95           1 
    0    0   43     3.665   0.1632E+02  0.8583E+01         1.90           1 
    0    0   44     3.582   0.2128E+04  0.4521E+02        47.08           1 
    0    0   45     3.502   0.9915E+01  0.6765E+01         1.47           1 
    0    0   46     3.426   0.1005E+02  0.7455E+01         1.35           1 
    0    0   47     3.353   0.2508E+01  0.7625E+01         0.33           1 
    0    0   48     3.283   0.1047E+05  0.2207E+03        47.46           1 
    0    0   49     3.216  -0.4977E+01  0.9296E+01        -0.54           1 
    0    0   50     3.152  -0.3501E+01  0.8495E+01        -0.41           1 
    0    0   51     3.090  -0.1182E+02  0.1021E+02        -1.16           1 
    0    0   52     3.031   0.8972E+04  0.1854E+03        48.40           1 
    0    0   53     2.974   0.2402E+02  0.9154E+01         2.62           1 
    0    0   54     2.918   0.8309E+01  0.7326E+01         1.13           1 
    0    0   55     2.865   0.5408E-02  0.8550E+01         0.00           1 
    0    0   56     2.814   0.3288E+04  0.6832E+02        48.13           1 
    0    0   57     2.765  -0.4412E+01  0.8586E+01        -0.51           1 
    0    0   58     2.717  -0.2749E+01  0.8378E+01        -0.33           1 
    0    0   59     2.671   0.2023E+01  0.7688E+01         0.26           1 
    0    0   60     2.627   0.2081E+04  0.4438E+02        46.90           1 
    0    0   61     2.584  -0.1021E+01  0.9532E+01        -0.11           1 
    0    0   62     2.542  -0.2745E+01  0.1038E+02        -0.26           1 
    0    0   63     2.502   0.1144E+02  0.9424E+01         1.21           1 
    0    0   64     2.462   0.2573E+04  0.5487E+02        46.89           1 
    0    0   65     2.425   0.6382E+00  0.1003E+02         0.06           1 
    0    0   66     2.388  -0.6922E+01  0.8730E+01        -0.79           1 
    1    0    0    51.593   0.7460E+00  0.1666E+01         0.45           2 
    3    0    0    17.198   0.8926E+01  0.3726E+01         2.40           2 
    4    0    0    12.898   0.1867E+03  0.7303E+01        25.56           2 
    5    0    0    10.319   0.9145E+00  0.6349E+01         0.14           2 
    6    0    0     8.599   0.1206E+03  0.7028E+01        17.16           2 
    7    0    0     7.370   0.1395E+01  0.7647E+01         0.18           2 
    8    0    0     6.449   0.4066E+04  0.6231E+02        65.25           2 
    9    0    0     5.733  -0.3075E+01  0.1029E+02        -0.30           2 
   10    0    0     5.159   0.1325E+05  0.2055E+03        64.45           2 
   11    0    0     4.690  -0.5078E+01  0.1407E+02        -0.36           2 
   12    0    0     4.299   0.1420E+05  0.2263E+03        62.77           2 
   13    0    0     3.969  -0.1917E+02  0.1830E+02        -1.05           2 
   14    0    0     3.685   0.1532E+05  0.2407E+03        63.63           2 
   15    0    0     3.440   0.2894E+02  0.1730E+02         1.67           2 
   16    0    0     3.225   0.8112E+03  0.3150E+02        25.75           2 
   17    0    0     3.035  -0.5179E+01  0.2702E+02        -0.19           2 
   18    0    0     2.866   0.5240E+03  0.2744E+02        19.10           2 
   19    0    0     2.715   0.1937E+02  0.1965E+02         0.99           2 
   20    0    0     2.580   0.1482E+03  0.3538E+02         4.19           1 
   21    0    0     2.457   0.9737E+00  0.2743E+02         0.04           1 
   22    0    0     2.345  -0.2036E+01  0.4144E+02        -0.05           1 
   23    0    0     2.243   0.5532E+01  0.3525E+02         0.16           1 
   24    0    0     2.150  -0.6056E+01  0.4672E+02        -0.13           1 
   25    0    0     2.064   0.5103E+02  0.4515E+02         1.13           1 
   26    0    0     1.984   0.1414E+03  0.4842E+02         2.92           1 
   27    0    0     1.911   0.4603E+02  0.4207E+02         1.09           1 

          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
 Rmrgd-F  = quality of amplitudes (F) of this data set
            For definition of R-meas and Rmrgd-F see 
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 S_norm   = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=TRUE
 S_ano    = mean value of Sigma(I) for acentric reflections in
            each resolution shell assuming FRIEDEL'S_LAW=FALSE
            Thus, anomalous scattering contributions to
            the intensities are indicated by S_norm/S_ano>1

       NOTE:      Friedel pairs are treated as different reflections.

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        4647    4647     14516       32.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        8478    8478     26362       32.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86       10920   10920     33980       32.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       12945   12945     40484       32.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       14604   14604     45710       31.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       16119   16119     50658       31.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       17434   17434     55252       31.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75       16038   16038     59146       27.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65       11214   11214     62822       17.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total      112399  112399    388930       28.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  0.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        4641    4641     14516       32.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        8463    8463     26362       32.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86       10892   10892     33980       32.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       12797   12797     40484       31.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       14379   14379     45710       31.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       15698   15698     50658       31.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87       16387   16387     55252       29.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75       14434   14434     59146       24.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        9683    9683     62822       15.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total      107374  107374    388930       27.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        4545    4545     14516       31.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        8320    8320     26362       31.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86       10430   10430     33980       30.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       11454   11454     40484       28.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       12252   12252     45710       26.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02       11855   11855     50658       23.4%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        9705    9705     55252       17.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        5902    5902     59146       10.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65        2606    2606     62822        4.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       77069   77069    388930       19.8%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  6.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        4449    4449     14516       30.6%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        8142    8142     26362       30.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        9865    9865     33980       29.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48       10124   10124     40484       25.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22       10003   10003     45710       21.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        8485    8485     50658       16.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        5444    5444     55252        9.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        2335    2335     59146        3.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         669     669     62822        1.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       59516   59516    388930       15.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00

 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >=  9.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  Rmrgd-F  S_norm/
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                     S_ano

     4.95        4351    4351     14516       30.0%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     3.50        7974    7974     26362       30.2%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.86        9341    9341     33980       27.5%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.48        8874    8874     40484       21.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.22        8197    8197     45710       17.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     2.02        6111    6111     50658       12.1%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.87        3236    3236     55252        5.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.75        1104    1104     59146        1.9%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
     1.65         204     204     62822        0.3%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00
    total       49392   49392    388930       12.7%     -99.9%    -99.9%        0  -99.00   -99.9%   -99.9%    0.00


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES  112401
 NUMBER OF REJECTED MISFITS                               0
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  0
 NUMBER OF ACCEPTED OBSERVATIONS                     112401
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS               112401

 NUMBER OF REFLECTIONS SAVED ON "XDS_ASCII.HKL"      112401
 (ACCEPTED OBSERVATIONS + REJECTED MISFITS + ABSENCES;
  MISFITS are marked by -1*SIGMA(IOBS) in "XDS_ASCII.HKL")



 ******************************************************************************
    WILSON STATISTICS OF DATA SET  "XDS_ASCII.HKL"
 ******************************************************************************

 Data is divided into resolution shells and a straight line 
 A - 2*B*SS is fitted to log<I>, where
   RES    = mean resolution (Angstrom) in shell
   SS     = mean of (sin(THETA)/LAMBDA)**2 in shell
   <I>    = mean reflection intensity in shell
   BO     = (A - log<I>)/(2*SS)
    #     = number of reflections in resolution shell

   WILSON LINE (using all data) : A=   8.435 B=  24.243 CORRELATION=  0.98
      #      RES      SS        <I>       log(<I>)       BO
     863     9.248   0.003  2.6204E+03       7.871      96.4
    1736     5.817   0.007  2.1094E+03       7.654      52.8
    2346     4.535   0.012  3.6584E+03       8.205       9.5
    2871     3.837   0.017  3.1597E+03       8.058      11.1
    3341     3.389   0.022  2.3242E+03       7.751      15.7
    3808     3.068   0.027  1.3583E+03       7.214      23.0
    4168     2.824   0.031  8.7044E+02       6.769      26.6
    4637     2.630   0.036  6.5829E+02       6.490      26.9
    5022     2.470   0.041  5.2886E+02       6.271      26.4
    5353     2.336   0.046  4.9738E+02       6.209      24.3
    5668     2.223   0.051  4.3982E+02       6.086      23.2
    6034     2.124   0.055  3.3957E+02       5.828      23.5
    6360     2.038   0.060  2.7315E+02       5.610      23.5
    6689     1.961   0.065  2.1137E+02       5.354      23.7
    6926     1.892   0.070  1.6237E+02       5.090      23.9
    6723     1.830   0.075  1.1005E+02       4.701      25.0
    6617     1.774   0.079  8.7301E+01       4.469      25.0
    5368     1.723   0.084  7.2734E+01       4.287      24.6
    4225     1.677   0.089  6.2961E+01       4.143      24.1


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF  CENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         3<I>**2     15<I>**3    105<I>**4 

       0   overall        0.000        0.000        0.000


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF ACENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         2<I>**2      6<I>**3     24<I>**4 

     863     9.248        1.299        2.023        3.441
    1736     5.817        1.126        1.304        1.449
    2346     4.535        1.005        0.963        0.879
    2871     3.837        1.058        1.228        1.576
    3341     3.389        1.042        1.184        1.514
    3808     3.068        1.020        1.066        1.127
    4168     2.824        1.123        1.402        1.879
    4637     2.630        1.064        1.162        1.263
    5022     2.470        1.053        1.190        1.381
    5353     2.336        1.069        1.229        1.454
    5668     2.223        2.114       40.274     1064.396
    6034     2.124        1.066        1.257        1.594
    6360     2.038        1.218        2.831       13.013
    6689     1.961        5.246      328.847    19319.108
    6926     1.892        2.954       66.302     1890.947
    6723     1.830        1.176        1.717        3.570
    6617     1.774        1.129        1.371        1.835
    5368     1.723        1.088        1.140        1.310
    4225     1.677        1.153        1.246        1.401
   88755   overall        1.625       33.647     1673.669

   ======= CUMULATIVE INTENSITY DISTRIBUTION =======
 DEFINITIONS:
   <I>    = mean reflection intensity
 Na(Z)exp = expected number of acentric reflections with I <= Z*<I>
 Na(Z)obs = observed number of acentric reflections with I <= Z*<I>
 Nc(Z)exp = expected number of  centric reflections with I <= Z*<I>
 Nc(Z)obs = observed number of  centric reflections with I <= Z*<I>



 Nc(Z)obs/Nc(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

       0   overall  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00


 Na(Z)obs/Na(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

     863     9.248  1.78  1.37  1.27  1.17  1.13  1.09  1.08  1.06  1.06  1.04
    1736     5.817  1.47  1.27  1.15  1.08  1.09  1.07  1.08  1.06  1.04  1.02
    2346     4.535  1.15  1.12  1.13  1.09  1.05  1.03  1.01  1.00  1.00  0.99
    2871     3.837  0.99  1.05  1.06  1.00  0.99  0.99  0.99  1.00  1.03  1.02
    3341     3.389  0.99  1.03  1.00  0.99  1.02  1.02  1.02  1.02  1.01  1.00
    3808     3.068  1.06  0.99  0.99  1.01  1.03  1.02  1.01  1.00  1.01  1.01
    4168     2.824  1.10  1.09  1.07  1.09  1.07  1.06  1.05  1.03  1.03  1.03
    4637     2.630  1.02  1.05  1.02  1.03  1.05  1.06  1.06  1.05  1.04  1.02
    5022     2.470  0.82  0.94  0.97  0.97  0.98  0.99  1.00  1.01  1.02  1.03
    5353     2.336  0.91  1.00  1.03  1.02  1.01  1.03  1.03  1.03  1.03  1.03
    5668     2.223  0.82  0.94  0.99  1.02  1.03  1.03  1.04  1.03  1.03  1.03
    6034     2.124  0.83  0.94  0.98  1.00  1.01  1.01  1.02  1.02  1.01  1.02
    6360     2.038  0.96  0.99  1.01  1.01  1.01  1.01  1.02  1.03  1.03  1.03
    6689     1.961  1.14  1.03  1.06  1.06  1.08  1.07  1.07  1.07  1.07  1.06
    6926     1.892  1.29  1.07  1.05  1.06  1.07  1.08  1.07  1.06  1.06  1.06
    6723     1.830  1.48  1.08  0.98  0.96  0.97  0.98  0.99  1.00  1.01  1.01
    6617     1.774  1.55  1.08  0.96  0.91  0.93  0.95  0.96  0.96  0.98  0.98
    5368     1.723  1.71  1.12  0.99  0.93  0.92  0.92  0.92  0.92  0.93  0.94
    4225     1.677  1.88  1.21  1.05  0.98  0.95  0.92  0.93  0.92  0.92  0.94
   88755   overall  1.18  1.05  1.02  1.01  1.01  1.01  1.01  1.01  1.02  1.02


 List of    135 reflections *NOT* obeying Wilson distribution (Z>8)

   h    k    l     RES      Z     Intensity    Sigma

   20   14  -31    1.95  235.98  0.4988E+05  0.1023E+04 "alien"
   23   -4  -41    1.92  128.57  0.2088E+05  0.4472E+03 "alien"
   19   -2  -39    2.25  109.59  0.4820E+05  0.1006E+04 "alien"
   19   -2  -58    1.92   78.91  0.1281E+05  0.4429E+03 "alien"
   16    9  -52    2.06   31.49  0.8600E+04  0.1822E+03 "alien"
   18   17  -32    1.92   30.98  0.5030E+04  0.1262E+03 "alien"
   25    0    3    2.06   25.92  0.7079E+04  0.1602E+03 "alien"
   12   19  -13    2.25   24.06  0.1058E+05  0.2252E+03 "alien"
   24   -5  -15    2.06   23.65  0.6461E+04  0.1538E+03 "alien"
   15    3   68    1.91   22.88  0.3715E+04  0.8360E+02 "alien"
    0   10   79    1.86   22.10  0.2432E+04  0.5978E+02 "alien"
   21    6   48    1.92   21.50  0.3491E+04  0.6195E+02 "alien"
   20   12  -41    1.92   21.39  0.3474E+04  0.8157E+02 "alien"
   21    4   50    1.92   17.58  0.2854E+04  0.6292E+02 "alien"
   17   -8   57    1.95   15.94  0.3370E+04  0.9082E+02 "alien"
   24   -6   29    1.95   14.87  0.3144E+04  0.9540E+02 "alien"
   10    0   79    1.86   14.72  0.2390E+04  0.6074E+02 "alien"
   25   -5  -27    1.91   14.29  0.2320E+04  0.8065E+02 "alien"
    8    0   72    2.07   14.22  0.3884E+04  0.1909E+03 "alien"
   25    6   25    1.91   14.09  0.2288E+04  0.4966E+02 "alien"
   19   18  -19    1.92   13.38  0.2173E+04  0.6717E+02 "alien"
   18   -8   36    2.25   13.31  0.5852E+04  0.1360E+03 "alien"
    9   -3   81    1.83   13.24  0.1458E+04  0.4149E+02 "alien"
   17    6  -61    1.92   13.11  0.2128E+04  0.5319E+02 "alien"
   13   25  -31    1.72   12.81  0.9317E+03  0.4785E+02 "alien"
    9    3   81    1.83   12.78  0.1407E+04  0.4723E+02 "alien"
   16   13   53    1.91   12.72  0.2065E+04  0.6217E+02 "alien"
   17    2  -64    1.91   12.72  0.2065E+04  0.5636E+02 "alien"
   25    7  -27    1.88   12.09  0.1964E+04  0.4986E+02 "alien"
   10   10   32    2.93   12.03  0.1047E+05  0.2401E+03 "alien"
   12  -12   73    1.76   11.94  0.1043E+04  0.5220E+02 "alien"
   24   12  -15    1.89   11.92  0.1936E+04  0.4353E+02 "alien"
    3    9   81    1.83   11.92  0.1311E+04  0.3928E+02 "alien"
   10   10   -7    3.60   11.91  0.2767E+05  0.6200E+03 "alien"
   10   10  -32    2.93   11.87  0.1033E+05  0.2315E+03 "alien"
   10   10    7    3.60   11.34  0.2636E+05  0.5910E+03 "alien"
   12   12   73    1.76   11.28  0.9845E+03  0.4283E+02 "alien"
    6    0  -34    4.08   11.21  0.3541E+05  0.7338E+03 "alien"
   16    0   55    2.14   11.03  0.3747E+04  0.6867E+02 "alien"
    9    2   79    1.88   10.99  0.1784E+04  0.5825E+02 "alien"
    5   -1    0   10.12   10.90  0.2857E+05  0.6754E+03 "alien"
    3   -9   81    1.83   10.90  0.1199E+04  0.2985E+02 "alien"
   18    0   75    1.69   10.86  0.6839E+03  0.3756E+02 "alien"
   17    5   62    1.91   10.57  0.1716E+04  0.4673E+02 "alien"
    0    8   78    1.93   10.56  0.2231E+04  0.5619E+02 "alien"
    6    2   84    1.83   10.51  0.1157E+04  0.3731E+02 "alien"
   16    0  -55    2.14   10.43  0.3542E+04  0.8437E+02 "alien"
    3    3    2   12.01   10.28  0.2693E+05  0.6221E+03 "alien"
    0    8   73    2.05   10.24  0.2798E+04  0.6417E+02 "alien"
   16   13  -53    1.91   10.24  0.1663E+04  0.5237E+02 "alien"
   13   16  -53    1.91   10.18  0.1653E+04  0.5131E+02 "alien"
    9   -9   62    2.15   10.12  0.3436E+04  0.8760E+02 "alien"
   11   -4   80    1.80   10.07  0.8793E+03  0.3334E+02 "alien"
   13   16   53    1.91   10.01  0.1625E+04  0.5211E+02 "alien"
    5    1    0   10.12   10.01  0.2622E+05  0.4376E+03 "alien"
    6    0   34    4.08    9.99  0.3158E+05  0.4891E+03 "alien"
    9    9   62    2.15    9.95  0.3378E+04  0.8894E+02 "alien"
    0    6   83    1.85    9.86  0.1085E+04  0.3088E+02 "alien"
    7    0   56    2.63    9.81  0.6459E+04  0.9816E+02 "alien"
   19   16    8    2.06    9.78  0.2671E+04  0.7847E+02 "alien"
   19    4   38    2.24    9.78  0.4300E+04  0.8224E+02 "alien"
   16  -12   65    1.77    9.76  0.8517E+03  0.5671E+02 "alien"
    9   16   60    1.92    9.73  0.1579E+04  0.5838E+02 "alien"
   16  -13   53    1.92    9.72  0.1578E+04  0.6752E+02 "alien"
    2    6   84    1.83    9.65  0.1062E+04  0.3467E+02 "alien"
    9    9    0    4.05    9.65  0.3049E+05  0.7234E+03 "alien"
   11   -9   70    1.91    9.63  0.1563E+04  0.5434E+02 "alien"
   18    0   43    2.26    9.59  0.4216E+04  0.7821E+02 "alien"
    7    0   66    2.27    9.58  0.4212E+04  0.6745E+02 "alien"
    9   14   48    2.25    9.57  0.4211E+04  0.9807E+02 "alien"
   15   11  -59    1.92    9.55  0.1551E+04  0.4734E+02 "alien"
   27   13   -7    1.72    9.51  0.6919E+03  0.5122E+02 "alien"
    8    0   73    2.05    9.49  0.2591E+04  0.4692E+02 "alien"
    9   -3  -81    1.83    9.42  0.1036E+04  0.3116E+02 "alien"
   10   -5   24    3.78    9.41  0.2973E+05  0.6447E+03 "alien"
   14  -13   54    1.98    9.38  0.1982E+04  0.7970E+02 "alien"
   11    4   80    1.80    9.32  0.8135E+03  0.4844E+02 "alien"
   14   14  -20    2.47    9.30  0.4917E+04  0.1208E+03 "alien"
    4    3   -2   10.22    9.18  0.2407E+05  0.4107E+03 "alien"
    4   11   80    1.80    9.18  0.8014E+03  0.3468E+02 "alien"
    0    7   66    2.27    9.11  0.4007E+04  0.9032E+02 "alien"
   21    2   27    2.26    9.10  0.4003E+04  0.6945E+02 "alien"
   14   14   20    2.47    9.08  0.4800E+04  0.1231E+03 "alien"
    2   -6  -84    1.83    9.05  0.9964E+03  0.2854E+02 "alien"
   20   -1  -53    1.95    9.05  0.1912E+04  0.6502E+02 "alien"
   14   -4   44    2.52    8.98  0.4747E+04  0.1145E+03 "alien"
   18    0  -43    2.26    8.97  0.3947E+04  0.1016E+03 "alien"
    4    3    2   10.22    8.93  0.2339E+05  0.4343E+03 "alien"
   22   19  -23    1.72    8.90  0.6470E+03  0.4386E+02 "alien"
    0    7   85    1.80    8.88  0.7755E+03  0.2653E+02 "alien"
   14    4  -44    2.52    8.86  0.4684E+04  0.1024E+03 "alien"
    1  -10  -78    1.88    8.85  0.1437E+04  0.4023E+02 "alien"
   18    4  -49    2.11    8.84  0.3003E+04  0.8033E+02 "alien"
    6   -6   77    1.94    8.84  0.1869E+04  0.4353E+02 "alien"
    4  -11   80    1.80    8.83  0.7712E+03  0.2860E+02 "alien"
    0    7  -56    2.63    8.83  0.5814E+04  0.1219E+03 "alien"
    7   12   83    1.69    8.74  0.5503E+03  0.3535E+02 "alien"
   10   13  -49    2.25    8.71  0.3829E+04  0.8516E+02 "alien"
    7   -8   76    1.91    8.70  0.1412E+04  0.3999E+02 "alien"
    5    4   84    1.83    8.66  0.9532E+03  0.3079E+02 "alien"
   16    0  -47    2.32    8.62  0.4286E+04  0.1026E+03 "alien"
   11    0  -36    3.20    8.55  0.1162E+05  0.2532E+03 "alien"
    2    0   68    2.31    8.52  0.4236E+04  0.8919E+02 "alien"
   11   -1  -43    2.88    8.50  0.7401E+04  0.1583E+03 "alien"
   18   -4  -49    2.11    8.47  0.2877E+04  0.8987E+02 "alien"
    1    1   66    2.38    8.47  0.4213E+04  0.9124E+02 "alien"
    7    0  -56    2.63    8.43  0.5553E+04  0.1162E+03 "alien"
    4    5   84    1.83    8.40  0.9242E+03  0.3415E+02 "alien"
    9    9  -62    2.15    8.40  0.2851E+04  0.6440E+02 "alien"
   22  -13   26    1.92    8.39  0.1362E+04  0.5242E+02 "alien"
   15    0    2    3.44    8.36  0.1942E+05  0.3071E+03 "alien"
   17    0   73    1.76    8.31  0.7251E+03  0.3595E+02 "alien"
   13   17  -59    1.79    8.30  0.7250E+03  0.3492E+02 "alien"
   14    4   44    2.52    8.30  0.4391E+04  0.7516E+02 "alien"
    6    6   77    1.94    8.30  0.1755E+04  0.4683E+02 "alien"
   15    0   -2    3.44    8.30  0.1929E+05  0.2947E+03 "alien"
   10    1   78    1.88    8.28  0.1345E+04  0.3219E+02 "alien"
   18    4   51    2.07    8.28  0.2262E+04  0.4597E+02 "alien"
   23    5  -25    2.07    8.27  0.2260E+04  0.5645E+02 "alien"
   10   -1   78    1.88    8.26  0.1342E+04  0.4109E+02 "alien"
   11   -2   54    2.47    8.26  0.4367E+04  0.1045E+03 "alien"
   15   -9   54    2.08    8.23  0.2248E+04  0.1020E+03 "alien"
   11   -4  -80    1.80    8.23  0.7181E+03  0.3149E+02 "alien"
    1   -1  -66    2.38    8.22  0.4090E+04  0.8642E+02 "alien"
    6   13   82    1.69    8.19  0.5155E+03  0.3637E+02 "alien"
   16    0   77    1.73    8.19  0.5956E+03  0.3434E+02 "alien"
   17   13  -59    1.79    8.15  0.7117E+03  0.3621E+02 "alien"
   12   -4   65    2.08    8.14  0.2764E+04  0.6814E+02 "alien"
   16    0   47    2.32    8.13  0.4046E+04  0.7019E+02 "alien"
   10   -7   77    1.84    8.07  0.8878E+03  0.3696E+02 "alien"
   17    0  -73    1.76    8.06  0.7041E+03  0.3256E+02 "alien"
   15    0   74    1.81    8.05  0.8854E+03  0.2939E+02 "alien"
   11    2  -54    2.47    8.03  0.4245E+04  0.9257E+02 "alien"
    0    8   74    2.02    8.03  0.2192E+04  0.5200E+02 "alien"
   12   16   55    1.92    8.02  0.1303E+04  0.4623E+02 "alien"


 List of    135 reflections *NOT* obeying Wilson distribution (sorted by resolution)
 Ice rings could occur at (Angstrom):
 3.897,3.669,3.441, 2.671,2.249,2.072, 1.948,1.918,1.883,1.721

   h    k    l     RES      Z     Intensity    Sigma

    7   12   83    1.69    8.74  0.5503E+03  0.3535E+02
   18    0   75    1.69   10.86  0.6839E+03  0.3756E+02
    6   13   82    1.69    8.19  0.5155E+03  0.3637E+02
   27   13   -7    1.72    9.51  0.6919E+03  0.5122E+02
   22   19  -23    1.72    8.90  0.6470E+03  0.4386E+02
   13   25  -31    1.72   12.81  0.9317E+03  0.4785E+02
   16    0   77    1.73    8.19  0.5956E+03  0.3434E+02
   12   12   73    1.76   11.28  0.9845E+03  0.4283E+02
   17    0   73    1.76    8.31  0.7251E+03  0.3595E+02
   17    0  -73    1.76    8.06  0.7041E+03  0.3256E+02
   12  -12   73    1.76   11.94  0.1043E+04  0.5220E+02
   16  -12   65    1.77    9.76  0.8517E+03  0.5671E+02
   17   13  -59    1.79    8.15  0.7117E+03  0.3621E+02
   13   17  -59    1.79    8.30  0.7250E+03  0.3492E+02
    0    7   85    1.80    8.88  0.7755E+03  0.2653E+02
    4   11   80    1.80    9.18  0.8014E+03  0.3468E+02
   11    4   80    1.80    9.32  0.8135E+03  0.4844E+02
   11   -4  -80    1.80    8.23  0.7181E+03  0.3149E+02
   11   -4   80    1.80   10.07  0.8793E+03  0.3334E+02
    4  -11   80    1.80    8.83  0.7712E+03  0.2860E+02
   15    0   74    1.81    8.05  0.8854E+03  0.2939E+02
    4    5   84    1.83    8.40  0.9242E+03  0.3415E+02
    5    4   84    1.83    8.66  0.9532E+03  0.3079E+02
    2    6   84    1.83    9.65  0.1062E+04  0.3467E+02
    2   -6  -84    1.83    9.05  0.9964E+03  0.2854E+02
    6    2   84    1.83   10.51  0.1157E+04  0.3731E+02
    3    9   81    1.83   11.92  0.1311E+04  0.3928E+02
    9    3   81    1.83   12.78  0.1407E+04  0.4723E+02
    9   -3  -81    1.83    9.42  0.1036E+04  0.3116E+02
    9   -3   81    1.83   13.24  0.1458E+04  0.4149E+02
    3   -9   81    1.83   10.90  0.1199E+04  0.2985E+02
   10   -7   77    1.84    8.07  0.8878E+03  0.3696E+02
    0    6   83    1.85    9.86  0.1085E+04  0.3088E+02
    0   10   79    1.86   22.10  0.2432E+04  0.5978E+02
   10    0   79    1.86   14.72  0.2390E+04  0.6074E+02
    9    2   79    1.88   10.99  0.1784E+04  0.5825E+02
    1  -10  -78    1.88    8.85  0.1437E+04  0.4023E+02
   10    1   78    1.88    8.28  0.1345E+04  0.3219E+02
   10   -1   78    1.88    8.26  0.1342E+04  0.4109E+02
   25    7  -27    1.88   12.09  0.1964E+04  0.4986E+02
   24   12  -15    1.89   11.92  0.1936E+04  0.4353E+02
   17    2  -64    1.91   12.72  0.2065E+04  0.5636E+02
    7   -8   76    1.91    8.70  0.1412E+04  0.3999E+02
   15    3   68    1.91   22.88  0.3715E+04  0.8360E+02
   25    6   25    1.91   14.09  0.2288E+04  0.4966E+02
   25   -5  -27    1.91   14.29  0.2320E+04  0.8065E+02
   13   16   53    1.91   10.01  0.1625E+04  0.5211E+02
   16   13   53    1.91   12.72  0.2065E+04  0.6217E+02
   17    5   62    1.91   10.57  0.1716E+04  0.4673E+02
   11   -9   70    1.91    9.63  0.1563E+04  0.5434E+02
   16   13  -53    1.91   10.24  0.1663E+04  0.5237E+02
   13   16  -53    1.91   10.18  0.1653E+04  0.5131E+02
   12   16   55    1.92    8.02  0.1303E+04  0.4623E+02
   21    4   50    1.92   17.58  0.2854E+04  0.6292E+02
   19   -2  -58    1.92   78.91  0.1281E+05  0.4429E+03
   23   -4  -41    1.92  128.57  0.2088E+05  0.4472E+03
   16  -13   53    1.92    9.72  0.1578E+04  0.6752E+02
   21    6   48    1.92   21.50  0.3491E+04  0.6195E+02
   19   18  -19    1.92   13.38  0.2173E+04  0.6717E+02
   20   12  -41    1.92   21.39  0.3474E+04  0.8157E+02
   22  -13   26    1.92    8.39  0.1362E+04  0.5242E+02
    9   16   60    1.92    9.73  0.1579E+04  0.5838E+02
   17    6  -61    1.92   13.11  0.2128E+04  0.5319E+02
   18   17  -32    1.92   30.98  0.5030E+04  0.1262E+03
   15   11  -59    1.92    9.55  0.1551E+04  0.4734E+02
    0    8   78    1.93   10.56  0.2231E+04  0.5619E+02
    6    6   77    1.94    8.30  0.1755E+04  0.4683E+02
    6   -6   77    1.94    8.84  0.1869E+04  0.4353E+02
   20   -1  -53    1.95    9.05  0.1912E+04  0.6502E+02
   24   -6   29    1.95   14.87  0.3144E+04  0.9540E+02
   17   -8   57    1.95   15.94  0.3370E+04  0.9082E+02
   20   14  -31    1.95  235.98  0.4988E+05  0.1023E+04
   14  -13   54    1.98    9.38  0.1982E+04  0.7970E+02
    0    8   74    2.02    8.03  0.2192E+04  0.5200E+02
    0    8   73    2.05   10.24  0.2798E+04  0.6417E+02
    8    0   73    2.05    9.49  0.2591E+04  0.4692E+02
   16    9  -52    2.06   31.49  0.8600E+04  0.1822E+03
   25    0    3    2.06   25.92  0.7079E+04  0.1602E+03
   19   16    8    2.06    9.78  0.2671E+04  0.7847E+02
   24   -5  -15    2.06   23.65  0.6461E+04  0.1538E+03
   23    5  -25    2.07    8.27  0.2260E+04  0.5645E+02
    8    0   72    2.07   14.22  0.3884E+04  0.1909E+03
   18    4   51    2.07    8.28  0.2262E+04  0.4597E+02
   15   -9   54    2.08    8.23  0.2248E+04  0.1020E+03
   12   -4   65    2.08    8.14  0.2764E+04  0.6814E+02
   18    4  -49    2.11    8.84  0.3003E+04  0.8033E+02
   18   -4  -49    2.11    8.47  0.2877E+04  0.8987E+02
   16    0   55    2.14   11.03  0.3747E+04  0.6867E+02
   16    0  -55    2.14   10.43  0.3542E+04  0.8437E+02
    9    9   62    2.15    9.95  0.3378E+04  0.8894E+02
    9    9  -62    2.15    8.40  0.2851E+04  0.6440E+02
    9   -9   62    2.15   10.12  0.3436E+04  0.8760E+02
   19    4   38    2.24    9.78  0.4300E+04  0.8224E+02
   19   -2  -39    2.25  109.59  0.4820E+05  0.1006E+04
   18   -8   36    2.25   13.31  0.5852E+04  0.1360E+03
   10   13  -49    2.25    8.71  0.3829E+04  0.8516E+02
    9   14   48    2.25    9.57  0.4211E+04  0.9807E+02
   12   19  -13    2.25   24.06  0.1058E+05  0.2252E+03
   21    2   27    2.26    9.10  0.4003E+04  0.6945E+02
   18    0   43    2.26    9.59  0.4216E+04  0.7821E+02
   18    0  -43    2.26    8.97  0.3947E+04  0.1016E+03
    0    7   66    2.27    9.11  0.4007E+04  0.9032E+02
    7    0   66    2.27    9.58  0.4212E+04  0.6745E+02
    2    0   68    2.31    8.52  0.4236E+04  0.8919E+02
   16    0   47    2.32    8.13  0.4046E+04  0.7019E+02
   16    0  -47    2.32    8.62  0.4286E+04  0.1026E+03
    1    1   66    2.38    8.47  0.4213E+04  0.9124E+02
    1   -1  -66    2.38    8.22  0.4090E+04  0.8642E+02
   11    2  -54    2.47    8.03  0.4245E+04  0.9257E+02
   11   -2   54    2.47    8.26  0.4367E+04  0.1045E+03
   14   14   20    2.47    9.08  0.4800E+04  0.1231E+03
   14   14  -20    2.47    9.30  0.4917E+04  0.1208E+03
   14    4   44    2.52    8.30  0.4391E+04  0.7516E+02
   14    4  -44    2.52    8.86  0.4684E+04  0.1024E+03
   14   -4   44    2.52    8.98  0.4747E+04  0.1145E+03
    7    0   56    2.63    9.81  0.6459E+04  0.9816E+02
    7    0  -56    2.63    8.43  0.5553E+04  0.1162E+03
    0    7  -56    2.63    8.83  0.5814E+04  0.1219E+03
   11   -1  -43    2.88    8.50  0.7401E+04  0.1583E+03
   10   10   32    2.93   12.03  0.1047E+05  0.2401E+03
   10   10  -32    2.93   11.87  0.1033E+05  0.2315E+03
   11    0  -36    3.20    8.55  0.1162E+05  0.2532E+03
   15    0    2    3.44    8.36  0.1942E+05  0.3071E+03
   15    0   -2    3.44    8.30  0.1929E+05  0.2947E+03
   10   10    7    3.60   11.34  0.2636E+05  0.5910E+03
   10   10   -7    3.60   11.91  0.2767E+05  0.6200E+03
   10   -5   24    3.78    9.41  0.2973E+05  0.6447E+03
    9    9    0    4.05    9.65  0.3049E+05  0.7234E+03
    6    0   34    4.08    9.99  0.3158E+05  0.4891E+03
    6    0  -34    4.08   11.21  0.3541E+05  0.7338E+03
    5    1    0   10.12   10.01  0.2622E+05  0.4376E+03
    5   -1    0   10.12   10.90  0.2857E+05  0.6754E+03
    4    3    2   10.22    8.93  0.2339E+05  0.4343E+03
    4    3   -2   10.22    9.18  0.2407E+05  0.4107E+03
    3    3    2   12.01   10.28  0.2693E+05  0.6221E+03

 cpu time used                 28.2 sec
 elapsed wall-clock time       28.7 sec

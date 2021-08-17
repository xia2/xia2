from xia2.Wrappers.XDS.XDSIntegrateHelpers import parse_integrate_lp


def test_parse_integrate_lp(tmpdir):
    integrate_lp = tmpdir.join("INTEGRATE.LP")
    with integrate_lp.open("w") as fh:
        fh.write(integrate_lp_example_1)
    per_image_stats = parse_integrate_lp(integrate_lp.strpath)
    assert list(per_image_stats) == list(range(1, 22))
    assert per_image_stats[1] == {
        "distance": 213.68,
        "all": 2486,
        "scale": 0.01,
        "overloads": 0,
        "rmsd_phi": 0.2,
        "rejected": 1,
        "beam": [2217.03, 2306.1],
        "fraction_weak": 0.9605792437650845,
        "rmsd_pixel": 0.5,
        "strong": 98,
        "unit_cell": (57.687, 57.687, 149.879, 90.0, 90.0, 90.0),
        "mosaic": 0.042,
    }

    integrate_lp = tmpdir.join("INTEGRATE.LP")
    with integrate_lp.open("w") as fh:
        fh.write(integrate_lp_big_n_refl)
    per_image_stats = parse_integrate_lp(integrate_lp.strpath)
    assert list(per_image_stats) == list(range(2601, 2611))
    print(per_image_stats[2601])
    assert per_image_stats[2601] == {
        "all": 1092650,
        "scale": 0.975,
        "overloads": 0,
        "rmsd_phi": 15.4,
        "rejected": 8,
        "fraction_weak": 0.9997409966594976,
        "rmsd_pixel": 1.86,
        "strong": 283,
    }


integrate_lp_example_1 = """\
 OSCILLATION_RANGE=  0.250000 DEGREES

 ******************************************************************************
                     PROCESSING OF IMAGES        1 ...      21
 ******************************************************************************

 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ   SIGMAB   SIGMAR
     1   0  0.010 16768425    0   2486      98     1  0.01970  0.05000
     2   0  0.010 16767966    0   2482     113     1  0.02078  0.05000
     3   0  0.010 16768952    0   2457      92     1  0.01999  0.05000
     4   0  0.010 16768674    0   2507      95     1  0.01898  0.05000
     5   0  0.010 16768968    0   2531      90     0  0.02025  0.05000
     6   0  0.010 16768173    0   2500     104     0  0.01927  0.05000
     7   0  0.010 16768177    0   2528     102     0  0.01925  0.05000
     8   0  0.010 16768711    0   2471      91     0  0.01968  0.05000
     9   0  0.010 16769564    0   2439      77     0  0.02068  0.05000
    10   0  0.010 16768394    0   2464     100     0  0.01907  0.05000
    11   0  0.010 16769104    0   2501      85     0  0.01894  0.05000
    12   0  0.010 16769057    0   2442      86     0  0.01787  0.05000
    13   0  0.010 16768710    0   2542      89     0  0.01865  0.05000
    14   0  0.010 16768293    0   2498      99     0  0.01954  0.05000
    15   0  0.010 16768756    0   2485      91     0  0.01893  0.05000
    16   0  0.010 16768205    0   2478     102     0  0.02038  0.05000
    17   0  0.010 16768731    0   2494      98     0  0.01906  0.05000
    18   0  0.010 16769096    0   2519      89     0  0.01905  0.05000
    19   0  0.010 16769308    0   2470      84     1  0.01861  0.05000
    20   0  0.010 16770288    0   2532      73     0  0.01845  0.05000
    21   0  0.010 16768056    0   2521     110     0  0.01916  0.05000

  1433 OUT OF   1433 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:   POSITION ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.50
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.05
 SPACE GROUP NUMBER     75
 UNIT CELL PARAMETERS     57.687    57.687   149.879  90.000  90.000  90.000
 REC. CELL PARAMETERS   0.017335  0.017335  0.006672  90.000  90.000  90.000
 COORDINATES OF UNIT CELL A-AXIS    17.374   -51.023    20.558
 COORDINATES OF UNIT CELL B-AXIS   -51.259    -7.193    25.468
 COORDINATES OF UNIT CELL C-AXIS   -51.864   -67.388  -123.421
 CRYSTAL ROTATION OFF FROM INITIAL ORIENTATION    -0.004     0.014     0.003
 shown as x,y,z components of rotation axis X angle (degrees)
 CRYSTAL MOSAICITY (DEGREES)     0.042
 LAB COORDINATES OF ROTATION AXIS  0.999943 -0.006986 -0.008051
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)   0.008789  0.010077  1.020035
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    2217.03   2306.10
 DETECTOR ORIGIN (PIXELS) AT                     2192.48   2277.95
 CRYSTAL TO DETECTOR DISTANCE (mm)       213.68
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000


 STANDARD DEVIATIONS OF BEAM DIVERGENCE AND REFLECTING RANGE OBTAINED
 FROM    1433 REFLECTION PROFILES AT 9 POSITIONS ON THE DETECTOR SURFACE.
 POSITION NUMBER        1      2      3      4      5      6      7      8      9
 X-COORDINATE (pixel) 2074.0 3619.9 3167.1 2074.0  980.9  528.1  980.9 2073.9 3167.0
 Y-COORDINATE (pixel) 2181.0 2181.0 3330.5 3806.6 3330.5 2181.1 1031.6  555.4 1031.4
 NUMBER                  467    137    165    155    104     72     82    111    132
 SIGMAB (degree)       0.016  0.017  0.017  0.017  0.017  0.017  0.016  0.016  0.017
 SIGMAR (degree)       0.038  0.037  0.037  0.038  0.037  0.036  0.037  0.038  0.038
"""

integrate_lp_big_n_refl = """\
 OSCILLATION_RANGE=  0.050000 DEGREES
  ******************************************************************************
                     PROCESSING OF IMAGES     2601 ...    2610
 ******************************************************************************
 IMAGE IER  SCALE     NBKG NOVL NEWALD NSTRONG  NREJ   SIGMAB   SIGMAR
  2601   0  0.975 16680318    01092650     283     8  0.01281  0.40765
  2602   0  0.969 16680543    01092588     268     6  0.01308  0.46286
  2603   0  0.973 16680424    01092451     274     5  0.01419  0.44668
  2604   0  0.979 16679844    01092457     282     7  0.01460  0.43985
  2605   0  0.972 16679268    01092620     294     4  0.01438  0.43988
  2606   0  0.979 16678476    01092578     301     8  0.01346  0.44049
  2607   0  0.975 16679456    01092483     285     8  0.01428  0.43287
  2608   0  0.980 16679874    01092729     283     6  0.01392  0.48593
  2609   0  0.985 16679847    01092438     280     5  0.01349  0.46816
  2610   0  0.978 16679911    01092542     276     5  0.01438  0.47244

  6989 OUT OF   9308 REFLECTIONS ACCEPTED FOR REFINEMENT
 REFINED PARAMETERS:   POSITION BEAM ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     1.86
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.77
"""

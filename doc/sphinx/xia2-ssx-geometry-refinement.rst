+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Overcoming problems with the detector geometry for SSX data
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

There are three different ways to run :samp:`xia2.ssx` with regards to detector geometry refinement.

* If a reference geometry (a DIALS :samp:`.expt` file) is provided as input to :samp:`xia2.ssx` with the option :samp:`reference_geometry=`, then no geometry refinement is performed and this reference geometry is used instead of the geometry from the image files.
* If a starting geometry (a DIALS :samp:`.expt` file) is provided as input to :samp:`xia2.ssx` with the option :samp:`starting_geometry=`, then this geometry is used instead of the geometry from the image files and a round of geometry refinement is run.
* If neither a reference geometry or starting geometry are given, the geometry is read from the image files and a round of geometry refinement is run.

The automated geometry refinement in :samp:`xia2.ssx` is designed to improve an existing
detector geometry that is reasonably accurate. Spotfinding and indexing are performed in
batches until at least 250 crystals are successfully indexed (this can be changed with the option
:samp:`geometry_refinement.n_crystals=`). Alternatively, an image range can be specified using e.g.
:samp:`geometry_refinement.images_to_use=1001:2000`. As a reminder, to just run the geometry refinement part
of the :samp:`xia2.ssx` pipeline, use the option :samp:`steps=None`, i.e. no processing steps.

In cases where the initial geometry is not reasonably well known, or the hit/indexing rate is low,
refining an accurate initial geometry is not straightforward, and can require experimenting
with program input and performing several cycles of geometry refinement i.e. using the :samp:`starting_geometry` option with 
:samp:`steps=None`, and using the resultant refined geometry as the :samp:`starting_geometry` for another run of :samp:`xia2.ssx`
and repeating until convergence.

Symptoms of a bad initial geometry include

* very low indexing success (i.e. low % of hits indexed)
* indexing success followed by low integration success rate
* failure at the geometry refinement step due to 'Error: No reflections available for refinement'

The sections below provide some guidance on how to discover the correct experimental geometry using :samp:`xia2.ssx`/DIALS.
Publications describing diffraction geometry refinement in DIALS are linked below:

* `Diffraction-geometry refinement in the DIALS framework <https://onlinelibrary.wiley.com/iucr/doi/10.1107/S2059798316002187>`_
* `Improving signal strength in serial crystallography with DIALS geometry refinement <https://scripts.iucr.org/cgi-bin/paper?lp5037>`_


-----------------------------------------
Setting the detector distance/beam centre
-----------------------------------------

A common issue is that the detector distance or beam centre is incorrectly set or incorrectly interpreted from the 
header of data files, or not known with sufficient accuracy. 
To set the detector distance, a custom phil file can be specified for the import step in :samp:`xia2.ssx`::

     xia2.ssx dials_import.phil=example1.phil image=example.h5 space_group=P1 unit_cell=79.1,79.1,38.2,90,90,90

Where :samp:`example1.phil` is a phil file containing phil options for :samp:`dials.import` e.g.::

    geometry.detector.distance=115
    geometry.detector.fast_slow_beam_centre=1200,1245

or::

    geometry.detector.panel.origin=-80,90,-115

(phil files are plain text files with the extension .phil, so can be created with a text editor or command line tools).
The :samp:`fast_slow_beam_centre` is the coordinate of the beam centre on the image (in pixels), and is what
is displayed as the beam centre in the :samp:`dials.image_viewer`. The distance is the translation along the z-axis
(the beam axis) from sample to detector *in millimeters* (typically to the centre of the detector).

Alternatively, the detector origin can be specified. The detector origin is the xyz coordinate (in millimeters) that
describes the location of the corner of the detector in the lab frame (the lab frame has its origin at the sample position).
Note that the z-coorindate is a negative value, which may also be the case for the x or y coordinate.
It is important to note that the z-coorindate of the origin is only the same as the detector distance if the detector face is
fully perpendicular to the z-axis, which will typically not be the case after geometry refinement, which refines the direction of the
:samp:`fast_axis` and :samp:`slow_axis` of the detector.

The detector origin, distance, fast and slow axis can be displayed by running :samp:`dials.show import/imported.expt`.
Note that to specify multiple panel options such as origin and fast and slow axes, one must use the following form of phil
specification to enable them to be all assigned to the same panel::

    geometry.detector.panel{
      origin=-80,90,-115
      fast_axis=0.9999,0.0001,0
      slow_axis=-0.0001,0.9999,0
    }

This can become cumbersome and error-prone for many-panel detectors. In these cases, it may be preferable to set only
the distance and beam centre, and do multiple cycles of geometry refinement using the :samp:`starting_geometry` option
as described above. Remember, it is also possible to manually edit :samp:`.expt` files in a text editor, as they are simply
json format files.

---------------------------------
Relaxing restraints in refinement
---------------------------------
    
Sometimes the geometry can be close enough to allow some indexing success, however the spot predictions are too far from
the observed spots such that the default filtering in :samp:`dials.refine` does not leave sufficient reflections for
geometry refinement, resulting in the :samp:`xia2.ssx` error message :samp:`Error: No reflections available for refinement`.
The indexing RMSDs can be seen towards the end of the :samp:`geometry_refinement/dials.ssx_index.log`, while the
:samp:`geometry_refinement/dials.refine.log` shows the outlier rejection is removing most or all reflections::

    Detecting centroid outliers using the SauterPoon algorithm
    150 reflections have been flagged as outliers
    0 reflections remain in the manager

Therefore it may be necessary to temporarily relax the outlier condition, to help with discovering the correct geometry, as shown
below. Once the underlying issue has been addressed and a good geometry has been obtained, it should be possible to
repeat a cycle of geometry refinement with the default outlier condition.

To see the program parameters used, we can inpsect the top of the :samp:`dials.refine.log`,
which shows which parameters are modified from the defaults in :samp:`dials.refine` ::

    $ head -25 dials.refine.log
    The following parameters have been modified:
    input.experiments = indexed.expt
    input.reflections = indexed.refl
    refinement {
        parameterisation {
            auto_reduction {
                action = fail *fix remove
            }
            beam {
                fix = *all in_spindle_plane out_spindle_plane wavelength
            }
            detector {
                fix_list = "Tau1"
            }
        }
        refinery {
            engine = SimpleLBFGS LBFGScurvs GaussNewton LevMar *SparseLevMar
        }
        reflections {
            outlier {
                algorithm = null auto mcd tukey *sauter_poon
            }
        }
    }

To change the outlier rejection, we can repeat the refinement with :samp:`dials.refine` and manually
change the outlier algorithm to null, keeping the other options the same::

    $ dials.refine indexed.expt indexed.refl \
      refinement.parameterisation.auto_reduction.action=fix \
      refinement.parameterisation.beam.fix=all \
      refinement.parameterisation.detector.fix_list=Tau1 \
      refinement.refinery.engine=SparseLevMar \ 
      refinement.reflections.outlier.algorithm=null

The alternative way would be to rerun the whole :samp:`xia2.ssx` pipeline, giving a geometry refinement phil file::

    xia2.ssx geometry_refinement.phil=example2.phil [..same options as previously..]

where :samp:`example2.phil` contains::

    refinement.reflections.outlier.algorithm=null

(note that :samp:`xia2.ssx` will add the rest of the non-default phil options for :samp:`dials.refine`).

In the dataset that motivated this example, the underlying issue was the fact that the detector had suffered
a slight rotation about the beam axis, compared to the metadata in the header of the image file.
By default, detector rotation about its plane normal is fixed in stills refinement with the option
:samp:`refinement.parameterisation.detector.fix_list=Tau1` (Tau1 is the parameter describing the rotation
of the detector about its plane normal). To allow this parameter to refine,
the solution was run :samp:`xia2.ssx` with a geometry refinement phil containing::

    refinement.parameterisation.detector.fix_list=None
    refinement.reflections.outlier.algorithm=null

This allowed enough reflections to be used by :samp:`dials.refine` to start to refine the geometry, allowing
rotations of the detector. After the first cycle of refinement, the refined origin, fast axis and slow axis
were used as input parameters for :samp:`dials.import` in a second run of :samp:`xia2.ssx`, as described in
the preceeding section. In this run, the RMSDs in indexing we significantly lower and more crystals were
successfully indexed, allowing further refinement and improvement of the detector geometry.

------------------------------
Refining multi-panel detectors
------------------------------

When refining the detector position in DIALS, the orientation and position of all physical panels that
constitute the detector are refined as a single entity, by default. This approach is suitable for well
calibrated modern detectors (e.g. Dectris photon-counting detectors), and within DIALS the detector
is modelled as a single panel with dead regions between the physical panels. However, other detectors,
such as multi-panel CCD detectors, or the CSPAD detector, are parameterised as a heirarchy of groupings
of physical panels. This then allows the possibility of refining relative shifts and rotations of the
physical panel groups with respect to each other. For multi-panel detectors, the RMSDs per panel are reported
to the :samp:`xia2.ssx.log`::

    --------------------- Joint refinement ---------------------

    Refinement steps:
    +--------+--------+----------+----------+-----------------+
    |   Step |   Nref |   RMSD_X |   RMSD_Y |   RMSD_DeltaPsi |
    |        |        |     (mm) |     (mm) |           (deg) |
    |--------+--------+----------+----------+-----------------|
    |      0 |  24372 | 0.10005  | 0.12819  |         0.21934 |
    |      1 |  24372 | 0.070669 | 0.080024 |         0.21677 |
    |      2 |  24372 | 0.063907 | 0.070151 |         0.21954 |
    |      3 |  24372 | 0.056994 | 0.062588 |         0.21902 |
    |      4 |  24372 | 0.051901 | 0.057296 |         0.20879 |
    |      5 |  24372 | 0.04756  | 0.05244  |         0.18595 |
    |      6 |  24372 | 0.043361 | 0.048249 |         0.15792 |
    |      7 |  24372 | 0.039968 | 0.045247 |         0.13055 |
    |      8 |  24372 | 0.03769  | 0.043169 |         0.11034 |
    |      9 |  24372 | 0.036764 | 0.042274 |         0.10335 |
    |     10 |  24372 | 0.036579 | 0.042079 |         0.1025  |
    |     11 |  24372 | 0.036547 | 0.042045 |         0.10247 |
    |     12 |  24372 | 0.03654  | 0.04204  |         0.10247 |
    |     13 |  24372 | 0.036539 | 0.04204  |         0.10247 |
    +--------+--------+----------+----------+-----------------+
    RMSD no longer decreasing

    Detector 1 RMSDs by panel:
    +---------+--------+----------+----------+-----------------+
    |   Panel |   Nref |   RMSD_X |   RMSD_Y |   RMSD_DeltaPsi |
    |      id |        |     (px) |     (px) |           (deg) |
    |---------+--------+----------+----------+-----------------|
    |       0 |    345 |  0.95269 |  1.0951  |        0.063433 |
    |       1 |   5969 |  0.6194  |  0.79187 |        0.088303 |
    |       2 |   5595 |  0.82114 |  0.78986 |        0.10815  |
    |       3 |     70 |  2.0579  |  1.0123  |        0.15923  |
    |       4 |    317 |  1.3802  |  1.5027  |        0.091092 |
    |       5 |   5680 |  0.74765 |  0.95258 |        0.11538  |
    |       6 |   6331 |  0.57757 |  0.68147 |        0.095794 |
    |       7 |     65 |  2.6382  |  3.2829  |        0.26076  |
    +---------+--------+----------+----------+-----------------+

Therefore for multi-panel data, if the spot residuals differ significantly from panel to panel, as viewed
in the :samp:`dials.image_viewer` or as reported in the :samp:`dials.refine.log / xia2.ssx.log`, it may be
necessary to allow multi-panel refinement to arrive at a more accurate model of the detector.
To enable relative refinement of the panels, the following :samp:`dials.refine` phil option must be changed::
    
    refinement.parameterisation.detector.hierarchy_level=1

The default :samp:`hierarchy_level` is 0, i.e. all panels are refined together, while a values of 1 allows
relative refinement at the first level of hierarchy. Values higher than one may be needed depending on the
detector parameterisation, e.g. CSPAD detectors have a hierarchy_level of 3.
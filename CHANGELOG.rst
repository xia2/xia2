xia2 0.7.32 (DIALS 3.0.0) (2020-05-27)
======================================

Features
--------

- Improve handling of diamond anvil cell data.  When calling xia2 with `high_pressure.correction=True`:
  - 'Dynamic shadowing' is enabled, to mask out the regions shadowed by the cell body.
  - The minimum observation counts for profile modelling are relaxed — the defaults are unrealistic in the case of a small data set from a small-molecule material in a diamond anvil cell.  In such cases, there are far fewer spots than the DIALS profile modelling expects, based on the norm in MX.  This had been a frequent cause of frustration when processing small-molecule data with xia2.
  - X-ray absorption in the diamond anvils is automatically corrected for using `dials.anvil_correction`. (#396)
- New command-line interface for xia2.to_shelxcde utility to support SAD/MAD datasets. (#433)
- - Include xtriage analysis in xia2.multiplex output
  - xia2.multiplex now exports json file including xtriage results
  - Include merging stats in multiplex json file (#443)
- Add the option ``multi_sweep_refinement`` to the DIALS pipelines.
  This performs the same indexing as ``multi_sweep_indexing`` and additionally refines all sweeps together, rather than refining each sweep individually.
  When refining the sweeps together, the unit cell parameters of each sweep are restrained to the mean unit cell during the scan-static refinement.
  This is achieved by setting the ``dials.refine`` option ``refinement.parameterisation.crystal.unit_cell.restraints.tie_to_group.sigmas=0.01,0.01,0.01,0.01,0.01,0.01``, but other values and ``tie_to_group``/``tie_to_target`` schemes of ``dials.refine`` may be invoked by passing suitable parameters.
  See the various xia2 configuration parameters under ``dials.refine.restraints``, which are identical to the settings one can pass to ``dials.refine`` via its own parameter set ``refinement.parameterisation.crystal.unit_cell.restraints``.
  As with the normal behaviour of xia2, the restraints do not apply to the scan-varying refinement step.

  Since this is likely to be most useful for small-molecule chemical crystallography, the ``multi_sweep_refinement`` behaviour is made the default when ``small_molecule=True``. (#456)


Bugfixes
--------

- Fixed printing of unit cells which are fixed by symmetry (89.9999999 -> 90.0) (#444)
- Changed outlier rejection in 3dii pipeline - no longer throw out outliers by default, and if outlier rejection requested only perform this after assessing resolution limits. (#445)
- Fix issue where missing images caused error: "can't convert negative value to unsigned int" (#463)


Deprecations and Removals
-------------------------

- xia2 0.7 no longer supports Python 2 (#450)
- Removed long-deprecated command line options -3dii / -dials and the like as well as the dials-full pipeline. (#452)
- Remove xia2.chef: this is deprecated and replaced by dials.damage_analysis (#460)


Misc
----

- #449


xia2 0.6.446 (DIALS 2.2.0) (2020-03-15)
=======================================

Features
--------

- xia2 now has coloured output by default.
  You can disable this by setting the environment variable NO_COLOR. (#267)
- The DIALS pipeline now generates .sca output files again (#384)
- Prescale data before dials.symmetry when in multi_sweep_indexing mode

  This mirrors the behaviour of the CCP4ScalerA by prescaling the data
  with KB scaling to ensure that all experiments are on the same scale
  before running dials.symmetry. This should lead to more reliable
  results from the symmetry analysis in multi_sweep_indexing mode. (#395)
- Switch the default plugin for reading HDF5 files with XDS to DURIN (#400)
- The error output file xia2.error has been renamed xia2-error.txt (#407)


Bugfixes
--------

- Export DANO when running cctbx French & Wilson procedure (#399)
- If .nxs and _master.h5 files reference the same underlying data files on disk, 
  do not process both, only process _master files. Fixes longstanding annoyance. (#408)
- Made image reading in xia2.overload more general, means screen19 now works with 
  Eiger detectors (#412)
- Fix bug for space_group= option in combination with the dials pipeline where
  output mtz files would be in the Laue group, rather than the space group. (#420)
- Remove the check that HDF5 data files are in place for master files, since this
  implicitly assumes that the data are written following DECTRIS manner. (#401)

xia2 0.6.362 (DIALS 2.1.0) (2019-12-16)
=======================================

Features
--------

- Perform systematic absence analysis in multiplex

  - Run dials.symmetry in systematic-absences-only mode after scaling to determine
    full space group in xia2.multiplex
  - Set laue_group= to skip Laue group determination by dials.cosym
  - Set space_group= to skip both Laue group determination by dials.cosym and
    systematic absences analysis by dials.symmetry (#355)
- Use cctbx-based French/Wilson procedure in place of ctruncate.
  Set truncate=ctruncate to use ctruncate instead. (#377)
- Generate integrated.mtz files for dials pipeline, saved in Datafiles (#385)


Bugfixes
--------

- Don't raise error if anomalous probability plot fails (#357)
- Ensure that integration results are copied to DataFiles. In some circumstances,
  when re-indexing/integrating the data, they were inadvertently missed (#379) (#379)
- Fix for running dials.symmetry in multi_sweep_indexing mode (#390)


Deprecations and Removals
-------------------------

- Retire mosflm/2d pipeline and related features (#222)
- -journal.txt output files are no longer created.
  Any output goes into the debug logfile instead. (#267)
- Retire command dev.xia2.pea_in_box (#348)
- Retire xdssum indexer (#351)
- Retire labelit/labelitii indexer and related features (#367)


Misc
----

- #342, #370


xia2 0.6.256 (DIALS 2.0.0) (2019-10-23)
=======================================

Features
--------

- Change the default pipeline (dials) to use DIALS for scaling instead of AIMLESS

  Scaling with AIMLESS is still available by running xia2 with ``pipeline=dials-aimless`` (#301)
- Reduce the number of calls to dials.export for performance improvement.

  The integrated.mtz (unscaled) no longer appears in the Logfiles but can
  be generated from the corresponding .refl and .expt files (#329)
- Reduce the total sweep range for searching for the correct beam centre.

  After 180 degrees no new information is provided so restrict the range if
  the total number of reflections is > 20,000 (only 10,000 randomly selected
  refections are used for this calculation anyway). (#249)

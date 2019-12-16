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

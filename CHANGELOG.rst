xia2 3.3.2 (2021-02-01)
=======================

Bugfixes
--------

- Fix unicode logging errors on Windows (`#558 <https://github.com/xia2/xia2/issues/558>`_)


xia2 3.3.0 (2021-01-04)
=======================

From this release, xia2 version numbers `now follow <https://github.com/xia2/xia2/pull/528#issuecomment-716577121>`_ the DIALS release model.

Features
--------

- xia2 has been turned into a python package. This change includes major
  refactoring work underneath the hood. (`#528 <https://github.com/xia2/xia2/issues/528>`_)
- Updates to ``xia2.mmcif`` output to conform to the latest pdb dictionaries (v5).
  ``output.mmcif.pdb_version=`` option added (choices of ``v5``, ``v5_next``).
  The default option ``v5_next`` includes output of unmerged reflection data. (`#537 <https://github.com/xia2/xia2/issues/537>`_)
- ``xia2.html``: Add ``<dF/s(dF)>``-by-resolution plot if running xia with ``anomalous=True`` (`#551 <https://github.com/xia2/xia2/issues/551>`_)


Bugfixes
--------

- ``xia2.multiplex``: pass ``dials.cosym`` parameter ``lattice_symmetry_max_delta=`` to ``dials.cosym``. (`#544 <https://github.com/xia2/xia2/issues/544>`_)
- ``xia2.multiplex``: fix occasional error generating stereographic projections. (`#546 <https://github.com/xia2/xia2/issues/546>`_)


Misc
----

- `#533 <https://github.com/xia2/xia2/issues/533>`_, `#535 <https://github.com/xia2/xia2/issues/535>`_,
  `#538 <https://github.com/xia2/xia2/issues/538>`_, `#540 <https://github.com/xia2/xia2/issues/540>`_,
  `#541 <https://github.com/xia2/xia2/issues/541>`_, `#545 <https://github.com/xia2/xia2/issues/545>`_,
  `#547 <https://github.com/xia2/xia2/issues/547>`_, `#548 <https://github.com/xia2/xia2/issues/548>`_,
  `#552 <https://github.com/xia2/xia2/issues/552>`_.


xia2 (DIALS 3.2.1) (2020-11-09)
===============================

Features
--------

- ``xia2.multiplex``: Allow the user to override the default ``dials.scale``
  parameter ``reflection_selection.method=``, to allow working around cases
  where default can fail (`#529 <https://github.com/xia2/xia2/issues/529>`_)
- ``xia2.merging_statistics``: Improved error handling  (`#531 <https://github.com/xia2/xia2/issues/531>`_)

Misc
----

- `#530 <https://github.com/xia2/xia2/issues/530>`_


xia2 0.7.101 (DIALS 3.2.0) (2020-10-27)
=======================================

Features
--------

- Add a radar plot to `xia2.multiplex` html report for comparison of merging
  statistics between clusters. (`#406 <https://github.com/xia2/xia2/issues/406>`_)
- Full matrix minimisation when using DIALS scaling is now Auto by default.
  This will use full matrix for 4 sweeps or fewer, meaning that large data sets
  now process much faster. (`#428 <https://github.com/xia2/xia2/issues/428>`_)


Bugfixes
--------
- Temporary files are no longer left around during the dials scaling process (`#497 <https://github.com/xia2/xia2/issues/497>`_)


Misc
----

- `#514 <https://github.com/xia2/xia2/issues/514>`_, `#523 <https://github.com/xia2/xia2/issues/523>`_


xia2 (DIALS 3.1.4) (2020-10-12)
========================

Bugfixes
--------

- ``xia2.compare_merging_stats``: Fix occasionally incorrect axis ylimits (`#517 <https://github.com/xia2/xia2/issues/517>`_)
- ``xia2.multiplex``: Fix corner case where reflections are present but not
  used in refinement, leading to an error when selecting reflections with
  ``reflections.select_on_experiment_identifiers()`` (`#524 <https://github.com/xia2/xia2/issues/524>`_)
- ``xia2.multiplex``: Fix error if one or more experiment has an image range
  that doesn't overlap with the requested dose range. Instead, remove this
  experiment from further analysis. (`#525 <https://github.com/xia2/xia2/issues/525>`_)
- ``xia2.multiplex``: Gracefully handle failure of resolution estimation (`#526 <https://github.com/xia2/xia2/issues/526>`_)
- Explicitly fail testing when the XDS licence has expired


xia2 (DIALS 3.1.1) (2020-09-01)
========================

Bugfixes
--------

- ``xia2.multiplex``: fix for dose parameter when scan doesn't start at 1 (`#518 <https://github.com/xia2/xia2/issues/518>`_)
- ``xia2.html``: Fix crash on python 3.8 (`#516 <https://github.com/xia2/xia2/issues/516>`_)


xia2 0.7.85 (DIALS 3.1.0) (2020-08-17)
======================================

Features
--------

- xia2 now support Python 3.8 (`#510 <https://github.com/xia2/xia2/issues/510>`_)
- Re-estimate resolution limit after deltacchalf filtering. Previously the
  resolution limit of the filtered dataset would always be the same as the
  unfiltered dataset. (`#466 <https://github.com/xia2/xia2/issues/466>`_)
- Add support for dose_decay model for dials.scale (`#467 <https://github.com/xia2/xia2/issues/467>`_)
- Report more useful error message if given an Eiger data file rather than a
  master file, including suggestions of possible master files in the same
  directory (`#509 <https://github.com/xia2/xia2/issues/509>`_)
- Speed up ``xia2.compare_merging_stats`` (`#502 <https://github.com/xia2/xia2/issues/502>`_)


Bugfixes
--------
- Work around changes to filenames output from dials.split_experiments (`#478 <https://github.com/xia2/xia2/issues/478>`_)


Deprecations and Removals
-------------------------
- No longer create the ``xia2-files.txt`` file. The output now goes to ``xia2-debug.txt`` (`#468 <https://github.com/xia2/xia2/issues/468>`_)


xia2 (DIALS 3.0.4) (2020-07-20)
===============================

Bugfixes
--------

- ``ispyb_xml``: Fix error reading PHIL files (`#484 <https://github.com/xia2/xia2/issues/484>`_)
- When using ``read_image_headers=False``, ignore missing images outside of the
  ``start:end`` range specified on the command line (`#491 <https://github.com/xia2/xia2/issues/491>`_)
- Improve treatment of reference instrument models when using ``reference_geometry=``.

  Previously, a separate 'experiment list' (``.expt``) file was required
  for each instrument model, but if any of the files contained multiple instrument
  models (e.g. they had been created from multiple-sweep rotation data), xia2
  could sometimes fail with a confusing message "no sweeps found".

  Now, one can pass any number of ``.expt`` files with ``reference_geometry=``
  arguments and each file may contain any number of instrument models. xia2
  will sort out any duplicate models for you. (`#485 <https://github.com/xia2/xia2/issues/485>`_)


xia2 (DIALS 3.0.3) (2020-07-06)
===============================

Bugfixes
--------

- Fix data from NSLS II with multiple triggers and one image per trigger (`#475 <https://github.com/xia2/xia2/issues/475>`_)
- Gracefully handle xtriage errors when generating xia2 report. (`#477 <https://github.com/xia2/xia2/issues/477>`_)
- xia2.compare_merging_stats: Plot the bin centres rather than bin d_min
  values. This previously could lead to misleading apparent differences between
  data sets with significantly different resolution limits. (`#480 <https://github.com/xia2/xia2/issues/480>`_)
- Increase XDS COLSPOT minimum_pixels_per_spot from 1 to 2. The previous value may
  have led to problems when spotfinding on images with many hot/warm pixels. (`#472 <https://github.com/xia2/xia2/issues/472>`_)

xia2 (DIALS 3.0.1) (2020-06-11)
===============================

Bugfixes
--------

- Fix missing anomalous info in hkl data converted for shelx
- Compatibility with DIALS project_name changes


xia2 0.7.32 (DIALS 3.0.0) (2020-05-27)
======================================

Features
--------

- Improve handling of diamond anvil cell data.  When calling xia2 with `high_pressure.correction=True`:
  - 'Dynamic shadowing' is enabled, to mask out the regions shadowed by the cell body.
  - The minimum observation counts for profile modelling are relaxed — the defaults are unrealistic in the case of a small data set from a small-molecule material in a diamond anvil cell.  In such cases, there are far fewer spots than the DIALS profile modelling expects, based on the norm in MX.  This had been a frequent cause of frustration when processing small-molecule data with xia2.
  - X-ray absorption in the diamond anvils is automatically corrected for using `dials.anvil_correction`. (`#396 <https://github.com/xia2/xia2/issues/396>`_)
- New command-line interface for xia2.to_shelxcde utility to support SAD/MAD datasets. (`#433 <https://github.com/xia2/xia2/issues/433>`_)
- - Include xtriage analysis in xia2.multiplex output
  - xia2.multiplex now exports json file including xtriage results
  - Include merging stats in multiplex json file (`#443 <https://github.com/xia2/xia2/issues/443>`_)
- Add the option ``multi_sweep_refinement`` to the DIALS pipelines.
  This performs the same indexing as ``multi_sweep_indexing`` and additionally refines all sweeps together, rather than refining each sweep individually.
  When refining the sweeps together, the unit cell parameters of each sweep are restrained to the mean unit cell during the scan-static refinement.
  This is achieved by setting the ``dials.refine`` option ``refinement.parameterisation.crystal.unit_cell.restraints.tie_to_group.sigmas=0.01,0.01,0.01,0.01,0.01,0.01``, but other values and ``tie_to_group``/``tie_to_target`` schemes of ``dials.refine`` may be invoked by passing suitable parameters.
  See the various xia2 configuration parameters under ``dials.refine.restraints``, which are identical to the settings one can pass to ``dials.refine`` via its own parameter set ``refinement.parameterisation.crystal.unit_cell.restraints``.
  As with the normal behaviour of xia2, the restraints do not apply to the scan-varying refinement step.

  Since this is likely to be most useful for small-molecule chemical crystallography, the ``multi_sweep_refinement`` behaviour is made the default when ``small_molecule=True``. (`#456 <https://github.com/xia2/xia2/issues/456>`_)


Bugfixes
--------

- Fixed printing of unit cells which are fixed by symmetry (89.9999999 -> 90.0) (`#444 <https://github.com/xia2/xia2/issues/444>`_)
- Changed outlier rejection in 3dii pipeline - no longer throw out outliers by default, and if outlier rejection requested only perform this after assessing resolution limits. (`#445 <https://github.com/xia2/xia2/issues/445>`_)
- Fix issue where missing images caused error: "can't convert negative value to unsigned int" (`#463 <https://github.com/xia2/xia2/issues/463>`_)


Deprecations and Removals
-------------------------

- xia2 0.7 no longer supports Python 2 (`#450 <https://github.com/xia2/xia2/issues/450>`_)
- Removed long-deprecated command line options -3dii / -dials and the like as well as the dials-full pipeline. (`#452 <https://github.com/xia2/xia2/issues/452>`_)
- Remove xia2.chef: this is deprecated and replaced by dials.damage_analysis (`#460 <https://github.com/xia2/xia2/issues/460>`_)


Misc
----

- `#449 <https://github.com/xia2/xia2/issues/449>`_


xia2 0.6.446 (DIALS 2.2.0) (2020-03-15)
=======================================

Features
--------

- xia2 now has coloured output by default.
  You can disable this by setting the environment variable NO_COLOR. (`#267 <https://github.com/xia2/xia2/issues/267>`_)
- The DIALS pipeline now generates .sca output files again (`#384 <https://github.com/xia2/xia2/issues/384>`_)
- Prescale data before dials.symmetry when in multi_sweep_indexing mode

  This mirrors the behaviour of the CCP4ScalerA by prescaling the data
  with KB scaling to ensure that all experiments are on the same scale
  before running dials.symmetry. This should lead to more reliable
  results from the symmetry analysis in multi_sweep_indexing mode. (`#395 <https://github.com/xia2/xia2/issues/395>`_)
- Switch the default plugin for reading HDF5 files with XDS to DURIN (`#400 <https://github.com/xia2/xia2/issues/400>`_)
- The error output file xia2.error has been renamed xia2-error.txt (`#407 <https://github.com/xia2/xia2/issues/407>`_)


Bugfixes
--------

- Export DANO when running cctbx French & Wilson procedure (`#399 <https://github.com/xia2/xia2/issues/399>`_)
- If .nxs and _master.h5 files reference the same underlying data files on disk, 
  do not process both, only process _master files. Fixes longstanding annoyance. (`#408 <https://github.com/xia2/xia2/issues/408>`_)
- Made image reading in xia2.overload more general, means screen19 now works with 
  Eiger detectors (`#412 <https://github.com/xia2/xia2/issues/412>`_)
- Fix bug for space_group= option in combination with the dials pipeline where
  output mtz files would be in the Laue group, rather than the space group. (`#420 <https://github.com/xia2/xia2/issues/420>`_)
- Remove the check that HDF5 data files are in place for master files, since this
  implicitly assumes that the data are written following DECTRIS manner. (`#401 <https://github.com/xia2/xia2/issues/401>`_)

xia2 0.6.362 (DIALS 2.1.0) (2019-12-16)
=======================================

Features
--------

- Perform systematic absence analysis in multiplex

  - Run dials.symmetry in systematic-absences-only mode after scaling to determine
    full space group in xia2.multiplex
  - Set laue_group= to skip Laue group determination by dials.cosym
  - Set space_group= to skip both Laue group determination by dials.cosym and
    systematic absences analysis by dials.symmetry (`#355 <https://github.com/xia2/xia2/issues/355>`_)
- Use cctbx-based French/Wilson procedure in place of ctruncate.
  Set truncate=ctruncate to use ctruncate instead. (`#377 <https://github.com/xia2/xia2/issues/377>`_)
- Generate integrated.mtz files for dials pipeline, saved in Datafiles (`#385 <https://github.com/xia2/xia2/issues/385>`_)


Bugfixes
--------

- Don't raise error if anomalous probability plot fails (`#357 <https://github.com/xia2/xia2/issues/357>`_)
- Ensure that integration results are copied to DataFiles. In some circumstances,
  when re-indexing/integrating the data, they were inadvertently missed (`#379 <https://github.com/xia2/xia2/issues/379>`_) (`#379 <https://github.com/xia2/xia2/issues/379>`_)
- Fix for running dials.symmetry in multi_sweep_indexing mode (`#390 <https://github.com/xia2/xia2/issues/390>`_)


Deprecations and Removals
-------------------------

- Retire mosflm/2d pipeline and related features (`#222 <https://github.com/xia2/xia2/issues/222>`_)
- -journal.txt output files are no longer created.
  Any output goes into the debug logfile instead. (`#267 <https://github.com/xia2/xia2/issues/267>`_)
- Retire command dev.xia2.pea_in_box (`#348 <https://github.com/xia2/xia2/issues/348>`_)
- Retire xdssum indexer (`#351 <https://github.com/xia2/xia2/issues/351>`_)
- Retire labelit/labelitii indexer and related features (`#367 <https://github.com/xia2/xia2/issues/367>`_)


Misc
----

- `#342 <https://github.com/xia2/xia2/issues/342>`_, `#370 <https://github.com/xia2/xia2/issues/370>`_


xia2 0.6.256 (DIALS 2.0.0) (2019-10-23)
=======================================

Features
--------

- Change the default pipeline (dials) to use DIALS for scaling instead of AIMLESS

  Scaling with AIMLESS is still available by running xia2 with ``pipeline=dials-aimless`` (`#301 <https://github.com/xia2/xia2/issues/301>`_)
- Reduce the number of calls to dials.export for performance improvement.

  The integrated.mtz (unscaled) no longer appears in the Logfiles but can
  be generated from the corresponding .refl and .expt files (`#329 <https://github.com/xia2/xia2/issues/329>`_)
- Reduce the total sweep range for searching for the correct beam centre.

  After 180 degrees no new information is provided so restrict the range if
  the total number of reflections is > 20,000 (only 10,000 randomly selected
  refections are used for this calculation anyway). (`#249 <https://github.com/xia2/xia2/issues/249>`_)

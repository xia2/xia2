xia2 3.20.1 (2024-08-19)
========================

Bugfixes
--------

- ``xia2.ssx_reduce``: Make sure space group naming correct after cosym batch reindexing (`#798 <https://github.com/xia2/xia2/issues/798>`_)


xia2 3.20.0 (2024-06-19)
========================

Features
--------

- ``xia2.ssx_reduce``: Optimise and apply an error model correction in scaling. (`#792 <https://github.com/xia2/xia2/issues/792>`_)


Bugfixes
--------

- ``xia2.multiplex``: Reset batches after filtering steps to prevent inconsistencies and duplications. (`#789 <https://github.com/xia2/xia2/issues/789>`_)
- ``xia2.ssx_reduce``: Improve indexing ambiguity resolution with a reference by direct call to ``dials.reindex`` methods. (`#794 <https://github.com/xia2/xia2/issues/794>`_)


Misc
----

- `#790 <https://github.com/xia2/xia2/issues/790>`_, `#795 <https://github.com/xia2/xia2/issues/795>`_


xia2 3.19.0 (2024-04-17)
========================

Bugfixes
--------

- ``xia2.multiplex``: Avoid space group analysis if given reference file. (`#770 <https://github.com/xia2/xia2/issues/770>`_)
- ``xia2.ssx``: Allow use of ``stills.indexer=sequences`` in ssx_index routine. (`#779 <https://github.com/xia2/xia2/issues/779>`_)
- ``xia2.multiplex``: Allow use of ``relative_length_tolerance=`` and ``absolute_angle_tolerance=`` (used by cosym) in multiplex. (`#786 <https://github.com/xia2/xia2/issues/786>`_)


Misc
----

- `#769 <https://github.com/xia2/xia2/issues/769>`_, `#772 <https://github.com/xia2/xia2/issues/772>`_, `#773 <https://github.com/xia2/xia2/issues/773>`_, `#776 <https://github.com/xia2/xia2/issues/776>`_, `#780 <https://github.com/xia2/xia2/issues/780>`_, `#785 <https://github.com/xia2/xia2/issues/785>`_


xia2 3.17.0 (2023-11-03)
========================

Features
--------

- ``xia2.ssx``: Enable slicing a subset of images/templates using ``<filename>:start:end`` syntax. (`#740 <https://github.com/xia2/xia2/issues/740>`_)
- ``xia2.ssx_reduce``: Improved workflow for resolving indexing ambiguity. (`#761 <https://github.com/xia2/xia2/issues/761>`_)
- ``xia2.ssx``: Add ``starting_geometry=`` option, to set an initial geometry for further geometry refinement. (`#763 <https://github.com/xia2/xia2/issues/763>`_)
- ``xia2.cluster_analysis``: Add ``run_cluster_identification=`` option to toggle cluster identification analysis. (`#767 <https://github.com/xia2/xia2/issues/767>`_)


Bugfixes
--------

- ``xia2.multiplex``: Automatically extend r_free flags for clusters and filtered datasets. (`#747 <https://github.com/xia2/xia2/issues/747>`_)
- ``xia2.ssx_reduce``: Improve data selection for indexing ambiguity resolution. (`#760 <https://github.com/xia2/xia2/issues/760>`_)
- ``xia2.cluster_analysis``: Fixed bug where interesting clusters were not identified, due to inconsistency in file paths. (`#764 <https://github.com/xia2/xia2/issues/764>`_)
- ``xia2.multiplex``: Fix duplicate-batch-offsets crash for multi-lattice data. (`#765 <https://github.com/xia2/xia2/issues/765>`_)
- ``xia2.multiplex``: Exit cleanly when supplied with still-shot data. (`#766 <https://github.com/xia2/xia2/issues/766>`_)
- ``xia2.ssx_reduce``: Fix test for potential accidental indexing ambiguities for non-MX space groups. (`#768 <https://github.com/xia2/xia2/issues/768>`_)


Xia2 3.17 (2023-11-03)
======================

Features
--------

- ``xia2.ssx``: Enable slicing a subset of images/templates using file:start:end syntax (`#740 <https://github.com/xia2/xia2/issues/740>`_)
- ``xia2.ssx_reduce``: Improved indexing ambiguity resolution workflow (`#761 <https://github.com/xia2/xia2/issues/761>`_)
- ``xia2.ssx``: Add starting_geometry= option, which is used as an initial geometry with further geometry refinement run. (`#763 <https://github.com/xia2/xia2/issues/763>`_)
- ``xia2.cluster_analysis``: Add run_cluster_identification option to toggle on/off cluster identification analysis (`#767 <https://github.com/xia2/xia2/issues/767>`_)


Bugfixes
--------

- ``xia2.multiplex``: Automatically extend r_free flags for clusters and filtered datasets. (`#747 <https://github.com/xia2/xia2/issues/747>`_)
- Improve data selection for indexing ambiguity resolution in ssx_reduce (`#760 <https://github.com/xia2/xia2/issues/760>`_)
- ``xia2.cluster_analysis``: Fixed bug where interesting clusters were not identified due to inconsistency in file paths (`#764 <https://github.com/xia2/xia2/issues/764>`_)
- ``xia2.multiplex``: Fix duplicate-batch-offsets crash for multi-lattice data (`#765 <https://github.com/xia2/xia2/issues/765>`_)
- ``xia2.multiplex``: Exit cleanly when supplied with still-shot data (`#766 <https://github.com/xia2/xia2/issues/766>`_)
- ``xia2.ssx_reduce``: Fix test for potential accidental indexing ambiguities for non-MX space groups (`#768 <https://github.com/xia2/xia2/issues/768>`_)


xia2 3.16.0 (2023-08-14)
========================

Features
--------

- ``xia2.cluster_analysis``: The cluster selection algorithm now handles edge cases more robustly. (`#744 <https://github.com/xia2/xia2/issues/744>`_)
- ``xia2.multiplex``: Added option ``reference=``, to use a reference pdb for consistent indexing. (`#748 <https://github.com/xia2/xia2/issues/748>`_)
- ``xia2.multiplex``: Add support for multi-wavelength processing. (`#755 <https://github.com/xia2/xia2/issues/755>`_)


Misc
----

- `#745 <https://github.com/xia2/xia2/issues/745>`_, `#752 <https://github.com/xia2/xia2/issues/752>`_, `#753 <https://github.com/xia2/xia2/issues/753>`_, `#754 <https://github.com/xia2/xia2/issues/754>`_, `#756 <https://github.com/xia2/xia2/issues/756>`_, `#757 <https://github.com/xia2/xia2/issues/757>`_


xia2 3.15.0 (2023-06-12)
========================

Features
--------

- ``xia2.cluster_analysis``: The clustering algorithm from ``xia2.multiplex`` is now available as a separated module, applicable to any merged data from dials (rotation or stills). (`#733 <https://github.com/xia2/xia2/issues/733>`_)
- ``xia2.ssx``: Report hit and indexing rates during processing. (`#735 <https://github.com/xia2/xia2/issues/735>`_)
- ``xia2.ssx_reduce``: Allow setting of the partiality threshold (default now 0.25). (`#743 <https://github.com/xia2/xia2/issues/743>`_)


Bugfixes
--------

- ``xia2.ssx``: Include solvent contribution when generating reference intensities from a model. Adds k_sol and b_sol parameters. (`#737 <https://github.com/xia2/xia2/issues/737>`_)
- ``xia2.ssx``: Fix error in progress reporting when no hits found, or when no images indexed in a batch. (`#739 <https://github.com/xia2/xia2/issues/739>`_)


Misc
----

- `#736 <https://github.com/xia2/xia2/issues/736>`_, `#742 <https://github.com/xia2/xia2/issues/742>`_


xia2 3.14.0 (2023-04-12)
========================

Features
--------

- ``xia2.ssx``: Enable arbitrary grouping of data for merging by specifying a grouping yml, add dose_series_repeat=$n option to indicate dose series for merging. (`#713 <https://github.com/xia2/xia2/issues/713>`_)
- Add handling for small-molecule chemical formula data, and extra help output when using ``xia2.small_molecule``. (`#723 <https://github.com/xia2/xia2/issues/723>`_)
- ``xia2.ssx``: Improve unit cell assessment and reporting when unit cell is not known. (`#731 <https://github.com/xia2/xia2/issues/731>`_)
- ``xia2.multiplex``: Generate ``FreeR_flag`` column in merged mtz output, ensuring flags are consistent across all clusters/filtered reflections. (`#732 <https://github.com/xia2/xia2/issues/732>`_)


Bugfixes
--------

- CPU allocation limits will now be correctly inherited from the Slurm cluster scheduler. (`#722 <https://github.com/xia2/xia2/issues/722>`_)
- ``xia2.ssx``: Don't use the beam model from a reference geometry. (`#724 <https://github.com/xia2/xia2/issues/724>`_)
- ``xia2.ssx``: If rerunning in same directory, make sure correct batch folders are generated. (`#725 <https://github.com/xia2/xia2/issues/725>`_)
- ``xia2.ssx``: When re-importing with the self-determined reference geometry, don't overwrite the detector model with manually specified phil options. (`#726 <https://github.com/xia2/xia2/issues/726>`_)


Misc
----

- `#728 <https://github.com/xia2/xia2/issues/728>`_, `#729 <https://github.com/xia2/xia2/issues/729>`_, `#730 <https://github.com/xia2/xia2/issues/730>`_


xia2 3.13.0 (2023-01-26)
========================

Features
--------

- ``xia2.ssx``: Handle data from PAL-XFEL and SACLA. (`#719 <https://github.com/xia2/xia2/issues/719>`_)
- ``xia2.ssx``: Report r-split metric in merging stats (`#721 <https://github.com/xia2/xia2/issues/721>`_)


Improved Documentation
----------------------

- Documentation: add `hdf5_plugin` description (`#716 <https://github.com/xia2/xia2/issues/716>`_)


Misc
----

- `#720 <https://github.com/xia2/xia2/issues/720>`_


xia2 3.12.0 (2022-10-31)
========================

Features
--------

- ``xia2.ssx`` and ``xia2.ssx_reduce`` are now considered stable, so have dropped the ``dev.`` prefix. (`#710 <https://github.com/xia2/xia2/issues/710>`_)


Bugfixes
--------

- ``xia2.ssx``: Fix error in deciding whether to assess indexing ambiguities. (`#705 <https://github.com/xia2/xia2/issues/705>`_)
- ``xia2.ssx``: Fix crash in geometry refinement when a block has no indexable images. (`#707 <https://github.com/xia2/xia2/issues/707>`_)
- Explicitly set the log file encoding to be UTF-8. This could break on systems set to non-native character encodings. (`#709 <https://github.com/xia2/xia2/issues/709>`_)
- ``xia2.ssx``: Avoid crash if no images successfully integrated. (`#711 <https://github.com/xia2/xia2/issues/711>`_)


Misc
----

- `#703 <https://github.com/xia2/xia2/issues/703>`_, `#704 <https://github.com/xia2/xia2/issues/704>`_


xia2 3.11.0 (2022-08-24)
========================

Features
--------

- ``dev.xia2.ssx``: Add data reduction to experimental ssx pipeline, and expose data reduction as the new standalone ``dev.xia2.ssx_reduce`` program. (`#683 <https://github.com/xia2/xia2/issues/683>`_)


Bugfixes
--------

- ``xia2.to_shelx``: Fix crash when using unmerged mtz with the ``--cell`` option. (`#698 <https://github.com/xia2/xia2/issues/698>`_)


Misc
----

- `#684 <https://github.com/xia2/xia2/issues/684>`_, `#688 <https://github.com/xia2/xia2/issues/688>`_, `#689 <https://github.com/xia2/xia2/issues/689>`_, `#690 <https://github.com/xia2/xia2/issues/690>`_, `#691 <https://github.com/xia2/xia2/issues/691>`_, `#692 <https://github.com/xia2/xia2/issues/692>`_, `#693 <https://github.com/xia2/xia2/issues/693>`_, `#696 <https://github.com/xia2/xia2/issues/696>`_, `#699 <https://github.com/xia2/xia2/issues/699>`_, `#701 <https://github.com/xia2/xia2/issues/701>`_


xia2 3.10.1 (2022-07-12)
========================

Bugfixes
--------

- ``dev.xia2.ssx``: Fix reporting of missing phil files, fix crash when no images indexed in a batch (`#686 <https://github.com/xia2/xia2/issues/686>`_)


xia2 3.10.0 (2022-06-09)
========================

Features
--------

- Add unmerged items to mmcif output, conform to the v5 mmcif dictionary by default. (`#667 <https://github.com/xia2/xia2/issues/667>`_)
- ``dev.xia2.ssx``: Add first part of a developmental ssx processing pipeline (data integration) (`#670 <https://github.com/xia2/xia2/issues/670>`_)


Bugfixes
--------

- Unit cell clustering fixes for `dials/dials#2081 <https://github.com/dials/dials/pull/2081>`_ (`#668 <https://github.com/xia2/xia2/issues/668>`_)
- Move ``DataManager`` to separate module to avoid circular import (`#669 <https://github.com/xia2/xia2/issues/669>`_)
- Fix cases where NeXus files not following the Eiger conventions (``/entry/data/data_[nnnn]```) were ignored. (`#672 <https://github.com/xia2/xia2/issues/672>`_)
- Fix bug in ``pipeline=dials`` where the working directory contains the letters ``"mtz"``, which would incorrectly be replaced with ``"sca"``, leading to an error. (`#674 <https://github.com/xia2/xia2/issues/674>`_)
- ``dev.xia2.ssx``: Correctly report all spot histograms for multi-imageset input to spotfinding (`#678 <https://github.com/xia2/xia2/issues/678>`_)


Deprecations and Removals
-------------------------

- The option ``report.resolution_bins`` for specifying the number of resolution bins in the merging statistics report in ``xia2.html`` is now deprecated.  Please use the ``merging_statistics.n_bins`` option instead.  If you don't specify either parameter, you will not notice any change in behaviour — the default will still be to use 20 resolution bins. (`#666 <https://github.com/xia2/xia2/issues/666>`_)


Misc
----

- `#661 <https://github.com/xia2/xia2/issues/661>`_, `#662 <https://github.com/xia2/xia2/issues/662>`_, `#663 <https://github.com/xia2/xia2/issues/663>`_, `#664 <https://github.com/xia2/xia2/issues/664>`_, `#675 <https://github.com/xia2/xia2/issues/675>`_, `#676 <https://github.com/xia2/xia2/issues/676>`_, `#677 <https://github.com/xia2/xia2/issues/677>`_, `#679 <https://github.com/xia2/xia2/issues/679>`_, `#681 <https://github.com/xia2/xia2/issues/681>`_, `#682 <https://github.com/xia2/xia2/issues/682>`_


xia2 3.9.0 (2022-03-14)
=======================

Features
--------

- ``xia2.delta_cc_half``: Add overall CC½, plus a completeness column to the table. (`#645 <https://github.com/xia2/xia2/issues/645>`_)


Bugfixes
--------

- ``xia2.multiplex``: Allow processing imported mtz when imageset is absent. (`#641 <https://github.com/xia2/xia2/issues/641>`_)
- Avoid hanging on a call to ``pointless`` to get version information. (`#651 <https://github.com/xia2/xia2/issues/651>`_)


Deprecations and Removals
-------------------------

- xia2 no longer supports Python 3.7. (`#646 <https://github.com/xia2/xia2/issues/646>`_)


Misc
----

- `#647 <https://github.com/xia2/xia2/issues/647>`_, `#648 <https://github.com/xia2/xia2/issues/648>`_, `#655 <https://github.com/xia2/xia2/issues/655>`_, `#657 <https://github.com/xia2/xia2/issues/657>`_, `#658 <https://github.com/xia2/xia2/issues/658>`_, `#659 <https://github.com/xia2/xia2/issues/659>`_


xia2 3.8.1 (2022-01-25)
=======================

Improved Documentation
----------------------

- ``xia2.multiplex``: Add, and update, PHIL parameter descriptions. (`#644 <https://github.com/xia2/xia2/issues/644>`_)


xia2 3.8.0 (2022-01-11)
=======================

Features
--------

- ``xia2.multiplex``: Extend available deltacchalf filtering options to match those in ``dials.scale``. (`#631 <https://github.com/xia2/xia2/issues/631>`_)
- ``xia2.compare_merging_stats latex=True``: include cc-anom. (`#633 <https://github.com/xia2/xia2/issues/633>`_)


Bugfixes
--------

- ``xia2.compute_merging_stats``: Avoid warning in output. (`#636 <https://github.com/xia2/xia2/issues/636>`_)
- Fix test failure by deprecation of DIALS' OptionParser. (`#642 <https://github.com/xia2/xia2/issues/642>`_)


Misc
----

- `#639 <https://github.com/xia2/xia2/issues/639>`_


xia2 3.7.1 (2021-11-17)
=======================

Features
--------

- ``xia2.multiplex``: Include additional graphs in json output (`#637 <https://github.com/xia2/xia2/issues/637>`_)


xia2 3.7.0 (2021-11-01)
=======================

Features
--------

- New option ``general.check_for_saturated_pixels=True``, to warn about saturated pixels found whilst performing spot finding. This may be turned on by default in a future release. (`#624 <https://github.com/xia2/xia2/issues/624>`_)


Bugfixes
--------

- ``xia2.compare_merging_statistics``: If no input files provided, print help, and not empty plots. (`#629 <https://github.com/xia2/xia2/issues/629>`_)
- ``xia2.overload``: Handle command arguments in a more standard way (`#415 <https://github.com/xia2/xia2/issues/415>`_)
- Handle installing xia2 as a "real" package when the ``conda_base/`` is read-only (`#616 <https://github.com/xia2/xia2/issues/616>`_)
- Allow xia2 installation while offline (`#619 <https://github.com/xia2/xia2/issues/619>`_)


Misc
----

- `#620 <https://github.com/xia2/xia2/issues/620>`_, `#630 <https://github.com/xia2/xia2/issues/630>`_


xia2 3.6.0 (2021-08-16)
=======================

Features
--------

- ``xia2.multiplex``
   - Add ``absorption_level=`` parameter to set the corresponding parameter in dials.scale. If
     unspecified, decisions about absorption correction will be deferred to ``dials.scale``. This
     means that for large sweeps (>60°), absorption correction will now be turned on automatically. (`#603 <https://github.com/xia2/xia2/issues/603>`_)
   - Add dano/sigdano by resolution plots to html report (`#604 <https://github.com/xia2/xia2/issues/604>`_)
   - Also output reflections in scalepack format (`#607 <https://github.com/xia2/xia2/issues/607>`_)
   - Enable sharing of an absorption correction for scaling with dials, with the option ``share.absorption=True`` (`#614 <https://github.com/xia2/xia2/issues/614>`_)


Bugfixes
--------

- Separate data by I+/I- in merged .sca file produced by the dials pipeline (`#606 <https://github.com/xia2/xia2/issues/606>`_)
- ``xia2.compare_merging_stats``: Print input files in deterministic order (`#612 <https://github.com/xia2/xia2/issues/612>`_)
- ``xia2.compare_merging_stats``: fix crash when setting ``anomalous=True`` (`#613 <https://github.com/xia2/xia2/issues/613>`_)


Misc
----

- `#596 <https://github.com/xia2/xia2/issues/596>`_, `#597 <https://github.com/xia2/xia2/issues/597>`_, `#598 <https://github.com/xia2/xia2/issues/598>`_, `#608 <https://github.com/xia2/xia2/issues/608>`_, `#609 <https://github.com/xia2/xia2/issues/609>`_


xia2 3.5.0 (2021-05-27)
=======================

Features
--------

- Separate anomalous pairs when scaling with ``dials.scale`` if ``anomalous=True``. The ``anomalous=`` parameter has also been added to ``xia2.multiplex``. (`#539 <https://github.com/xia2/xia2/issues/539>`_)
- Add new ``surface_weight=`` parameter, to control the ``dials.scale`` absorption correction. (`#584 <https://github.com/xia2/xia2/issues/584>`_)
- Add ``error_model_grouping=`` option to allow refining of an individual or grouped error model in dials. (`#585 <https://github.com/xia2/xia2/issues/585>`_)
- Added ``absorption_level=[low|medium|high]`` option for control of the absorption correction, when using ``dials.scale``. (`#592 <https://github.com/xia2/xia2/issues/592>`_)


Bugfixes
--------

- Prevent unintended output when checking version of ``pointless`` (`#586 <https://github.com/xia2/xia2/issues/586>`_)
- Fix documentation section on resolution estimation (`#593 <https://github.com/xia2/xia2/issues/593>`_)


Deprecations and Removals
-------------------------

- Removed python test files from the xia2 package installation, slightly reducing the package size. (`#587 <https://github.com/xia2/xia2/issues/587>`_)
- Remove leftover Travis CI-related files (`#588 <https://github.com/xia2/xia2/issues/588>`_)


Misc
----

- `#582 <https://github.com/xia2/xia2/issues/582>`_


xia2 3.4.2 (2021-04-12)
=======================

Bugfixes
--------

- Fix reading of split HKL files output from XSCALE (`#579 <https://github.com/xia2/xia2/issues/579>`_)


xia2 3.4.1 (2021-04-01)
=======================

Features
--------

- ``xia2.multiplex``: Use resolution cutoff determined during scaling for cluster analysis (`#576 <https://github.com/xia2/xia2/issues/576>`_)


Bugfixes
--------

- ``xia2.multiplex``: Fix cos-angle clustering varying between runs (`#576 <https://github.com/xia2/xia2/issues/576>`_)


xia2 3.4.0 (2021-03-15)
=======================

- Fix tests affected by changes to profile fitting in `dials/dials#1297 <https://github.com/dials/dials/pull/1297>` (`#569 <https://github.com/xia2/xia2/issues/569>`_)
- The main development branch of xia2 was renamed from 'master' to 'main'. (`#561 <https://github.com/xia2/xia2/issues/561>`_)

Misc
----

- `#550 <https://github.com/xia2/xia2/issues/550>`_, `#554 <https://github.com/xia2/xia2/issues/554>`_, `#555 <https://github.com/xia2/xia2/issues/555>`_, `#556 <https://github.com/xia2/xia2/issues/556>`_, `#565 <https://github.com/xia2/xia2/issues/565>`_, `#568 <https://github.com/xia2/xia2/issues/568>`_, `#572 <https://github.com/xia2/xia2/issues/572>`_, `#573 <https://github.com/xia2/xia2/issues/573>`_, `#574 <https://github.com/xia2/xia2/issues/574>`_, `#575 <https://github.com/xia2/xia2/issues/575>`_


xia2 3.3.4 (2021-03-05)
=======================

Bugfixes
--------

- Fix ``type object has no attribute 'ignore'`` error (`#570 <https://github.com/xia2/xia2/issues/570>`_)


xia2 3.3.3 (2021-02-15)
========================

Bugfixes
--------

- Fix for missing ``SENSOR_THICKNESS=`` in XDS.INP generated for EIGER datasets introduced in 3.3.1 (`#564 <https://github.com/xia2/xia2/issues/564>`_)


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

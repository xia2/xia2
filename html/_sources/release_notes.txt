+++++++++++++
Release notes
+++++++++++++


Changes since 0.3.8.0
---------------------

  * Removed references to scala - rarely used command line
    option scala secondary now aimless secondary.
  * Fixed processing of MAD data with AIMLESS.
  * Removed rather a lot of clutter, of things which were once a good
    idea but never followed through with...

Changes since 0.3.7.0: Added DIALS (mostly)
-------------------------------------------

  * Added support for DIALS_ software. Thanks to Richard Gildea at Diamond for
    most of the work.
  * Create AIMLESS xml output; useful for displaying results
    through alternative interfaces.
  * Squashed nasty bug where input spacegroup set to e.g. I222 but
    pointgroup derived to be P222 (think this one was reported a while
    back but I could not find the source at the time... sorry!)
  * Squashed some other bugs which have appeared in recent history.

Changes since 0.3.6.3: Bug fixes, add CC-half, removing Scala.
--------------------------------------------------------------

  * -cc_half 0.5 (say) resolution limit criterion available -
    suggest set -misigma 0.5 -isigma 0.5 or similar with this.
  * -freer_file where free flag != FreeR_flag fixed.
  * Massively trimmed all of the command line options for the
    pipelines and removed the use of Scala in all pipelines, replaced
    with Aimless (not before time!) This means that -3dr and so forth
    *will no longer work* so please use -2d, -3d, -3di etc.
  * -phil command line option now deprecated: phil parameters passed
    on the command-line will be respected, also phil files, without this
    clue
  * Parallelisation options: can now cleanly process sweeps from one
    wavelength in parallel (to aid with multi-crystal data sets) use
    Phil parameters njob=4 nproc=12 mode=parallel (say) to allow processing
    four sweeps at a time each using 12 cores [#f0.3.6.3]_.

Changes since 0.3.6.2: Cope with new CCP4.
------------------------------------------

  * Mend xia2 working on Windows.
  * Cope with new version of CTRUNCATE in CCP4 6.4.0.
  * xia2ccp4i added - thanks to David Waterman.
  * Improved handling of nasty image names.
  * Mend -reversephi functionality.
  * Take spacegroup from reference reflection file correctly.

Changes since 0.3.6.1: New XDS etc.
-----------------------------------

  * Default 1 pixel for XDS spot finding for indexing.
  * Remove need for XIA2 environment variables.
  * Add capability to override cctbx.python location.

Changes since 0.3.5.2: dealing with huge data sets
--------------------------------------------------

  * If single sweep, do not rebatch.
  * Replace CCP4 Mtzdump with CCTBX-powered equivalent.
  * If reindex for changing spacegroup name but not indices
    (i.e. no REINDEX= card) then use CCTBX-powered replacement.
  * Cleaned up repository by pulling xia2core into
    xia2/core.
  * Patched against dxtbx being included in Phenix. (temporary)

Changes since 0.3.5.1: CCP4 patch release
-----------------------------------------

  * Resolution limit calculation now delegated to resolutionizer.
  * Twinning test now uses CCTBX code not sfcheck.
  * PythonDriver added to support execution of Python code as separate
    process.

Changes since 0.3.5.0
---------------------

  * -hdr_in mode - pass in text file containing image
    header. Can also generate this file with xia2 with -hdr_out example.hdr
  * -xparm_ub mode for XDS processing only, provide a UB matrix (XDS
    XPARM file) to match the orientation to: primarily useful if you record
    data from several regions on a sample, and the sample has close-to
    symmetry (i.e. you almost certainly don't need this)
  * Removed usage of BINSORT_SCR as this is being deprecated by CCP4.
  * Allow Phil overrides on selection of autoindexing solutions, where
    indexing can give large variations in unit cell constants (e.g. low
    resolution virus data)
  * Properly set the resolution in CAD copying free R flags.
  * Allow access to profile grid size through the Phil interface:
    :samp:`xds.parameter.profile_grid_size=13,13`
  * Implement TRUSTED_REGION through Phil as suggested by Luca Jovine
  * Updates to process simulated data from SIM_MX
  * More measures of anomalous signal in output.
  * Corrected citations in output
  * Replaced TRUNCATE with CTRUNCATE.
  * Replace sfcheck with E^4 calculation from cctbx.
  * Exclude grid-scan data when running automatic setup.
  * If XDS refinement not performed, exception not warning.
  * If -3d and sweep narrower than 10 degrees, use XDS II indexer.

Changes since 0.3.4.0
---------------------

  * Additional information in output: correct directory for BINSORT_SCR,
    free space in working directory, warns if less than 200MB in
    BINSORT_SCR directory.
  * EXCLUDE keyword added to XINFO SWEEP block to allow
    specific resolution ranges to be excluded in processing,
    contributed by Andrew Perry at Monash University.
  * Include the resolution limits at the XSCALE stage rather
    than simply in the merging.
  * Support for 2x2 binned ADSC Quantum 270 detector.
  * Support for '.' in file names.
  * Support for NOIR1 detector on ALS 4.2.2
  * Smarter 3dii mode - if 3di style indexing will give better answer,
    it will do that...
  * Use ctruncate in place of truncate (finally!)

Changes since 0.3.3.4
---------------------

  * Use Phil to override XDS parameters.
  * Use Pointless in place of Reindex; Aimless in place of Scala; no
    limit to number of batches which can be processed.

Changes since 0.3.3.3
---------------------

  * Fixed bug in polarization correction vector for Pilatus data.
  * Fixed bug relating to assigning spacegroup on command-line.
  * Begun work on supporting Pilatus 300K for small molecule
    crystallography. Have now successfully processed data from Diamond
    Light Source beamline I19 EH2. N.B. Only works -3dii!

Changes since 0.3.3.2
---------------------

  * Many bug fixes as a result of implementing a comprehensive testing scheme.
  * Support for full cbf format, making use of cbflib Python bindings
    pycbf now included in cctbx releases.
  * Merged functionality from XDSIntegraterR into XDSIntegrater, removed
    duplicate code. Will make for more maintainable suite in the future.
  * Improved 2d pipeline scaling, now tests 8 permutations.
  * Improved handling of twinned data for multiple sweeps.
  * Fixed occasional bugs with multiple sweeps, reindexing trigonal
    data sets with XDS.
  * Removed "old" scaling modes, 2d and 3d, as these were unhelpful.

Changes since 0.3.3.1
---------------------

  * -xparallel -1 option added which will split your data into 30 degree
    chunks and process with forkintegrate.
    *Note well you are responsible for setting up forkintegrate correctly!*

Changes since 0.3.3.0
---------------------

  * Handle division in updated CCTBX.
  * Squash bug with -3d and -resolution.
  * Squash bug with resolution and -2d, result slightly different to
    that reported.
  * Trap weirdness with XDS reindexing, causes problems sometimes
    trying to process in C2 from P222 not P2 as you would hope!
  * Adjustments to cope with excludively narrow sweeps i.e. all 3
    image sweeps.

Changes since 0.3.2.0
---------------------

  * Support for new XDS build.
  * Small bug fix / improvement in XDS indexer implementation.
  * Capability to ptovide refined experimental geometry *via*
    XDS GXPARM.XDS - useful for polycrystal data reduction.
  * Now check what you tell the program, viz::

      gw56@ws050 nonsense]$ xia2 -3d -nonsense /data/gw56/dl/Cowan/Insulin/insulin/
      Traceback (most recent call last):
        File "/home/gw56/svn/xia2/Applications/xia2.py", line 45, in
          from xia2setup import write_xinfo
        File "/home/gw56/svn/xia2/Applications/xia2setup.py", line 35, in
          from Handlers.CommandLine import CommandLine
        File "/home/gw56/svn/xia2/Handlers/CommandLine.py", line 1513, in
          CommandLine.setup()
        File "/home/gw56/svn/xia2/Handlers/CommandLine.py", line 349, in setup
          raise RuntimeError, nonsense
      RuntimeError: Unknown command-line options: -nonsense

    and complain if you type in something xia2 does not understand.
  * Removed a *lot* of cruft from the xia2 code base in preparation
    for some more substantial refactoring.
  * Found bug which meant that the labelit beam centre computed in the
    setup phase was not used - mostly this is not important, unless you are
    using -3dii.
  * Added -ice command-line argument, which will exclude measurements
    from regions which are typically where ice rings land. Will need to
    add more subtle mechanism which will allow specific regions to be
    excluded.
  * Specifying resolution with 3d(r) pipeline now works correctly.
  * Removed XDS version check by default, which was annoying every new
    year. If you would like to check that the XDS version is explicitly
    supported, add -check_xds_version to the command-line.
  * Added table of scala runs to sweep name in the debug output, helpful
    for reviewing in polycrystal data reduction cases.
  * Mosaic spread used from Mosflm is now average of all images, not the
    first or last image.
  * Fixed header reading for new Pilatus instruments at DLS and
    elsewhere.
  * Added capacity to pass in known globally postrefined experimental
    setup via -xparm GXPARM.XDS, only useful with XDS processing
    pipelines.
  * Removed use of ccp4 printpeaks tool, which crashes on new pilatus
    images, replace with Mosflm for the moment. Move to replacement with
    labelit code at later stage planned.

Changes since 0.3.1.7
---------------------

  * Now report the min, mean, max mosaic spread (according to the
    *program definitions* after integration of each sweep.
  * Resolved problems with overriding environment.
  * Added -serial pun for -parallel 1.
  * Allow resolution limit to be assigned on a per-sweep basis.
  * Handled corner case with images 200 - 250 (say) giving REBATCH
    error.
  * Added full 8-way search for scaling models for 2d pipelines.
  * Partial support for two-theta offset data collection (tested with
    Rigaku X-ray equipment and Diamond I19 data.)
  * Added -min_images keyword which is helpful when analysing virus data
    with e.g. 4 images / sweep.

Changes since 0.3.1.6
---------------------

  * Changes suitable for working on microcrystals - reachable through
    a -microcrystal command line flag, and -failover is probably helpful
    too.
  * If lattice or spacegroup specified, do not run tests.
  * 2dr and 3dr now the default pipelines - use 2dold or 3dold if you
    need to get to the old pipelines.
  * Fixed selection of known lattice in IDXREF reindexing.

Changes since 0.3.1.0
---------------------

  * Fixed bug where the resolution limit was not reset in an indexer
    solution elimination.
  * Added support for XDS from Dec 09.
  * Fixed some of the issues found in the resolution limit determination
    when processing low resolution data.
  * Fixed use of I/sigma limit assignment.
  * Added command-line control of individual indexer, integrater,
    scaler.
  * Repaired regular expression for image matching, to cope with
    images where there is e.g. 3.5 in the template. This was previously
    misinterpreted as an image name of the form setup.NNNN.
  * Implemented new resolution limit pipelines, based on new merging code
    to give more robust control: -2dr and -3dr (recommended.) Fine
    control over the choices can be made using the -isigma, -misigma,
    -completeness and -rmerge command line options.
  * Added interactive indexing mechanism, where user can assign images
    to use for autoindexing, e.g.::

      Existing images for indexing: 1, 90, 180
      >1, 60, 120, 180
      New images for indexing: 1, 60, 120, 180

    Assign -interactive on the command line (Mosflm and Labelit indexers)

Changes since 0.3.0.6
---------------------

  * Added -xparallel command line option to allow use of forkinitegrate
    on a cluster with the 3d pipeline.
  * Allow for xia2html and (beta) ISPyB output (latter more useful for
    synchrotron sources, former handy if you want a report.
  * Smart scaling mode switched on by default.
  * Chef now run by default, for radiation damage analysis, e.g.::

      Group 1: 2-wedge data collection
      Group 2: Single wedge
      Significant radiation damage detected:
      Rd analysis (12287/LREM): 15.17
      Rd analysis (12287/INFL): 7.89
      Rd analysis (12287/PEAK): 12.82
      Conclusion: cut off after DOSE ~ 608.8

  * Blank images now handled more gracefully.
  * Overloaded and blank images now correctly reported in the summary
    output, along with abandoned images for the processing with
    Mosflm. Also postrefinement results.
  * Substantially cleaned up the program output.

Changes since 0.3.0.5
---------------------

  * No lattice test mode added (you can guess the command-line option)
    for tricky data sets where this perhaps falls over.
  * Fixed side effect of changes which allowed setting of unit cell
    etc. - lattices were no longer eliminated, failed complaining
    can't eliminate only solution.
  * Tidied up the generation of output files and so on - now only have
    the main log file and the debug trace.
  * Added copy of the command line to program output.

Changes since 0.3.0.4
---------------------

  * Now able to specify number or fraction of reflections assigned to
    the free set, rather than the default 5 percent.
  * Added trap for sdcorrection not being refined in XDS correct if
    multiplicity rather low. Unusual case.
  * Assigning a freer_file by definition sets this as an indexing
    reference and also copies the spacegroup assignment. This is
    what you would expect!

Changes since 0.3.0.3
---------------------

  * User now able to assign cell constants: use with great care, as
    there is little in the way of nonsense trapping. This may however
    be used to handle cases where the solution you want is monoclinic
    with a pseudo-orthorhombic lattice, where the default indexing would
    select a different setting. This will not currently work with a
    Mosflm indexer. Usage is::

      -cell a,b,c,alpha,beta,gamma

    and the correct symmetry should also be assigned. Can also assign
    USER_CELL a b c alpha beta gamma in the xinfo file.

Changes since 0.3.0.0
---------------------

  * Now automatically determine the number of available processor
    cores.
  * Implemented check for centring of crystallographic basis from
    autoindexing.
  * Started to use CCTBX - this will be bundled with the release
    from now on...
  * Now runs "smart scaling" i.e. will customise the scaling model
    used to the data. This can seriously improve the xia2 run time in
    cases where some of the default scaling models do not converge.
  * Now also includes running of CHEF for radiation damage, which will
    slice and dice your data into dose groups, then run a correctly
    time sequenced radiation damage analysis. N.B. for data measured in
    "dose mode" the doses will be scaled to &lt; 1,000,000 to ensure that
    the output is tidy.
  * Corner case of running XDS pipelines from data from a Rigaku setup.
    The low resolution was previously calculated to be 0.0! D'oh!
  * Added access to reference reflection file functionality to the
    command line - -reference_reflection_file foo.mtz.
  * Fixed the use of the -image command-line option. Now works.
  * Removed all of the binaries from the distribution, so now
    **you need to be using CCP4 6.1.0 or later!**
  * Will correctly handle reindexing with the 3d pipeline (XDS/XSCALE)
    with trigonal spacegroups and multiple sweeps.

Changes since 0.2.7.2
---------------------

  * Fixed merging statistics bug - I/sigma output were very slightly
    different.
  * Now extend FreeR column if copying from lower resolution input
    file.
  * Detector limits now correctly specified around the detector centre
    for Mosflm, rather than the beam centre. Only useful if your beam
    centre is a fair way from the image centre...
  * Parallelised integration with Mosflm - divides the sweeps into an
    appropriate number of chunks and then sorts together the resulting
    reflection files. -parallel N, remember.
  * Added a putative 'small molecule' mode, which will autoindex with
    Mosflm from a modest number of images, for smaller molecules where
    Labelit is unhappy with the number of good Bragg reflections.

Changes since 0.2.7.0
---------------------

  * Fixed to work correctly with XDS and Rigaku Saturn/RAXIS
    detectors.
  * Better determination of resolution limits.
  * Correct merging of data from XSCALE (needs to invert the I=F*F
    scale factor...)
  * Fixed output of scalepack unmerged output using 3d pipeline.
  * Use fewer frames for background calculation with 3dii pipeline -
    speeds things up a fair amount.
  * Write chef output files with correct SD correction parameters.
  * Print SD correction factors for scala runs - if these are bigger
    than about 2 there is something properly wrong. Also print the
    same from XDS CORRECT step.

Changes since 0.2.6.6
---------------------

  * All command line options now echoed to the standard output if
    -debug selected.
  * Command line options now copied to .xinfo file when operating in
    automatic mode.
  * XDS: low resolution limit determined from spot list from
    IDXREF.
  * Now include explicit python version check in xia2 main program.
  * High resolution limits for integration now assessed from Wilson
    plot rather than integration program log output.
  * If no images are given, a more helpful error message is produced
    than before, viz::

      ------------------------------------------
      | No images assigned for crystal DEFAULT |
      ------------------------------------------

  * If images are not readable (i.e. a permissions problem) then
    warnings will be sent to the debug channel (switch on -debug
    for more information.)
  * If in automatic mode an image is given in place of a directory,
    xia2 will now complain in a more helpful way.
  * Resolution limits will now be based on analysis of the reflection
    files rather than the program output, since this will generally give
    a more helpful answer...
  * Now correctly set the reindex matrix for running correct with
    multiple sweeps of data for non primitive matrix (subtle bug,
    thanks to Kay Diederichs for helping to fix this one.)*
  * Is images are missing from a sweep, xia2 will now tell you
    this before starting processing rather than giving a strange error -
    if the images are unreadable you will also be told.

Changes since 0.2.6.5
---------------------

  * Now supports CCP4 6.1 (forthcoming release) though you may need
    to add XIA2_CCP4_61=1 to your environment. This release should include
    xia2.
  * Added -user_resolution keyword, also support for this on a
    per-wavelength basis in the xinfo file.
  * Added support for reverse-phi data collection - either add
    reversephi to the xinfo file or -reversephi to the command line.

Changes since 0.2.6.4
---------------------

  * Now handles complex image names with e.g. + in them correctly.
  * New option for processing :samp:`-3dii` added - this will run
    the 3D pipeline (XDS, XSCALE) using all images for spot picking and
    autoindexing - useful for properly tricky cases.
  * Now correctly propogate the profile information to Mosflm when not
    using Mosflm for autoindexing - this is done by running a "fake"
    autoindexing task.
  * Use the raster information for the cell refinement test, and changed
    the selection of images for this.
  * Added support for the output of BioXHIT XML in the LogFiles
    directory - for project tracking.
  * Now copy the XDS log files ("LP" files) into the LogFiles
    directory - as always these are the most up-to-date versions from
    processing.
  * Added support for latest release of XDS (June 2, 2008.)

Changes since 0.2.6.3
---------------------

  * Added possibility to give a reflection file with an existing
    FreeR_flag column, which will be copied to the output MTZ::

      xia2 -freer_file free.mtz

    or... ::

      FREER_FILE free.mtz

    in the xinfo file (in the same way as the reference reflection file -
    indeed, this may be the same file...)

  * Added command line control of the spacegroup - note well that this
    means that the data WILL NOT be reindexed to a standard setting.
  * Added support for ADSC Quantum 270.
  * Intelligent selection of autoindex threshold for Mosflm.
  * Added support for latest XDS version.
  * Added support for pilatus 6M mini CBF images.
  * Fixed problem with cell refinement giving negative mosaic
    spreads sometimes for 2d pipeline.

Changes since 0.2.6.2
---------------------

  * Now works for images with long image numbers, as typically
    recorded on Rigaku X-Ray sets.
  * Signed off for operation with Rigaku Saturn and RAXIS IV
    detectors.
  * Now works with no input, e.g.::

      xia2 -project TG6623 -crystal X77788 -atom se /my/images/are/here

    However this relies on your image headers being accurate and the
    images having some kind of recognisable format...

  * Repaired operation on ppc and intel macs - added required libraries
    to the installation and reset the library paths appropriately.
  * Slightly improved error reporting from xinfo file errors.

Changes since 0.2.6.1
---------------------

  * Now carefully select the images to use for cell refinement based
    on the orientation of the crystal lattice.
  * Fixed numerous bugs to do with the naming of the detector class
    which changed in the previous version.

Changes since 0.2.6.0
---------------------

  * Fixed bug where if the distance was read incorrectly from the
    image header (or was wrong therein) XDS would get the wrong value
    even if you had put the correct value in the .xinfo file.
  * Now "unroll" the unmerged reflections from XSCALE and then
    merge them in their original sweeps in Scala. This should give
    a useful Rmerge vs. time plot.
  * Including updated versions of Pointless and Scala.
  * Includes new and more robust handling of pointgroups, lattices
    and unstable refinement of parameters during integration.
  * Include support for a reference reflection file, which will
    ensure that the reflections are indexed in the same way and
    with the same spacegroup - useful for mutants.
  * Now always use three wedges of images for the cell refinement
    with Mosflm as this makes the lattice elimination more reliable.
  * If one of the images in a sweep is broken (e.g. corrupted)
    xia2 will tell you more helpfully rather than just crashing.
  * Now correctly read distance from Mar 165 images. Thanks to
    Francois Remacle for this fix to DiffractionImage.
  * Fixed the use of xia2 -3d with RAXIS IV detectors.
  * Use more images for Mosflm autoindexing (three instead of two)
    as this gives uniformly better results.

Changes since 0.2.5.2
---------------------

  * Now works for highly incomplete data sets, so long as you
    have either 4 times the mosaic spread or 8 images, whichever
    is the larger. This is to allow pointgroup identification
    from e.g. the first 10 images in a data set - designed to assist
    in synchrotron / lab source data collection.
  * Now include the latest Mosflm binaries in the extras package -
    these are often better than those in the CCP4 distribution,
    as they come directly from Harry Powell's web page.
  * Added -ehtpx_xml_out option which will write out marked
    up metadata about the data reduction, for inclusion in the
    e-HTPX data reduction portal and, perhaps, other automated
    systems. Usage::

      xia2 -ehtpx_xml_out project.xml

  * If data are very incomplete (e.g. less than 50% complete) then don't
    try to refine the error parameters. This is both incorrect and a
    waste of time.
  * Renamed the output reflection files - these are now in DataFiles
    directory with names like "PROJECT_CRYSTAL_free.mtz." This makes
    them a little easier to identify.
  * Harvesting (deposition) files now in subdirectory of Harvest
    rather than being spread around the place. These will have
    names Harvest/DepositFiles/PROJECT/WAVELENGTH.scala etc.
  * **Have now fixed xia2setup so it works much more sensibly - the**
    **decision about when a new sweep starts was a little broken**
    **(rounding errors issue) now fixed!**
  * Added -parallel flag to work when using XDS for data reduction.
  * **Added XDS support!** This is however much less mature than**
    **the support for Mosflm/CCP4. It is also worth noting that this**
    **relies on many CCP4 tools.**
  * Added selection of the "pipeline" to use through a command line
    option, either -2d for mosflm/ccp4 or -3d for xds/xscale though
    the latter still uses a number of CCP4 programs.

Changes since 0.2.5.1 - big changes in **bold**
--------------------------------------------------

  * **Process data as native if no heavy atom information, only one**
    **wavelength specified and no anomalous scattering form factors**
    **provided. Otherwise separate anomalous pairs for scaling.**
  * **Added a -quick option to the xia2 command line, which will**
    **cut out many of the data reduction optimisation steps (not**
    **refine detector parameters, resolution or scaling parameters)**
    **but will still include everything else. This is to allow quick**
    **characterisation of data at the beamline, and perhaps map**
    **calculation?**
  * Correctly print the unmerged scalepack file name for single
    wavelength data.
  * Perform radiation damage analysis using R merge and B factor
    as a function of *time* - note that this is not *batch.*
    This is likely to have interesting side-effects.
  * If time of data collection not recorded in header *but*
    the time stamp for the images are correct (e.g. you have not moved
    them since collection) then the command line flag
    :samp:`-trust_timestamps` can be used, which will use the
    time stamps on the image files to analyse things like radiation
    damage.
  * If you are running this on a cluster, have added an option
    to migrate the diffraction data to a local disk (e.g. /tmp.)
    To do this add :samp:`-migrate_data` to the command line -
    the data will be removed from the local disk once the processing
    is finished.
  * Copy all final reflection files to a DataFiles directory.
  * Now, when something goes horribly wrong, just write the actual
    message to the screen and the horrible stack trace gunk to a file
    called xia2.error. This should be sent in for error reports!
  * Remerge individual wavelengths to get the merging statistics to
    the most appropriate resolution limit, rather than the furthest
    extent of any data, for the summary table.
  * If GAIN included in SWEEP block, will be used as the default
    value for integration. E.g. GAIN 0.25.

Changes since 0.2.5
-------------------

  * Fixed problem with spacegroup R3:H (naming convention problem
    - there's a surprise.)
  * GAIN estimation temporarily removed.
  * Pointgroup evaluation fixed - found a **major** gremlin in
    there
  * Allow environment variables and tilde in DIRECTORY token::

      DIRECTORY $DATA/example or ~/data or %DATA%/example (win32)

  * Now tracks the citations for the programs used, writing them
    to the standard output in plain text and to xia-citations.bib
    in BIBTeX format.
  * Removed [XIA2] tokens from standard output - the reason for
    having this there no longer applies.

Changes since 0.2.4
-------------------

  * xia2setup will now add the f', f'' values if a scan is available
    and has been processed by chooch
  * GAIN now estimated by diffdump - enabling future parallelisation
    of the integration stage.
  * For detectors formed as a mosaic of a number of tiles, with "gaps"
    in between, now mask those gapped areas in Mosflm to reduce the
    number of bad reflections.
  * Now has a fix for the ongoing indexing problem which gave rise
    to errors like "something horrible has happened in indexing".
  * The "best" log file for each process will now be recorded in a
    LogFiles directory - which means no more hunting around for the
    final scala log file and what not.
  * Chaling now produces unmerged reflection files in scalepack format
    as well as merged scalepack and merged MTZ format. This is done by
    scala (if used) by recycling the final SCALES and adding
    "output polish unmerged."
  * Now runs a twinning test using the CCP4 program sfcheck, and
    will warn you if your data look twinned.
  * Now allow up to 100 cycles of scale refinement to cope with
    more extreme cases where data at very different resolutions
    are scaled together.

Changes since 0.2.3
-------------------

  * Added <a href="preferences.html">preferences file</a>
  * Added xia2setup program to create the .xinfo file - this will
    also run LABELIT to configure the beam centre if it is installed
  * Added a strategy-of-data-reduction step to the pipeline
  * Added run-time check that CCP4 and so on are available

Changes since 0.2.2.4
---------------------

  * Changed to a BSD license
  * Added "python setup" check to xia2
  * Relaxed criteria on isomorphism to 1% not 0.5A etc.
  * **Now wavelengths in wavelength record will override header
    values if provided, but do not (indeed, should not) be included
    if wavelength values are correct.**

Changes since 0.2.2.3
---------------------

  * Created version for Power PC G4/G5
  * Fixed .csh setup scripts
  * If wavelength values not specified in the .xinfo file will use
    values from the image headers
  * If loggraph output from scala is broken by having Mn(I/sigma)
    greater than 99.99 can now cope (ignores that record)
  * Will now use a maximum of 180 degrees of data for deciding
    e.g. the point group, spacegroup and correct indexing standards -
    this helps the cases where exceptionally high redundancy data
    has been measured


Changes since 0.2.2.2
---------------------

  * Updated printheader to cope with MAR 165
  * Cleaner error messages when data missing
  * Added support for MAR image plate data
  * Included more example .xinfo files in the examples directory
  * Relaxed refinement parameters in Mosflm cell refinement


.. [#f0.3.6.3] N.B. you may wait for a while until you see output - it
              will all be cached while parallel processing is happening to avoid
              it getting mangled.

.. _DIALS: http://dials.github.io

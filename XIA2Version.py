#!/usr/bin/env python
# XIA2Version.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 6th June 2006
# 
# A file containing the version number of the current xia2.
# 
# History:
# 
# 0.0.1 - initial build 06/06/06 - incomplete implementations of most
#         things but wanted to get the ball rolling on the version
#         numbering.
# 
# 0.0.2 - 21/JUN/06 added first application xia2scan for analysing 
#         humidifier images, added many useful types in Schema, 
#         handlers in Handler etc and Wrappers.                          
# 
# 0.0.3 - 16/AUG/06 getting something usefil in eventually, which 
#         will integrate data using only mosflm - xia2process.
# 
# 0.0.4 - 25/AUG/06 beginning work on a scaling module, will allow
#         reasonably complete processing from start to end
#
# 0.0.5 - 06/SEP/06 moved all text in programs from camelCase to tidy_style
#         and also implemented connection between XSweep and Integrater
#         factory
#
# 0.1.0 - 27/SEP/06 can successfully integrate & scale multiwavelength
#         data though this is not yet perfected!
#         25/OCT/06 can now run with JUST ccp4-6.0.1 through all 4 TS
#         examples from the .xinfo files, so this is version 0.1.0.
#         Tagging... - oh that's 0.1.1 then.
#
# 0.1.1.1 27/OCT/06 added new functionality to xia2scan.
#
# 0.2.0 - 08/NOV/06 this is it - it will now refine the resolution, refine
#         standard deviation parameters, feed back from scaling to integration
#         and all that jazz...
# 
# 0.2.1 - 15/NOV/06 release candidate to go with CCP4 6.0.2.
# 
# 0.2.2 - 21/NOV/06 second release candidate - this one includes stuff for
#         estimating number of molecules in ASU, solvent fraction, spacegroup.
# 
# 0.2.2a - 22/NOV/06 fixed typo!
#
# 0.2.2.1 - 23/NOV/06 fixed bug in TS01 - was running freer_flag with hklin
#         = hklout - Doh!
# 0.2.2.2 - added html help file and simple example, as well as a few small
#         fixes (like writing a xia2.txt file)
# 0.2.2.3 - added support for MAR 165 CCD, Mar 345 Image plate data. Works
#         now with insulin SAD data from SRS 7.2.
# 
# 0.2.2.4 - update build 
# 4 - includes changes documented in xia2.html.
# 
# --------------------------- UPDATED TO BSD LICENSE --------------------
# 0.2.3 - new license, feedback implemented.
#
# 0.2.4 - improved recycling of lattices, added xia2setup
# 
# 0.2.5 - adding phasing, fake scalers, fixed big bug with Mosflm indexing
#         selecting the wrong indexing solution, included support for saturn
#         detectors I think...
#
# 0.2.5.1 - bug fix to 0.2.5 detailed in xia2.html
#
# 0.2.5.2 - changes to read timestamps, migrate data etc. - detailed in
#           xia2.html. Also create DataFiles firectory.
#
# 0.2.5.3 - including new structure of integration etc. Never released.
#
# 0.2.6.0 - includes XDS as an integration and data reduction option and
#           also being parallel. Big change.
# 
# 0.2.6.1 - includes new ways of eliminating bad indexing solutions, allows
#           use of an external indexing reference, includes merging of
#           XDS data in Scala as separate batches.
#
# 0.2.6.2 - improved selection of cell refinement images, updated mosflm
#           version.
#
# 0.2.6.3 - completely automatic - just type xia2 /directory and it should
#           do "something sensible" - also added kernel of ccp4i interface.
#
# 0.2.6.4 - bug fix release prior to 0.3.0
# 
# 0.2.6.5 - this is not quite going according to plan - have still not hit 
#           0.3.0 (no chef in there yet) but have fixed some useful bugs.
# 
# 0.2.6.6 - back ported changes to allow for CCP4 6.1, included fixes for
#           othercell wrapper, added -user_resolution keyword (hopefully)
# 
# 0.2.7.0 - many big changes, made much more robust, added checks in for
#           common failure points, fixed XDS REIDX records, reset reindex
#           flags if eliminated lattice ...
# 
# 0.2.7.1 - panic ccp4 6.1 non-release
# 
# 0.2.7.2 - proper xia2 release - fixed upteen things including output 
#           polish unmerged for XDS processing
#
# 0.2.7.2a - XDS update
#
# 0.3.0.0 - major version update - now allows parallel integration with
#           Mosflm
#
# 0.3.0.1 - revision to accomodate small molecule data reduction (first pass)
# 
# 0.3.0.3 - revision which fixes the problems with reindexing in P321 &c.
#
# 0.3.0.4 - revision which allows the user to assign the correct cell constants
#           &c. - see html.
# 
# 0.3.0.5 - revision to give more flexibility to assiging the Free reflections,
#           also taking copies and using indexing reference if from freer file.
#
# 0.3.0.6 - fixed bug which appeared from the user setability of the cell etc.
#           tidied up output (i.e. much less clutter in main log now) and
#           allowed lattice test to be switched off for tricky cases.
#
# 0.3.1.0 - included xia2html, chef running and so on.
#
# 0.3.1.5 - overhauled the resolution limit calculations, viz:
#           http://xia2.blogspot.com/2010/03/resolution-limit-overhaul.html

VersionNumber = "0.3.1.6"
Version = "XIA2 %s" % VersionNumber
CVSTag = "xia2-%s" % VersionNumber.replace('.', '_')
Directory = "xia2-%s" % VersionNumber
if __name__ == '__main__':
    print 'This is XIA 2 version %s' % VersionNumber
    print 'This should be in a directory called "%s"' % Directory
    print 'And should be CVS tagged as "%s"' % CVSTag

    

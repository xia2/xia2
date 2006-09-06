#!/usr/bin/env python
# XIA2DPAVersion.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 6th June 2006
# 
# A file containing the version number of the current xia2dpa.
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

VersionNumber = "0.0.5"
Version = "XIA2DPA %s" % VersionNumber
CVSTag = "xia2dpa-%s" % VersionNumber.replace('.', '_')
Directory = "xia2dpa-%s" % VersionNumber

if __name__ == '__main__':
    print 'This is XIA 2 DPA version %s' % VersionNumber
    print 'This should be in a directory called "%s"' % Directory
    print 'And should be CVS tagged as "%s"' % CVSTag

    

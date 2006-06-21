#!/usr/bin/env python
# XIA2DPAVersion.py
# Maintained by G.Winter
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


VersionNumber = "0.0.2a"
Version = "XIA2DPA %s" % VersionNumber
CVSTag = "xia2dpa-%s" % VersionNumber.replace('.', '_')
Directory = "xia2dpa-%s" % VersionNumber

if __name__ == '__main__':
    print 'This is XIA 2 DPA version %s' % VersionNumber
    print 'This should be in a directory called "%s"' % Directory
    print 'And should be CVS tagged as "%s"' % CVSTag

    

#!/usr/bin/env python
# Pointless.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 2nd june 2006
# 
# A wrapper for the latest version of Phil Evans' program pointless - a
# program for deciding the correct pointgroup for diffraction data and also
# for computing reindexing operations to map one (merged or unmerged) data
# set onto a merged reference set.
# 
# To do:
# 
# (1) Implement the simplest pointless interface, which will simply assert
#     the appropriate pointgroup for diffraction data.
# (2) Implement reindexing-to-reference-set. This will require adding
#     code to handle HKLREF.
#
# FIXME this is hard-coded to use pointless-1.0.5 as the executable name...
#
# Update 14/JUN/06 to 1.0.6 - now available for windows mac linux
# 
# This will use the results written to an XMLOUT file. This file looks like:
# 
# <POINTLESS version="1.0.5" RunTime="Fri Jun  2 14:07:59 2006">
# <ReflectionFile stream="HKLIN" name="12287_1_E1.mtz">
# <cell>
#    <a>  51.64</a>
#    <b>  51.64</b>
#    <c>  157.7</c>
#    <alpha>     90</alpha>
#    <beta>     90</beta>
#    <gamma>     90</gamma>
# </cell>
# <SpacegroupName> P 43 21 2</SpacegroupName>
# </ReflectionFile>
#
# <LatticeSymmetry>
#   <LatticegroupName>P 4 2 2</LatticegroupName>
#    <cell>
#    <a>  51.64</a>
#    <b>  51.64</b>
#    <c>  157.7</c>
#    <alpha>     90</alpha>
#    <beta>     90</beta>
#    <gamma>     90</gamma>
#
# <snip...>
# 
# <BestSolution Type="pointgroup">
#   <GroupName>P 4 2 2</GroupName>
#   <ReindexMatrix>     1     0     0
#                       0     1     0
#                       0     0     1
#    </ReindexMatrix>
#    <Confidence>    1.000</Confidence>
#    <TotalProb>  1.071</TotalProb>
# </BestSolution>
# </POINTLESS>
#
#
# 11/AUG/06 changed from 1.0.6 to 1.0.8 pointless version (looks like the
# reindexing operators have changed in the latest version... was that a bug?)
# 
# FIXED 11/AUG/06 for I222 (example set: 13140) the GroupName comes out
# as P 2 2 2 not I 2 2 2 - this needs to be coded for somehow - is this
# correct? Check with Phil E. The pointgroup probably is correct, but I
# will need to know the correct centring to get the reflections correctly
# organized. :o( Just figure it out in the code here... Done.
# 
# FIXME perhaps 11/AUG/06 beware - this looks like pointless will now 
# also perform axis reindexing if the spacegroup looks like something
# like P 2 21 21 - it will reindex l,h,k - beware of this because that
# will change all of the unit cell parameters and may not be a desirable
# thing to have. Can this be switched off? Have emailed pre - for the
# moment just be aware of this!

import os
import sys

import xml.dom.minidom

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Pointless(DriverType = None):
    '''A factory for PointlessWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class PointlessWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Pointless, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.setExecutable('pointless-1.0.8')

            self._pointgroup = None
            self._spacegroup = None
            self._reindex_matrix = None
            self._confidence = 0.0

        def decide_pointgroup(self):
            '''Decide on the correct pointgroup for hklin.'''

            self.checkHklin()

            self.setTask('Computing the correct pointgroup for %s' % \
                         self.getHklin())

            # FIXME this should probably be a standard CCP4 keyword

            self.addCommand_line('xmlout')
            self.addCommand_line('pointless.xml')

            self.start()

            self.close_wait()

            # check for errors
            self.check_for_errors()

            # check the CCP4 status - oh, there isn't one!
            # FIXME I manually need to check for errors here....

            # parse the XML file for the information I need...
            # FIXME this needs documenting - I am using xml.dom.minidom.

            # FIXME 2: This needs extracting to a self.parse_pointless_xml()
            # or something.

            xml_file = os.path.join(self.getWorking_directory(),
                                    'pointless.xml')

            dom = xml.dom.minidom.parse(xml_file)

            best = dom.getElementsByTagName('BestSolution')[0]
            self._pointgroup = best.getElementsByTagName(
                'GroupName')[0].childNodes[0].data
            self._confidence = float(best.getElementsByTagName(
                'Confidence')[0].childNodes[0].data)
            self._totalprob = float(best.getElementsByTagName(
                'TotalProb')[0].childNodes[0].data)
            self._reindex_matrix = map(float, best.getElementsByTagName(
                'ReindexMatrix')[0].childNodes[0].data.split())
            self._reindex_operator = best.getElementsByTagName(
                'ReindexOperator')[0].childNodes[0].data.strip()

            # this bit is to figure out the correct spacegroup to
            # reindex into (see FIXME above for 11/AUG/06)

            spacegroups = []

            spags = dom.getElementsByTagName('SpacegroupList')[0]
            
            # work through these to compute the probable solution

            for s in spags.getElementsByTagName('Spacegroup'):
                name = s.getElementsByTagName(
                    'SpacegroupName')[0].childNodes[0].data.strip()
                reindex_op = s.getElementsByTagName(
                    'ReindexOperator')[0].childNodes[0].data.strip()

                if reindex_op == self._reindex_operator:
                    break

            self._spacegroup = name


            return 'ok'

        def getReindex_matrix(self):
            return self._reindex_matrix

        def getPointgroup(self):
            return self._spacegroup

        def getConfidence(self):
            return self._confidence
            
    return PointlessWrapper()

if __name__ == '__main__':

    # then run some sort of test

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    xia2core = os.environ['XIA2CORE_ROOT']

    hklin = os.path.join(xia2core,
                         'Data', 'Test', 'Mtz', '12287_1_E1.mtz')

    if len(sys.argv) > 1:
        hklin = sys.argv[1]

    p = Pointless()

    p.setHklin(hklin)

    p.decide_pointgroup()

    print 'Correct pointgroup: %s' % p.getPointgroup()
    print 'Reindexing matrix: ' + \
          '%4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f' % \
          tuple(p.getReindex_matrix())
    print 'Confidence: %f' % p.getConfidence()

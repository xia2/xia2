#!/usr/bin/env python
# Pointless.py
# Maintained by G.Winter
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
            self.setExecutable('pointless-1.0.5')

            self._pointgroup = None
            self._reindex_matrix = None

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
            self._reindex_matrix = map(float, best.getElementsByTagName(
                'ReindexMatrix')[0].childNodes[0].data.split())

            return 'ok'

        def getReindex_matrix(self):
            return self._reindex_matrix

        def getPointgroup(self):
            return self._pointgroup
            
    return PointlessWrapper()

if __name__ == '__main__':

    # then run some sort of test

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    xia2core = os.environ['XIA2CORE_ROOT']

    hklin = os.path.join(xia2core,
                         'Data', 'Test', 'Mtz', '12287_1_E1.mtz')

    p = Pointless()

    p.setHklin(hklin)

    p.decide_pointgroup()

    print 'Correct pointgroup: %s' % p.getPointgroup()
    print 'Reindexing matrix: ' + \
          '%4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f' % \
          tuple(p.getReindex_matrix())

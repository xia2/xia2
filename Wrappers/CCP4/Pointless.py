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
# This is still a FIXME there is actually a bug in pointless! The reflection
# file is written out in P222. Contacted pre@mrc-lmb.ac.uk about this, will
# be interesting to see what the result is. Upshot is that the code below
# to get the correct spacegroup out isn't needed. Theory states that this
# should be fixed in pointless-1.0.9. This is indeed fixed, need to therefore
# update the version herein and also remove the guesswork code I added
# as a workaround.
# 
# FIXME perhaps 11/AUG/06 beware - this looks like pointless will now 
# also perform axis reindexing if the spacegroup looks like something
# like P 2 21 21 - it will reindex l,h,k - beware of this because that
# will change all of the unit cell parameters and may not be a desirable
# thing to have. Can this be switched off? Have emailed pre - for the
# moment just be aware of this!
# 
# FIXME 15/AUG/06 pointless is a little over keen with respect to the 
#                 pointgroup for the 1VR9 native data. It is therefore
#                 worth adding an option to try scaling in all of the
#                 "legal" spacegroups (with +ve score) to check that the
#                 assertions pointless makes about the symmetry
#                 are correct.
# 
# FIXED 22/AUG/06 update to the latest version of pointless which needs
#                 to read command line input. "systematicabsences off".
# 
# FIXED 23/OCT/06 with TS03/PEAK data (1vpj) the "most likely" solution comes
#                 out as C222, but the solution with the highest NetZc is the
#                 correct one of P 4/mmm. Need therefore to be able to get 
#                 this information from the output file. Perhaps need to 
#                 balance likelihood against NetZc? Perhaps it is simply
#                 a problem with this version of pointless? This is not
#                 fixed in version 1.1.0.5! :o(
#
# FIXME 24/OCT/06 need to plumb this into the indexer solution management
#                 system so that in the case of 1VR9/TS01 the "correct"
#                 pointgroup of I222 is not specified, as it has already
#                 been eliminated at the processing stage.
# 
# FIXED 16/NOV/05 also want to run this in a manner which will give a correct
#                 spacegroup from the systematic absences once the pointgroup
#                 is correctly set...
#

import os
import sys
import math

import xml.dom.minidom

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

from Handlers.Streams import Chatter, Science

# this was rather complicated - now simpler!
from lib.SymmetryLib import lauegroup_to_lattice

def Pointless(DriverType = None):
    '''A factory for PointlessWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class PointlessWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Pointless, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            
            # FIXME 08/SEP/06 this needs updating to
            # version 1.1.0.4 - done
            self.set_executable('pointless-1.1.0.4')

            self._input_laue_group = None

            self._pointgroup = None
            self._spacegroup = None
            self._reindex_matrix = None
            self._confidence = 0.0
            self._hklref = None

            # space to store all possible solutions, to allow discussion of
            # the correct lattice with the indexer... this should be a
            # list containing e.g. 'tP'
            self._possible_lattices = []

            self._lattice_to_laue = { }

            # all "likely" spacegroups...
            self._likely_spacegroups = []

        def set_hklref(self, hklref):
            self._hklref = hklref
            return

        def get_hklref(self):
            return self._hklref

        def check_hklref(self):
            if self._hklref is None:
                raise RuntimeError, 'hklref not defined'
            if not os.path.exists(self._hklref):
                raise RuntimeError, 'hklref %s does not exist' % self._hklref

        def set_correct_lattice(self, lattice):
            '''In a rerunning situation, set the correct lattice, which will
            assert a correct lauegroup based on the previous run of the
            program...'''

            if self._lattice_to_laue == { }:
                raise RuntimeError, 'no lattice to lauegroup mapping'

            if not self._lattice_to_laue.has_key(lattice):
                raise RuntimeError, 'lattice %s not possible' % lattice

            self._input_laue_group = self._lattice_to_laue[lattice]

            return

        def decide_pointgroup(self):
            '''Decide on the correct pointgroup for hklin.'''

            self.check_hklin()

            self.set_task('Computing the correct pointgroup for %s' % \
                          self.get_hklin())

            # FIXME this should probably be a standard CCP4 keyword

            self.add_command_line('xmlout')
            self.add_command_line('pointless.xml')

            if self._hklref:
                self.add_command_line('hklref')
                self.add_command_line(self._hklref)

            self.start()

            # change 22/AUG/06 add this command to switch off systematic
            # absence analysis of the spacegroups.
            
            self.input('systematicabsences off')

            # change 23/OCT/06 if there is an input laue group, use this
            if self._input_laue_group:
                self.input('lauegroup %s' % self._input_laue_group)

            self.close_wait()

            # check for errors
            self.check_for_errors()

            
            # check the CCP4 status - oh, there isn't one!
            # FIXME I manually need to check for errors here....

            hklin_spacegroup = ''

            for o in self.get_all_output():

                if 'Spacegroup from HKLIN file' in o:
                    hklin_spacegroup = o.split(':')[-1].strip()

                if 'No alternative indexing possible' in o:
                    # then the XML file will be broken - no worries...

                    self._pointgroup = hklin_spacegroup
                    self._confidence = 1.0
                    self._totalprob = 1.0
                    self._reindex_matrix = [1.0, 0.0, 0.0,
                                            0.0, 1.0, 0.0,
                                            0.0, 0.0, 1.0]
                    self._reindex_operator = 'h,k,l'

                    return 'ok'

                if '**** Incompatible symmetries ****' in o:
                    # then there is an important error in here I need
                    # to trap...
                    raise RuntimeError, \
                          'reindexing against a reference with ' + \
                          'different symmetry'

            # parse the XML file for the information I need...
            # FIXME this needs documenting - I am using xml.dom.minidom.

            # FIXME 2: This needs extracting to a self.parse_pointless_xml()
            # or something.

            xml_file = os.path.join(self.get_working_directory(),
                                    'pointless.xml')

            if not self._hklref:

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

            else:

                # if we have provided a HKLREF input then the xml output
                # is changed...
    
                dom = xml.dom.minidom.parse(xml_file)
                
                best = dom.getElementsByTagName('IndexScores')[0]

                hklref_pointgroup = ''

                # FIXME need to get this from the reflection file HKLREF
                reflection_file_elements = dom.getElementsByTagName(
                    'ReflectionFile')
                
                for rf in reflection_file_elements:
                    stream = rf.getAttribute('stream')
                    if stream == 'HKLREF':
                        hklref_pointgroup = rf.getElementsByTagName(
                            'SpacegroupName')[0].childNodes[0].data.strip()
                        # Chatter.write('HKLREF pointgroup is %s' % \
                        # hklref_pointgroup)

                if hklref_pointgroup == '':
                    # should raise an exception here
                    pass

                self._pointgroup = hklref_pointgroup

                self._confidence = 1.0
                self._totalprob = 1.0
                
                index = best.getElementsByTagName('Index')[0]

                self._reindex_matrix = map(float, index.getElementsByTagName(
                    'ReindexMatrix')[0].childNodes[0].data.split())
                self._reindex_operator = index.getElementsByTagName(
                    'ReindexOperator')[0].childNodes[0].data.strip()

            # while we're here also inspect the NetZc information (see
            # FIXME for 23/OCT/06) to make sure that pointless has made
            # a sensible decision.

            # if it looks like it has not, then the best thing to do
            # is to select the "correct" Laue group (by my estimation)
            # and then feed this into pointless through the e.g.
            # "lauegroup P4/mmm" input record. Have also reported this
            # to Phil Evans as a bug.

            best_netzc = 0.0
            best_likelihood = 0.0
            best_laue = ''
            best_r = 0.0
            best_delta = 0.0

            # do not want to do this is we have specified the correct
            # pointgroup either through the command input or implicitly
            # through providing a reference set..
            
            if not self._input_laue_group and not self._hklref:

                scorelist = dom.getElementsByTagName('LaueGroupScoreList')[0]
                scores = scorelist.getElementsByTagName('LaueGroupScore')

                lauegroups = { }
                netzcs = { }
                likelihoods = { }
                
                correct_netzc = 0.0
                correct_laue = ''
                correct_r = 0.0
                correct_delta = 0.0

                for s in scores:
                    number = int(s.getElementsByTagName(
                        'number')[0].childNodes[0].data)
                    lauegroup = s.getElementsByTagName(
                        'LaueGroupName')[0].childNodes[0].data
                    reindex = s.getElementsByTagName(
                        'ReindexOperator')[0].childNodes[0].data
                    netzc = float(s.getElementsByTagName(
                        'NetZCC')[0].childNodes[0].data)
                    likelihood = float(s.getElementsByTagName(
                        'Likelihood')[0].childNodes[0].data)
                    r_merge = float(s.getElementsByTagName(
                        'R')[0].childNodes[0].data)
                    delta = float(s.getElementsByTagName(
                        'CellDelta')[0].childNodes[0].data)

                    # record this as a possible lattice... if it's Z score
                    # is positive, anyway

                    lattice = lauegroup_to_lattice(lauegroup)
                    if not lattice in self._possible_lattices:
                        if netzc > 0.0:
                            self._possible_lattices.append(lattice)
                            self._lattice_to_laue[lattice] = lauegroup
                    
                    # check to see if this is the "correct" answer - if it
                    # is (and it should be the first!) then record the NetZc
                    
                    if number == 1:
                        if math.fabs(likelihood -
                                     self._totalprob) < 0.001 and \
                                     reindex == self._reindex_operator:

                            correct_netzc = netzc
                            correct_laue = lauegroup
                            correct_r = r_merge
                            correct_delta = delta

                        else:
                            raise RuntimeError, 'something horribly wrong'

                    else:
                        # otherwise, have a look at the likelihood - if it is 
                        # within 0.1 of the "correct" answer, have a look at
                        # the NetZc and if it is much better then consider
                        # that the other solution may indeed be correct.
                    
                        if math.fabs(likelihood - self._totalprob) < 0.1:
                            if netzc - correct_netzc > 1.0:
                                # this is perhaps more likely?
                                if netzc > best_netzc:
                                    Science.write(
                                        'Found likely solution with ' + \
                                        'better Z score')
                                      
                                    best_netzc = netzc
                                    best_laue = lauegroup
                                    best_likelihood = likelihood
                                    best_r = r_merge

                        # also contemplate different solutions based on
                        # the Rmerge - for instance (TS01 NATIVE) it may be
                        # the case that the R merge is a factor of two
                        # better for a pretty likely solution
                        # use sqrt(3.0) as a "magic factor" ;o) - oh
			# this doesn't work very well - use 1.5!

                        # FIXME 08/NOV/06 will have to do better at this
                        # - the R merge kills the correct solution (and it
                        # is needed for TS01 NATIVE...) - have to look at
                        # the cell delta as well - for TS03 LREM this is 0.0,
                        # for TS01 NATIVE this is around 0.5... require delta
                        # also measurable (e.g. not exactly 0.0)

                        if math.fabs(likelihood - self._totalprob) < 0.1:
                            if correct_r / r_merge > 1.5 and \
                                   correct_delta > 0.1:
                                if netzc > 0.0:
                                    # this is perhaps more likely?
                                    Science.write(
                                        'Found likely solution with ' + \
                                        'better Rmerge: %4.2f vs. %4.2f' % \
                                        (r_merge, correct_r))
                                    Science.write(
                                        'and cell delta: %4.2f vs. %4.2f' % \
                                        (delta, correct_delta))
                                    
                                    best_netzc = netzc
                                    best_laue = lauegroup
                                    best_likelihood = likelihood
                                    best_r = r_merge
                                    best_delta = delta

            if best_laue:
                # the solution pointless gave is probably wrong!
                Science.write(
                    'I disagree with pointless over the correct solution')
                Science.write(
                    '%s [%4.2f] vs. %s [%4.2f]' % \
                    (correct_laue, self._totalprob,
                     best_laue, best_likelihood))
                Science.write('NetZc: %5.2f vs. %5.2f' % \
                              (correct_netzc, best_netzc))

                # remember this!
                self._input_laue_group = best_laue

                Science.write(
                    'Re-running with the correct pointgroup asserted')
                return self.decide_pointgroup()

            # this bit is to figure out the correct spacegroup to
            # reindex into (see FIXME above for 11/AUG/06)
            # see FIXME for 22/AUG this should no longer be needed
            # since the systematic absence stuff is now switched off...

            # spacegroups = []

            # spags = dom.getElementsByTagName('SpacegroupList')[0]
            
            # work through these to compute the probable solution

            # for s in spags.getElementsByTagName('Spacegroup'):
            # name = s.getElementsByTagName(
            # 'SpacegroupName')[0].childNodes[0].data.strip()
            # reindex_op = s.getElementsByTagName(
            # 'ReindexOperator')[0].childNodes[0].data.strip()

            # if reindex_op == self._reindex_operator:
            # break

            # self._spacegroup = name


            return 'ok'

        def decide_spacegroup(self):
            '''Given data indexed in the correct pointgroup, have a
            guess at the spacegroup.'''

            self.check_hklin()

            self.set_task('Computing the correct spacegroup for %s' % \
                          self.get_hklin())

            # FIXME this should probably be a standard CCP4 keyword

            self.add_command_line('xmlout')
            self.add_command_line('pointless.xml')

            self.start()

            self.input('lauegroup hklin')

            self.close_wait()

            # check for errors
            self.check_for_errors()

            hklin_spacegroup = ''

            xml_file = os.path.join(self.get_working_directory(),
                                    'pointless.xml')

            dom = xml.dom.minidom.parse(xml_file)
            
            sg_list = dom.getElementsByTagName('SpacegroupList')[0]
            sg_node = sg_list.getElementsByTagName('Spacegroup')[0]
            best_prob = float(sg_node.getElementsByTagName(
                'TotalProb')[0].childNodes[0].data.strip())

            # FIXME 21/NOV/06 in here record a list of valid spacegroups
            # (that is, those which are as likely as the most likely)
            # for later use...

            self._spacegroup = sg_node.getElementsByTagName(
                'SpacegroupName')[0].childNodes[0].data.strip()
            self._spacegroup_reindex_operator = sg_node.getElementsByTagName(
                'ReindexOperator')[0].childNodes[0].data.strip()

            # get a list of "equally likely" spacegroups

            for node in sg_list.getElementsByTagName('Spacegroup'):
                prob = float(node.getElementsByTagName(
                    'TotalProb')[0].childNodes[0].data.strip())
                name = node.getElementsByTagName(
                    'SpacegroupName')[0].childNodes[0].data.strip()

                if math.fabs(prob - best_prob) < 0.01:
                    # this is jolly likely!
                    self._likely_spacegroups.append(name)

            return 'ok'

        def get_reindex_matrix(self):
            return self._reindex_matrix

        def get_reindex_operator(self):
            return self._reindex_operator

        def get_pointgroup(self):
            # FIXED on 22/AUG/06 this was spacegroup
            return self._pointgroup

        def get_spacegroup(self):
            return self._spacegroup

        def get_spacegroup_reindex_operator(self):
            return self._spacegroup_reindex_operator

        def get_likely_spacegroups(self):
            return self._likely_spacegroups

        def get_confidence(self):
            return self._confidence

        def get_possible_lattices(self):
            return self._possible_lattices
            
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

    p.set_hklin(hklin)

    pointgroup = True

    if pointgroup:
        p.decide_pointgroup()
        
        print 'Correct pointgroup: %s' % p.get_pointgroup()
        print 'Reindexing matrix: ' + \
              '%4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f' % \
              tuple(p.get_reindex_matrix())
        print 'Confidence: %f' % p.get_confidence()

    else:
        p.decide_spacegroup()
        
        print 'Correct spacegroup: %s' % p.get_spacegroup()
        print 'Reindex operator: %s' % p.get_spacegroup_reindex_operator()

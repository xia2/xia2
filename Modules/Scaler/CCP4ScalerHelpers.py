#!/usr/bin/env python
# CCP4ScalerHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 3rd November 2006
# 
# Helpers for the "CCP4" Scaler implementation - this contains little
# functions which wrap the wrappers which are needed. It will also contain
# small functions for computing e.g. resolution limits.
#

import os
import math

from Wrappers.CCP4.Mtzdump import Mtzdump
from Wrappers.CCP4.Rebatch import Rebatch
from lib.bits import auto_logfiler
from Handlers.Streams import Chatter, Debug
from Handlers.Files import FileHandler
from Handlers.Flags import Flags
from Experts.ResolutionExperts import remove_blank

############ JIFFY FUNCTIONS #################

def _resolution_estimate(ordered_pair_list, cutoff):
    '''Come up with a linearly interpolated estimate of resolution at
    cutoff cutoff from input data [(resolution, i_sigma)].'''

    x = []
    y = []

    for o in ordered_pair_list:
        x.append(o[0])
        y.append(o[1])

    if max(y) < cutoff:
        # there is no resolution where this exceeds the I/sigma
        # cutoff
        return -1.0

    # this means that there is a place where the resolution cutof
    # can be reached - get there by working backwards

    x.reverse()
    y.reverse()

    if y[0] >= cutoff:
        # this exceeds the resolution limit requested
        return x[0]

    j = 0
    while y[j] < cutoff:
        j += 1

    resolution = x[j] + (cutoff - y[j]) * (x[j - 1] - x[j]) / \
                 (y[j - 1] - y[j])

    return resolution

def _prepare_pointless_hklin(working_directory,
                             hklin,
                             phi_width):
    '''Prepare some data for pointless - this will take only 180 degrees
    of data if there is more than this (through a "rebatch" command) else
    will simply return hklin.'''

    # also remove blank images?

    if not Flags.get_microcrystal():

        Debug.write('Excluding blank images')

        hklout = os.path.join(
            working_directory,
            '%s_noblank.mtz' % (os.path.split(hklin)[-1][:-4]))
    
        FileHandler.record_temporary_file(hklout)

        hklin = remove_blank(hklin, hklout)
    
    # find the number of batches

    md = Mtzdump()
    md.set_working_directory(working_directory)
    auto_logfiler(md)
    md.set_hklin(hklin)
    md.dump()

    batches = max(md.get_batches()) - min(md.get_batches())

    phi_limit = 180

    if batches * phi_width < phi_limit:
        return hklin

    hklout = os.path.join(
        working_directory,
        '%s_prepointless.mtz' % (os.path.split(hklin)[-1][:-4]))

    rb = Rebatch()
    rb.set_working_directory(working_directory)
    auto_logfiler(rb)
    rb.set_hklin(hklin)
    rb.set_hklout(hklout)

    first = min(md.get_batches())
    last = first + int(phi_limit / phi_width)

    Debug.write('Preparing data for pointless - %d batches (%d degrees)' % \
                ((last - first), phi_limit))

    rb.limit_batches(first, last)

    # we will want to delete this one exit
    FileHandler.record_temporary_file(hklout)

    return hklout

def _fraction_difference(value, reference):
    '''How much (what %age) does value differ to reference?'''

    if reference == 0.0:
        return value

    return math.fabs((value - reference) / reference)

from Wrappers.CCP4.Pointless import Pointless as _Pointless

############### HELPER CLASS #########################

class CCP4ScalerHelper:
    '''A class to help the CCP4 Scaler along a little.'''

    def __init__(self):
        self._working_directory = os.getcwd()
        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def Pointless(self):
        '''Create a Pointless wrapper from _Pointless - and set the
        working directory and log file stuff as a part of this...'''
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def pointless_indexer_jiffy(self, hklin, indexer):
        '''A jiffy to centralise the interactions between pointless
        (in the blue corner) and the Indexer, in the red corner.'''

        need_to_return = False

        pointless = self.Pointless()
        pointless.set_hklin(hklin)
        pointless.decide_pointgroup()
        
        if indexer:
            rerun_pointless = False

            possible = pointless.get_possible_lattices()

            correct_lattice = None

            Debug.write('Possible lattices (pointless):')
            lattices = ''
            for lattice in possible:
                lattices += '%s ' % lattice
            Debug.write(lattices)

            for lattice in possible:
                state = indexer.set_indexer_asserted_lattice(lattice)
                if state == 'correct':
                            
                    Debug.write(
                        'Agreed lattice %s' % lattice)
                    correct_lattice = lattice
                    
                    break
                
                elif state == 'impossible':
                    Debug.write(
                        'Rejected lattice %s' % lattice)
                    
                    rerun_pointless = True
                    
                    continue
                
                elif state == 'possible':
                    Debug.write(
                        'Accepted lattice %s ...' % lattice)
                    Debug.write(
                        '... will reprocess accordingly')
                    
                    need_to_return = True
                    
                    correct_lattice = lattice
                    
                    break

            if correct_lattice == None:
                # this is an odd turn of events which may have been brought
                # about by the user assigning a lower spacegroup than is
                # true, which will give it a negative Z score but it may
                # stull be "true".

                correct_lattice = indexer.get_indexer_lattice()
                rerun_pointless = True
                
                Debug.write(
                    'No solution found: assuming lattice from indexer')
                    
            if rerun_pointless:
                pointless.set_correct_lattice(correct_lattice)
                pointless.decide_pointgroup()

        Debug.write('Pointless analysis of %s' % pointless.get_hklin())

        pointgroup = pointless.get_pointgroup()
        reindex_op = pointless.get_reindex_operator()
        
        Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        return pointgroup, reindex_op, need_to_return
        
# Sweep info class to replace dictionary... #884

class SweepInformation:

    def __init__(self, integrater):

        self._project_info = integrater.get_integrater_project_info()
        self._sweep_name = integrater.get_integrater_sweep_name()
        self._integrater = integrater
        self._batches = integrater.get_integrater_batches()

        self._image_to_epoch = integrater.get_integrater_sweep(                
            ).get_image_to_epoch()
        self._image_to_dose = { }

        return

    def get_project_info(self):
        return self._project_info

    def get_sweep_name(self):
        return self._sweep_name

    def get_integrater(self):
        return self._integrater
        
    def get_batches(self):
        return self._batches

    def get_batch_range(self):
        return min(self._batches), max(self._batches)

    def get_header(self):
        return self._integrater.get_header()

    def get_template(self):
        return self._integrater.get_template()

    def set_dose_information(self, epoch_to_dose):
        for i in self._image_to_epoch:
            e = self._image_to_epoch[i]
            d = epoch_to_dose[e]
            self._image_to_dose[i] = d

        return

    def get_circle_resolution(self):
        '''Get the resolution of the inscribed circle used for this sweep.'''

        header = self._integrater.get_header()
        wavelength = self._integrater.get_wavelength()

        detector_width = header['size'][0] * header['pixel'][0] 
        detector_height = header['size'][1] * header['pixel'][1]

        distance = self._integrater.get_integrater_indexer(
            ).get_indexer_distance()

        beam = self._integrater.get_integrater_indexer(
            ).get_indexer_beam()

        radius = min([beam[0], detector_width - beam[0],
                      beam[1], detector_height - beam[1]])
        
        theta = 0.5 * math.atan(radius / distance)

        return wavelength / (2 * math.sin(theta))
        
    def get_integrater_resolution(self):
        return self._integrater.get_integrater_high_resolution()

    def get_reflections(self):
        return self._integrater.get_integrater_reflections()

class SweepInformationHandler:

    def __init__(self, epoch_to_integrater):
        
        self._sweep_information = { }

        for epoch in epoch_to_integrater:
            self._sweep_information[epoch] = SweepInformation(
                epoch_to_integrater[epoch])

        self._first = sorted(self._sweep_information)[0]

        return

    def get_epochs(self):
        return sorted(self._sweep_information)

    def get_sweep_information(self, epoch):
        return self._sweep_information[epoch]

    def get_project_info(self):
        si = self._sweep_information(self._first)
        pname, xname, dname = si.get_project_information()

        for e in self._sweep_information:
            si = self._sweep_information[e]

            assert(e.get_project_info()[0] == pname)
            assert(e.get_project_info()[1] == xname)
        
        return pname, xname

    
        

        


#!/usr/bin/env python
# CCP4ScalerImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 21/SEP/06
# 
# An implementation of the Scaler interface using CCP4 programs.
# 
# FIXED 21/SEP/06 this needs to have a working directory property
#                 so we can specify where it is being run... 
#                 This should also be inherited by the "child" jobs...
# 
# FIXME 25/SEP/06 need to include pointgroup determination in the pipeline
#                 though this will begin to impact on the lattice management
#                 stuf in XCrystal.

import os
import sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

# the wrappers that this will use
from Wrappers.CCP4.Scala import Scala
from Wrappers.CCP4.Sortmtz import Sortmtz
from Wrappers.CCP4.Mtzdump import Mtzdump
# FIXME this needs implementing!
# from Wrappers.CCP4.Truncate import Truncate
from Wrappers.CCP4.Rebatch import Rebatch
from Wrappers.CCP4.Reindex import Reindex
from Wrappers.CCP4.Pointless import Pointless

from Handlers.Streams import Chatter

# jiffys
from lib.Guff import is_mtz_file, nifty_power_of_ten

class CCP4Scaler(Scaler):
    '''An implementation of the Scaler interface using CCP4 programs.'''

    def __init__(self):
        Scaler.__init__(self)

        self._working_directory = os.getcwd()

        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def _scale(self):
        '''Perform all of the operations required to deliver the scaled
        data.'''

        # first gather reflection files - seeing as we go along if any
        # of them need transforming to MTZ format, e.g. from d*TREK
        # format. N.B. this will also require adding the project,
        # crystal, dataset name from the parent integrater.

        input_information = { }

        for key in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[key]
            pname, xname, dname = intgr.get_integrater_project_information()
            input_information[key] = {
                'hklin':intgr.get_integrater_reflections(),
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'batches':intgr.get_integrater_batches()}

        # next check through the reflection files that they are all MTZ
        # format - if not raise an exception.
        # FIXME this should include the conversion to MTZ.
        for key in input_information.keys():
            if not is_mtz_file(input_information[key]['hklin']):
                raise RuntimeError, \
                      'input file %s not MTZ format' % \
                      input_information[key]['hklin']

        # then check that the unit cells &c. in these reflection files
        # correspond to those rescribed in the indexers belonging to the
        # parent integraters.

        # at this stage (see FIXME from 25/SEP/06) I need to run pointless
        # to assess the likely pointgroup. This, unfortunately, will need to
        # tie into the .xinfo hierarchy, as the crystal lattice management
        # takes place in there...
        # also need to make sure that the results from each sweep match
        # up...

        for key in input_information.keys():
            pl = Pointless()
            hklin = input_information[key]['hklin']
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            pl.set_working_directory(self.get_working_directory())
            pl.set_hklin(hklin)
            pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % hklin)

            # FIXME here - do I need to contemplate reindexing
            # the reflections? if not, don't bother - could be an
            # expensive waste of time for large reflection files
            # (think Ed Mitchell data...)

            # get the correct pointgroup
            poingroup = pl.get_pointgroup()

            # and reindexing operation
            reindex_op = pl.get_reindex_operator()

            Chatter.write('Pointgroup: %s (%s)' % (poingroup, reindex_op))

            # perform a reindexing operation
            ri = Reindex()
            ri.set_hklin(hklin)
            ri.set_hklout(hklout)
            ri.set_spacegroup(pointgroup)
            ri.set_operator(reindex_op)
            ri.reindex()

            # record the change in reflection file...
            input_information[key]['hklin'] = hklout
            

        max_batches = 0
        
        for key in input_information.keys():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            batches = input_information[key]['batches']
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1
            
            hklin = input_information[key]['hklin']

            md = Mtzdump()
            md.set_working_directory(self.get_working_directory())
            md.set_hklin(hklin)
            md.dump()

            # FIXME assert that there will only be one dataset in this
            # reflection file

            datasets = md.get_datasets()

            Chatter.write('In reflection file %s found:' % hklin)
            for d in datasets:
                Chatter.write('... %s' % d)
            
            dataset_info = md.get_dataset_info(datasets[0])

            # FIXME should also confirm the batch numbers from this
            # reflection file...

            # now make the comparison - FIXME this needs to be implemented
            # FIXME also - if the pname, xname, dname is not defined by
            # this time, make a note of this so that it can be included
            # at a later stage.

        max_batches = nifty_power_of_ten(max_batches)
    
        # then rebatch the files, to make sure that the batch numbers are
        # in the same order as the epochs of data collection.

        keys = input_information.keys()
        keys.sort()

        # need to check that the batches are all sensible numbers
        # so run rebatch on them! note here that we will need new
        # MTZ files to store the output...

        counter = 0

        common_pname = input_information[keys[0]]['pname']
        common_xname = input_information[keys[0]]['xname']
        common_dname = input_information[keys[0]]['dname']

        # FIXME the checks in here need to be moved to an earlier
        # stage in the processing

        for key in keys:
            rb = Rebatch()
            rb.set_working_directory(self.get_working_directory())

            hklin = input_information[key]['hklin']

            pname = input_information[key]['pname']
            if common_pname != pname:
                raise RuntimeError, 'all data must have a common project name'
            xname = input_information[key]['xname']
            if common_xname != xname:
                raise RuntimeError, \
                      'all data for scaling must come from one crystal'
            dname = input_information[key]['dname']
            if common_dname != dname:
                common_dname = None

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_%s_%d.mtz' % \
                                  (pname, xname, dname, counter))

            rb.set_hklin(hklin)
            rb.set_first_batch(counter * max_batches + 1)
            rb.set_hklout(hklout)

            new_batches = rb.rebatch()

            # update the "input information"

            input_information[key]['hklin'] = hklout
            input_information[key]['batches'] = new_batches

            # update the counter & recycle

            counter += 1

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = Sortmtz()
        s.write_log_file(os.path.join(self.get_working_directory(),
                                      'sortmtz.log'))
        s.set_working_directory(self.get_working_directory())

        s.set_hklout(os.path.join(self.get_working_directory(),
                                  '%s_%s_sorted.mtz' % \
                                  (common_pname, common_xname)))

        for key in keys:
            s.add_hklin(input_information[key]['hklin'])

        s.sort()


        # then perform some scaling - including any parameter fiddling
        # which is required.

        # FIXME in here I need to implement "proper" scaling...

        sc = Scala()
        sc.set_working_directory(self.get_working_directory())

        sc.write_log_file(os.path.join(self.get_working_directory(),
                                       'scala.log'))

        sc.set_hklin(s.get_hklout())

        # this will require first sorting out the batches/runs, then
        # deciding what the "standard" wavelength/dataset is, then
        # combining everything appropriately...

        for key in keys:
            input = input_information[key]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (common_pname, common_xname)))
        
        sc.set_anomalous()
        sc.set_tails()

        sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        # finally put all of the results "somewhere useful"
        
        self._scalr_statistics = data
        self._scalr_scaled_reflection_fikles = sc.get_hklout()

        return

    

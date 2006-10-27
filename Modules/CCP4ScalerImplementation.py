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
# 
# FIXME 27/SEP/06 need to define a reference wavelength for the anomalous
#                 dispersive differences. This is best assigned at this 
#                 level as the wavelength with the smallest |f'| + |f''|
#                 or something:
# 
#                 BASE keyword to scala - BASE [crystal xname] dataset dname
# 
#                 This defaults to the data set with the shortest wavelength.
#  
# FIXME 27/OCT/06 need to make sure that the pointless run in here does not
#                 select a symmetry for the crystal which has been eliminated
#                 already...
# 
# 

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
from Wrappers.CCP4.Truncate import Truncate
from Wrappers.CCP4.Rebatch import Rebatch
from Wrappers.CCP4.Reindex import Reindex
from Wrappers.CCP4.Mtz2various import Mtz2various
from Wrappers.CCP4.Cad import Cad
from Wrappers.CCP4.Pointless import Pointless

from Handlers.Streams import Chatter

# jiffys
from lib.Guff import is_mtz_file, nifty_power_of_ten, auto_logfiler

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

        # FIXME 27/OCT/06 need a hook in here to the integrater->indexer
        # to inspect the lattices which have ben contemplated (read tested)
        # because it is quite possible that pointless will come up with
        # a solution which has already been eliminated in the data reduction
        # (e.g. TS01 native being reindexed to I222.)
        
        for key in input_information.keys():
            pl = Pointless()
            hklin = input_information[key]['hklin']
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            pl.set_working_directory(self.get_working_directory())
            pl.set_hklin(hklin)

            # write a pointless log file...
            auto_logfiler(pl)
            pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % hklin)

            # FIXME here - do I need to contemplate reindexing
            # the reflections? if not, don't bother - could be an
            # expensive waste of time for large reflection files
            # (think Ed Mitchell data...)

            # get the correct pointgroup
            pointgroup = pl.get_pointgroup()

            # and reindexing operation
            reindex_op = pl.get_reindex_operator()

            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            # perform a reindexing operation
            ri = Reindex()
	    ri.set_working_directory(self.get_working_directory())
            ri.set_hklin(hklin)
            ri.set_hklout(hklout)
            ri.set_spacegroup(pointgroup)
            ri.set_operator(reindex_op)
            auto_logfiler(ri)
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
            auto_logfiler(md)
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

        Chatter.write('Biggest sweep has %d batches' % max_batches)
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

            auto_logfiler(rb)
            new_batches = rb.rebatch()

            # update the "input information"

            input_information[key]['hklin'] = hklout
            input_information[key]['batches'] = new_batches

            # update the counter & recycle

            counter += 1

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = Sortmtz()
        s.set_working_directory(self.get_working_directory())

        s.set_hklout(os.path.join(self.get_working_directory(),
                                  '%s_%s_sorted.mtz' % \
                                  (common_pname, common_xname)))

        for key in keys:
            s.add_hklin(input_information[key]['hklin'])

        auto_logfiler(s)
        s.sort()

        # then perform some scaling - including any parameter fiddling
        # which is required.

        # FIXME in here I need to implement "proper" scaling...

        sc = Scala()
        sc.set_working_directory(self.get_working_directory())
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

        auto_logfiler(sc)
        sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        # finally put all of the results "somewhere useful"
        
        self._scalr_statistics = data

        # FIXME this is not correct for multi-wavelength data...
        # it should be now!

        scaled_reflection_files = sc.get_scaled_reflection_files()
        self._scalr_scaled_reflection_files = { }
        
        # compute a "standard unit cell" - FIXME perhaps - looks like
        # sortmtz will already assign somehow a standard unit cell -
        # interesting!

        # convert reflection files to .sca format - use mtz2various for this

        self._scalr_scaled_reflection_files['sca'] = { }
        for key in scaled_reflection_files:
            file = scaled_reflection_files[key]
            m2v = Mtz2various()
            m2v.set_working_directory(self.get_working_directory())
            auto_logfiler(m2v)
            m2v.set_hklin(file)
            m2v.set_hklout('%s.sca' % file[:-4])
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][
                key] = '%s.sca' % file[:-4]

        # convert I's to F's in Truncate

        self._scalr_scaled_reflection_files['mtz'] = { }
        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            t = Truncate()
            t.set_working_directory(self.get_working_directory())
            auto_logfiler(t)
            t.set_hklin(file)
            # this is tricksy - need to really just replace the last
            # instance of this string FIXME 27/OCT/06

            hklout = ''
            for path in os.path.split(file)[:-1]:
                hklout = os.path.join(hklout, path)
            hklout = os.path.join(hklout, os.path.split(file)[-1].replace(
                '_scaled', '_truncated'))
            t.set_hklout(hklout)
            t.truncate()

            # replace old with the new version which has F's in it 
            scaled_reflection_files[key] = hklout

            # record the separated reflection file too
            self._scalr_scaled_reflection_files['mtz'][key] = hklout

        # standardise the unit cells and relabel each of the columns in
        # each reflection file appending the DNAME to the column name

        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            c = Cad()
            c.set_working_directory(self.get_working_directory())
            auto_logfiler(c)
            c.add_hklin(file)
            c.set_new_suffix(key)
            hklout = '%s_cad.mtz' % file[:-4]
            c.set_hklout(hklout)
            c.update()
            scaled_reflection_files[key] = hklout

        # merge all columns into a single uber-reflection-file

        c = Cad()
        c.set_working_directory(self.get_working_directory())
        auto_logfiler(c)
        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            c.add_hklin(file)
        
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_merged.mtz' % (common_pname,
                                                    common_xname))

        c.set_hklout(hklout)
        c.merge()
            
        self._scalr_scaled_reflection_files['mtz_merged'] = hklout

        return

    

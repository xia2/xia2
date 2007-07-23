#!/usr/bin/env python
# XDSIntegrate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=INTEGRATE module in XDS.
#

import os
import sys
import shutil
import math
import copy

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

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from XDS import header_to_xds, xds_check_version_supported, xds_check_error

# specific helper stuff
from XDSIntegrateHelpers import _parse_integrate_lp, \
     _parse_integrate_lp_updates

# global flags etc.
from Handlers.Flags import Flags
from Handlers.Streams import Chatter, Debug

# exceptions

from Schema.Exceptions.BadLatticeError import BadLatticeError

def XDSIntegrate(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIntegrateWrapper(DriverInstance.__class__,
                              FrameProcessor):
        '''A wrapper for wrapping XDS in integrate mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...            
            
            self._parallel = Flags.get_parallel()

            if self._parallel <= 1:
                self.set_executable('xds')
            else:
                self.set_executable('xds_par')

            # generic bits

            self._data_range = (0, 0)

            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = ['X-CORRECTIONS.pck',
                                           'Y-CORRECTIONS.pck',
                                           'BLANK.pck',
                                           'BKGPIX.pck',
                                           'GAIN.pck',
                                           'XPARM.XDS']

            self._output_data_files_list = ['FRAME.pck']

            self._refined_xparm = False

            self._updates = { }

            # note well - INTEGRATE.HKL is not included in this list
            # because it is likely to be very large - this is treated
            # separately...

            self._integrate_hkl = None

            return

        # getter and setter for input / output data

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data
            return

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def get_integrate_hkl(self):
            return self._integrate_hkl

        # this needs setting up from setup_from_image in FrameProcessor

        def set_refined_xparm(self):
            self._refined_xparm = True

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def set_updates(self, updates):
            self._updates = updates

        def get_updates(self):
            return copy.deepcopy(self._updates)

        def run(self):
            '''Run integrate.'''

            image_header = self.get_header()

            # crank through the header dictionary and replace incorrect
            # information with updated values through the indexer
            # interface if available...

            # need to add distance, wavelength - that should be enough...

            if self.get_distance():
                image_header['distance'] = self.get_distance()

            if self.get_wavelength():
                image_header['wavelength'] = self.get_wavelength()

            header = header_to_xds(image_header)

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=INTEGRATE\n')
            xds_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                          self._parallel) 

            # write out lots of output
            xds_inp.write('TEST=2\n')

            fixed_2401 = True

            if self._refined_xparm and fixed_2401:
                # allow only for crystal movement
                if Flags.get_refine():
                    Debug.write('Refining ORIENTATION CELL')
                    xds_inp.write('REFINE(INTEGRATE)=ORIENTATION CELL\n')
                else:
                    Debug.write('Not refining ORIENTATION CELL')
                    xds_inp.write('REFINE(INTEGRATE)=!\n')                
            else:
                # bug 2420 - have found for some examples that the
                # refinement is unstable - perhaps some of this is
                # best postrefined? was ALL
                xds_inp.write('REFINE(INTEGRATE)=BEAM ORIENTATION CELL\n')

            # check for updated input parameters
            if self._updates.has_key('BEAM_DIVERGENCE') and \
                   self._updates.has_key('BEAM_DIVERGENCE_E.S.D.'):
                xds_inp.write(
                    'BEAM_DIVERGENCE=%f BEAM_DIVERGENCE_E.S.D.=%f\n' % \
                    (self._updates['BEAM_DIVERGENCE'],
                     self._updates['BEAM_DIVERGENCE_E.S.D.']))
                Debug.write(
                    'BEAM_DIVERGENCE=%f BEAM_DIVERGENCE_E.S.D.=%f' % \
                    (self._updates['BEAM_DIVERGENCE'],
                     self._updates['BEAM_DIVERGENCE_E.S.D.']))
                
            if self._updates.has_key('REFLECTING_RANGE') and \
                   self._updates.has_key('REFLECTING_RANGE_E.S.D.'):
                xds_inp.write(
                    'REFLECTING_RANGE=%f REFLECTING_RANGE_E.S.D.=%f\n' % \
                    (self._updates['REFLECTING_RANGE'],
                     self._updates['REFLECTING_RANGE_E.S.D.']))
                Debug.write(
                    'REFLECTING_RANGE=%f REFLECTING_RANGE_E.S.D.=%f' % \
                    (self._updates['REFLECTING_RANGE'],
                     self._updates['REFLECTING_RANGE_E.S.D.']))
            
            for record in header:
                xds_inp.write('%s\n' % record)

            name_template = os.path.join(self.get_directory(),
                                         self.get_template().replace('#', '?'))

            record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
                     name_template

            if len(record) < 80:
                xds_inp.write(record)
                
            else:
                # else we need to make a softlink, then run, then remove 
                # softlink....

                try:
                    Debug.write('Linking %s to %s' % (
                        self.get_directory(),
                        os.path.join(self.get_working_directory(),
                                     'xds-image-directory')))

                                
                    os.symlink(self.get_directory(),
                               os.path.join(self.get_working_directory(),
                                            'xds-image-directory'))
                except OSError, e:
                    Debug.write('Error linking: %s' % str(e))
                
                name_template = os.path.join('xds-image-directory',
                                             self.get_template().replace(
                    '#', '?'))
                record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
                         name_template

                xds_inp.write(record)

            xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)
            # xds_inp.write('MINIMUM_ZETA=0.1\n')
            
            xds_inp.close()

            # copy the input file...
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'XDS.INP'),
                            os.path.join(self.get_working_directory(),
                                        'INTEGRATE.INP'))
            
            # write the input data files...

            for file in self._input_data_files_list:
                open(os.path.join(
                    self.get_working_directory(), file), 'wb').write(
                    self._input_data_files[file])

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())
            xds_check_error(self.get_all_output())

            # look for errors
            # like this perhaps - what the hell does this mean?
            #   !!! ERROR !!! "STRONGHKL": ASSERT VIOLATION

            # tidy up...
            try:
                os.remove(os.path.join(self.get_working_directory(),
                                       'xds-image-directory'))
            except OSError, e:
                pass
            
            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = open(os.path.join(
                    self.get_working_directory(), file), 'rb').read()

            self._integrate_hkl = os.path.join(self.get_working_directory(),
                                               'INTEGRATE.HKL')

            # look through integrate.lp for some useful information
            # to help with the analysis

            space_group_number = 0

            for o in open(os.path.join(
                self.get_working_directory(),
                'INTEGRATE.LP')).readlines():
                if 'SPACE_GROUP_NUMBER' in o:
                    space_group_number = int(o.split()[-1])

            stats = _parse_integrate_lp(os.path.join(
                self.get_working_directory(),
                'INTEGRATE.LP'))

            self._updates = _parse_integrate_lp_updates(os.path.join(
                self.get_working_directory(),
                'INTEGRATE.LP'))

            # analyse stats here, perhaps raising an exception if we
            # are unhappy with something, so that the indexing solution
            # can be eliminated in the integrater.

            images = stats.keys()
            images.sort()

            # these may not be present if only a couple of the
            # images were integrated...

            try:

                stddev_pixel = [stats[i]['rmsd_pixel'] for i in images]

                # fix to bug # 2501 - remove the extreme values from this
                # list...

                stddev_pixel = list(set(stddev_pixel))
                stddev_pixel.sort()
                stddev_pixel = stddev_pixel[1:-1]

                low, high = min(stddev_pixel), \
                            max(stddev_pixel)          

                Chatter.write('Standard Deviation in pixel range: %f %f' % \
                              (low, high))

                # print a one-spot-per-image rendition of this...
                stddev_pixel = [stats[i]['rmsd_pixel'] for i in images]

                # FIXME need to allow for blank images in here etc.

                status_record = ''
                for stddev in stddev_pixel:
                    if stddev > 2.5:
                        status_record += '!'
                    elif stddev > 1.0:
                        status_record += '%'
                    else:
                        status_record += 'o'

                if len(status_record) > 60:
                    Chatter.write('Integration status per image (60/record):')
                else:
                    Chatter.write('Integration status per image:')

                for chunk in [status_record[i:i + 60] \
                              for i in range(0, len(status_record), 60)]:
                    Chatter.write(chunk)
                Chatter.write(
                    '"o" => ok          "%" => iffy rmsd "!" => bad rmsd')
                Chatter.write(
                    '"O" => overloaded  "#" => many bad  "." => blank') 

                # next look for variations in the unit cell parameters
                unit_cells = [stats[i]['unit_cell'] for i in images]

                # compute average
                uc_mean = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                for uc in unit_cells:
                    for j in range(6):
                        uc_mean[j] += uc[j]

                for j in range(6):
                    uc_mean[j] /= len(unit_cells)

                max_rel_dev = 0.0

                for uc in unit_cells:
                    for j in range(6):
                        if (math.fabs(uc[j] - uc_mean[j]) / \
                            uc_mean[j]) > max_rel_dev:
                            max_rel_dev = math.fabs(uc[j] - uc_mean[j]) / \
                                          uc_mean[j]

                Chatter.write('Maximum relative deviation in cell: %.3f' % \
                              max_rel_dev)                

                # change - make this only a problem if not triclinic.

                if (high - low) / (0.5 * (high + low)) > 0.5 and \
                       space_group_number > 1 and False:
                    # there was a very large variation in deviation
                    # FIXME 08/JAN/07 this should raise a BadLatticeException

                    # FIXME 26/MAY/07 this should also look for large
                    # variations in the unit cell parameters...
                    # need to have both to distinguish TS01 NAT and TS02.
                    # This doesn't really help...

                    # 23/JUL/07 no longer use this as a metric -
                    # use the results of postrefinement...
                
                    raise BadLatticeError, \
                          'very large variation in pixel deviation'

            except KeyError, e:
                Chatter.write('Refinement not performed...')

            return

    return XDSIntegrateWrapper()

if __name__ == '__main__':

    integrate = XDSIntegrate()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    
    integrate.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    for file in ['X-CORRECTIONS.pck',
                 'Y-CORRECTIONS.pck',
                 'BLANK.pck',
                 'BKGPIX.pck',
                 'GAIN.pck',
                 'XPARM.XDS']:
        integrate.set_input_data_file(file, open(file, 'rb').read())
    
    integrate.set_data_range(1, 1)

    integrate.run()



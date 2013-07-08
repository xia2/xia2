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
from XDS import header_to_xds, xds_check_version_supported, xds_check_error, \
    _running_xds_version

# specific helper stuff
from XDSIntegrateHelpers import _parse_integrate_lp, \
    _parse_integrate_lp_updates

# global flags etc.
from Handlers.Flags import Flags
from Handlers.Streams import Chatter, Debug

from libtbx.phil import parse

master_params = parse("""
refine = *ORIENTATION *CELL BEAM DISTANCE AXIS
  .type = choice(multi = True)
  .help = 'what to refine in first pass of integration'
refine_final = *ORIENTATION *CELL BEAM DISTANCE AXIS
  .type = choice(multi = True)
  .help = 'what to refine in final pass of integration'
fix_scale = False
  .type = bool
""")  

def XDSIntegrate(DriverType = None, params = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIntegrateWrapper(DriverInstance.__class__,
                              FrameProcessor):
        '''A wrapper for wrapping XDS in integrate mode.'''

        def __init__(self, params = None):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # phil parameters

            if not params:
                params = master_params.extract()
            self._params = params
            
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

            self._input_data_files_list = ['X-CORRECTIONS.cbf',
                                           'Y-CORRECTIONS.cbf',
                                           'BLANK.cbf',
                                           'BKGPIX.cbf',
                                           'GAIN.cbf',
                                           'XPARM.XDS']

            self._output_data_files_list = ['FRAME.cbf']

            self._refined_xparm = False

            self._updates = { }

            # note well - INTEGRATE.HKL is not included in this list
            # because it is likely to be very large - this is treated
            # separately...

            self._integrate_hkl = None

            # FIXME these will also be wanted by the full integrater
            # interface I guess?

            self._mean_mosaic = None
            self._min_mosaic = None
            self._max_mosaic = None

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

        def get_mosaic(self):
            return self._min_mosaic, self._mean_mosaic, self._max_mosaic

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

            if self.get_two_theta():
                image_header['two_theta'] = self.get_two_theta()

            header = header_to_xds(image_header)

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=INTEGRATE\n')
            xds_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                          self._parallel)

            from Handlers.Phil import PhilIndex
            xds_params = PhilIndex.params.deprecated_xds
            if xds_params.parameter.profile_grid_size:
                ab, c = xds_params.parameter.profile_grid_size
                assert(ab > 0 and ab < 22 and (ab % 2) == 1)
                assert(c > 0 and c < 22 and (c % 2) == 1)
                xds_inp.write(
                    'NUMBER_OF_PROFILE_GRID_POINTS_ALONG_ALPHA/BETA= %d\n' % ab)
                xds_inp.write(
                    'NUMBER_OF_PROFILE_GRID_POINTS_ALONG_GAMMA= %d\n' % c)

            if Flags.get_xparallel() > 1:
                xds_inp.write('MAXIMUM_NUMBER_OF_JOBS=%d\n' % \
                              Flags.get_xparallel())

            elif Flags.get_xparallel() == -1:
                chunk_width = 30.0

                nchunks = int(
                    (self._data_range[1] - self._data_range[0] + 1) * \
                    (image_header['phi_end'] - image_header['phi_start']) /
                    chunk_width)

                Debug.write('Xparallel: -1 using %d chunks' % nchunks)

                xds_inp.write('MAXIMUM_NUMBER_OF_JOBS=%d\n' % nchunks)

            if not Flags.get_profile():
                xds_inp.write('PROFILE_FITTING=FALSE\n')

            # write out lots of output
            xds_inp.write('TEST=2\n')

            if Flags.get_small_molecule():
                xds_inp.write('DELPHI=%.1f\n' % \
                              xds_params.parameter.delphi_small)
            else:
                xds_inp.write('DELPHI=%.1f\n' % \
                              xds_params.parameter.delphi)

            if self._refined_xparm:
                xds_inp.write('REFINE(INTEGRATE)=%s\n' %
                              ' '.join(self._params.refine_final))
            else:
                xds_inp.write('REFINE(INTEGRATE)=%s\n' %
                              ' '.join(self._params.refine))

            if self._params.fix_scale:
                if _running_xds_version() >= 20130330:
                    xds_inp.write('DATA_RANGE_FIXED_SCALE_FACTOR= %d %d 1\n' % 
                                  self._data_range)
                else:
                    xds_inp.write('FIXED_SCALE_FACTOR=TRUE\n')    
                
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

            xds_inp.write(record)

            xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)
            # xds_inp.write('MINIMUM_ZETA=0.1\n')

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'XDS.INP'),
                            os.path.join(self.get_working_directory(),
                                         '%d_INTEGRATE.INP' % self.get_xpid()))

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

            # copy the LP file
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'INTEGRATE.LP'),
                            os.path.join(self.get_working_directory(),
                                         '%d_INTEGRATE.LP' % self.get_xpid()))

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = open(os.path.join(
                    self.get_working_directory(), file), 'rb').read()

            self._integrate_hkl = os.path.join(self.get_working_directory(),
                                               'INTEGRATE.HKL')

            # look through integrate.lp for some useful information
            # to help with the analysis

            space_group_number = 0

            mosaics = []

            for o in open(os.path.join(
                self.get_working_directory(),
                'INTEGRATE.LP')).readlines():
                if 'SPACE_GROUP_NUMBER' in o:
                    space_group_number = int(o.split()[-1])
                if 'CRYSTAL MOSAICITY (DEGREES)' in o:
                    mosaic = float(o.split()[-1])
                    mosaics.append(mosaic)

            self._min_mosaic = min(mosaics)
            self._max_mosaic = max(mosaics)
            self._mean_mosaic = sum(mosaics) / len(mosaics)

            Debug.write(
                'Mosaic spread range: %.3f %.3f %.3f' % \
                (self._min_mosaic, self._mean_mosaic, self._max_mosaic))

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

                # only remove the extremes if there are enough values
                # that this is meaningful... very good data may only have
                # two values!

                if len(stddev_pixel) > 4:
                    stddev_pixel = stddev_pixel[1:-1]

                low, high = min(stddev_pixel), \
                            max(stddev_pixel)

                Chatter.write('Processed batches %d to %d' % \
                              (min(images), max(images)))

                Chatter.write('Standard Deviation in pixel range: %f %f' % \
                              (low, high))

                # print a one-spot-per-image rendition of this...
                stddev_pixel = [stats[i]['rmsd_pixel'] for i in images]
                overloads = [stats[i]['overloads'] for i in images]
                strong = [stats[i]['strong'] for i in images]
                fraction_weak = [stats[i]['fraction_weak'] for i in images]

                # FIXME need to allow for blank images in here etc.

                status_record = ''
                for i, stddev in enumerate(stddev_pixel):
                    if fraction_weak[i] > 0.99:
                        status_record += '.'
                    elif stddev > 2.5:
                        status_record += '!'
                    elif stddev > 1.0:
                        status_record += '%'
                    elif overloads[i] > 0.01 * strong[i]:
                        status_record += 'O'
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
                    '"o" => good        "%" => ok        "!" => bad rmsd')
                Chatter.write(
                    '"O" => overloaded  "#" => many bad  "." => blank')
                Chatter.write(
                    '"@" => abandoned')

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

            except KeyError, e:
                raise RuntimeError, 'Refinement not performed...'

            return

    return XDSIntegrateWrapper(params)

if __name__ == '__main__':

    integrate = XDSIntegrate()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    integrate.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    for file in ['X-CORRECTIONS.cbf',
                 'Y-CORRECTIONS.cbf',
                 'BLANK.cbf',
                 'BKGPIX.cbf',
                 'GAIN.cbf',
                 'XPARM.XDS']:
        integrate.set_input_data_file(file, open(file, 'rb').read())

    integrate.set_data_range(1, 1)

    integrate.run()

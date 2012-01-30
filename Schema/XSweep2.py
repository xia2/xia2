#!/usr/bin/env python
# XSweep2.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A smarter plug-in replacement for the XSweep class which will allow more
# straightforward extensibility as well as generally smarter handling of
# detectors through the ImageFormat system and proper experiment description.

import sys
import os
import math
import exceptions
import copy
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter, Debug
from Handlers.Files import FileHandler
from Handlers.Flags import Flags
from Handlers.Environment import Environment

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory
from Experts.Filenames import expand_path

# image header reading functionality
from dxtbx.format.Registry import Registry

# access to factory classes
import Modules.Indexer.IndexerFactory as IndexerFactory
import Modules.Integrater.IntegraterFactory as IntegraterFactory

class XSweep2():
    '''A new and smarter object representation of the sweep.'''

    def __init__(self, name,
                 wavelength,
                 goniometer_instance,
                 detector_instance,
                 beam_instance,
                 scan_instance,
                 resolution_high = None,
                 resolution_low = None,
                 user_lattice = None,
                 user_cell = None):
        '''Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the experiment defined by the goniometer,
        detector, beam and scan.'''

        if not wavelength.__class__.__name__ == 'XWavelength':
            raise RuntimeError, 'wavelength not instance of XWavelength'

        self._name = name
        self._wavelength = wavelength

        # FIXME need to work out better way to handle these as input...

        self._user_lattice = user_lattice
        self._user_cell = user_cell

        self._resolution_high = resolution_high
        self._resolution_low = resolution_low

        # hooks into the dynamic data hierarchy

        self._indexer = None
        self._integrater = None

        self._goniometer = goniometer_instance
        self._detector = detector_instance
        self._beam = beam_instance
        self._scan = scan_instance

        return

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.get_wavelength():
            repr = 'SWEEP %s [WAVELENGTH %s]\n' % \
                   (self._name, self.get_wavelength().get_name())
        else:
            repr = 'SWEEP %s [WAVELENGTH UNDEFINED]\n' % self._name

        repr += 'TEMPLATE %s\n' % self._scan.get_template()
        repr += 'DIRECTORY %s\n' % self._scan.get_directory()
        repr += 'EXPOSURE TIME %f\n' % self._scan.get_exposure_time()
        repr += 'PHI WIDTH %.2f\n' % self._scan.get_oscillation()[1]
        repr += 'IMAGES (USER) %d to %d\n' % self._scan.get_image_range()

        # add some stuff to implement the actual processing implicitly
        # FIXME implement this once it is ready!

        # repr += 'MTZ file: %s\n' % self.get_integrater_intensities()

        return repr

    def get_goniometer(self):
        return self._goniometer

    def get_detector(self):
        return self._detector

    def get_beam(self):
        return self._beam

    def get_scan(self):
        return self._scan

    def get_image_name(self, number):
        '''Convert an image number into a name.'''

        return self._scan.get_image_name(number)

    def get_all_image_names(self):
        '''Get a full list of all images in this sweep...'''

        start, end = self._scan.get_image_range()

        return [self._scan.get_image_name(image) \
                for image in range(start, end + 1)]

    def get_epoch(self, image):
        '''Get the exposure epoch for this image.'''

        return self._scan.get_image_epoch(image)

    def get_reversephi(self):
        '''Get whether this is a reverse-phi sweep...'''

        if self._scan.get_oscillation()[1] < 0:
            return True

        return False

    def get_image_to_epoch(self):
        '''Get the image to epoch mapping table.'''

        return copy.deepcopy(self._scan.get_epochs())

    # to see if we have been instructed...

    def get_user_lattice(self):
        return self._user_lattice

    def get_user_cell(self):
        return self._user_cell

    def summarise(self):

        summary = ['Sweep: %s' % self._name]

        summary.append('Files %s' % os.path.join(self._scan.get_directory(),
                                                 self._scan.get_template()))

        summary.append('Images: %d to %d' % self._scan.get_image_range())

        # FIXME add some more interesting things in here...

        return summary

    def get_directory(self):
        return self._scan.get_directory()

    def get_image(self):
        start, end = self._scan.get_image_range()

        return self._scan.get_image_name(start)

    def get_beam(self):

        # FIXME derive the beam centre in the coordinate frame (fast, slow)
        # in mm - will need self._beam and self._detector

        return beam

    def get_distance(self):

        # FIXME derive the distance to the detector along the detector normal
        # N.B. this could turn out to be negative if the detector is read
        # in an unusual convention (i.e. the detector normal points towards
        # the sample

        return distance

    def set_resolution_high(self, resolution_high):
        self._resolution_high = resolution_high
        return

    def set_resolution_low(self, resolution_low):
        self._resolution_low = resolution_low
        return

    def get_resolution_high(self):
        return self._resolution_high

    def get_resolution_low(self):
        return self._resolution_low

    def get_polarization(self):
        return self._beam.get_polarization_fraction()

    def get_name(self):
        return self._name

    # These methods will be delegated down to Indexer and Integrater
    # implementations, through the defined API.

    def _get_indexer(self):
        '''Get my indexer, if set, else create a new one from the
        factory.'''

        if self._indexer == None:
            self._indexer = IndexerFactory.IndexerForXSweep(self)

            if self._user_lattice:
                self._indexer.set_indexer_input_lattice(self._user_lattice)
                self._indexer.set_indexer_user_input_lattice(True)

                if self._user_cell:
                    self._indexer.set_indexer_input_cell(self._user_cell)

            else:
                if self._user_cell:
                    raise RuntimeError, 'cannot assign cell without lattice'

            # set the working directory for this, based on the hierarchy
            # defined herein...

            # that would be CRYSTAL_ID/WAVELENGTH/SWEEP/index &c.

            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"

            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal().get_name()

            self._indexer.set_working_directory(
                Environment.generate_directory([crystal_id,
                                                wavelength_id,
                                                self.get_name(),
                                                'index']))

            frames = self._scan.get_image_range()
            self._indexer.set_frame_wedge(frames[0],
                                          frames[1])

            self._indexer.set_indexer_sweep_name(self._name)

        return self._indexer

    def _get_integrater(self):
        '''Get my integrater, and if it is not set, create one.'''

        if self._integrater == None:
            self._integrater = IntegraterFactory.IntegraterForXSweep(self)

            self._integrater.set_integrater_indexer(self._get_indexer())

            self._integrater.set_integrater_ice(
                self._get_indexer().get_indexer_ice())

            if Flags.get_ice():
                self._integrater.set_integrater_ice(Flags.get_ice())

            # set the working directory for this, based on the hierarchy
            # defined herein...

            # that would be CRYSTAL_ID/WAVELENGTH/SWEEP/index &c.

            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"
                project_id = "default"

            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal(
                    ).get_name()
                project_id = self.get_wavelength().get_crystal(
                    ).get_project().get_name()

            self._integrater.set_working_directory(
                Environment.generate_directory([crystal_id,
                                                wavelength_id,
                                                self.get_name(),
                                                'integrate']))

            self._integrater.set_integrater_project_info(project_id,
                                                         crystal_id,
                                                         wavelength_id)

            self._integrater.set_integrater_sweep_name(self._name)

            # copy across anomalous flags in case it's useful - #871

            self._integrater.set_integrater_anomalous(
                self.get_wavelength().get_crystal().get_anomalous())

            # see if we have any useful detector parameters to pass
            # on

            if self.get_polarization():
                self._integrater.set_polarization(self.get_polarization())

            # look to see if there are any global integration parameters
            # we can set...

            if global_integration_parameters.get_parameters(crystal_id):
                Debug.write('Using integration parameters for crystal %s' \
                            % crystal_id)
                self._integrater.set_integrater_parameters(
                    global_integration_parameters.get_parameters(crystal_id))

            # frames to process... looks here like we have multiple definitions
            # of the wedge somehow...

            frames = self._scan.get_image_range()
            self._indexer.set_frame_wedge(frames[0],
                                          frames[1])
            self._integrater.set_integrater_wedge(frames[0],
                                                  frames[1])
            self._integrater.set_frame_wedge(frames[0],
                                             frames[1])

        return self._integrater

    def get_indexer_lattice(self):
        return self._get_indexer().get_indexer_lattice()

    def get_indexer_cell(self):
        return self._get_indexer().get_indexer_cell()

    def get_integrater_lattice(self):
        return self._get_integrater().get_integrater_lattice()

    def get_integrater_cell(self):
        return self._get_integrater().get_integrater_cell()

    def get_indexer_distance(self):
        return self._get_indexer().get_indexer_distance()

    def get_indexer_mosaic(self):
        return self._get_indexer().get_indexer_mosaic()

    def get_indexer_beam(self):
        return self._get_indexer().get_indexer_beam()

    def get_wavelength(self):
        return self._wavelength

    def get_wavelength_value(self):
        '''Return the wavelength value in Angstroms.'''

        try:
            return self.get_wavelength().get_wavelength()
        except:
            return 0.0

    def get_integrater_intensities(self):
        reflections = self._get_integrater().get_integrater_intensities()

        # look to see if there are any global integration parameters
        # we can store...

        try:
            crystal_id = self.get_wavelength().get_crystal().get_name()
            if self._integrater.get_integrater_export_parameters():
                global_integration_parameters.set_parameters(
                    crystal_id,
                    self._integrater.get_integrater_export_parameters())
                Debug.write('Stored integration parameters' + \
                            ' for crystal %s' % crystal_id)

        except exceptions.Exception, e:
            # Chatter.write('Error storing parameters for crystal %s' % \
            # crystal_id)
            # Chatter.write('%s' % str(e))
            pass

        return reflections

    def get_crystal_lattice(self):
        '''Get the parent crystal lattice pointer.'''
        try:
            lattice = self.get_wavelength().get_crystal().get_lattice()
        except:
            lattice = None

        return lattice

class XSweep2Factory:
    '''A factory for XSweep2 instances, which can be constructed from e.g.
    a list of image files or alternatively an existing sweep with a subset of
    images.'''

    # FIXME still need to manage: user input cell and symmetry
    #                             resolution limits

    @staticmethod
    def FromX(name, wavelength, goniometer_instance, detector_instance,
              beam_instance, scan_instance):
        '''Construct an XSweep2 instance from already assembled Xthing
        instances, along with a name and an XWavelength instance.'''

        return XSweep2(name, wavelength, goniometer_instance,
                       detector_instance, beam_instance, scan_instance)

    @staticmethod
    def FromImages(name, wavelength, list_of_images):
        '''From a list of images, construct sweep or raise exception if the
        images logically belong to more than one sweep. N.B. the images must
        exist. Also needs the name and wavelength (XWavelength instance) to
        tie this into the data hierarchy.'''

        for image in list_of_images:
            assert(os.path.exists(image))

        list_of_images.sort()

        format = Registry.find(list_of_images[0])

        # verify that these are all the same format i.e. that they are all
        # understood equally well by the format instance.

        format_score = format.understand(list_of_images[0])

        for image in list_of_images:
            assert(format.understand(image) == format_score)

        i = format(list_of_images[0])

        beam = i.get_beam()
        gonio = i.get_goniometer()
        det = i.get_detector()
        scan = i.get_scan()

        # now verify that they share the same detector position, rotation axis
        # and beam properties.

        scans = [scan]

        for image in list_of_images[1:]:
            i = format(image)
            assert(beam == i.get_beam())
            assert(gonio == i.get_goniometer())
            assert(det == i.get_detector())
            scans.append(i.get_scan())

        for s in sorted(scans)[1:]:
            scan += s

        return XSweep2Factory.FromX(name, wavelength, gonio, det, beam, scan)

if __name__ == '__main__':

    # run some tests

    class XProject:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakeproject'

    class XCrystal:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakecrystal'
        def get_anomalous(self):
            return False
        def get_project(self):
            return XProject()
        def get_lattice(self):
            return None

    class XWavelength:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakewavelength'
        def get_wavelength(self):
            return math.pi / 4

    print XSweep2Factory.FromImages(
        'noddy', XWavelength(), sys.argv[1:])

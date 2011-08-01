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

# FIXME do I need this? What does it add?
from Object import Object

from Handlers.Streams import Chatter, Debug
from Handlers.Files import FileHandler
from Handlers.Flags import Flags
from Handlers.Environment import Environment

# Notes on XSweep
# 
# This points through wavelength to crystal, so the lattice information
# (in particular, the lattice class e.g. tP) will be kept in
# self.getWavelength().getCrystal().getLattice() - this itself will be 
# a versioning object, so should be tested for overdateness.
# 
# The only dynamic object property that this has is the resolution, which 
# may be set during processing or by the user. If it is set by the 
# user then this should be used and not updated. It should also only 
# be asserted once during processing => only update if currently None.
# Update 21/JUL/08 - now removed in the process of doing the resolution
# limits properly.

# Things which are needed to populate this object from the pointer to a
# single image.

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory
from Experts.Filenames import expand_path

# image header reading functionality
from Wrappers.XIA.Diffdump import Diffdump

# access to factory classes
import Modules.Indexer.IndexerFactory as IndexerFactory
import Modules.Integrater.IntegraterFactory as IntegraterFactory

# N.B. removed "integrated reflection file" options, as this is not clear how
# it should interact with the system...

class XSweep2(Object):
    '''A new and smarter object representation of the sweep.'''

    def __init__(self, name,
                 wavelength,
                 directory = None,
                 image = None,
                 beam = None,
                 reversephi = False,
                 distance = None,
                 gain = 0.0,
                 dmin = 0.0,
                 dmax = 0.0,
                 polarization = 0.0,
                 frames_to_process = None,
                 user_lattice = None,
                 user_cell = None,
                 epoch = 0):
        '''Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the images in directory starting with image,
        with beam centre optionally defined.'''

        # + check the wavelength is an XWavelength object
        #   raise an exception if not...

        Object.__init__(self)

        if not wavelength.__class__.__name__ == 'XWavelength':
            pass

        directory = expand_path(directory)

        directory = FileHandler.migrate(directory)

        self._name = name
        self._wavelength = wavelength
        self._directory = directory
        self._image = image
        self._reversephi = reversephi
        self._epoch = epoch
        self._user_lattice = user_lattice
        self._user_cell = user_cell

        # OK here is a first place where we will see some changes - this
        # constructor will need to take XDetector / XBeam / XScan / XGoniometer
        # objects...

        self._header = { } 


        self._resolution_high = dmin
        self._resolution_low = dmax

        # OK this will be handled by XScan on the future.

        self._epoch_to_image = { }
        self._image_to_epoch = { }

        # to allow first, last image for processing to be
        # set... c/f integrater interface
        self._frames_to_process = frames_to_process

        # + derive template, list of images - this will now vanish as it will
        # be handled by XScan and the XSweep2 Factory.

        # <will-go-away>

        if directory and image:
            self._template, self._directory = \
                            image2template_directory(os.path.join(directory,
                                                                  image))

            self._images = find_matching_images(self._template,
                                                self._directory)

            if self._frames_to_process:

                error = False
                
                start, end = self._frames_to_process
                for j in range(start, end + 1):
                    if not j in self._images:
                        Debug.write('image %s missing' % \
                                    self.get_image_name(j))
                        error = True
                        continue
                    if not os.access(self.get_image_name(j), os.R_OK):
                        Debug.write('image %s unreadable' % \
                                    self.get_image_name(j))
                        error = True
                        continue

                if error:
                    raise RuntimeError, 'problem with sweep %s' % self._name

            else:

                error = False
                
                start, end = min(self._images), max(self._images)
                for j in range(start, end + 1):
                    if not j in self._images:
                        Debug.write('image %s missing' % \
                                    self.get_image_name(j))
                        error = True
                        continue
                    if not os.access(self.get_image_name(j), os.R_OK):
                        Debug.write('image %s unreadable' % \
                                    self.get_image_name(j))
                        error = True
                        continue

                if error:
                    raise RuntimeError, 'problem with sweep %s' % self._name

            # + read the image header information into here?
            #   or don't I need it? it would be useful for checking
            #   against wavelength.getWavelength() I guess to make
            #   sure that the plumbing is all sound.

            dd = Diffdump()
            dd.set_image(os.path.join(directory, image))
            try:
                header = dd.readheader()
            except RuntimeError, e:
                raise RuntimeError, 'error reading %s: %s' % \
                      (os.path.join(directory, image), str(e))

            # check that they match by closer than 0.0001A, if wavelength
            # is not None

            if not wavelength == None:

                # FIXME 29/NOV/06 if the wavelength wavelength value
                # is 0.0 then first set it to the header value - note
                # that this assumes that the header value is correct
                # (a reasonable assumption)

                if wavelength.get_wavelength() == 0.0:
                    wavelength.set_wavelength(header['wavelength'])

                # FIXME 08/DEC/06 in here need to allow for the fact
                # that the wavelength in the image header could be wrong and
                # in fact it should be replaced with the input value -
                # through the user will need to be warned of this and
                # also everything using the FrameProcessor interface
                # will also have to respect this!

                if math.fabs(header['wavelength'] -
                             wavelength.get_wavelength()) > 0.0001:
                    # format = 'wavelength for sweep %s does not ' + \
                    # 'match wavelength %s'
                    # raise RuntimeError, format  % \
                    # (name, wavelength.get_name())

                    format = 'Header wavelength for sweep %s differerent' + \
                             ' to assigned value (%4.2f vs. %4.2f)'

                    Chatter.write(format % (name, header['wavelength'],
                                            wavelength.get_wavelength()))


            # also in here look at the image headers to see if we can
            # construct a mapping between exposure epoch and image ...

            if header.has_key('epoch'):
                # then we can do something interesting in here - note
                # well that this will require reading the headers of
                # every image to be processed!

                images = []

                if self._frames_to_process:
                    start, end = self._frames_to_process
                    for j in self._images:
                        if j >= start and j <= end:
                            images.append(j)

                else:
                    images = self._images

                start_t = time.time()

                
                for j in images:
                    dd = Diffdump()
                    dd.set_image(self.get_image_name(j))
                    try:
                        header = dd.readheader()
                    except RuntimeError, e:
                        raise RuntimeError, 'error reading %s: %s' % \
                              (self.get_image_name(j), str(e))
                    self._epoch_to_image[header['epoch']] = j
                    self._image_to_epoch[j] = header['epoch']

                end_t = time.time()

                epochs = self._epoch_to_image.keys()

                Debug.write('Reading %d headers took %ds' % \
                            (len(images), int(end_t - start_t)))
                Debug.write('Exposure epoch for sweep %s: %d %d' % \
                            (self._template, min(epochs), max(epochs)))
            
        else:

            raise RuntimeError, \
                  'directory + image needed to create XSweep'
            
        self._header = header

        # </will-go-away>

        # + get the lattice - can this be a pointer, so that when
        #   this object updates lattice it is globally-for-this-crystal
        #   updated? The lattice included directly in here includes an
        #   exact unit cell for data reduction, the crystal lattice
        #   contains an approximate unit cell which should be
        #   from the unit cells from all sweeps contained in the
        #   XCrystal. FIXME should I be using a LatticeInfo object
        #   in here? See what the Indexer interface produces. ALT:
        #   just provide an Indexer implementation "hook".
        #   See Headnote 001 above. See also _get_indexer,
        #   _get_integrater below.

        self._indexer = None
        self._integrater = None

        # I don't need this - it is equivalent to self.getWavelength(
        # ).getCrystal().getLattice()
        # self._crystal_lattice = None

        # this means that this module will have to present largely the
        # same interface as Indexer and Integrater so that the calls
        # can be appropriately forwarded.

        # finally configure the beam if set - this will go away too...

        self._beam = beam
        self._distance = distance
        self._gain = gain
        self._polarization = polarization
        
        return

    def get_image_name(self, number):
        '''Convert an image number into a name.'''

        return template_directory_number2image(self._template,
                                               self._directory,
                                               number)

    def get_all_image_names(self):
        '''Get a full list of all images in this sweep...'''
        result = []
        for image in self._images:
            result.append(template_directory_number2image(self._template,
                                                          self._directory,
                                                          image))
        return result

    def get_epoch(self, image):
        '''Get the exposure epoch for this image.'''

        return self._image_to_epoch.get(image, 0)

    def get_reversephi(self):
        '''Get whether this is a reverse-phi sweep...'''
        return self._reversephi

    def get_image_to_epoch(self):
        '''Get the image to epoch mapping table.'''
        return copy.deepcopy(self._image_to_epoch)

    # to see if we have been instructed...

    def get_user_lattice(self):
        return self._user_lattice

    def get_user_cell(self):
        return self._user_cell    
    
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.get_wavelength():
            repr = 'SWEEP %s [WAVELENGTH %s]\n' % \
                   (self._name, self.get_wavelength().get_name())
        else:
            repr = 'SWEEP %s [WAVELENGTH UNDEFINED]\n' % self._name

        if self._template:
            repr += 'TEMPLATE %s\n' % self._template
        if self._directory:
            repr += 'DIRECTORY %s\n' % self._directory
        if self._integrated_reflection_file:
            repr += 'INTEGRATED REFLECTION FILE %s\n' % \
                    self._integrated_reflection_file
            
        if self._header:
            # print some header information
            if self._header.has_key('detector'):
                repr += 'DETECTOR %s\n' % self._header['detector']
            if self._header.has_key('exposure_time'):
                repr += 'EXPOSURE TIME %f\n' % self._header['exposure_time']
            if self._header.has_key('phi_start'):
                repr += 'PHI WIDTH %.2f\n' % \
                        (self._header['phi_end'] - self._header['phi_start'])

        if self._frames_to_process:
            frames = self._frames_to_process
            repr += 'IMAGES (USER) %d to %d\n' % (frames[0],
                                                  frames[1])
        elif self._images:
                repr += 'IMAGES %d to %d\n' % (min(self._images),
                                               max(self._images))

        else:
            repr += 'IMAGES UNKNOWN\n'            

        # add some stuff to implement the actual processing implicitly

        repr += 'MTZ file: %s\n' % self.get_integrater_reflections()

        return repr

    def summarise(self):

        summary = ['Sweep: %s' % self._name]

        if self._template and self._directory:
            summary.append('Files %s' % os.path.join(self._directory,
                                                     self._template))

        if self._frames_to_process:
            summary.append('Images: %d to %d' % tuple(self._frames_to_process))

        if self._header and self._get_indexer():
            # print the comparative values

            header= self._header
            indxr = self._get_indexer()

            hbeam = header['beam']
            ibeam = indxr.get_indexer_beam()

            summary.append('Beam %.2f %.2f => %.2f %.2f' % \
                           (hbeam[0], hbeam[1], ibeam[0], ibeam[1]))

            hdist = header['distance']
            idist = indxr.get_indexer_distance()
            
            summary.append('Distance %.2f => %.2f' % (hdist, idist))

            summary.append('Date: %s' % header['date'])

        return summary
            
    def get_directory(self):
        return self._directory

    def get_image(self):
        return self._image

    def get_beam(self):
        return self._beam

    def get_distance(self):
        return self._distance

    def get_gain(self):
        return self._gain

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
        return self._polarization

    def get_name(self):
        return self._name

    # Real "action" methods - note though that these should never be
    # run directly, only implicitly...

    # These methods will be delegated down to Indexer and Integrater
    # implementations, through the defined method names. This should
    # make life interesting!

    # Note well - to get this to do things, ask for the
    # integrate_get_reflection() - this will kickstart everything.

    def _get_indexer(self):
        '''Get my indexer, if set, else create a new one from the
        factory.'''

        if self._indexer == None:
            # FIXME the indexer factory should probably be able to
            # take self [this object] as input, to help with deciding
            # the most appropriate indexer to use... this will certainly
            # be the case for the integrater. Maintaining this link
            # will also help the system cope with updates (which
            # was going to be one of the big problems...)
            # 06/SEP/06 no keep these interfaces separate - want to
            # keep "pure" interfaces to the programs for reuse, then
            # wrap in XStyle.
            self._indexer = IndexerFactory.IndexerForXSweep(self)

            # set the user supplied lattice if there is one
            if self._user_lattice:
                self._indexer.set_indexer_input_lattice(self._user_lattice)
                self._indexer.set_indexer_user_input_lattice(True)

                # and also the cell constants - but only if lattice is
                # assigned
                
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

            if self._frames_to_process:
                frames = self._frames_to_process
                self._indexer.set_frame_wedge(frames[0],
                                              frames[1])

            self._indexer.set_indexer_sweep_name(self._name)

        # FIXME in here I should probably check that the indexer
        # is up-to-date with respect to the crystal &c. if this has
        # changed the indexer will need to be updated...
        #
        # I need to think very hard about how this will work..
            
        return self._indexer

    def _get_integrater(self):
        '''Get my integrater, and if it is not set, create one.'''

        if self._integrater == None:
            self._integrater = IntegraterFactory.IntegraterForXSweep(self)

            # configure the integrater with the indexer - unless
            # we don't want to...

            if not self._integrated_reflection_file:
                self._integrater.set_integrater_indexer(self._get_indexer())

                # copy across "is this be icy" information... n.b. this
                # could change the order of execution?

                self._integrater.set_integrater_ice(
                    self._get_indexer().get_indexer_ice())

                # or if we have been told this on the command-line -
                # N.B. should really add a mechanism to specify the ice
                # rings we want removing, #1317.

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

            if self.get_gain():
                # this is assuming that an Integrater is also a FrameProcessor
                self._integrater.set_gain(self.get_gain())

            if self.get_polarization():
                self._integrater.set_polarization(self.get_polarization())
                
            # look to see if there are any global integration parameters
            # we can set...

            if global_integration_parameters.get_parameters(crystal_id):
                Debug.write('Using integration parameters for crystal %s' \
                            % crystal_id)
                self._integrater.set_integrater_parameters(
                    global_integration_parameters.get_parameters(crystal_id))

            # frames to process...

            if self._frames_to_process:
                frames = self._frames_to_process
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

    def get_integrater_reflections(self):
        reflections = self._get_integrater().get_integrater_reflections()
        
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
    

if __name__ == '__main__':

    # directory = os.path.join(os.environ['XIA2_ROOT'],
    # 'Data', 'Test', 'Images')

    directory = os.path.join('z:', 'data', '12287')
    
    image = '12287_1_E1_001.img'

    xs = XSweep('DEMO', None, directory, image)

    xs_descr = str(xs)

    Chatter.write('.')
    for record in xs_descr.split('\n'):
        Chatter.write(record.strip())

    Chatter.write('.')

    Chatter.write('Refined beam is: %6.2f %6.2f' % xs.get_indexer_beam())
    Chatter.write('Distance:        %6.2f' % xs.get_indexer_distance())
    Chatter.write('Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                  xs.get_indexer_cell())
    Chatter.write('Lattice: %s' % xs.get_indexer_lattice())
    Chatter.write('Mosaic: %6.2f' % xs.get_indexer_mosaic())
    Chatter.write('Hklout: %s' % xs.get_integrater_reflections())
    

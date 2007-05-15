#!/usr/bin/env python
# XSweep.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A versioning object representation of the sweep. This will include
# methods for handling the required actions which may be performed
# on a sweep, and will also include integration with the rest of the
# .xinfo hierarchy. 
# 
# The following properties are defined for sweep:
# 
# resolution
# 
# The following properties defined elsewhere impact in the definition
# of the sweep:
#
# lattice - contained in XCrystal, to levels above XSweep.
#
# FIXME this needs to be defined!
#
# Headnote 001: LatticeInfo & Stuff.
# 
# Ok, so this is complicated. The crystal lattice will apply to all sweeps
# measured from that crystal (*1) so that they should share the same
# orientation matrix. This means that this could best contain a pointer
# to an Indexer implementation. This can then decide what to do - for 
# instance, we want to make sure that the indexing is kept common. That
# would mean that Mosflm would do a better job for indexing second and
# subsequent sets than labelit, perhaps, since the matrix can be passed
# as input - though this will need to be communicated to the factory.
# 
# Index 1st sweep - store indexer pointer, pass info also to crystal. Next
# sweep will update this information at the top level, with the original
# Indexer still "watching". Next get() may trigger a recalculation.
# By the time the second sweep is analysed, the first should be pretty
# solidly sorted with the correct pointgroup &c.
# 
# The upshot of all of this is that this will maintain a link to the 
# indexer which was used, which need to keep an eye on the top level
# lattice, which in turn will be updated as a weighted average of
# Indexer results. Finally, the top level will maintain a more high-tech
# "Lattice handler" object, which can deal with lattice -- and lattice ++.
# 
# (*1) This assumes, of course, that the kappa information or whatever
#      is properly handled.
#
# Bugger - slight complication! Want to make sure that multiple sweeps
# in the same wavelength have "identical" unit cells (since the error
# on the wavelength should be small) which means that the XWavelength
# level also needs to be able to handle this kind of information. Note
# well - this is an old thought, since the overall crystal unit cell
# is a kind of average from the wavelengths, which is in turn a kind
# of average from all of the sweeps. Don't miss out the wavelength
# level.
# 
# This means that the lattice information will have to cascade up and
# down the tree, to make sure that everything is kept up-to-date. This
# should be no more difficult, just a little more complicated.
#
# FIXME 06/SEP/06 need to add in hooks here to handle collection time,
#                 e.g. the epoch information from xia2find. This will
#                 need to be used for sorting sweeps in a wavelength - 
#                 so must be defined in the property list, as per
#                 the old Sweep defition. Sort on START of collection.
#                 Though the end is also important...? Discuss!
# 
# FIXME 23/OCT/06 need to plumb in the cell handler/lattice handler stuff
#                 to make the system cope with TS01. This raises an 
#                 interesting problem - should this just be composed of the
#                 indexing results, or also the stuff generated by Othercell?
#                 The former is perhaps more appropriate... Fixed elsewhere!
# 
# FIXME 30/OCT/06 need to be able to pass in already integrated data for
#                 instance so that this will perform just the scaling & 
#                 merging. This will come from the .xinfo file in an
#                 INTEGRATED_REFLECTION_FILE record.

import sys
import os
import math
import exceptions
import copy
import time

# we all inherit from Object
from Object import Object

# allow output
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter
from Handlers.Files import FileHandler
from Handlers.Environment import Environment

# helper class definitions
# in _resolution, need to think about how a user defined resolution
# will be handled - should this be a readonly attribute?

class _resolution(Object):
    '''An object to represent resolution for the XSweep object.'''

    def __init__(self, resolution = None,
                 o_handle = None,
                 o_readonly = False):
        Object.__init__(self, o_handle, o_readonly)

        if not resolution is None:
            Chatter.write('%s set to %5.2f' % (self.handle(), resolution))
        self._resolution = resolution

        return

    def get(self):
        return self._resolution

    def set(self, resolution):
        self._resolution = resolution
        Chatter.write('%s set to %5.2f' % (self.handle(), resolution))
        self.reset()
        return

# See FIXME Integrater interface definition, 27/SEP/06

class _global_integration_parameters:
    '''A global class to record the integration parameters which are exported
    for each crystal. This is a dictionary keyed by the crystal id.'''

    # FIXME this is a threat to parallelism!
    # FIXME added copy.deepcopy to help prevent mashing of parameters...

    def __init__(self):
        self._parameter_dict = { }

    def set_parameters(self, crystal, parameters):
        self._parameter_dict[crystal] = copy.deepcopy(parameters)
        return

    def get_parameters(self, crystal):
        return copy.deepcopy(self._parameter_dict.get(crystal, { }))

global_integration_parameters = _global_integration_parameters()

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

# Things which are needed to populate this object from the pointer to a
# single image.

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory
from Experts.Filenames import expand_path

# image header reading functionality
from Wrappers.XIA.Printheader import Printheader

# access to factory classes
import Modules.IndexerFactory as IndexerFactory
import Modules.IntegraterFactory as IntegraterFactory

class XSweep(Object):
    '''An object representation of the sweep.'''

    def __init__(self, name,
                 wavelength,
                 directory = None,
                 image = None,
                 integrated_reflection_file = None,
                 beam = None,
                 distance = None,
                 resolution = None,
                 gain = 0.0,
                 frames_to_process = None,
                 epoch = 0):
        '''Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the images in directory starting with image,
        with beam centre optionally defined.'''

        # + check the wavelength is an XWavelength object
        #   raise an exception if not...

        Object.__init__(self)

        if not wavelength.__class__.__name__ == 'XWavelength':
            pass

        # FIXME bug 2221 if DIRECTORY starts with ~/ or ~graeme (say) need to
        # interpret this properly - e.g. map it to a full PATH.

        directory = expand_path(directory)
        integrated_reflection_file = expand_path(
            integrated_reflection_file)

        # bug # 2274 - maybe migrate the data to a local disk (this
        # will depend if el user has added -migrate_data to the cl)

        directory = FileHandler.migrate(directory)

        self._name = name
        self._wavelength = wavelength
        self._directory = directory
        self._image = image
        self._integrated_reflection_file = integrated_reflection_file
        self._epoch = epoch

        self._epoch_to_image = { }
        self._image_to_epoch = { }

        # to allow first, last image for processing to be
        # set... c/f integrater interface
        self._frames_to_process = frames_to_process

        # + derive template, list of images

        if directory and image:
            self._template, self._directory = \
                            image2template_directory(os.path.join(directory,
                                                                  image))

            self._images = find_matching_images(self._template,
                                                self._directory)

            # + read the image header information into here?
            #   or don't I need it? it would be useful for checking
            #   against wavelength.getWavelength() I guess to make
            #   sure that the plumbing is all sound.

            ph = Printheader()
            ph.set_image(os.path.join(directory, image))
            header = ph.readheader()

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
                    ph = Printheader()
                    ph.set_image(self.get_image_name(j))
                    header = ph.readheader()
                    
                    self._epoch_to_image[header['epoch']] = j
                    self._image_to_epoch[j] = header['epoch']

                end_t = time.time()

                epochs = self._epoch_to_image.keys()

                Chatter.write('Reading %d headers took %ds' % \
                              (len(images), int(end_t - start_t)))
                Chatter.write('Exposure epoch for sweep %s: %d %d' % \
                              (self._template, min(epochs), max(epochs)))
            
        else:

            if not self._integrated_reflection_file:
                raise RuntimeError, \
                      'integrated intensities or directory + ' + \
                      'image needed to create XSweep'
            
            # parse the reflection file header here to get the wavelength
            # out - put this in the header record...

            header = { }
            self._images = None
            self._template = None

        self._header = header

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

        #   this means that this module will have to present largely the
        #   same interface as Indexer and Integrater so that the calls
        #   can be appropriately forwarded.

        # set up the resolution object

        resolution_handle = '%s RESOLUTION' % name
        self._resolution = _resolution(resolution = resolution,
                                       o_handle = resolution_handle)

        # finally configure the beam if set

        self._beam = beam
        self._distance = distance
        self._gain = gain
        
        return

    def get_image_name(self, number):
        '''Convert an image number into a name.'''

        return template_directory_number2image(self._template,
                                               self._directory,
                                               number)

    def get_epoch(self, image):
        '''Get the exposure epoch for this image.'''

        return self._image_to_epoch.get(image, 0)

    def get_image_to_epoch(self):
        '''Get the image to epoch mapping table.'''
        return copy.deepcopy(self._image_to_epoch)
    
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

    def get_resolution(self):
        return self._resolution.get()

    def set_resolution(self, resolution):
        if not self._resolution.get():
            self._resolution.set(resolution)
        # else:
        # Chatter.write('%s already set' % self._resolution.handle())

        return

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


        # FIXME in here I should probably check that the indexer
        # is up-to-date with respect to the crystal &c. if this has
        # changed the indexer will need to be updated...
        #
        # I need to think very hard about how this will work...
            
        return self._indexer

    def _get_integrater(self):
        '''Get my integrater, and if it is not set, create one.'''

        if self._integrater == None:
            self._integrater = IntegraterFactory.IntegraterForXSweep(self)

            # configure the integrater with the indexer - unless
            # we don't want to...

            if not self._integrated_reflection_file:
                self._integrater.set_integrater_indexer(self._get_indexer())

            # set the working directory for this, based on the hierarchy
            # defined herein...

            # that would be CRYSTAL_ID/WAVELENGTH/SWEEP/index &c.

            if not self.get_wavelength():
                wavelength_id = "default"
                crystal_id = "default"
                project_id = "default"

            else:
                wavelength_id = self.get_wavelength().get_name()
                crystal_id = self.get_wavelength().get_crystal().get_name()
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

            # see if we have any useful detector parameters to pass
            # on

            if self.get_gain():
                # this is assuming that an Integrater is also a FrameProcessor
                self._integrater.set_gain(self.get_gain())

            # look to see if there are any global integration parameters
            # we can set...

            if global_integration_parameters.get_parameters(crystal_id):
                Chatter.write('Using integration parameters for crystal %s' \
                              % crystal_id)
                self._integrater.set_integrater_parameters(
                    global_integration_parameters.get_parameters(crystal_id))

            # frames to process...

            if self._frames_to_process:
                frames = self._frames_to_process
                self._integrater.set_integrater_wedge(frames[0],
                                                      frames[1])

        return self._integrater

    def get_indexer_lattice(self):
        return self._get_indexer().get_indexer_lattice()

    def get_indexer_cell(self):
        return self._get_indexer().get_indexer_cell()

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
                Chatter.write('Stored integration parameters' + \
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
    

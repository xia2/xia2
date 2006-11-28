#!/usr/bin/env python
# Dataset.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 12th June 2006
# 
# A class to represent the structure of a data set. This inherits from 
# the generic object, and includes information about the data set. This
# can consist of one or more other data sets and a sweep. In the first 
# iteration this will simply point at a sweep.
# 
# This also includes prior information provided from "outside" either
# downstream or from the user.

import os
import sys
import copy
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

# stuff to allow population and inspection of the data set

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory

# base class of all xia2dpa objects
from Schema.Object import Object

# delegation of lazy-evaluation calculations
from Modules.IndexerFactory import Indexer

# image header reading functionality
from Wrappers.XIA.Printheader import Printheader

class Dataset(Object):
    '''A class to represent a data set. In this implementation this is a
    sweep.'''

    def __init__(self,
                 image,
                 beam = None,
                 fp_fpp = None,
                 lattice = None):
        '''Initialise the object with all of the required information.
        Image is required - as a pointer to an image. The rest (beam,
        fp_fpp) are optional. These should both be passsed in a 2-ples.'''
        
        Object.__init__(self)

        # Dataset objects are defined by the attributes template,
        # directory and image range - see Object.py

        self._identity_attributes = ['_template', '_directory',
                                     '_image_range', '_lattice']
        
        self._template, self._directory = \
                        image2template_directory(image)

        self._images = find_matching_images(self._template,
                                            self._directory)

        # this will be populated by the Printheader class if we're
        # not in a hurry (e.g. we can take our time.)
        # FIXME need to implement a "hurry" mechanism...

        self._init_headers()

        self._image_range = (min(self._images), max(self._images))

        if lattice:
            self._lattice = lattice
        else:
            self._lattice = None

        if beam:

            # check the type etc.

            if not type(beam) is type((1, 2)):
                raise RuntimeError, 'beam should be a tuple'
            if not len(beam) is 2:
                raise RuntimeError, 'beam should be a 2-tuple'
            
            self._beam = (beam[0], beam[1])

            self.write('Set beam to (%f, %f) from input' % self._beam)
            
        else:
            # initialise from the first image in the set

            self._beam = self._headers[min(self._images)]['beam']

            self.write('Set beam to (%f, %f) from header' % tuple(self._beam))

            pass

        if fp_fpp:
        
            # check the type etc.

            if not type(fp_fpp) is type((1, 2)):
                raise RuntimeError, 'fp_fpp should be a tuple'
            if not len(fp_fpp) is 2:
                raise RuntimeError, 'fp_fpp should be a 2-tuple'
            
            self._fp_fpp = (fp_fpp[0], fp_fpp[1])

        else:
            # have a stupid default value
            
            self._fp_fpp = (0.0, 0.0)

        return

    # internal methods...

    def _init_headers(self):
        '''Work through all of the images populating the headers.'''

        self._headers = { }
        
        ph = Printheader()

        t = time.time()
        
        for i in self._images:
            image = template_directory_number2image(self._template,
                                                    self._directory,
                                                    i)
            ph.setImage(image)
            header = ph.readheader()
            self._headers[i] = header

        self.write('reading %d headers took %s s' % (len(self._images),
                                                     int(time.time() - t)))

        return

    # setters - very few of these and they really change the whole
    # system...

    def setLattice(self, lattice):
        self._lattice = lattice
        self.reset()
        return

    def getLattice(self):
        return self._lattice

    def getTemplate(self):
        return self._template

    def getDirectory(self):
        return self._directory

    def getImages(self):
        return copy.deepcopy(self._images)

    def getBeam(self):
        return self._beam

    def getFp_fpp(self):
        return self._fp_fpp

    # next a set of interesting methods - these imply "real" work and
    # also delegation via some interesting factories....

    def getLattice_info(self):
        '''Get the lattice information for this data set. If not already
        available, then generate it!. A full history of this is kept in
        this object.'''

        if not hasattr(self, '_lattice_info'):
            self._lattice_info = []

        self._lattice_info.sort()
            
        if len(self._lattice_info) == 0 or \
           (self._lattice_info[-1] < self):
            # then I need to do something - calculate a new solution
            indexer = Indexer(self)
            self._lattice_info.append(indexer.getLattice_info())

        # ok, can now return the latest version of this answer
        return self._lattice_info[-1]

if __name__ == '__main__':

    if len(sys.argv) > 1:
        d = Dataset(sys.argv[1])
        sys.exit()

    d = Dataset(os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    e = Dataset(os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    if d != e:
        raise RuntimeError, 'these should be identical'

    li = d.getLattice_info()

    cell = li.getCell()

    print '%s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          (li.getLattice(), cell[0], cell[1], cell[2],
           cell[3], cell[4], cell[5])
    
    d.setLattice('oP')

    li = d.getLattice_info()

    cell = li.getCell()

    print '%s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          (li.getLattice(), cell[0], cell[1], cell[2],
           cell[3], cell[4], cell[5])
    

#!/usr/bin/env python
# Dataset.py
# Maintained by G.Winter
# 12th June 2006
# 
# A class to represent the structure of a data set. This inherits from 
# the generic object, and includes information about the data set. This
# can consist of one or more other data sets and a sweep. In the first 
# iteration this will simply point at a sweep.
# 
# 

import os
import sys
import copy

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

# stuff to allow population and inspection of the data set

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory

from Object import Object

class Dataset(Object):
    '''A class to represent a data set. In this implementation this is a
    sweep.'''

    def __init__(self,
                 image,
                 beam = None,
                 fp_fpp = None):
        '''Initialise the object with all of the required information.
        Image is required - as a pointer to an image. The rest (beam,
        fp_fpp) are optional. These should both be passsed in a 2-ples.'''
        
        Object.__init__(self)

        # Dataset objects are defined by the attributes template,
        # directory and image range - see Object.py

        self._identity_attributes = ['_template', '_directory',
                                     '_image_range']
        
        self._template, self._directory = \
                        image2template_directory(image)

        self._images = find_matching_images(self._template,
                                            self._directory)

        self._image_range = (min(self._images), max(self._images))

        if beam:

            # check the type etc.

            if not type(beam) is type((1, 2)):
                raise RuntimeError, 'beam should be a tuple'
            if not len(beam) is 2:
                raise RuntimeError, 'beam should be a 2-tuple'
            
            self._beam = (beam[0], beam[1])
            
        else:
            # initialise from the first image in the set
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

if __name__ == '__main__':
    d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    e = Dataset(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    if d != e:
        raise RuntimeError, 'these should be identical'

    print d

        
    

# a quick wrapper for mosflm indexer using driver
# note that this is using Driver but little else (e.g. needs to explicitly
# be given command script...)

import os
import sys
import shutil
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory

def MosflmIndexer(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class MosflmIndexerWrapper(DriverInstance.__class__):

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable('ipmosflm')

            # random things
            self._other_commands = []
                        
            # useful things
            self._template = None
            self._directory = None
            self._distance = None
            self._beam = None
            self._wavelength = None
            self._images = []
            self._threshold = 20

            self._p1 = True

            # optional input - perhaps we tell the cell
            self._cell = None

            # note well - all calculations will be done in P1

            return

        def set_template(self, template):
            self._template = template
            return
            
        def set_directory(self, directory):
            self._directory = directory
            return
            
        def set_beam(self, beam):
            self._beam = beam
            return
            
        def set_distance(self, distance):
            self._distance = distance
            return
            
        def set_wavelength(self, wavelength):
            self._wavelength = wavelength
            return
            
        def set_images(self, images):
            self._images = images
            return

        def set_not_p1(self):
            self._p1 = False
        
        def set_threshold(self, threshold):
            self._threshold = threshold
            return

        def index(self):

            self.start()

            self.input('template %s' % self._template)
            self.input('directory %s' % self._directory)
            if self._beam:
                self.input('beam %f %f' % self._beam)
            if self._distance:
                self.input('distance %f' % self._distance)
            if self._wavelength:
                self.input('wavelength %f' % self._wavelength)
            for image in self._images:
                self.input('autoindex dps refime image %d threshold %f' % \
                           (image, self._threshold))

            if self._p1:
                self.input('symm p1')
            self.input('newmat auto.mat')
            self.input('go')

            self.close_wait()

            # check here for errors

            # for o in self.get_all_output():
            # print o[:-1]

            cell = tuple(map(float, open(
                os.path.join(self.get_working_directory(),
                             'auto.mat')).read().split()[21:27]))
            
            return cell

    return MosflmIndexerWrapper()

def autoindex(mi_id, template, directory, beam, images, p1 = True):

    startdir = os.getcwd()

    jobname = 'R%d' % images[0]
    for i in images[1:]:
        jobname += '.%d' % i

    mi = MosflmIndexer('cluster.sge')
    mi.set_name(jobname)
    mi.set_working_directory(os.path.join(startdir, mi_id))
    mi.set_directory(directory)
    mi.set_template(template)
    mi.set_beam(beam)
    mi.set_images(images)
    if not p1:
        mi.set_not_p1()
    cell = mi.index()

    return cell

if __name__ == '__main__':

    # run a test...

    from BitsAndBobs import celldiff

    mi = MosflmIndexer()

    directory = os.path.join(os.environ['XIA2_ROOT'], 'Data', 'Test', 'Images')
    template = '12287_1_E1_###.img'
    beam = (109.0, 105.0)

    mi.set_directory(directory)
    mi.set_template(template)
    mi.set_beam(beam)
    mi.set_images((1, 90))

    cd = celldiff(mi.index(), (51.73, 51.85, 158.13, 90.00, 90.05, 90.20))

    if cd[0] > 0.5 or cd[1] > 0.5:
        raise RuntimeError, 'large autoindex error'


    

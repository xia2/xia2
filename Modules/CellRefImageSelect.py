# CellRefImageSelect.py
# Maintained by G.Winter
# 19th November 2007
# 
# A jiffy to try selecting images for cell refinement then running with them
# to assess how well the cell refinement goes...
# 

import os
import sys

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# classes to make this work

# something to read the headers 

# one liner around labelit.index

def LabelitIndex(DriverType = None):
    DriverInstance = DriverFactory.Driver(DriverType)
    
    from Schema.Interfaces.FrameProcessor import FrameProcessor

    class LabelitIndexWrapper(DriverInstance.__class__,
                              FrameProcessor):

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            self.set_executable('labelit.index')
            FrameProcessor.__init__(self)

            # input

            self._images = []
            self._beam = None

            # results

            self._lattice = None
            self._matrix = None
            self._distance = None
            self._rbeam = None
            self._mosaic = None
            self._penalties = None

            return

        def set_images(self, images):
            self._images = images
            return

        def set_beam(self, beam):
            self._beam = beam
            return

        def write_dataset_preferences(self):
            fout = open('dataset_preferences.py', 'w')
            fout.write('wedgelimit = 4\n')
            if self._beam:
                fout.write('autoindex_override_beam = %f, %f\n' % self._beam)
            fout.close()
            return

        def autoindex(self):

            self.add_command_line('--index_only')

            for i in self._images:
                self.add_command_line(self.get_image_name(i))

            self.write_dataset_preferences()

            self.start()

            self.close_wait()

            # parse output table

            solutions = []

            for line in self.get_all_output():
                if 'Beam center x' in line:
                    L = line.replace('mm', ' ').split()
                    self._rbeam = (float(L[3]), float(L[6]))
                    self._distance = float(L[9])
                    self._mosaic = float(L[12].replace('mosaicity=', ''))
                if ':)' in line:
                    solutions.append(line.replace(':)', '').split())

            # run labelit.mosflm_script N to get the right matrix file

            solution = int(solutions[0][0])

            lms = LabelitMosflmScript()
            lms.set_solution(solution)
            lms.run()
            self._matrix = lms.get_matrix()

            # get the lattice information etc..
            self._lattice = solutions[0][6]
            
            metric = float(solutions[0][1])
            rmsd = float(solutions[0][3])

            self._penalties = (metric, rmsd)
            
            # cell = tuple(map(float, solutions[7:13]))

            return

        def get_lattice(self):
            return self._lattice

        def get_matrix(self):
            return self._matrix

        def get_beam(self):
            return self._rbeam

        def get_distance(self):
            return self._distance

        def get_mosaic(self):
            return self._mosaic

        def get_penalties(self):
            return self._penalties

    return LabelitIndexWrapper()
            
def LabelitMosflmScript(DriverType = None):
    DriverInstance = DriverFactory.Driver(DriverType)
    
    class LabelitMosflmScriptWrapper(DriverInstance.__class__):

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            self.set_executable('labelit.mosflm_script')

            # input

            self._solution = None

            # results

            self._matrix = None
    
            return

        def set_solution(self, solution):
            self._solution = solution
            return

        def run(self):

            if not self._solution:
                raise RuntimeError, 'solution not set'

            self.add_command_line('%d' % self._solution)

            self.start()

            self.close_wait()

            # pick up integrationNN.csh

            script = open('integration%02d.csh' % self._solution).readlines()

            # parse this to get the appropriate matrix file out...

            matrix = ''

            for line in script:

                if 'eof-cat' in line[:7]:
                    break
                
                if not 'cat' in line and not 'csh' in line:
                    matrix += line

            self._matrix = matrix
            return

        def get_matrix(self):
            return self._matrix

    return LabelitMosflmScriptWrapper()

def MosflmCellRefine(DriverType = None):
    DriverInstance = DriverFactory.Driver(DriverType)
    
    from Schema.Interfaces.FrameProcessor import FrameProcessor

    class MosflmCellRefineWrapper(DriverInstance.__class__,
                                  FrameProcessor):

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            self.set_executable('ipmosflm-7.0.1')
            FrameProcessor.__init__(self)

            # input

            self._matrix = None
            self._beam = None
            self._distance = None
            self._lattice = None
            self._wedges = None
            self._mosaic = None
            
            # results

            return

        def set_matrix(self, matrix):
            self._matrix = matrix
            return

        def set_beam(self, beam):
            self._beam = beam
            return

        def set_distance(self, distance):
            self._distance = distance
            return

        def set_lattice(self, lattice):
            self._lattice = lattice
            return

        def set_mosaic(self, mosaic):
            self._mosaic = mosaic
            return

        def set_wedges(self, wedges):
            self._wedges = wedges
            return

    

# one liner around mosflm cell refinement

# ---------------------------------

# autoindex with labelit

# convert this to p1, compute real space unit cell axes in xia2 frame

# for phi in images find when A.X = 0 and maximised and so on

# select some images

# run cell refinement

# run cell refinement in P1

# gather stats on results (quality of cell refinement)

# gather stats on results p1 (quality of cell refinement)

# divide the ratios to look at the quality of this as a lattice check

# repeat

if __name__ == '__main__':

    images = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60,
              65, 70, 75, 80, 85, 90]


    directory = os.path.join('/media', 'data1', 'graeme', 'jcsg',
                             '1vpj', 'data', 'jcsg', 'als1', '8.2.1',
                             '20040926', 'collection', 'TB0541B', '12287')

    image = os.path.join(directory, '12287_1_E1_001.img')

    for i in images[:-2]:
        for j in images[i:-1]:
            for k in images[j:]:
                
                li = LabelitIndex()
                li.setup_from_image(image)
                li.set_beam((109.0,105.0))
                li.set_images([i, j, k])

                li.autoindex()

                metric, rmsd = li.get_penalties()

                print '%2d %2d %2d %.4f %.4f' % (i, j, k, metric, rmsd)

# CellRefImageSelect.py
# Maintained by G.Winter
# 19th November 2007
# 
# A jiffy to try selecting images for cell refinement then running with them
# to assess how well the cell refinement goes...
# 

import os
import sys
import math

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# classes to make this work

from Experts.MatrixExpert import rot_x, mosflm_a_matrix_to_real_space, \
     matvecmul, dot

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

def compute_something(phi_start, phi_end, phi_width,
                      wavelength, lattice, matrix):

    # compute the P1 real-space cell axes

    a, b, c = mosflm_a_matrix_to_real_space(wavelength, lattice, matrix)

    # compute rotations of these and find minimum for axis.Z - that is the
    # Z component of the rotated axis... check workings and definitions!

    phi = phi_start + 0.5 * phi_width

    # initialize search variables

    phi_a = phi_start
    phi_b = phi_start
    phi_c = phi_start

    dot_a = 100.0
    dot_b = 100.0
    dot_c = 100.0

    while phi < phi_end:
        RX = rot_x(phi)

        RXa = matvecmul(RX, a)
        RXb = matvecmul(RX, b)
        RXc = matvecmul(RX, c)

        if math.fabs(RXa[2]) < dot_a:
            dot_a = math.fabs(RXa[2])
            phi_a = phi

        if math.fabs(RXb[2]) < dot_b:
            dot_b = math.fabs(RXb[2])
            phi_b = phi

        if math.fabs(RXc[2]) < dot_c:
            dot_c = math.fabs(RXc[2])
            phi_c = phi
            
        phi += phi_width

    length_a = math.sqrt(dot(a, a))
    length_b = math.sqrt(dot(b, b))
    length_c = math.sqrt(dot(c, c))

    pi = 4.0 * math.atan(1.0)

    angle_a = 0.5 * pi - math.acos(dot_a / length_a)
    angle_b = 0.5 * pi - math.acos(dot_b / length_b)
    angle_c = 0.5 * pi - math.acos(dot_c / length_c)

    return phi_a, phi_b, phi_c, angle_a, angle_b, angle_c

def compute_something_else(phi_start, phi_end, phi_width,
                           wavelength, lattice, matrix):

    # compute the P1 real-space cell axes

    a, b, c = mosflm_a_matrix_to_real_space(wavelength, lattice, matrix)

    # compute rotations of these and find minimum for axis.Z - that is the
    # Z component of the rotated axis... check workings and definitions!

    phi = phi_start + 0.5 * phi_width

    # initialize search variables

    phi_a = phi_start
    phi_b = phi_start
    phi_c = phi_start

    dot_a = 0.0
    dot_b = 0.0
    dot_c = 0.0

    while phi < phi_end:
        RX = rot_x(phi)

        RXa = matvecmul(RX, a)
        RXb = matvecmul(RX, b)
        RXc = matvecmul(RX, c)

        if math.fabs(RXa[2]) > dot_a:
            dot_a = math.fabs(RXa[2])
            phi_a = phi

        if math.fabs(RXb[2]) > dot_b:
            dot_b = math.fabs(RXb[2])
            phi_b = phi

        if math.fabs(RXc[2]) > dot_c:
            dot_c = math.fabs(RXc[2])
            phi_c = phi
            
        phi += phi_width

    length_a = math.sqrt(dot(a, a))
    length_b = math.sqrt(dot(b, b))
    length_c = math.sqrt(dot(c, c))

    angle_a = math.acos(dot_a / length_a)
    angle_b = math.acos(dot_b / length_b)
    angle_c = math.acos(dot_c / length_c)

    return phi_a, phi_b, phi_c, angle_a, angle_b, angle_c

# for phi in images find when A.X = 0 and maximised and so on

# select some images

# run cell refinement

# run cell refinement in P1

# gather stats on results (quality of cell refinement)

# gather stats on results p1 (quality of cell refinement)

# divide the ratios to look at the quality of this as a lattice check

# repeat

if __name__ == '__main__':

    # assign the image name here... need user input checking

    image = sys.argv[1]
    count = int(sys.argv[2])

    # in here read first image to get the oscillation range

    from Wrappers.XIA.Diffdump import Diffdump
    from lib.Guff import nint

    dd = Diffdump()

    dd.set_image(image)

    header = dd.readheader()

    phi_start = header['phi_start']
    phi_width = header['phi_width']
    wavelength = header['wavelength']

    # then run labelit with three images 0,45,90 ish to get the
    # beam centre - now 35, 75

    _images = [1]
    if int(90.0 / phi_width) <= count:
        _images.append(int(35.0 / phi_width))
        _images.append(int(75.0 / phi_width))
    else:
        _images.append(int(0.5 * count))
        _images.append(count)

    li = LabelitIndex()
    li.setup_from_image(image)
    li.set_images(_images)
    li.autoindex()

    beam = li.get_beam()
    matrix = li.get_matrix()
    lattice = li.get_lattice()

    phi_end = phi_start + count * phi_width

    phi_a, phi_b, phi_c, a_a, a_b, a_c = compute_something_else(
        phi_start, phi_end, phi_width, wavelength, lattice, matrix)
    
    print '%.2f %.2f %.2f' % (phi_a, phi_b, phi_c)
    print '%.2f %.2f %.2f' % (a_a, a_b, a_c)

if __name__ == '__main__old__bits__':

    # print '# refined beam: %f %f' % beam

    # then compose the list of images

    images = [1]
    j = nint(5 / phi_width)
    while j <= count:
        images.append(j)
        j += nint(5 / phi_width)

    r = len(images) - 2

    for i in range(1):
        for j in range(i + 1, r + 1):
            for k in range(j + 1, r + 2):
                _i = images[i]
                _j = images[j]
                _k = images[k]

                li = LabelitIndex()
                li.setup_from_image(image)
                li.set_beam(beam)
                li.set_images([_i, _j, _k])

                li.autoindex()
            
                metric, rmsd = li.get_penalties()

                # finally in here put in the image numbers * phi width
            
                print '%2d %.2f %.2f %.4f %.4f' % \
                      (_i, (_j - _i + 1) * phi_width,
                       (_k - _i + 1) * phi_width,
                       metric, rmsd)

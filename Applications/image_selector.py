#!/usr/bin/env python
# image_selector.py
# Maintained by G.Winter
# 
# A jiffy application to help with the determination of the best images
# to use for cell refinement. This is to test possible assertions as
# to which images will result in the smallest errors in the cell 
# parameters from the Mosflm cell refinement process.
# 
# Requires:
#
# Crystal lattice (e.g. tP)
# Mosflm orientation matrix
# Phi start, end, delta
# First image number
# Mosaic
#
# Will write to the standard output the appropriate "postref multi"
# spell for Mosflm.
#
# 28/SEP/07

import os
import sys
import math

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])
    
if not os.environ['XIA2CORE_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

from Driver.DriverFactory import DriverFactory

from Experts.MatrixExpert import get_reciprocal_space_primitive_matrix

def nint(a):
    b = int(a)
    if a - b > 0.5:
        b += 1
    return b

def find_best_images(lattice, matrix, phi_start, phi_end, phi_width,
                     first_image, mosaic):
    '''Find the best images to use for cell refinement, based on the
    primitive orientation of the crystal.'''

    astar, bstar, cstar = get_reciprocal_space_primitive_matrix(
        lattice, matrix)

    num_images = nint((phi_end - phi_start) / phi_width)

    dtor = 180.0 / (4.0 * math.atan(1.0))    

    min_a = 0
    min_b = 0
    min_c = 0
    min_a_val = 1.0e6
    min_b_val = 1.0e6
    min_c_val = 1.0e6
    max_a = 0
    max_b = 0
    max_c = 0
    max_a_val = 0.0
    max_b_val = 0.0
    max_c_val = 0.0
    

    for j in range(num_images):

        phi = (j + 0.5) * phi_width + phi_start

        c = math.cos(phi / dtor)
        s = math.sin(phi / dtor)
        
        dot_a = math.fabs(-s * astar[0] + c * astar[2])
        dot_b = math.fabs(-s * bstar[0] + c * bstar[2])
        dot_c = math.fabs(-s * cstar[0] + c * cstar[2])        

        if dot_a < min_a_val:
            min_a = j
            min_a_val = dot_a

        if dot_a > max_a_val:
            max_a = k
            max_a_val = dot_a

        if dot_b < min_b_val:
            min_b = j
            min_b_val = dot_b

        if dot_b > max_b_val:
            max_b = k
            max_b_val = dot_b

        if dot_c < min_c_val:
            min_c = j
            min_c_val = dot_c

        if dot_c > max_c_val:
            max_c = k
            max_c_val = dot_c

    # next digest these - first put them in order, then define
    # wedges around them, then tidy up the resulting blocks

    best_images = [min_a, min_b, min_c, max_a, max_b, max_c]
    best_images.sort()

    half = max(2, nint(mosaic / phi_width))

    if best_images[0] < half:
        wedges = [(0, 2 * half)]
    else:
        wedges = [(best_images[0] - half, best_images[0] + half)]

    for i in best_images[1:]:
        handled = False
        
        for j in range(len(wedges)):
            if (i - half) < wedges[j][1]:
                # just stretch this wedge..
                wedges[j] = (wedges[j][0], wedges[j][i + half])
                handled = True
                break

        if not handled:
            wedges.append((i - half, i + half))

    # next print these wedges
    print 'postref multi segments %d' % len(wedges)

    for w in wedges:
        print 'process %d %d' % w
        print go

    return

def MosflmJiffy(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)    

    class MosflmJiffyClass(DriverInstance.__class__):
        '''A wrapper for mosflm for a specific purpose.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            
            self.set_executable('ipmosflm')

            self._image_range = None
            self._commands = None
            self._wedge_width = None
            self._num_wedges = 1

            # this will be keyed by the wedge middle images
            # used for cell refinement and contain sigmas
            # for a b c alpha beta gamma
            
            self._results = { }

        def set_image_range(self, image_range):
            self._image_range = image_range

        def set_commands(self, command_file):
            self._commands = []
            for record in open(command_file, 'r').readlines():
                if 'process' in record:
                    continue
                if 'postref multi' in record:
                    continue
                if record.strip() == 'go':
                    continue
                self._commands.append(record)

        def set_wedge_width(self, wedge_width):
            self._wedge_width = wedge_width

        def set_num_wedges(self, num_wedges):
            self._num_wedges = num_wedges

        def run_batches(self, batches):
            '''Run mosflm and get the results.'''

            self._runs += 1

            id = ''
            for b in batches:
                id += ' %d' % ((b[0] + b[1]) / 2)
            
            self.start()

            for record in self._commands:
                self.input(record)

            self.input('postref multi segments %d' % \
                       len(batches))

            for b in batches:
                self.input('process %d %d' % b)
                self.input('go')

            self.close_wait()

            output = self.get_all_output()

            errors = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0]

            for j in range(len(output)):
                if 'Cell refinement is complete' in output[j]:
                    errors = map(float, output[j + 3].split()[1:])

            print '%s %.4f %.4f %.4f %.4f %.4f %.4f' % \
                  (id, errors[0], errors[1], errors[2],
                   errors[3], errors[4], errors[5])

            return errors

        def run(self):

            self._runs = 0

            blocks = int((1 + self._image_range[1] - self._image_range[0]) /
                         self._wedge_width)


            f = self._image_range[0]

            end = blocks - self._num_wedges + 1

            for i in range(0, end):
                if self._num_wedges == 1:
                    w = self._wedge_width
                    batches = [(i * w + f, i * w + w)]
                    self._results[
                        i, 0, 0, 0, 0, 0] = \
                        self.run_batches(batches)

                    continue
                
                for j in range(i + 1, end + 1):
                    if self._num_wedges == 2:
                        w = self._wedge_width
                        batches = [(i * w + f, i * w + w),
                                   (j * w + f, j * w + w)]
                        self._results[
                            i, j, 0, 0, 0, 0] = \
                            self.run_batches(batches)
                        continue

                    for k in range(j + 1, end + 2):
                        if self._num_wedges == 3:
                            w = self._wedge_width
                            batches = [(i * w + f, i * w + w),
                                       (j * w + f, j * w + w),
                                       (k * w + f, k * w + w)]
                            
                            self._results[
                                i, j, k, 0, 0, 0] = \
                                self.run_batches(batches)
                            continue

                        for l in range(k + 1, end + 3):
                            if self._num_wedges == 4:
                                w = self._wedge_width
                                batches = [(i * w + f, i * w + w),
                                           (j * w + f, j * w + w),
                                           (k * w + f, k * w + w),
                                           (l * w + f, l * w + w)]
                                
                                self._results[
                                    i, j, k, l, 0, 0] = \
                                    self.run_batches(batches)
                                continue

                            for m in range(l + 1, end + 4):
                                if self._num_wedges == 5:
                                    w = self._wedge_width
                                    batches = [(i * w + f, i * w + w),
                                               (j * w + f, j * w + w),
                                               (k * w + f, k * w + w),
                                               (l * w + f, l * w + w),
                                               (m * w + f, m * w + w)]
                                    self._results[
                                        i, j, k, l, m, 0] = \
                                        self.run_batches(batches)
                                    
                                    continue

                                for n in range(m + 1, end + 5):
                                    if self._num_wedges == 6:
                                        w = self._wedge_width
                                        batches = [(i * w + f, i * w + w),
                                                   (j * w + f, j * w + w),
                                                   (k * w + f, k * w + w),
                                                   (l * w + f, l * w + w),
                                                   (m * w + f, m * w + w),
                                                   (n * w + f, n * w + w)]
                                        
                                        self._results[
                                            i, j, k, l, m, n] = \
                                            self.run_batches(batches)

            print '%d runs' % self._runs
            
    return MosflmJiffyClass()

if __name__ == '__main__':

    if len(sys.argv) < 6:
        raise RuntimeError, '%s start end width nwedge runit' % \
              sys.argv[0]

    mj = MosflmJiffy()

    mj.set_image_range((int(sys.argv[1]), int(sys.argv[2])))
    mj.set_wedge_width(int(sys.argv[3]))
    mj.set_num_wedges(int(sys.argv[4]))
    mj.set_commands(sys.argv[5])

    mj.run()

    

                                    
                                    

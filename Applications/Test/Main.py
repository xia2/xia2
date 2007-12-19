# main program

import os
import sys
import math
import threading
import time
import shutil
import Queue

from MosflmIndexer import autoindex as m_index
from BitsAndBobs import celldiff

inq = Queue.Queue(-1)
outq = Queue.Queue(-1)
tq = Queue.Queue(-1)

class Launcher(threading.Thread):

    def __init__(self, jid, template, directory, beam, cell):

        global inq

        threading.Thread.__init__(self)

        self._id = jid
        self._template = template
        self._directory = directory
        self._beam = beam
        self._cell = cell
        
        self._images = inq.get()
        
        return

    def run(self):

        global inq
        global outq
        global tq

        if len(self._images) == 2:
            print 'Running %d %d' % self._images
            print '(%d left...)' % inq.qsize()
        elif len(self._images) == 3:
            print 'Running %d %d %d' % self._images
            print '(%d left...)' % inq.qsize()
        elif len(self._images) == 4:
            print 'Running %d %d %d %d' % self._images
            print '(%d left...)' % inq.qsize()

        mi_id = self._id

        # make a directory

        startdir = os.getcwd()

        if not os.path.exists(os.path.join(startdir, mi_id)):
            os.makedirs(os.path.join(startdir, mi_id))
        
        cell = m_index(mi_id, self._template, self._directory,
                       self._beam, self._images)

        shutil.rmtree(os.path.join(startdir, mi_id), True)

        outq.put((self._images, celldiff(cell, self._cell)))
        tq.put(self._id)

        return

# FIXED these need to start with image 1

def generate_2(start, end, width):

    blocks = (1 + end - start) / width

    images = []

    for i in range(1, blocks):

            images.append((start,
                           i * width + start))

    return images

def generate_3(start, end, width):

    blocks = (1 + end - start) / width

    images = []

    for i in range(1, blocks - 1):

        for j in range(i + 1, blocks):

            images.append((start,
                           i * width + start,
                           j * width + start))

    return images

def generate_4(start, end, width):

    blocks = (1 + end - start) / width

    images = []

    for i in range(1, blocks - 2):

        for j in range(i + 1, blocks - 1):

            for k in range(j + 1, blocks):

                images.append((start,
                               i * width + start,
                               j * width + start,
                               k * width + start))

    return images

if __name__ == '__main__':

    template = '12287_1_E1_###.img'
    beam = (109.0, 105.0)
    directory = '/home/gw56/scratch/data/jcsg/1vpj/data/' + \
                'jcsg/als1/8.2.1/20040926/collection/TB0541B/12287/'

    images = generate_3(1, 90, 1)

    cell = (51.6924, 51.6986, 157.8512, 90.0399, 89.9713, 89.9465)

    #template = 'plat2a3_1_####.img'
    #directory = '/media/data2/graeme/plat'
    #beam = (93.35, 93.87)
    #cell = (90.2346, 90.1967, 90.2473, 90.0073, 90.0314, 89.9910)


    for i in images:
        inq.put(i)

    ncpu = 50

    for j in range(ncpu):
        tq.put('job%d' % j)

    while not inq.empty():
        tid = tq.get()
        l = Launcher(tid, template, directory, beam, cell)
        l.start()

    # next wait, then gather and print the results

    while threading.activeCount() > 1:
        print '%d threads remaining...' % threading.activeCount()
        time.sleep(1)

    results = { }

    while not outq.empty():
        o = outq.get()
        results[o[0]] = o[1]

    out = open('results.txt', 'w')

    for i in images:
        if len(i) == 2:
            print '%d %d %.4f %.4f' % (i[0], i[1],
                                       results[i][0], results[i][1])
            out.write('%d %d %.4f %.4f\n' % \
                      (i[0], i[1], results[i][0], results[i][1]))
        if len(i) == 3:
            print '%d %d %d %.4f %.4f' % (i[0], i[1], i[2],
                                             results[i][0], results[i][1])
            out.write('%d %d %d %.4f %.4f\n' % \
                      (i[0], i[1], i[2], results[i][0], results[i][1]))
        if len(i) == 4:
            print '%d %d %d %d %.4f %.4f' % (i[0], i[1], i[2], i[3],
                                             results[i][0], results[i][1])
            out.write('%d %d %d %d %.4f %.4f\n' % \
                      (i[0], i[1], i[2], i[3], results[i][0], results[i][1]))

    
    print '%d jobs run' % len(images)
    

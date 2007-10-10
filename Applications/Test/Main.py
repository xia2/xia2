# main program

import os
import sys
import math
import threading
import Queue

from MosflmIndexer import autoindex as m_index
from BitsAndBobs import celldiff

inq = Queue.Queue(-1)
outq = Queue.Queue(-1)
tq = Queue.Queue(-1)

class Launcher(threading.Thread):

    def __init__(self, template, directory, beam, cell):

        global inq

        threading.Thread.__init__(self)

        self._template = template
        self._directory = directory
        self._beam = beam
        self._cell = cell
        
        self._images = inq.get()
        

        return

    def run(self):

        global outq
        global tq

        cell = m_index(self._template, self._directory,
                       self._beam, self._images)

        outq.put((self._images, celldiff(cell, self._cell)))
        tq.put(1)

        return

def generate_3(start, end, width):

    blocks = (end - start) / width

    images = []

    for i in range(0, blocks - 2):

        for j in range(i + 1, blocks - 1):

            for k in range(j + 1, blocks):

                images.append((i * width + start,
                               j * width + start,
                               k * width + start))

    return images

if __name__ == '__main__':

    template = '12287_1_E1_###.img'
    beam = (109.0, 105.0)
    directory = '/home/gw56/scratch/data/jcsg/1vpj/data/' + \
                'jcsg/als1/8.2.1/20040926/collection/TB0541B/12287/'

    images = generate_3(1, 90, 5)

    cell = (51.6924, 51.6986, 157.8512, 90.0399, 89.9713, 89.9465)

    for i in images:
        inq.put(i)

    ncpu = 10

    for j in range(ncpu):
        tq.put(1)

    while not inq.empty():
        t = tq.get()
        l = Launcher(template, directory, beam, cell)
        l.start()

    # next gather and print the results

    results = { }

    while not outq.empty():
        o = outq.get()
        results[o[0]] = o[1]

    for i in images:
        print '%2d %2d %2d %.4f %.4f' % (i[0], i[1], i[2],
                                         results[i][0], results[i][1])

    

    

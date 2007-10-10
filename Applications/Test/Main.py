# main program

import os
import sys
import math
import threading
import Queue

from MosflmIndexer import autoindex as m_index
from BitsAndBobs import celldiff

inq = Queue.Queue(-1)
inl = []
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

    images = generate_3(1, 10, 1)

    for i in images:

        print '%2d %2d %2d' % i

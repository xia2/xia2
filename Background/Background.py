#!/usr/bin/env python
# Background.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to allow background (i.e. threaded) running of tasks.

import threading
import exceptions
import time
import os
import sys
import traceback

class Background(threading.Thread):
  '''A class to allow background operation.'''

  def __init__(self, o, m, a = None):
    '''Create a thread to call o.m(a).'''

    threading.Thread.__init__(self)

    if not hasattr(o, m):
      raise RuntimeError, 'method missing from object'

    self._object = o
    self._method = m
    self._arguments = a
    self._exception = None
    self._traceback = None
    self._result = None

    return

  def run(self):
    '''Run o.m with arguments a in background.'''

    task = getattr(self._object, self._method)

    try:
      if self._arguments:
        self._result = task(self._arguments)
      else:
        self._result = task()
    except exceptions.Exception, e:
      self._traceback = traceback.format_exc()
      self._exception = e

    return

  def get_traceback(self):
    return self._traceback

  def stop(self):
    '''Rejoin the thread.'''

    self.join()

    if self._exception:
      raise self._exception

    return self._result

if __name__ == '__main__':
  from xia2.Driver.DriverFactory import DriverFactory

  drivers = []
  backgrounds = []

  for j in range(4):

    driver = DriverFactory.Driver()
    driver.set_executable('/tmp/920/cpu.py')
    driver.start()
    drivers.append(driver)
    backgrounds.append(Background(driver, 'close_wait'))
    backgrounds[-1].start()

  for j in range(4):
    backgrounds[j].stop()

if __name__ == '__cpu.py__':
  # this be a script! #!/usr/bin/env python

  import math
  import sys

  for record in sys.stdin:
    pass

  def factor(v):
    m = int(math.sqrt(v)) + 1

    for j in range(2, m):
      if v % j == 0:
        f = [j]
        f.extend(factor(v / j))
        return f

    return [v]

  for j in range(10000000000, 10000000100):
    print factor(j)

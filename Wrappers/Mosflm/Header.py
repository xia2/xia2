from __future__ import absolute_import, division, print_function

def Header(DriverType = None):
  '''A factory for HeaderWrapper(ipmosflm) classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class HeaderWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      import os
      self.set_executable(os.path.join(
        os.environ['CCP4'], 'bin', 'ipmosflm'))

      from collections import defaultdict
      self._headers = defaultdict(dict)

    def __call__(self, fp, images = None):
      from xia2.Handlers.Streams import Debug

      if images is None:
        images = fp.get_matching_images()

      Debug.write('Running mosflm to read header from images %d to %d' % \
                  (min(images), max(images)))

      self.start()
      self.input('template "%s"' % fp.get_template())
      self.input('directory "%s"' % fp.get_directory())
      self.input('image %d' % images[0])
      self.input('head')
      self.input('go')
      for image in images[1:]:
        self.input('image %d' % image)
        self.input('head brief')
        self.input('go')
      self.close_wait()

      image = -1

      for record in self.get_all_output():
        if '===> image' in record:
          image = int(record.split()[-1])
          continue
        if 'Start and end phi values' in record:
          tokens = record.split()
          start, end = float(tokens[-4]), float(tokens[-2])
          image = int(tokens[7])
          self._headers['phi-start'][image] = start
          self._headers['phi-end'][image] = end
        if 'recognized as:' in record:
          self._headers['mosflm-detector'] = record.split()[-1]
        if 'Wavelength of' in record:
          self._headers['wavelength'] = float(
            record.split()[2].replace('A', ''))

  return HeaderWrapper()

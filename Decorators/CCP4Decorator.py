#!/usr/bin/env python
# CCP4Decorator.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 25th May 2006
#
# A decorator to add hklin and hklout methods to a Driver instance.
# This will probably include some other interesting things like
# xyzin etc at some point in the future, once such things become
# important.
#
# Supported Keywords:
# HKLIN input MTZ reflection file (.mtz)
# HLKOUT output MTZ reflection file (.mtz)
# MAPIN input map file (.map)
# MAPOUT output map file (.map)
# XYZIN input coordinate file (.pdb)
# XYZOUT output coordinate file (.pdb)
#
# All accessed via setHklin(hklin) getHklin() etc.
#
# List from:
#
# http://www.ccp4.ac.uk/dist/html/ccp4.html
#
# Done:
# Add a mechanism for recording and parsing of loggraph output.
#
# FIXME 06/NOV/06 would be fun to record the HKLIN and HKLOUT files to
#                 be able to track how the processing went and what jobs
#                 were executed to make that happen...
#
# FIXME 24/NOV/06 need to be able to cope with columns in loggraph output
#                 running together.
#

from __future__ import absolute_import, division
import os

from xia2.Decorators.DecoratorHelper import inherits_from

def CCP4DecoratorFactory(DriverInstance):
  '''Create a CCP4 decorated Driver instance - based on the Driver
  instance which is passed in. This is an implementation of
  dynamic inheritance. Note well - this produces a new object and
  leaves the original unchanged.'''

  DriverInstanceClass = DriverInstance.__class__

  # verify that the input object satisfies the Driver interface -
  # in this case that at some point it inherited from there.
  # note well - instances of DefaultDriver must not be used
  # directly.

  if not inherits_from(DriverInstanceClass, 'DefaultDriver'):
    raise RuntimeError('object %s is not a Driver implementation' % \
          str(DriverInstance))

  # verify that the object matches the Driver specification

  class CCP4Decorator(DriverInstanceClass):
    '''A decorator class for a Driver object which will add some nice CCP4
    sugar on top.'''

    # to get hold of the original start() methods and so on - and
    # also to the parent class constructor
    _original_class = DriverInstanceClass

    def __init__(self):
      # note well - this is evil I am calling another classes constructor
      # in here. Further this doesn't know what it is constructing!

      self._original_class.__init__(self)

      self._hklin = None
      self._hklout = None
      self._xyzin = None
      self._xyzout = None
      self._mapin = None
      self._mapout = None

      # somewhere to store the loggraph output
      self._loggraph = { }

      # put the CCP4 library directory at teh start of the
      # LD_LIBRARY_PATH in case it mashes CCP4 programs...
      # N.B. need to check the syntax!
      if 'CLIB' in os.environ and os.name == 'posix':
        if os.uname()[0] == 'Darwin':
          self.add_working_environment('DYLD_LIBRARY_PATH',
                                       os.environ['CLIB'])
        else:
          self.add_working_environment('LD_LIBRARY_PATH',
                                       os.environ['CLIB'])

    def set_hklin(self, hklin):
      return self.setHklin(hklin)

    def get_hklin(self):
      return self.getHklin()

    def check_hklin(self):
      return self.checkHklin()

    def setHklin(self, hklin):
      self._hklin = hklin

    def getHklin(self):
      return self._hklin

    def checkHklin(self):
      if self._hklin is None:
        raise RuntimeError('hklin not defined')
      if not os.path.exists(self._hklin):
        raise RuntimeError('hklin %s does not exist' % self._hklin)

    def set_hklout(self, hklout):
      return self.setHklout(hklout)

    def get_hklout(self):
      return self.getHklout()

    def check_hklout(self):
      return self.checkHklout()

    def setHklout(self, hklout):
      self._hklout = hklout

    def getHklout(self):
      return self._hklout

    def checkHklout(self):
      if self._hklout is None:
        raise RuntimeError('hklout not defined')

      # check that these are different files!

      if self._hklout == self._hklin:
        raise RuntimeError( \
              'hklout and hklin are the same file (%s)' % \
              str(self._hklin))

    def set_xyzin(self, xyzin):
      return self.setXyzin(xyzin)

    def get_xyzin(self):
      return self.getXyzin()

    def check_xyzin(self):
      return self.checkXyzin()

    def setXyzin(self, xyzin):
      self._xyzin = xyzin

    def getXyzin(self):
      return self._xyzin

    def checkXyzin(self):
      if self._xyzin is None:
        raise RuntimeError('xyzin not defined')
      if not os.path.exists(self._xyzin):
        raise RuntimeError('xyzin %s does not exist' % self._xyzin)

    def set_xyzout(self, xyzout):
      return self.setXyzout(xyzout)

    def get_xyzout(self):
      return self.getXyzout()

    def check_xyzout(self):
      return self.checkXyzout()

    def setXyzout(self, xyzout):
      self._xyzout = xyzout

    def getXyzout(self):
      return self._xyzout

    def checkXyzout(self):
      if self._xyzout is None:
        raise RuntimeError('xyzout not defined')

    def set_mapin(self, mapin):
      return self.setMapin(mapin)

    def get_mapin(self):
      return self.getMapin()

    def check_mapin(self):
      return self.checkMapin()

    def setMapin(self, mapin):
      self._mapin = mapin

    def getMapin(self):
      return self._mapin

    def checkMapin(self):
      if self._mapin is None:
        raise RuntimeError('mapin not defined')
      if not os.path.exists(self._mapin):
        raise RuntimeError('mapin %s does not exist' % self._mapin)

    def set_mapout(self, mapout):
      return self.setMapout(mapout)

    def get_mapout(self):
      return self.getMapout()

    def check_mapout(self):
      return self.checkMapout()

    def setMapout(self, mapout):
      self._mapout = mapout

    def getMapout(self):
      return self._mapout

    def checkMapout(self):
      if self._mapout is None:
        raise RuntimeError('mapout not defined')

    def describe(self):
      '''An overloading of the Driver describe() method.'''

      description = 'CCP4 program: %s' % self.get_executable()

      if self._hklin is not None:
        description += ' %s' % ('hklin')
        description += ' %s' % (self._hklin)

      if self._hklout is not None:
        description += ' %s' % ('hklout')
        description += ' %s' % (self._hklout)

      if self._xyzin is not None:
        description += ' %s' % ('xyzin')
        description += ' %s' % (self._xyzin)

      if self._xyzout is not None:
        description += ' %s' % ('xyzout')
        description += ' %s' % (self._xyzout)

      if self._mapin is not None:
        description += ' %s' % ('mapin')
        description += ' %s' % (self._mapin)

      if self._mapout is not None:
        description += ' %s' % ('mapout')
        description += ' %s' % (self._mapout)

      return description

    def start(self):
      '''Add all the hklin etc to the command line then call the
      base classes start() method. Also make any standard ccp4
      scratch directories. The latter shouldnt be needed however.'''

      for env in ['BINSORT_SCR', 'CCP4_SCR']:
        if env in os.environ:
          directory = os.environ[env]
          self.add_scratch_directory(directory)
          try:
            os.mkdir(directory)
          except:
            pass

      if self._hklin is not None:
        self.add_command_line('hklin')
        self.add_command_line(self._hklin)

      if self._hklout is not None:
        self.add_command_line('hklout')
        self.add_command_line(self._hklout)

      if self._xyzin is not None:
        self.add_command_line('xyzin')
        self.add_command_line(self._xyzin)

      if self._xyzout is not None:
        self.add_command_line('xyzout')
        self.add_command_line(self._xyzout)

      if self._mapin is not None:
        self.add_command_line('mapin')
        self.add_command_line(self._mapin)

      if self._mapout is not None:
        self.add_command_line('mapout')
        self.add_command_line(self._mapout)

      # delegate the actual starting to the parent class
      self._original_class.start(self)

    def check_ccp4_errors(self):
      '''Look through the standard output for a few "usual" CCP4
      errors, for instance incorrect file formats &c.'''

      # check that the program has finished...

      if not self.finished():
        raise RuntimeError('program has not finished')

      for line in self.get_all_output():
        if 'CCP4 library signal' in line:
          error = line.split(':')[1].strip()

          # throw away the "status" in brackets

          if '(' in error:
            error = error.split('(')[0]

          # handle specific cases...

          if 'Write failed' in error:
            # work out why...
            for l in self.get_all_output():
              if '>>>>>> System signal' in l:
                cause = l.split(':')[1].split('(')[0]
                raise RuntimeError('%s:%s' % (error, cause))

          # then cope with the general case

          else:
            raise RuntimeError(error)

    def get_ccp4_status(self):
      '''Check through the standard output and get the program
      status. Note well - this will only work if called once the
      program is finished.'''

      # check that the program has finished...

      if not self.finished():
        raise RuntimeError('program has not finished')

      # look in the last 10 lines for the status

      # Added 1/SEP/06 to check if .exe is on the end of the
      # command line...

      program_name = os.path.split(self.get_executable())[-1].lower()
      if program_name[-4:] == '.exe':
        program_name = program_name[:-4]

      # special case for FFT which calls itself FFTBIG in the status
      # output..

      if program_name == 'fft':
        program_name = 'fftbig'

      for line in self.get_all_output()[-10:]:
        l = line.split()
        if len(l) > 1:
          if l[0][:-1].lower() == program_name:
            # then this is the status line
            status = line.split(':')[1].replace('*', '')
            return status.strip()

          if l[0][:-1].lower() == program_name.split('-')[0]:
            # then this is also probably the status line
            status = line.split(':')[1].replace('*', '')
            return status.strip()

      raise RuntimeError('could not find status')

    def parse_ccp4_loggraph(self):
      '''Look through the standard output of the program for
      CCP4 loggraph text. When this is found store it in a
      local dictionary to allow exploration.'''

      # reset the loggraph store
      self._loggraph = { }

      output = self.get_all_output()

      for i in range(len(output)):
        line = output[i]
        if '$TABLE' in line:

          n_dollar = line.count('$$')

          current = line.split(':')[1].replace('>',
                                                        '').strip()
          self._loggraph[current] = { }
          self._loggraph[current]['columns'] = []
          self._loggraph[current]['data'] = []

          loggraph_info = ''

          # FIXME 09/FEB/07 this is assumed to represent the
          # end of a loggraph but really it isn't

          # almost exactly one year later this has come back to
          # bite me - with chef! indeed... OK, in Smartie the
          # way this worked was to count the number of $$
          # following the $TABLE spell - when this was equal to
          # 4 this table is complete. Good idea.

          # while not 'inline graphs' in line and not 'FONT' in line:
          while n_dollar < 4:
            n_dollar += line.count('$$')
            loggraph_info += line

            if n_dollar == 4:
              break

            i += 1
            line = output[i]

          # at this stage I should have the whole 9 yards in
          # a single string...

          tokens = loggraph_info.split('$$')
          self._loggraph[current]['columns'] = tokens[1].split()

          if len(tokens) < 4:
            raise RuntimeError('loggraph "%s" broken' % current)

          data = tokens[3].split('\n')

          # pop takes the data off the end so...
          # data.reverse()

          columns = len(self._loggraph[current]['columns'])

          # while len(data) > 0:
          # record = []
          # for i in range(columns):
          # record.append(data.pop())
          # self._loggraph[current]['data'].append(record)

          # code around cases where columns merge together...

          for j in range(len(data)):
            record = data[j].split()
            if len(record) == columns:
              self._loggraph[current]['data'].append(record)

      return self._loggraph

  return CCP4Decorator()

if __name__ == '__main__':
  from xia2.Driver.DriverFactory import DriverFactory

  d = DriverFactory.Driver('script')

  d = CCP4DecoratorFactory(d)

  from pydoc import help

  print help(d.__class__)

#!/usr/bin/env python
# SunGridEngineClusterDriver.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 20th June 2006
#
# A Driver implementation to work with sun grid engine clusters via the
# "qsub" shell command. This is based on ScriptDriver. This works like...
#
# Inherited from DefaultClusterDriver

from __future__ import absolute_import, division

import os
import subprocess

from xia2.Driver.DefaultClusterDriver import DefaultClusterDriver

class SunGridEngineClusterDriver(DefaultClusterDriver):

  def __init__(self):

    DefaultClusterDriver.__init__(self)
    self._job_id = 0

  def _check_sge_errors(self, sge_stderr_list):
    '''Check through the standard error from Sun Grid Engine
    for indications that something went wrong... called from
    cleanup()'''

    for o in sge_stderr_list:
      if 'command not found' in o:
        missing_program = o.split(':')[2].strip()
        raise RuntimeError('executable "%s" missing' % \
              missing_program)

  def submit(self):
    '''This is where most of the work will be done - in here is
    where the script itself gets written and run, and the output
    file channel opened when the process has finished...'''

    # this will return almost instantly, once the job is in
    # the queue
    pipe = subprocess.Popen(['qsub', '-V', '-cwd',
                             '%s.sh' % self._script_name],
                            cwd = self._working_directory,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE)

    # this will get all of the output as a tuple (stdout, stderr)
    stdout, stderr = pipe.communicate()

    # check the standard error
    if stderr:
      # something probably went wrong
      if 'error opening' in stderr:
        raise RuntimeError('executable "%s" does not exist' % \
              stdout.split('\n')[0].split(':')[0].replace(
            'error opening ', ''))

    # probably everything is ok then

    # the job id etc go to the standard output
    self._job_id = stdout.split('\n')[0].split()[2]

  def cleanup(self):
    '''Cleanup and close-out.'''

    sge_stdout = os.path.join(self._working_directory,
                              '%s.sh.o%s' % (self._script_name,
                                             self._job_id))

    sge_stderr = os.path.join(self._working_directory,
                              '%s.sh.e%s' % (self._script_name,
                                             self._job_id))

    # check the standard error file for any indications that
    # something went wrong running this job...

    error_output = open(sge_stderr, 'r').readlines()
    self._check_sge_errors(error_output)

    # check the stderr records for errors...
    self.check_for_error_text(error_output)

    # at this stage I should delete the sge specific files defined
    # above to be tidy...

    try:
      os.remove(sge_stdout)
      os.remove(sge_stderr)
    except Exception:
      # something wrong with this deletion?
      pass

  def kill(self):
    '''This is meaningless...'''

    pass


if __name__ == '__main__':
  # Then run a simple test

  d = SunGridEngineClusterDriver()

  d.set_executable('ExampleProgram')
  d.start()
  d.close()

  while True:
    line = d.output()

    if not line:
      break

    print line.strip()

#!/usr/bin/env python
# DefaultClusterDriver.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 19th June 2006
#
# A general ClusterDriver which should be inherited from for specific
# cluster driver implementations. This provides facility for recording
# jobs finishing, writing scripts etc, but not the queue-specific
# submission, which should be handled by classes derived from this.
#

from __future__ import absolute_import, division, print_function

import os
import time

from xia2.Driver.DefaultDriver import DefaultDriver
from xia2.Driver.DriverHelper import executable_exists, script_writer


class DefaultClusterDriver(DefaultDriver):
    """A general class for Driving programs on clusters. This should not
  be used directly!"""

    def __init__(self):
        super(DefaultClusterDriver, self).__init__()

        if os.name != "posix":
            raise RuntimeError('os "%s" not supported' % os.name)

        DefaultDriver.__init__(self)

        self._script_command_line = []
        self._script_standard_input = []

        self._script_name = self._name

        self._script_status = 0

        # this is opened by the close() method and read by output
        # from self._script_name.xout

        self._output_file = None

    def set_name(self, name):
        """Set the name to something sensible."""
        self._script_name = name

    def start(self):
        """This is pretty meaningless in terms of running things through
    scripts..."""

        for c in self._command_line:
            self._script_command_line.append(c)

    def submit(self):
        """Submit to the queue - this MUST be overloaded."""
        raise NotImplementedError("do not use this class directly")

    def cleanup(self):
        """Cleanup after the job is finished."""
        raise NotImplementedError("do not use this class directly")

    def check(self):
        """NULL overloading of the default check method."""
        return True

    def _check_executable(self, executable):
        """Pass this on to executable_exists."""

        return executable_exists(executable)

    def _input(self, record):
        self._script_standard_input.append(record)

    def _output(self):
        return self._output_file.readline()

    def _status(self):
        return self._script_status

    def close(self):
        """This is where most of the work will be done - in here is
    where the script itself gets written and run, and the output
    file channel opened when the process has finished..."""

        # ensure that there is no .xstatus file here

        script_writer(
            self._working_directory,
            self._script_name,
            self._executable,
            self._script_command_line,
            self._working_environment,
            self._script_standard_input,
            mkdirs=self._scratch_directories,
        )

        # call the queue submission - this will be overloaded
        self.submit()

        # now have a while loop watching for the .xstatus file
        # using os.path.exists()

        xstatus_file = os.path.join(
            self._working_directory, "%s.xstatus" % self._script_name
        )

        while True:
            if os.path.exists(xstatus_file):
                time.sleep(1)
                break
            time.sleep(5)

        try:
            with open(xstatus_file, "r") as fh:
                self._script_status = int(fh.read())
        except Exception:
            self._script_status = 0

        # set this up for reading the "standard output" of the job.
        self._output_file = open(
            os.path.join(self._working_directory, "%s.xout" % self._script_name), "r"
        )

        self.cleanup()

    def kill(self):
        """This is meaningless..."""
        pass

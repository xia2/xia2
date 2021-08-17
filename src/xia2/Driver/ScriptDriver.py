import os
import subprocess

from xia2.Driver.DefaultDriver import DefaultDriver
from xia2.Driver.DriverHelper import script_writer


class ScriptDriver(DefaultDriver):
    def __init__(self):
        super().__init__()

        self._script_command_line = []
        self._script_standard_input = []

        self._script_name = self._name

        self._script_status = 0

        # this is opened by the close() method and read by output
        # from self._script_name.xout

        self._output_file = None

    def reset(self):
        DefaultDriver.reset(self)

        self._script_command_line = []
        self._script_standard_input = []

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

    def check(self):
        """NULL overloading of the default check method."""
        return True

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

        script_writer(
            self._working_directory,
            self._script_name,
            self._executable,
            self._script_command_line,
            self._working_environment,
            self._script_standard_input,
        )

        if os.name == "posix":
            pipe = subprocess.Popen(
                ["bash", "%s.sh" % self._script_name], cwd=self._working_directory
            )

        else:
            pipe = subprocess.Popen(
                ["%s.bat" % self._script_name], cwd=self._working_directory, shell=True
            )

        self._script_status = pipe.wait()

        # at this stage I should read the .xstatus file to determine if the
        # process has indeed finished - though it should have done...

        try:
            xstatus_file = os.path.join(
                self._working_directory, "%s.xstatus" % self._script_name
            )
            with open(xstatus_file) as fh:
                self._script_status = int(fh.read())
        except Exception:
            # this could happen on windows if the program in question
            # is a batch file...
            self._script_status = 0

        self._output_file = open(
            os.path.join(self._working_directory, "%s.xout" % self._script_name)
        )

    def kill(self):
        """This is meaningless..."""

        pass

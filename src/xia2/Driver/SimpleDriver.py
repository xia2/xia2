import copy
import os
import subprocess
import time

from xia2.Driver.DefaultDriver import DefaultDriver
from xia2.Driver.DriverHelper import kill_process


class SimpleDriver(DefaultDriver):
    def __init__(self):
        super().__init__()

        self._popen = None
        self._popen_status = None

    def start(self):
        if self._executable is None:
            raise RuntimeError("no executable is set.")

        if os.name == "nt":
            # pass in CL as a list of tokens
            command_line = []
            command_line.append(self._executable)
            for c in self._command_line:
                command_line.append(c)
        else:
            # now pass in the command line as a string and allow the
            # shell to parse it - note well though that the tokens
            # on the command line are quoted..

            command_line = self._executable
            for c in self._command_line:
                command_line += " '%s'" % c

        environment = copy.deepcopy(os.environ)

        for name in self._working_environment:
            added = self._working_environment[name][0]
            for value in self._working_environment[name][1:]:
                added += f"{os.pathsep}{value}"

            if name in environment and name not in self._working_environment_exclusive:
                environment[name] = "%s%s%s" % (added, os.pathsep, environment[name])
            else:
                environment[name] = added

        self._runtime_log["process start"] = time.time()
        self._popen = subprocess.Popen(
            command_line,
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self._working_directory,
            universal_newlines=True,
            env=environment,
            shell=True,
        )
        self._popen_status = None

    def _input(self, record):
        if not self.check():
            raise RuntimeError("child process has termimated")

        try:
            self._popen.stdin.write(record)
        except OSError:
            while True:
                line = self.output()
                if not line.strip():
                    break
                self.check_for_errors()
            raise  # unexpected error

    def _output(self):
        # need to put some kind of timeout facility on this...

        return self._popen.stdout.readline()

    def _status(self):
        # get the return status of the process

        if self._popen_status is not None:
            return self._popen_status

        if self._popen:
            return self._popen.poll()

        return 0

    def close(self):
        if not self.check():
            raise RuntimeError("child process has termimated")

        self._popen.stdin.close()

    def cleanup(self):
        self._popen_status = self._popen.poll()
        self._popen = None

    def kill(self):
        kill_process(self._popen)

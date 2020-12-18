import logging
import os
import time
import signal

import xia2.Driver.timing
from xia2.Driver.DriverHelper import (
    error_abrt,
    error_fp,
    error_kill,
    error_library_not_loaded,
    error_missing_library,
    error_no_program,
    error_python_traceback,
    error_segv,
    executable_exists,
    generate_random_name,
)
from xia2.DriverExceptions.NotAvailableError import NotAvailableError

logger = logging.getLogger("xia2.Driver.DefaultDriver")


class DefaultDriver:
    """A class to run other programs, specifically from the CCP4 suite
    but also others, to achieve crystallographic processes. This will also
    provide functionality for controlling the job, limited only by the
    needs of portability across Windows, Macintosh OS X and Linux."""

    def __init__(self):
        """Initialise the Driver instance."""
        super().__init__()

        # settings for the job to run
        self._executable = None

        # command_line should be a list of separate elements
        # note well that this is different to how things worked before
        self._command_line = []
        self._working_directory = os.getcwd()
        self._working_environment = {}
        self._working_environment_exclusive = set()

        # presuming here that the number of input commands is
        # usually small
        self._standard_input_records = []

        # this will be bigger but that is ok...
        self._standard_output_records = []

        # optional - possibly useful if using a batch submission
        # system or wanting to describe better what the job is doing
        self._input_files = []

        self._scratch_directories = []

        self._log_file = None
        self._log_file_name = None

        self._task = None

        self._finished = False

        self._name = generate_random_name()

        # this will be assigned if auto-logfiler (c/f xia2.lib.guff)
        # note that there are no guidelines for this...!
        # bug 2690... xia2 process id is name...

        self._xpid = 0

        self._cpu_threads = 1

        self._runtime_log = {"object initialization": time.time()}

    def __del__(self):
        # the destructor - close the log file etc.

        if self._log_file is not None:
            self._log_file.flush()
            self._log_file.close()

    # getter and setter methods

    def set_xpid(self, xpid):
        self._xpid = xpid

    def get_xpid(self):
        return self._xpid

    def set_cpu_threads(self, cpu_threads):
        self._cpu_threads = cpu_threads

    def _check_executable(self, executable):
        """Pass this on to executable_exists."""

        return executable_exists(executable)

    def set_executable(self, executable):
        """Set the name of the executable."""

        full_path = self._check_executable(executable)

        if full_path:
            self._executable = full_path
        else:
            raise NotAvailableError("executable %s does not exist in PATH" % executable)

    def get_executable(self):
        """Get the name of the executable."""
        return self._executable

    def set_working_environment(self, name, value):
        """Overwrite the environment for processing."""

        self._working_environment[name] = [value]

        if name not in self._working_environment_exclusive:
            self._working_environment_exclusive.add(name)

    def add_working_environment(self, name, value):
        """Add an extra token to the environment for processing."""
        if name not in self._working_environment:
            self._working_environment[name] = []
        self._working_environment[name].append(value)

    def add_scratch_directory(self, directory):
        """Add a scratch directory."""

        if directory not in self._scratch_directories:
            self._scratch_directories.append(directory)

    def set_task(self, task):
        """Set a helpful record about what the task is doing."""

        self._task = task

    def clear_command_line(self):
        """Clear the command line."""

        self._command_line = []

    def get_command_line(self):
        """Get the command line."""

        return self._command_line

    def add_command_line(self, command_line_token):
        """Add a token to the command line."""

        if self._command_line is None:
            self.clearCommand_line()
        elif isinstance(command_line_token, list) or isinstance(
            command_line_token, tuple
        ):
            for token in command_line_token:
                self._command_line.append(token)
        else:
            assert isinstance(command_line_token, str)
            self._command_line.append(command_line_token)

    def set_command_line(self, command_line):
        """Set the command line which wants to be run."""

        if not isinstance(command_line, type([])):
            raise RuntimeError("command line should be a list")

        self._command_line = command_line

    def set_working_directory(self, working_directory):
        """Set the working directory for this process."""

        self._working_directory = working_directory

    def get_working_directory(self):
        """Get the working directory for this process."""

        return self._working_directory

    def describe(self):
        """Give a short description of what this job will do..."""

        return "%s task" % self.getExecutable()

    def reset(self):
        """Reset the output things."""

        self._standard_input_records = []
        self._standard_output_records = []

        self._command_line = []

        # optional - possibly useful if using a batch submission
        # system or wanting to describe better what the job is doing
        self._input_files = []
        self._scratch_directories = []
        if self._log_file is not None:
            self._log_file.flush()
            self._log_file.close()
        self._log_file = None

        # reset the name to a new value...
        self._name = generate_random_name()

    def start(self):
        """Start the sub process - which is to say if interactive start the
        interactive job, if batch start the batch job. This implementation
        will fail because youre not supposed to use it!"""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

    def check(self):
        """Check that the running process is ok - this is an optional
        interface which may not be defined for some implementations of
        Driver. Returns True if children are all ok, False otherwise."""

        return True

    def check_for_error_text(self, records):
        """Check records for error-like information."""

        for record in records:
            error_library_not_loaded(record)
            error_no_program(record)
            error_missing_library(record)
            error_segv(record)
            error_kill(record)
            error_abrt(record)
            error_fp(record)

        try:
            error_python_traceback(records)
        except Exception:
            raise RuntimeError(
                "%s terminated with an error: see %s for more details"
                % (os.path.basename(self._executable), self.get_log_file())
            )

    def check_for_errors(self):
        """Work through the standard output of the program and see if
        any standard error conditions (listed in DriverHelper) can be
        found. This will raise an appropriate exception if an error
        is found."""

        # only look for errors in the last 30 lines of the standard
        # output - if something went wrong, it went wrong in there...

        self.check_for_error_text(self._standard_output_records[-30:])
        # next check the status

        self.check_return_code()

    def check_return_code(self):
        """Check the return code for indications of errors."""

        code = self.status()
        if not code:
            return

        if self.get_log_file():
            log_file_extra = ": see %s for more details" % self.get_log_file()
        else:
            log_file_extra = ""
        executable = "%s" % os.path.basename(self._executable)

        if os.name == "nt":
            if code == 3:
                raise RuntimeError("child error")

        else:
            # return codes in POSIX are -ve

            segv = signal.SIGSEGV * -1
            kill = signal.SIGKILL * -1
            abrt = signal.SIGABRT * -1

            if code == segv:
                raise RuntimeError(
                    "{executable}: child segmentation fault{log_file_extra}".format(
                        executable=executable, log_file_extra=log_file_extra
                    )
                )

            if code == kill:
                raise RuntimeError(
                    "{executable} killed{log_file_extra}".format(
                        executable=executable, log_file_extra=log_file_extra
                    )
                )

            if code == abrt:
                raise RuntimeError(
                    "{executable} failed{log_file_extra}".format(
                        executable=executable, log_file_extra=log_file_extra
                    )
                )

        raise RuntimeError(
            "{executable} subprocess failed with exitcode {code}{log_file_extra}".format(
                executable=executable, code=code, log_file_extra=log_file_extra
            )
        )

    def _input(self, record):
        """Pass record into the child programs standard input."""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

    def input(self, record, newline=True):
        """Pass record into child program via _input & copying mechanism."""

        # copy record somehow

        if newline:
            record = "%s\n" % record

        self._standard_input_records.append(record)

        # this method should be overridden by the implementation
        # of the Driver

        self._input(record)

    def _output(self):
        """Pass record from the child programs standard output."""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

    def output(self):
        """Pull a record from the child program via _output."""

        record = self._output()

        # copy record somehow
        self._standard_output_records.append(record)

        if self._log_file is not None:
            self._log_file.write(record)

            # FIXME 07/NOV/06 I have noticed that sometimes
            # information is missed from the log files - perhaps
            # flushing here will help??

            self._log_file.flush()

        # presume if there is no output that the program has finished
        if not record:
            self._finished = True
        else:
            self._finished = False

        return record

    def finished(self):
        """Check if the program has finished."""

        return self._finished

    def write_log_file(self, filename):

        if self._log_file:
            # close the existing log file
            self._log_file.close()
            self._log_file = None

        # should have bufsize = 0 here... won't work on mac!

        self._log_file = open(filename, "w")
        if self._standard_output_records:
            for s in self._standard_output_records:
                self._log_file.write(s)

        self._log_file_name = self._log_file.name

    def get_log_file(self):
        """Get a pointer to the log file if set."""

        if self._log_file_name:
            return self._log_file_name

        return ""

    def get_all_output(self):
        """Return all of the output of the job."""

        return self._standard_output_records

    def close(self):
        """Close the standard input channel."""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

    def close_wait(self):
        """Close the standard input channel and wait for the standard
        output to stop. Note that the results can still be obtained through
        self.get_all_output()..."""

        self.close()

        while True:
            line = self.output()

            if not line:
                break

        endtime = time.time()
        if self._log_file:
            # close the existing log file: also add a comment at the end containing the
            # command-line (replacing working directory & executable path for brevity)
            command_line = "%s " % os.path.basename(self._executable)
            for c in self._command_line:
                command_line += " '%s'" % c.replace(
                    self._working_directory + os.sep, ""
                )
            self._log_file.write("# command line:\n")
            self._log_file.write("# %s\n" % command_line)
            if hasattr(self, "_runtime_log") and self._runtime_log:
                self._log_file.write("#\n# timing information:\n")
                for k in self._runtime_log:
                    self._log_file.write(
                        "#   time since {name}: {time:.1f} seconds\n".format(
                            name=k, time=endtime - self._runtime_log[k]
                        )
                    )
            self._log_file.close()
            self._log_file = None
            with open(self._log_file_name, encoding="latin-1") as fh:
                lines = fh.readlines()
            n = min(50, len(lines))
            logger.debug("Last %i lines of %s:", n, self._log_file_name)
            for line in lines[-n:]:
                logger.debug(line.rstrip("\n"))
        elif hasattr(self, "_runtime_log") and self._runtime_log:
            if self._executable:
                command_line = "%s " % os.path.basename(self._executable)
                for c in self._command_line:
                    command_line += " '%s'" % c.replace(
                        self._working_directory + os.sep, ""
                    )
            else:
                command_line = "(unknown)"
        if self._runtime_log:
            xia2.Driver.timing.record(
                {
                    "command": command_line.strip(),
                    "time_end": endtime,
                    "time_start": min(self._runtime_log.values()),
                    "details": self._runtime_log,
                }
            )

        self.cleanup()

    def kill(self):
        """Kill the child process."""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

    def cleanup(self):
        pass

    def status(self):
        """Check the status of the child process - implemented by _status
        in other Driver implementations."""

        return self._status()

    def _status(self):
        """The acrual implementation - this MUST be overridden - at the
        very least return 0."""

        raise NotImplementedError("Do not use the DefaultDriver class directly")

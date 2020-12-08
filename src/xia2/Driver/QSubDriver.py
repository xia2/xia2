import os
import shlex
import subprocess
import time

from xia2.Driver.DefaultDriver import DefaultDriver
from xia2.Driver.DriverHelper import script_writer
from xia2.Handlers.Phil import PhilIndex

# Now depend on Phil scope from xia2...


def get_qsub_command():
    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    if mp_params.qsub_command:
        return mp_params.qsub_command
    return None


class QSubDriver(DefaultDriver):
    def __init__(self):
        if os.name != "posix":
            raise RuntimeError('os "%s" not supported' % os.name)

        super().__init__()

        self._script_command_line = []
        self._script_standard_input = []

        self.set_qsub_name(self._name)

        self._script_status = 0

        # this is opened by the close() method and read by output
        # from self._script_name.xout

        self._output_file = None

    def set_qsub_name(self, name):
        """Set the name to something sensible."""
        self._script_name = "J%s" % name

    def start(self):
        """This is pretty meaningless in terms of running things through
        scripts..."""

        for c in self._command_line:
            self._script_command_line.append(c)

    def check(self):
        """NULL overloading of the default check method."""
        return True

    def check_sge_errors(self, sge_stderr_list):
        """Check through the standard error from Sun Grid Engine
        for indications that something went wrong..."""

        for o in sge_stderr_list:
            if "command not found" in o:
                missing_program = o.split(":")[2].strip()
                raise RuntimeError('executable "%s" missing' % missing_program)

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

        script_name = os.path.join("jobs", self._script_name)

        try:
            os.mkdir(os.path.join(self._working_directory, "jobs"))
        except OSError:
            if not os.path.exists(os.path.join(self._working_directory, "jobs")):
                raise

        # copy in LD_LIBRARY_PATH - SGE squashes this
        if (
            "LD_LIBRARY_PATH" in os.environ
            and "LD_LIBRARY_PATH" not in self._working_environment
        ):
            self._working_environment["LD_LIBRARY_PATH"] = os.environ[
                "LD_LIBRARY_PATH"
            ].split(os.pathsep)

        script_writer(
            self._working_directory,
            script_name,
            self._executable,
            self._script_command_line,
            self._working_environment,
            self._script_standard_input,
        )

        # this will return almost instantly, once the job is in
        # the queue

        qsub_command = get_qsub_command()
        if not qsub_command:
            qsub_command = "qsub"

        qsub_command = shlex.split(qsub_command)
        if self._cpu_threads > 1:
            pipe = subprocess.Popen(
                qsub_command
                + [
                    "-V",
                    "-cwd",
                    "-pe",
                    "smp",
                    "%d" % self._cpu_threads,
                    "%s.sh" % script_name,
                ],
                cwd=self._working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            pipe = subprocess.Popen(
                qsub_command + ["-V", "-cwd", "%s.sh" % script_name],
                cwd=self._working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        # this will get all of the output as a tuple (stdout, stderr)
        stdout, stderr = pipe.communicate()

        # check the standard error
        if stderr:
            # something probably went wrong
            if "error opening" in stderr:
                raise RuntimeError(
                    'executable "%s" does not exist'
                    % stdout.split("\n")[0].split(":")[0].replace("error opening ", "")
                )

        # probably everything is ok then

        # the job id etc go to the standard output

        for record in stdout.split("\n"):
            if "Your job" in record:
                job_id = record.split()[2]

        # now have a while loop watching this job id via qstat -j

        while True:
            pipe = subprocess.Popen(
                ["qstat", "-j", "%s" % job_id],
                cwd=self._working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = pipe.communicate()

            if "Following jobs do not exist" in stderr:
                # then the job has finished
                break

            # sleep for 10 seconds
            time.sleep(10)

        # the following files may have some interesting contents - despite
        # the fact that all of the output was supposed to be piped to
        # the standard output...

        # oh - just looked. in the DriverHelper.script_writer method
        # the output is simply piped > not 2>&1 - which means that the
        # standard error output will appear below...

        sge_stdout = os.path.join(
            self._working_directory, f"{self._script_name}.sh.o{job_id}"
        )

        sge_stderr = os.path.join(
            self._working_directory, f"{self._script_name}.sh.e{job_id}"
        )

        sge_pstdout = os.path.join(
            self._working_directory, f"{self._script_name}.sh.po{job_id}"
        )

        sge_pstderr = os.path.join(
            self._working_directory, f"{self._script_name}.sh.pe{job_id}"
        )

        # check the standard error file for any indications that
        # something went wrong running this job...

        with open(sge_stderr) as fh:
            error_output = fh.readlines()
        self.check_sge_errors(error_output)

        # it's nearly impossible to get the return status from qsub
        # so don't bother
        self._script_status = 0

        # set this up for reading the "standard output" of the job.
        self._output_file = open(
            os.path.join(self._working_directory, "%s.xout" % script_name)
        )

        # at this stage I should delete the sge specific files defined
        # above to be tidy...

        try:
            os.remove(sge_stdout)
            os.remove(sge_stderr)
            if os.path.exists(sge_pstdout):
                os.remove(sge_pstdout)
            if os.path.exists(sge_pstderr):
                os.remove(sge_pstderr)

        except Exception:
            # something wrong with this deletion?
            pass

    def kill(self):
        """This is meaningless..."""

        pass

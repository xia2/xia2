import os

import xia2.Driver.DefaultDriver


def CCP4DecoratorFactory(DriverInstance):
    """Create a CCP4 decorated Driver instance - based on the Driver
    instance which is passed in. This is an implementation of
    dynamic inheritance. Note well - this produces a new object and
    leaves the original unchanged."""

    DriverInstanceClass = DriverInstance.__class__

    assert issubclass(DriverInstanceClass, xia2.Driver.DefaultDriver.DefaultDriver), (
        "%s is not a Driver implementation" % DriverInstance
    )

    # verify that the object matches the Driver specification

    class CCP4Decorator(DriverInstanceClass):
        """A decorator class for a Driver object which will add some nice CCP4
        sugar on top."""

        # to get hold of the original start() methods and so on - and
        # also to the parent class constructor
        _original_class = DriverInstanceClass

        def __init__(self):
            # note well - this is evil I am calling another classes constructor
            # in here. Further this doesn't know what it is constructing!

            self._original_class.__init__(self)

            self._hklin = None
            self._hklout = None

            # somewhere to store the loggraph output
            self._loggraph = {}

            # put the CCP4 library directory at the start of the
            # LD_LIBRARY_PATH in case it mashes CCP4 programs...
            if "CLIB" in os.environ and os.name == "posix":
                if os.uname()[0] == "Darwin":
                    self.add_working_environment(
                        "DYLD_LIBRARY_PATH", os.environ["CLIB"]
                    )
                else:
                    self.add_working_environment("LD_LIBRARY_PATH", os.environ["CLIB"])

        def set_hklin(self, hklin):
            self._hklin = hklin

        def get_hklin(self):
            return self._hklin

        def check_hklin(self):
            if self._hklin is None:
                raise RuntimeError("hklin not defined")
            elif isinstance(self._hklin, str):
                if not os.path.exists(self._hklin):
                    raise RuntimeError("hklin %s does not exist" % self._hklin)
            else:
                for hklin in self._hklin:
                    if not os.path.exists(hklin):
                        raise RuntimeError("hklin %s does not exist" % hklin)

        def set_hklout(self, hklout):
            self._hklout = hklout

        def get_hklout(self):
            return self._hklout

        def check_hklout(self):
            if self._hklout is None:
                raise RuntimeError("hklout not defined")

            # check that these are different files!

            if self._hklout == self._hklin:
                raise RuntimeError(
                    "hklout and hklin are the same file (%s)" % str(self._hklin)
                )

        def describe(self):
            """An overloading of the Driver describe() method."""

            description = "CCP4 program: %s" % self.get_executable()

            if self._hklin is not None:
                description += " %s" % ("hklin")
                description += " %s" % (self._hklin)

            if self._hklout is not None:
                description += " %s" % ("hklout")
                description += " %s" % (self._hklout)

            return description

        def start(self):
            """Add all the hklin etc to the command line then call the
            base classes start() method. Also make any standard ccp4
            scratch directories. The latter shouldnt be needed however."""

            for env in ["BINSORT_SCR", "CCP4_SCR"]:
                if env in os.environ:
                    directory = os.environ[env]
                    self.add_scratch_directory(directory)
                    try:
                        os.mkdir(directory)
                    except Exception:
                        pass

            if self._hklin is not None:
                self.add_command_line("hklin")
                if isinstance(self._hklin, str):
                    self.add_command_line(self._hklin)
                else:
                    for hklin in self._hklin:
                        self.add_command_line(hklin)

            if self._hklout is not None:
                self.add_command_line("hklout")
                self.add_command_line(self._hklout)

            # delegate the actual starting to the parent class
            self._original_class.start(self)

        def check_ccp4_errors(self):
            """Look through the standard output for a few "usual" CCP4
            errors, for instance incorrect file formats &c."""

            # check that the program has finished...

            if not self.finished():
                raise RuntimeError("program has not finished")

            for line in self.get_all_output():
                if "CCP4 library signal" in line:
                    error = line.split(":")[1].strip()

                    # throw away the "status" in brackets

                    if "(" in error:
                        error = error.split("(")[0]

                    # handle specific cases...

                    if "Write failed" in error:
                        # work out why...
                        for l in self.get_all_output():
                            if ">>>>>> System signal" in l:
                                cause = l.split(":")[1].split("(")[0]
                                raise RuntimeError(f"{error}:{cause}")

                    # then cope with the general case

                    else:
                        raise RuntimeError(error)

        def get_ccp4_status(self):
            """Check through the standard output and get the program
            status. Note well - this will only work if called once the
            program is finished."""

            # check that the program has finished...

            if not self.finished():
                raise RuntimeError("program has not finished")

            # look in the last 10 lines for the status

            # Added 1/SEP/06 to check if .exe is on the end of the
            # command line...

            program_name = os.path.split(self.get_executable())[-1].lower()
            if program_name[-4:] == ".exe":
                program_name = program_name[:-4]

            # special case for FFT which calls itself FFTBIG in the status
            # output..

            if program_name == "fft":
                program_name = "fftbig"

            for line in self.get_all_output()[-10:]:
                l = line.split()
                if len(l) > 1:
                    if l[0][:-1].lower() == program_name:
                        # then this is the status line
                        status = line.split(":")[1].replace("*", "")
                        return status.strip()

                    if l[0][:-1].lower() == program_name.split("-")[0]:
                        # then this is also probably the status line
                        status = line.split(":")[1].replace("*", "")
                        return status.strip()

            raise RuntimeError("could not find status")

        def parse_ccp4_loggraph(self):
            """Look through the standard output of the program for
            CCP4 loggraph text. When this is found store it in a
            local dictionary to allow exploration."""

            # reset the loggraph store
            self._loggraph = {}

            output = self.get_all_output()

            for i in range(len(output)):
                line = output[i]
                if "$TABLE" in line:

                    n_dollar = line.count("$$")

                    current = line.split(":")[1].replace(">", "").strip()
                    self._loggraph[current] = {}
                    self._loggraph[current]["columns"] = []
                    self._loggraph[current]["data"] = []

                    loggraph_info = ""

                    # while not 'inline graphs' in line and not 'FONT' in line:
                    while n_dollar < 4:
                        n_dollar += line.count("$$")
                        loggraph_info += line

                        if n_dollar == 4:
                            break

                        i += 1
                        line = output[i]

                    # at this stage I should have the whole 9 yards in
                    # a single string...

                    tokens = loggraph_info.split("$$")
                    self._loggraph[current]["columns"] = tokens[1].split()

                    if len(tokens) < 4:
                        raise RuntimeError('loggraph "%s" broken' % current)

                    data = tokens[3].split("\n")

                    # pop takes the data off the end so...
                    # data.reverse()

                    columns = len(self._loggraph[current]["columns"])

                    # while len(data) > 0:
                    # record = []
                    # for i in range(columns):
                    # record.append(data.pop())
                    # self._loggraph[current]['data'].append(record)

                    # code around cases where columns merge together...

                    for j in data:
                        record = j.split()
                        if len(record) == columns:
                            self._loggraph[current]["data"].append(record)

            return self._loggraph

    return CCP4Decorator()

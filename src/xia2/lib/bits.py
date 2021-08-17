# Python routines which don't really belong anywhere else.


import logging
import math
import os

from multiprocessing import Lock, Value

logger = logging.getLogger("xia2.lib.bits")


def is_mtz_file(filename):
    """Check if a file is MTZ format - at least according to the
    magic number."""

    with open(filename, "rb") as fh:
        magic = fh.read(4)

    return magic == b"MTZ "


def nifty_power_of_ten(num):
    """Return 10^n: 10^n > num; 10^(n-1) <= num."""

    result = 10

    while result <= num:
        result *= 10

    return result


def mean_sd(list_of_numbers):
    mean = sum(list_of_numbers) / len(list_of_numbers)
    sd = 0.0
    for l in list_of_numbers:
        sd += (l - mean) * (l - mean)
    sd /= len(list_of_numbers)
    return (mean, math.sqrt(sd))


##### START MESSY CODE #####
# Shared counter for multiprocessing
# http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/


class Counter:
    def __init__(self, initval=0):
        self.val = Value("i", initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1
            return self.val.value

    def value(self):
        with self.lock:
            return self.val.value


_run_number = Counter(0)


def _get_number():
    global _run_number
    return _run_number.increment()


###### END MESSY CODE ######


def auto_logfiler(DriverInstance, extra=None):
    """Create a "sensible" log file for this program wrapper & connect it."""

    working_directory = DriverInstance.get_working_directory()

    if not working_directory:
        return

    executable = os.path.split(DriverInstance.get_executable())[-1]
    number = _get_number()

    if executable[-4:] == ".bat":
        executable = executable[:-4]

    if executable[-4:] == ".exe":
        executable = executable[:-4]

    if extra:
        logfile = os.path.join(
            working_directory, "%d_%s_%s.log" % (number, executable, extra)
        )
    else:
        logfile = os.path.join(working_directory, "%d_%s.log" % (number, executable))

    DriverInstance.set_xpid(number)

    logger.debug("Logfile: %s -> %s", executable, logfile)

    DriverInstance.write_log_file(logfile)

    return logfile


def transpose_loggraph(loggraph_dict):
    """Transpose the information in the CCP4-parsed-loggraph dictionary
    into a more useful structure."""

    columns = loggraph_dict["columns"]
    data = loggraph_dict["data"]

    results = {}

    # FIXME column labels are not always unique - so prepend the column
    # number - that'll make it unique! PS counting from 1 - 01/NOV/06

    new_columns = []

    for j, c in enumerate(columns):
        col = "%d_%s" % (j + 1, c)
        new_columns.append(col)
        results[col] = []

    for record in data:
        for j, nc in enumerate(new_columns):
            results[nc].append(record[j])

    return results


def nint(a):
    """return the nearest integer to a."""

    i = int(a)

    if a > 0:
        if a - i > 0.5:
            i += 1

    elif a < 0:
        if a - i < -0.5:
            i -= 1

    return i

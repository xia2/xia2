#!/usr/bin/env python
# bits.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21/SEP/06
#
# Python routines which don't really belong anywhere else.
#

from __future__ import absolute_import, division, print_function

from builtins import range
import math
import os
from multiprocessing import Lock, Value

from xia2.Handlers.Streams import Chatter, Debug


def is_mtz_file(filename):
    """Check if a file is MTZ format - at least according to the
    magic number."""

    magic = open(filename, "rb").read(4)

    if magic == "MTZ ":
        return True

    return False


def is_xds_file(filename):
    """Check to see if a file looks like XDS_ASCII format."""

    first_token = open(filename, "r").readline().split()[0]

    if first_token == "!FORMAT=XDS_ASCII":
        return True

    return False


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


# FIXNE redundant


def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)


def remove_outliers(values, limit):
    result = []
    outliers = []
    for j in range(len(values)):
        scratch = []
        for k in range(len(values)):
            if j != k:
                scratch.append(values[k])
        m, s = meansd(scratch)
        if math.fabs(values[j] - m) / s <= limit * s:
            result.append(values[j])
        else:
            outliers.append(values[j])

    return result, outliers


##### START MESSY CODE #####
# Shared counter for multiprocessing
# http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/


class Counter(object):
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

    Debug.write("Logfile: %s -> %s" % (executable, logfile))

    DriverInstance.write_log_file(logfile)

    return logfile


def unique_elements(list_of_tuples):
    """Extract unique elements from list of tuples, return as sorted list."""
    return sorted(set(sum(map(list, list_of_tuples), [])))


def transpose_loggraph(loggraph_dict):
    """Transpose the information in the CCP4-parsed-loggraph dictionary
    into a more useful structure."""

    columns = loggraph_dict["columns"]
    data = loggraph_dict["data"]

    results = {}

    # FIXME column labels are not always unique - so prepend the column
    # number - that'll make it unique! PS counting from 1 - 01/NOV/06

    new_columns = []

    j = 0
    for c in columns:
        j += 1
        col = "%d_%s" % (j, c)
        new_columns.append(col)
        results[col] = []

    nc = len(new_columns)

    for record in data:
        for j in range(nc):
            results[new_columns[j]].append(record[j])

    return results


def message_Darwin(text):
    def run(command):
        import subprocess
        import shlex

        subprocess.call(shlex.split(command))
        return

    def say(this):
        run('say "%s"' % this)

    def notify(this):
        run('osascript -e \'display notification "%s" with title "xia2"\'' % this)

    say(text)
    notify(text)

    return


def message_Linux(text):
    def run(command):

        # FIXME replace this with something using subprocess but which can also
        # clobber LD_LIBRARY_PATH as cctbx.python has things in PATH which break
        # notify-send

        os.system(command)
        return

    def notify(this):
        run("LD_LIBRARY_PATH='' notify-send 'xia2' '%s' &" % this)

    notify(text)

    return


def message(text):
    import platform

    if platform.system() == "Darwin":
        try:
            message_Darwin(text)
        except IOError:  # deliberately ignoring errors
            pass

    elif platform.system() == "Linux":
        try:
            message_Linux(text)
        except Exception:  # deliberately ignoring errors
            pass

    return


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


if __name__ == "__main__":
    message("This is a test")

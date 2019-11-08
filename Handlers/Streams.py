# "Standard" output streams for the output of xia2 - these will allow
# filtering of the output to files, the standard output, a GUI, none of
# the above, all of the above.
#
# The idea of this is to separate the "administrative", "status" and
# "scientific" output of the program. Finally I also decided (5/SEP/06)
# to add a stream for "chatter", that is the odds and ends which are
# going on inside the program which tells you it's doing things.

from __future__ import absolute_import, division, print_function

import inspect
import io
import logging
import os
import sys
from datetime import date

import libtbx.load_env

try:
    from dlstbx.util.colorstreamhandler import ColorStreamHandler
except ImportError:
    ColorStreamHandler = None

april = {
    "CC half   ": "Cromulence",
    "I/sigma   ": "Excellence",
    "Total observations": "How many spots    ",
    "Total unique": "Unique spots",
    "High resolution limit ": "Littlest visible thing",
    "Low resolution limit ": "Biggest visible thing",
    "Resolution limit for": "Littlest visible thing",
}


def banner(comment, forward=True, size=60):

    if not comment:
        return "-" * size

    l = len(comment)
    m = (size - (l + 2)) // 2
    n = size - (l + 2 + m)
    return "%s %s %s" % ("-" * m, comment, "-" * n)


class _Stream(object):
    """A class to represent an output stream. This will be used as a number
    of static instances - Debug and Chatter in particular."""

    def __init__(self, streamname, prefix):
        """Create a new stream."""

        # FIXME would rather this goes to a file...
        # unless this is impossible

        if streamname:
            self._file_name = "%s.txt" % streamname
        else:
            self._file_name = None

        self._file = None

        self._streamname = streamname
        self._prefix = prefix

        self._otherstream = None
        self._off = False

        self._cache = False
        self._cachelines = []

        self._additional = False

        self._filter = None

    def cache(self):
        self._cache = True
        self._cachelines = []

    def filter(self, filter):
        self._filter = filter

    def uncache(self):
        if not self._cache:
            return
        self._cache = False
        for record, forward in self._cachelines:
            self.write(record, forward)
        return self._cachelines

    def get_file(self):
        if self._file:
            return self._file
        if not self._file_name:
            self._file = sys.stdout
        else:
            self._file = io.open(self._file_name, "w", encoding="utf-8")
        return self._file

    def set_file(self, file):
        self._file = file

    def set_additional(self):
        self._additional = True

    def write(self, record, forward=True, strip=True):
        if self._filter:
            for replace in self._filter:
                record = record.replace(replace, self._filter[replace])
        if self._off:
            return None

        if self._cache:
            self._cachelines.append((record, forward))
            return

        if self._additional:
            f = inspect.currentframe().f_back
            m = f.f_code.co_filename
            l = f.f_lineno
            record = "Called from %s / %d\n%s" % (m, l, record)

        for r in record.split("\n"):
            if self._prefix:
                result = self.get_file().write(
                    u"[%s]  %s\n" % (self._prefix, r.strip() if strip else r)
                )
            else:
                result = self.get_file().write(u"%s\n" % (r.strip() if strip else r))

            self.get_file().flush()

        if self._otherstream and forward:
            self._otherstream.write(record, strip=strip)

        return result

    def bigbanner(self, comment, forward=True, size=60):
        """Write a big banner for something."""

        hashes = "#" * size

        self.write(hashes, forward)
        self.write("# %s" % comment, forward)
        self.write(hashes, forward)

    def banner(self, comment, forward=True, size=60):
        self.write(banner(comment, forward=forward, size=size))

    def smallbanner(self, comment, forward):
        """Write a small batter for something, like this:
        ----- comment ------."""

        dashes = "-" * 10

        self.write("%s %s %s" % (dashes, comment, dashes), forward)

    def block(self, task, data, program, options):
        """Print out a description of the task being performed with
        the program and a dictionary of options which will be printed
        in alphabetical order."""

        self.banner("%s %s with %s" % (task, data, program), size=80)
        for o in sorted(options):
            if options[o]:
                oname = "%s:" % o
                self.write("%s %s" % (oname.ljust(30), options[o]))

    def entry(self, options):
        """Print subsequent entries to the above block."""

        for o in sorted(options):
            if options[o]:
                oname = "%s:" % o
                self.write("%s %s" % (oname.ljust(30), options[o]))

    def join(self, otherstream):
        """Join another stream so that all output from this stream goes also
        to that one."""

        self._otherstream = otherstream

    def off(self):
        """Switch the stream writing off..."""

        self._off = True


# FIXME 23/NOV/06 now write a xia2.txt from chatter and rename that
# output stream Stdout... then copy everything there!

cl = libtbx.env.dispatcher_name
if cl:
    if "xia2" not in cl or "python" in cl or cl == "xia2.new":
        cl = "xia2"
else:
    cl = "xia2"

if cl.endswith(".bat"):
    # windows adds .bat extension to dispatcher
    cl = cl[:-4]

Chatter = _Stream("%s" % cl, None)
Journal = _Stream("%s-journal" % cl, None)
Stdout = _Stream(None, None)
day = date.today().timetuple()
if (day.tm_mday == 1 and day.tm_mon == 4) or "XIA2_APRIL" in os.environ:
    # turning log fonts to GREEN
    Stdout.filter(april)
Debug = _Stream("%s-debug" % cl, None)

Chatter.join(Stdout)


def streams_off():
    """Switch off the chatter output - designed for unit tests..."""
    Chatter.off()
    Journal.off()
    Debug.off()


def setup_logging(logfile=None, debugfile=None, verbose=False):
    """
    Initialise logging for xia2

    :param logfile: Filename for info/info+debug log output.
    :type logfile: str
    :param debugfile: Filename for debug log output.
    :type debugfile: str
    :param verbose: Enable debug output for logfile and console.
    :type verbose: bool
    """
    if verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    if os.getenv("COLOURLOG") and ColorStreamHandler:
        console = ColorStreamHandler(sys.stdout)
    else:
        console = logging.StreamHandler(sys.stdout)
    console.setLevel(loglevel)

    xia2_logger = logging.getLogger("xia2")
    xia2_logger.addHandler(console)
    xia2_logger.setLevel(loglevel)

    other_loggers = [logging.getLogger(package) for package in ("dials", "dxtbx")]

    if logfile:
        fh = logging.FileHandler(filename=logfile, mode="w")
        fh.setLevel(loglevel)
        xia2_logger.addHandler(fh)
        for logger in other_loggers:
            logger.addHandler(fh)
            logger.setLevel(loglevel)

    if debugfile:
        fh = logging.FileHandler(filename=debugfile, mode="w")
        fh.setLevel(logging.DEBUG)
        for logger in [xia2_logger] + other_loggers:
            logger.addHandler(fh)
            logger.setLevel(logging.DEBUG)


def reconfigure_streams_to_logging():
    "Modify xia2 Chatter/Debug objects to use python logging"

    def logger_file(loggername, level=logging.INFO):
        "Returns a file-like object that writes to a logger"
        log_function = logging.getLogger(loggername).log

        class _(object):
            @staticmethod
            def flush():
                pass

            @staticmethod
            def write(logobject):
                if logobject.endswith("\n"):
                    # the Stream.write() function adds a trailing newline.
                    # remove that again
                    logobject = logobject[:-1]
                log_function(level, logobject)

        return _()

    Debug.set_file(logger_file("xia2.stream.debug", level=logging.DEBUG))
    Debug.join(None)
    Chatter.set_file(logger_file("xia2.stream.chatter"))
    Chatter.join(None)
    Stdout.set_file(logger_file("xia2.stream.stdout"))
    Stdout.join(None)


if __name__ == "__main__":
    setup_logging(logfile="logfile", debugfile="debugfile")
    reconfigure_streams_to_logging()
    Chatter.write("nothing much, really")
    Debug.write("this is a debug-level message")
    Stdout.write("I write to stdout")

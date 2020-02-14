# A handler for matters of the operating environment, which will impact
# on data harvesting, working directories, a couple of other odds & sods.

from __future__ import absolute_import, division, print_function

import ctypes
import logging
import os
import platform
import tempfile

from xia2.Handlers.Streams import Chatter

logger = logging.getLogger("xia2.Handlers.Environment")


def which(pgm, debug=False):
    path = os.getenv("PATH")
    for p in path.split(os.path.pathsep):
        p = os.path.join(p, pgm)
        if debug:
            Chatter.write("Seeking %s" % p)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p


def memory_usage():
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception as e:
        logger.debug("Error getting RAM usage: %s" % str(e))
        return 0


def debug_memory_usage():
    """Print line, file, memory usage."""

    try:
        import inspect

        frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
        logger.debug(
            "RAM usage at %s %d: %d"
            % (os.path.split(frameinfo.filename)[-1], frameinfo.lineno, memory_usage())
        )
    except Exception as e:
        logger.debug("Error getting RAM usage: %s" % str(e))


def df(path=None):
    """Return disk space in bytes in path."""
    path = path or os.getcwd()

    if platform.system() == "Windows":
        try:
            bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path), None, None, ctypes.pointer(bytes)
            )
            return bytes.value
        except Exception as e:
            logger.debug("Error getting disk space: %s" % str(e))
            return 0

    s = os.statvfs(path)
    return s.f_frsize * s.f_bavail


def ulimit_n():
    # see xia2#172 - change limit on number of file handles to smaller of
    # hard limit, 4096

    try:
        import resource
    except ImportError:
        # not available on all operating systems. do nothing.
        return
    current, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    demand = min(4096, hard)
    resource.setrlimit(resource.RLIMIT_NOFILE, (demand, demand))
    current, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    return current, demand, hard


class _Environment(object):
    """A class to store environmental considerations."""

    def __init__(self, working_directory=None):
        if working_directory is None:
            self._working_directory = os.getcwd()
        else:
            self._working_directory = working_directory
        self._is_setup = False

    def _setup(self):
        if self._is_setup:
            return

        # define a local CCP4_SCR
        ccp4_scr = tempfile.mkdtemp()
        os.environ["CCP4_SCR"] = ccp4_scr
        logger.debug("Created CCP4_SCR: %s" % ccp4_scr)

        ulimit = ulimit_n()
        if ulimit:
            logger.debug("File handle limits: %d/%d/%d" % ulimit)

        self._is_setup = True

    def generate_directory(self, path_tuple):
        """Used for generating working directories."""
        self._setup()

        path = self._working_directory

        if isinstance(path_tuple, type("string")):
            path_tuple = (path_tuple,)

        for p in path_tuple:
            path = os.path.join(path, p)

        if not os.path.exists(path):
            logger.debug("Making directory: %s" % path)
            os.makedirs(path)
        else:
            logger.debug("Directory exists: %s" % path)

        return path

    def getenv(self, name):
        """A wrapper for os.environ."""
        self._setup()
        return os.environ.get(name)


Environment = _Environment()

# jiffy functions


def get_number_cpus():
    """Portably get the number of processor cores available."""

    if os.name == "nt":
        # Windows only has once CPU because easy_mp does not support more. #191
        return 1

    # if environmental variable NSLOTS is set to a number then use that
    try:
        return int(os.environ.get("NSLOTS"))
    except (ValueError, TypeError):
        pass

    from libtbx.introspection import number_of_processors

    return number_of_processors(return_value_if_unknown=-1)

# A handler for matters of the operating environment, which will impact
# on data harvesting, working directories, a couple of other odds & sods.


import atexit
import ctypes
import logging
import os
import platform
import tempfile

from libtbx.introspection import number_of_processors

logger = logging.getLogger("xia2.Handlers.Environment")


def which(pgm):
    path = os.getenv("PATH")
    for p in path.split(os.path.pathsep):
        p = os.path.join(p, pgm)
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
    logger.debug("File handle limits: %d/%d/%d" % (current, demand, hard))


def set_up_ccp4_tmpdir():
    """define a local CCP4_SCR"""
    ccp4_scr = tempfile.mkdtemp()
    os.environ["CCP4_SCR"] = ccp4_scr
    logger.debug("Created CCP4_SCR: %s" % ccp4_scr)

    def drop_ccp4_scr_tmpdir_if_possible():
        try:
            os.rmdir(ccp4_scr)
        except Exception:
            pass

    atexit.register(drop_ccp4_scr_tmpdir_if_possible)


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

    return number_of_processors(return_value_if_unknown=-1)


set_up_ccp4_tmpdir()
ulimit_n()

from __future__ import annotations

import contextlib
import io
import logging
import os
import time
from collections.abc import Generator
from pathlib import Path

from dials.util.log import DialsLogfileFormatter, print_banner

import xia2.Driver.timing

xia2_logger = logging.getLogger(__name__)


def report_timing(fn):
    def wrap_fn(*args, **kwargs):
        start_time = time.time()
        result = fn(*args, **kwargs)
        xia2_logger.debug("\nTiming report:")
        xia2_logger.debug("\n".join(xia2.Driver.timing.report()))
        duration = time.time() - start_time
        # write out the time taken in a human readable way
        xia2_logger.info(
            "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
        )
        return result

    return wrap_fn


def config_quiet(logfile: str, verbosity: int = 0) -> None:
    dials_logger = logging.getLogger("dials")
    logging.captureWarnings(True)
    warning_logger = logging.getLogger("py.warnings")
    if verbosity > 1:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    fh = logging.FileHandler(filename=logfile, mode="w", encoding="utf-8")
    fh.setLevel(loglevel)
    fh.setFormatter(DialsLogfileFormatter(timed=verbosity))
    dials_logger.addHandler(fh)
    warning_logger.addHandler(fh)
    dials_logger.setLevel(loglevel)
    print_banner(use_logging=True)


@contextlib.contextmanager
def redirect_xia2_logger(verbosity: int = 0) -> Generator[io.StringIO, None, None]:
    # we want the xia2 logging to redirect to an iostream
    xia2_logger = logging.getLogger("xia2")
    original_levels = [fh.level for fh in xia2_logger.handlers]
    try:
        for fh in xia2_logger.handlers:
            fh.setLevel(logging.ERROR)
        iostream = io.StringIO()
        sh = logging.StreamHandler(iostream)
        sh.setFormatter(DialsLogfileFormatter(timed=verbosity))
        xia2_logger.addHandler(sh)
        yield iostream
    finally:
        iostream.close()
        sh.close()
        xia2_logger.handlers.pop()
        for fh, oldlevel in zip(xia2_logger.handlers, original_levels):
            fh.setLevel(oldlevel)


@contextlib.contextmanager
def run_in_directory(directory: Path) -> Generator[Path, None, None]:
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)


@contextlib.contextmanager
def log_to_file(filename: str) -> Generator[logging.Logger, None, None]:
    try:
        config_quiet(logfile=filename)
        dials_logger = logging.getLogger("dials")
        yield dials_logger
    finally:
        dials_logger = logging.getLogger("dials")
        dials_logger.handlers.clear()
        warning_logger = logging.getLogger("py.warnings")
        if warning_logger.handlers:
            warning_logger.handlers.pop()

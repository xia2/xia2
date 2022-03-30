from __future__ import annotations

import contextlib
import logging
import os
import time
from pathlib import Path
from typing import Generator

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

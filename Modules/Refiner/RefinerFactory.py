from __future__ import absolute_import, division, print_function

import logging
import os

# other odds and ends
from xia2.DriverExceptions.NotAvailableError import NotAvailableError

# selection stuff
from xia2.Handlers.PipelineSelection import get_preferences

# refiner implementations
from xia2.Modules.Refiner.DialsRefiner import DialsRefiner
from xia2.Modules.Refiner.XDSRefiner import XDSRefiner

logger = logging.getLogger("xia2.Modules.Refiner.RefinerFactory")


def RefinerForXSweep(xsweep, json_file=None):
    """Create a Refiner implementation to work with the provided
    XSweep."""

    # FIXME this needs properly implementing...
    if xsweep is None:
        raise RuntimeError("XSweep instance needed")

    if not xsweep.__class__.__name__ == "XSweep":
        raise RuntimeError("XSweep instance needed")

    refiner = Refiner()

    if json_file is not None:
        assert os.path.isfile(json_file)
        logger.debug("Loading refiner from json: %s", json_file)
        refiner = refiner.__class__.from_json(filename=json_file)

    refiner.add_refiner_sweep(xsweep)

    return refiner


def Refiner():
    """Create a Refiner implementation."""

    refiner = None
    preselection = get_preferences().get("refiner")

    if not refiner and (not preselection or preselection == "dials"):
        try:
            refiner = DialsRefiner()
            logger.debug("Using Dials Refiner")
        except NotAvailableError:
            if preselection == "dials":
                raise RuntimeError("preselected refiner dials not available")

    if not refiner and (not preselection or preselection == "xds"):
        try:
            refiner = XDSRefiner()
            logger.debug("Using XDS Refiner")
        except NotAvailableError:
            if preselection == "xds":
                raise RuntimeError("preselected refiner xds not available")

    return refiner

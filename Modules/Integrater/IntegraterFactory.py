# A factory for Integrater implementations. At the moment this will
# support only XDS and the null integrater implementation.


import logging
import os

from xia2.DriverExceptions.NotAvailableError import NotAvailableError
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.PipelineSelection import get_preferences
from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater
from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater

logger = logging.getLogger("xia2.Modules.Integrater.IntegraterFactory")


def IntegraterForXSweep(xsweep, json_file=None):
    """Create an Integrater implementation to work with the provided
    XSweep."""

    # FIXME this needs properly implementing...
    if xsweep is None:
        raise RuntimeError("XSweep instance needed")

    if not xsweep.__class__.__name__ == "XSweep":
        raise RuntimeError("XSweep instance needed")

    integrater = Integrater()

    if json_file is not None:
        assert os.path.isfile(json_file)
        logger.debug("Loading integrater from json: %s" % json_file)
        import time

        t0 = time.time()
        integrater = integrater.__class__.from_json(filename=json_file)
        t1 = time.time()
        logger.debug("Loaded integrater in %.2f seconds" % (t1 - t0))
    else:
        integrater.setup_from_imageset(xsweep.get_imageset())
    integrater.set_integrater_sweep_name(xsweep.get_name())

    # copy across resolution limits
    if xsweep.get_resolution_high() or xsweep.get_resolution_low():

        d_min = PhilIndex.params.xia2.settings.resolution.d_min
        d_max = PhilIndex.params.xia2.settings.resolution.d_max

        # override with sweep versions if set - xia2#146
        if xsweep.get_resolution_high():
            d_min = xsweep.get_resolution_high()
        if xsweep.get_resolution_low():
            d_max = xsweep.get_resolution_low()

        if d_min is not None and d_min != integrater.get_integrater_high_resolution():

            logger.debug("Assigning resolution limits from XINFO input:")
            logger.debug("d_min: %.3f" % d_min)
            integrater.set_integrater_high_resolution(d_min, user=True)

        if d_max is not None and d_max != integrater.get_integrater_low_resolution():

            logger.debug("Assigning resolution limits from XINFO input:")
            logger.debug("d_max: %.3f" % d_max)
            integrater.set_integrater_low_resolution(d_max, user=True)

    # check the epoch and perhaps pass this in for future reference
    # (in the scaling)
    if xsweep._epoch > 0:
        integrater.set_integrater_epoch(xsweep._epoch)

    # need to do the same for wavelength now as that could be wrong in
    # the image header...

    if xsweep.get_wavelength_value():
        logger.debug(
            "Integrater factory: Setting wavelength: %.6f"
            % xsweep.get_wavelength_value()
        )
        integrater.set_wavelength(xsweep.get_wavelength_value())

    # likewise the distance...
    if xsweep.get_distance():
        logger.debug(
            "Integrater factory: Setting distance: %.2f" % xsweep.get_distance()
        )
        integrater.set_distance(xsweep.get_distance())

    integrater.set_integrater_sweep(xsweep, reset=False)

    return integrater


def Integrater():
    """Return an  Integrater implementation."""

    # FIXME this should take an indexer as an argument...

    integrater = None
    preselection = get_preferences().get("integrater")

    if not integrater and (not preselection or preselection == "dials"):
        try:
            integrater = DialsIntegrater()
            logger.debug("Using Dials Integrater")
            if PhilIndex.params.xia2.settings.scaler == "dials":
                integrater.set_output_format("pickle")
        except NotAvailableError:
            if preselection == "dials":
                raise RuntimeError(
                    "preselected integrater dials not available: "
                    + "dials not installed?"
                )

    if not integrater and (not preselection or preselection == "xdsr"):
        try:
            integrater = XDSIntegrater()
            logger.debug("Using XDS Integrater in new resolution mode")
        except NotAvailableError:
            if preselection == "xdsr":
                raise RuntimeError(
                    "preselected integrater xdsr not available: " + "xds not installed?"
                )

    if not integrater:
        raise RuntimeError("no integrater implementations found")

    # check to see if resolution limits were passed in through the
    # command line...

    dmin = PhilIndex.params.xia2.settings.resolution.d_min
    dmax = PhilIndex.params.xia2.settings.resolution.d_max

    if dmin:
        logger.debug("Adding user-assigned resolution limits:")

        if dmax:

            logger.debug(f"dmin: {dmin:.3f} dmax: {dmax:.2f}")
            integrater.set_integrater_resolution(dmin, dmax, user=True)

        else:

            logger.debug("dmin: %.3f" % dmin)
            integrater.set_integrater_high_resolution(dmin, user=True)

    return integrater

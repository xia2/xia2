import logging

# other odds and ends
from xia2.DriverExceptions.NotAvailableError import NotAvailableError

# selection stuff
from xia2.Handlers.PipelineSelection import get_preferences

# scaler implementations
from xia2.Modules.Scaler.CCP4ScalerA import CCP4ScalerA
from xia2.Modules.Scaler.XDSScalerA import XDSScalerA
from xia2.Modules.Scaler.DialsScaler import DialsScaler

logger = logging.getLogger("xia2.Modules.Scaler.ScalerFactory")


def Scaler(*args, **kwargs):
    """Create a Scaler implementation."""
    scaler = None
    preselection = get_preferences().get("scaler")

    if not scaler and (not preselection or preselection == "ccp4a"):
        try:
            scaler = CCP4ScalerA(*args, **kwargs)
            logger.debug("Using CCP4A Scaler")
        except NotAvailableError:
            if preselection == "ccp4a":
                raise RuntimeError("preselected scaler ccp4a not available")

    if not scaler and (not preselection or preselection == "xdsa"):
        try:
            scaler = XDSScalerA(*args, **kwargs)
            logger.debug("Using XDSA Scaler")
        except NotAvailableError:
            if preselection == "xdsa":
                raise RuntimeError("preselected scaler xdsa not available")

    if not scaler and (not preselection or preselection == "dials"):
        try:
            scaler = DialsScaler(*args, **kwargs)
            logger.debug("Using DIALS Scaler")
        except NotAvailableError:
            if preselection == "dials":
                raise RuntimeError("preselected scaler dials not available")

    return scaler

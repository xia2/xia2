# A couple of classes to assist with resolution calculations - these
# are for calculating resolution (d, s) for either distance / beam /
# wavelength / position or h, k, l, / unit cell.


import logging
import math
import os
import tempfile

from xia2.Wrappers.CCP4.Pointless import Pointless
from xia2.Modules.Scaler.rebatch import rebatch

logger = logging.getLogger("xia2.Experts.ResolutionExperts")


def meansd(values):
    if not values:
        return 0.0, 0.0

    if len(values) == 1:
        return values[0], 0.0

    mean = sum(values) / len(values)
    sd = 0.0

    for v in values:
        sd += (v - mean) * (v - mean)

    sd /= len(values)

    return mean, math.sqrt(sd)


def find_blank(hklin):
    try:
        # first dump to temp. file
        with tempfile.NamedTemporaryFile(
            suffix=".hkl", dir=os.environ["CCP4_SCR"], delete=False
        ) as fh:
            hklout = fh.name

        p = Pointless()
        p.set_hklin(hklin)
        _ = p.sum_mtz(hklout)

        if os.path.getsize(hklout) == 0:
            logger.debug("Pointless failed:")
            logger.debug("".join(p.get_all_output()))
            raise RuntimeError("Pointless failed: no output file written")

        isig = {}

        with open(hklout) as fh:
            for record in fh:
                lst = record.split()
                if not lst:
                    continue
                batch = int(lst[3])
                i, sig = float(lst[4]), float(lst[5])

                if not sig:
                    continue

                if batch not in isig:
                    isig[batch] = []

                isig[batch].append(i / sig)

    finally:
        os.remove(hklout)

    # look at the mean and sd

    blank = []
    good = []

    for batch in sorted(isig):
        m, s = meansd(isig[batch])
        if m < 1:
            blank.append(batch)
        else:
            good.append(batch)

    return blank, good


def remove_blank(hklin, hklout):
    """Find and remove blank batches from the file. Returns hklin if no
    blanks."""

    blanks, goods = find_blank(hklin)

    if not blanks:
        return hklin

    # if mostly blank return hklin too...
    if len(blanks) > len(goods):
        logger.debug("%d blank vs. %d good: ignore", len(blanks), len(goods))
        return hklin

    rebatch(hklin, hklout, exclude_batches=blanks)

    return hklout

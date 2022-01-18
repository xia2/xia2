from __future__ import annotations

import os

from iotbx import mtz


def run():
    for f in os.listdir("DataFiles"):
        if f.endswith(".mtz"):
            print(f)
            for c in mtz.object(os.path.join("DataFiles", f)).crystals():
                print(
                    "%20s: %7.3f %7.3f %7.3f  %7.3f %7.3f %7.3f"
                    % tuple([c.name()] + list(c.unit_cell_parameters()))
                )

from __future__ import absolute_import, division, print_function

import os
import sys

# Invert FPE trap defaults, https://github.com/cctbx/cctbx_project/pull/324
if "boost.python" in sys.modules:
    import boost.python

    boost.python.ext.trap_exceptions(
        bool(os.getenv("BOOST_ADAPTBX_TRAP_FPE")),
        bool(os.getenv("BOOST_ADAPTBX_TRAP_INVALID")),
        bool(os.getenv("BOOST_ADAPTBX_TRAP_OVERFLOW")),
    )
elif not os.getenv("BOOST_ADAPTBX_TRAP_FPE") and not os.getenv(
    "BOOST_ADAPTBX_TRAP_OVERFLOW"
):
    os.environ["BOOST_ADAPTBX_FPE_DEFAULT"] = "1"

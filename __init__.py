from __future__ import absolute_import, division, print_function

import os
import sys
import warnings

if sys.version_info.major == 2:
    warnings.warn(
        "Python 2 is no longer fully supported. Please consider using the DIALS 2.2 release branch. "
        "For more information on Python 2.7 support please go to https://github.com/dials/dials/issues/1175.",
        DeprecationWarning,
    )

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

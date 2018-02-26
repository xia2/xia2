from __future__ import absolute_import, division, print_function

import sys

# Hack to disable any DIALS banner showing up.
# To work properly this requires *this* file here to be essentially empty.
# Load *this* file here as dials.util.banner, so any future import
# will do exactly nothing.
sys.modules['dials.util.banner'] = __import__('xia2')

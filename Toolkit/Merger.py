#!/usr/bin/env cctbx.python
# Merger.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A toolkit component for merging symmetry related intensity measurements
# to calculate:
# 
#  - Rmerge vs. batch, resolution
#  - Chi^2
#  - Multiplicity
#  - Unmerged I/sigma
# 
# Then in a separate calculation, E^4, merged I/sigma and completeness will
# be calculated. This should be a different Toolkit component.

import sys
import math
import os
import time

from iotbx import mtz



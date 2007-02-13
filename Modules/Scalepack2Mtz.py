# Scalepack2Mtz.py
# Maintained by G.Winter
# 12th February 2007
# 
# A module to carefully convert scalepack reflection files (merged or
# unmerged) into properly structured MTZ files. This is based on the last
# section of CCP4ScalerImplementation, as that does largely the same.
# 
# This will:
# 
# if (unmerged) combat -> scala for merging (else) convert to mtz
# truncate all wavelengths
# if (mad) compute cell, cad in cell, cad together
# add freeR column
# if (mad) look for inter radiation damage
# 
# This assumes:
# 
# Reflections are correctly indexed
# One reflection file per wavelength
# All files from same crystal
# 
# Should produce results similar to CCP4ScalerImplementation.
#
# Example data will come from xia2.
# 
# Implementation fill follow line 1469++ of CCP4ScalerImplementation.
#
# Uses:
# 
# scalepack2mtz wrapper for merged files
# combat, sortmtz, scala for unmerged files
# mtzdump, cad, freerflag to muddle with files
# truncate to compute F's from I's.
# 
# funfunfun!


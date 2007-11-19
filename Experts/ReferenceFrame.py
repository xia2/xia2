# ReferenceFrame.py
# Maintained by G.Winter
# 19th November 2007
# 
# Code to handle transformations between reference frames, e.g. from xia2
# to Mosflm, xia2 to XDS &c.
# 
# This is prone to errors most likely... the following descriptions assume
# Rossmann geometry for the experiment, with the X-ray beam at right angles
# with a rotation axis which is parallel to a detector axis and with the
# beam perpendicular (approximately) to the detector face.
# 
# Reference frame definitions 
# ---------------------------
# 
# (1) Cambridge as used in Mosflm, cribbed from Mosflm documentation.
# 
# X: the direction of the X-ray beam photons
# Y: defined to give a right handed coordinate system
# Z: the principle rotation axis, such that looking down this axis
#    towards the sample, positive phi is anti-clockwise
#
# (2) imgCIF as used in xia2, cribbed from presentation from Herb Bernstein.
#
# X: the principle goniometer axis
# Y: defined to give a right handed coordinate system
# Z: from the sample towards the X-ray source (=> is -X in Cambridge frame)
#
# (3) XDS frame, as used by xia2.
#
# This is largely free, as the program allows the user to define everything
# in laboratory coordinates. However, I adopt the following conventions:
#
# X: identical to the detector fast axis*1 and parallel (approximately) to
#    the rotation axis [MAR, MARCCD, ADSC]
#    [*1 for RIGAKU SATURN this is antiparallel]
# Y: identical to the detector slow axis and parallel (approximately) to
#    the rotation axis [RIGAKU SATURN] or antiparallel (approximately)
#    [RIGAKU RAXIS]
# Z: orthogonal to the detector face and parallel (approximately) to the
#    direct beam vector - this is defined as 0,0,1 initially and refined
#

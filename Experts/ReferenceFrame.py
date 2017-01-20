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

from __future__ import absolute_import, division

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
#    [the component perpendicular to the rotation axis]
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
# This last lot is a mess so I should probably define a robust coordinate
# frame for the XDS interface and perform the transformations inside the
# XDS wrappers...
#
# Thus, the definitions will be as follows:
#
# X: parallel to the detector fast axis
# Y: parallel to the detector slow axis
# Z: perpendicular to the face of the detector
#
# So the rotation and beam axes may need to be altered... in a detector
# dependent manner.
#
#

Mos2Xia2 = (0, 0, 1, 0, 1, 0, -1, 0, 0)

def mosflm_to_xia2(v):
  '''Convert a vector v from Mosflm reference frame to xia2.'''

  from xia2.Experts.MatrixExpert import matvecmul, invert

  return matvecmul(Mos2Xia2, v)

def xia2_to_mosflm(v):
  '''Convert a vector v from xia2 frame to Mosflm.'''

  from xia2.Experts.MatrixExpert import matvecmul, invert

  Xia22Mos = invert(Mos2Xia2)

  return matvecmul(Xia22Mos, v)

if __name__ == '__main__':

  if mosflm_to_xia2((1, 0, 0)) != [0, 0, -1]:
    raise RuntimeError, 'transformation error i'
  if mosflm_to_xia2((0, 1, 0)) != [0, 1, 0]:
    raise RuntimeError, 'transformation error j'
  if mosflm_to_xia2((0, 0, 1)) != [1, 0, 0]:
    raise RuntimeError, 'transformation error k'

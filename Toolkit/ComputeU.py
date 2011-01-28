# Code to compute a U matrix from a unit cell and some other bits and bobs.

from cctbx.uctbx import unit_cell as cctbx_unit_cell
from scitbx import matrix
import math

a2kev = 12.39854
r2d = 180.0 / math.pi

uc = cctbx_unit_cell((3.573, 3.573, 5.643, 90, 90, 120))

ruc = uc.reciprocal()

B = matrix.sqr(ruc.orthogonalization_matrix())

roi = B * (0, 0, 4)
azir = B * (0, 1, 0)

dr = math.sqrt(roi.dot())
da = math.sqrt(azir.dot())

e = 5.993
w = a2kev / e

t = math.asin(w * dr / 2)

print 2 * t * r2d

dt = roi.angle(azir)

print dt * r2d

x_roi = matrix.col([- dr * math.sin(t), 0, dr * math.cos(t)])

print x_roi
x_azir = matrix.col([da * math.sin(dt - t), 0, da * math.cos(dt - t)])

print x_azir

# now we look to busing and levy to get the U matrix...

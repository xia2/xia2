# LIBTBX_SET_DISPATCHER_NAME dev.xia2.check_mosaic

import pickle
import sys

from dials.array_family import flex


def mosaic_profile_xyz(profile):
    nz, ny, nx = profile.focus()

    x = flex.double(nx, 0.0)
    for j in range(nx):
        x[j] = flex.sum(profile[:, :, j : j + 1])

    y = flex.double(ny, 0.0)
    for j in range(ny):
        y[j] = flex.sum(profile[:, j : j + 1, :])

    z = flex.double(nz, 0.0)
    for j in range(nz):
        z[j] = flex.sum(profile[j : j + 1, :, :])

    return x, y, z


def go(filename):
    with open(filename, "rb") as fh:
        allprof = pickle.load(fh)
    for prof in allprof:
        x, y, z = mosaic_profile_xyz(prof[0])
        for profile in prof[1:]:
            _x, _y, _z = mosaic_profile_xyz(profile)
            x += _x
            y += _y
            z += _z

        x /= flex.max(x)
        data = (100 * x).iround()
        fmt = "%3d " * x.size()
        print("X:", fmt % tuple(data))

        y /= flex.max(y)
        data = (100 * y).iround()
        fmt = "%3d " * y.size()
        print("Y:", fmt % tuple(data))

        z /= flex.max(z)
        data = (100 * z).iround()
        fmt = "%3d " * z.size()
        print("Z:", fmt % tuple(data))


if __name__ == "__main__":
    go(sys.argv[1])

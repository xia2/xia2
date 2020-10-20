import math

import numpy as np
import scitbx.math


def order_from_nterm(n):
    return {0: 0, 80: 8, 3: 1, 8: 2, 15: 3, 48: 6, 99: 9, 35: 5, 24: 4, 63: 7}[n]


def evaluate_1degree(ClmList):
    d2r = math.pi / 180.0
    order = order_from_nterm(len(ClmList))
    lfg = scitbx.math.log_factorial_generator(2 * order + 1)
    nsssphe = scitbx.math.nss_spherical_harmonics(order, 50000, lfg)
    Clm = {}
    idx = 0
    for l in range(1, order + 1):
        for m in range(-l, l + 1):
            Clm[(l, m)] = ClmList[idx]
            idx += 1

    abscor = np.empty((1 + 180 // 1, 1 + 360 // 1), float, "C")
    sqrt2 = math.sqrt(2)
    for t in range(0, 181, 1):
        for p in range(0, 361, 1):
            a = 1.0
            for l in range(1, order + 1):
                for m in range(-l, l + 1):
                    # Ylm = nsssphe.spherical_harmonic(l, m, t*d2r, p*d2r)
                    # Convert from complex to real according to
                    # http://en.wikipedia.org/wiki/Spherical_harmonics#Real_form
                    Ylm = nsssphe.spherical_harmonic(l, abs(m), t * d2r, p * d2r)
                    if m < 0:
                        a += Clm[(l, m)] * sqrt2 * ((-1) ** m) * Ylm.imag
                    elif m == 0:
                        assert Ylm.imag == 0.0
                        a += Clm[(l, m)] * Ylm.real
                    else:
                        a += Clm[(l, m)] * sqrt2 * ((-1) ** m) * Ylm.real
            abscor[(t // 1, p // 1)] = a
    return abscor


def generate_map(abscor, png_filename):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot

    pyplot.imshow(abscor)
    pyplot.colorbar()
    pyplot.savefig(png_filename)


def scrape_coefficients(log_file_name=None, log=None):
    # FIXME cope with cases where the surfaces are not LINKed => will be several
    # of them... and cases where scaling failed need trapping too...
    coefficients = []
    if not log:
        with open(log_file_name) as fh:
            log = fh.readlines()
    for record in log:
        if "Coefficient(Sd)" in record:
            for token in record.split()[1:]:
                coefficients.append(float(token.split("(")[0]))
    return coefficients

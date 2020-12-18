# NMol per ASU Calculations based on the Kantardjieff & Rupp method.
#
# Implementing the cell volume calculations of Kantardjieff and Rupp,
# Protein Science volume 12, 2002. Uses "nmol-params.dat" from
# http://www-structure.llnl.gov/mattprob
#
# Relies on $XIA2_ROOT/Data/nmol-params.dat


import logging
import math
import os

from xia2.Handlers.Syminfo import Syminfo
from xia2.Wrappers.CCP4.Matthews_coef import Matthews_coef

logger = logging.getLogger("xia2.lib.NMolLib")

nmolparams = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Data", "nmol-params.dat")
)

if not os.path.exists(nmolparams):
    raise RuntimeError("nmol-params.dat not found")


def unit_cell_volume(cell_a, cell_b, cell_c, cell_alpha, cell_beta, cell_gamma):
    """From the unit cell constants, compute the volume of the unit cell in
    A^3. Note that it is assumed that the cell_alpha, cell_beta, cell_gamma,
    angles are in degrees and the cell lengths (a, b, c) are in A."""

    # convert angles to radians from degrees

    pi = 4.0 * math.atan(1.0)
    dtor = pi / 180.0

    # then compute the required sines and cosines

    ca = math.cos(dtor * cell_alpha)
    cb = math.cos(dtor * cell_beta)
    cc = math.cos(dtor * cell_gamma)

    # finally evaluate the volume - this is simply the volume of a
    # parallelopiped

    V = (
        cell_a
        * cell_b
        * cell_c
        * math.sqrt(1 - ca * ca - cb * cb - cc * cc + 2 * ca * cb * cc)
    )
    return V


def spacegroup_number_operators(spacegroup):
    """From the spacegroup name (either the long or short version of the name)
    compute the number of symmetry operators. This will use the CCP4 symmetry
    library in "counting" mode."""

    if spacegroup.isdigit():
        spacegroup_number = int(spacegroup)
    else:
        # spacegroup was passed in as a name
        spacegroup_number = Syminfo.spacegroup_name_to_number(spacegroup.upper())

    return Syminfo.get_num_symops(spacegroup_number)


def sequence_mass(sequence):
    """Return a mass for this sequence - initially will be 128.0 * len"""

    # if input is simply a sequence length, return the appropriate
    # multiple

    if isinstance(sequence, type(42)):
        return 128.0 * sequence

    # otherwise it must be a string

    return 128.0 * len(sequence)


def compute_nmol_from_volume(volume, mass, resolution):
    with open(nmolparams) as fh:

        while True:
            line = fh.readline()
            if not line[0] == "#":
                break

        resolutions = [float(x) for x in line.split(",")[:13]]
        P0_list = [float(x) for x in fh.readline().split(",")[:13]]
        Vm_bar_list = [float(x) for x in fh.readline().split(",")[:13]]
        w_list = [float(x) for x in fh.readline().split(",")[:13]]
        A_list = [float(x) for x in fh.readline().split(",")[:13]]
        s_list = [float(x) for x in fh.readline().split(",")[:13]]

    if resolution > resolutions[-1]:
        logger.info(
            "Resolution lower than %s -> computing for %f", resolutions[-1], resolution
        )
        resolution = resolutions[-1]
    if resolution < resolutions[0]:
        logger.info("Resolution higher than peak %f -> %f", resolution, resolutions[0])
        resolution = resolutions[0]

    for start in range(12):
        if resolution > resolutions[start] and resolution < resolutions[start + 1]:
            break

    # can start at start - interpolate

    diff = (resolution - resolutions[start]) / (
        resolutions[start + 1] - resolutions[start]
    )

    P0 = P0_list[start] + diff * (P0_list[start + 1] - P0_list[start])
    Vm_bar = Vm_bar_list[start] + diff * (Vm_bar_list[start + 1] - Vm_bar_list[start])
    w = w_list[start] + diff * (w_list[start + 1] - w_list[start])
    A = A_list[start] + diff * (A_list[start + 1] - A_list[start])
    s = s_list[start] + diff * (s_list[start + 1] - s_list[start])

    nmols = []
    pdfs = []

    nmol = 1
    Vm = volume / (mass * nmol)
    while True:
        z = (Vm - Vm_bar) / w
        p = P0 + A * math.exp(-math.exp(-z) - z * s + 1)
        nmols.append(nmol)
        pdfs.append(p)
        nmol += 1
        Vm = volume / (mass * nmol)
        if Vm < 1.0:
            break

    return nmols, pdfs


def compute_nmol(
    cell_a,
    cell_b,
    cell_c,
    cell_alpha,
    cell_beta,
    cell_gamma,
    spacegroup,
    resolution,
    sequence_length,
):
    """From some information about the unit cell & symmetry, and the
    length of the sequence and an estimate of the resolution, return
    a likely number of molecules."""

    # since we have as input the lattice and so on some transformation
    # is needed - first compute unit cell volume

    volume = unit_cell_volume(cell_a, cell_b, cell_c, cell_alpha, cell_beta, cell_gamma)

    # then compute the likely unit of mass within the unit cell - that
    # is, one copy of the molecule per asymmetric unit

    mass = sequence_mass(sequence_length) * spacegroup_number_operators(spacegroup)

    # this returns a list of possible nmols, with another list of the
    # associated probabilities

    nmols, pdfs = compute_nmol_from_volume(volume, mass, resolution)

    mbest = 0
    pbest = 0.0

    # pick the most likely probability and return the associated nmol
    # value

    for m, p in zip(nmols, pdfs):
        if p > pbest:
            pbest = p
            mbest = m

    return mbest


def compute_solvent(
    cell_a,
    cell_b,
    cell_c,
    cell_alpha,
    cell_beta,
    cell_gamma,
    spacegroup,
    nmol,
    sequence_length,
):
    """Compute (using matthews_coef) the solvent fraction [0-1] of the
    crystal."""

    m = Matthews_coef()

    m.set_spacegroup(spacegroup)
    m.set_cell((cell_a, cell_b, cell_c, cell_alpha, cell_beta, cell_gamma))
    m.set_nmol(nmol)
    m.set_nres(sequence_length)

    m.compute_solvent()

    return m.get_solvent()

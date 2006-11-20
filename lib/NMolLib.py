#!/usr/bin/env python
# NMolLib.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 21/SEP/06

# NMol per ASU Calculations based on the Kantardjieff & Rupp method.
# 
# Implementing the cell volume calculations of Kantardjieff and Rupp,
# Protein Science volume 12, 2002. Uses "mattprob_params.dat" from
# http://www-structure.llnl.gov/mattprob
#
# Relies on $DPA_ROOT/Data/NMol/mattprob_params.dat

import os, sys, math

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Handlers.Syminfo import Syminfo

if not os.path.exists(os.path.join(os.environ['DPA_ROOT'],
                                   'Data', 'NMol',
                                   'mattprob_params.dat')):
    raise RuntimeError, 'mattprob_params.dat not found'

def unit_cell_volume(cell_a, cell_b, cell_c,
                     cell_alpha, cell_beta, cell_gamma):
    '''From the unit cell constants, compute the volume of the unit cell in
    A^3. Note that it is assumed that the cell_alpha, cell_beta, cell_gamma,
    angles are in degrees and the cell lengths (a, b, c) are in A.'''

    # convert angles to radians from degrees

    pi = 4.0 * math.atan(1.0)
    dtor = pi / 180.0
    rtod = 180.0 / pi

    # then compute the required sines and cosines
    
    ca = math.cos(dtor * cell_alpha)
    cb = math.cos(dtor * cell_beta)
    cc = math.cos(dtor * cell_gamma)
    sa = math.sin(dtor * cell_alpha)
    sb = math.sin(dtor * cell_beta)
    sc = math.sin(dtor * cell_gamma)

    # finally evaluate the volume - this is simply the volume of a
    # parallelopiped
    
    V = cell_a * cell_b * cell_c * math.sqrt(1 - ca * ca - cb * cb - cc * cc
                                             + 2 * ca * cb * cc)
    return V

def spacegroup_number_operators(spacegroup):
    '''From the spacegroup name (either the long or short version of the name)
    compute the number of symmetry operators. This will use the CCP4 symmetry
    library in "counting" mode.'''

    # note slight (!) abuse of exception handling - however this works
    # well as a way of seeing if the input is something which can
    # be interpreted as a number

    try:
        spacegroup_number = int(spacegroup)
    except:
        # spacegroup was passed in as a name
        spacegroup_number = Syminfo.spacegroup_name_to_number(
            spacegroup.upper())

    return Syminfo.get_num_symops(spacegroup_number)

def sequence_mass(sequence):
    '''Return a mass for this sequence - initially will be 128.0 * len'''

    # if input is simply a sequence length, return the appropriate
    # multiple
    
    if type(sequence) == type(42):
        return 128.0 * sequence

    # otherwise it must be a string

    return 128.0 * len(sequence)

def compute_nmol(volume, mass, resolution):

    file = open(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'NMol',
                             'mattprob_params.dat'), 'r')

    while 1:
        line = file.readline()
        if not line[0] == '#':
            break
    
    resolutions = map(float, line.split(','))[:13]
    P0_list = map(float, file.readline().split(','))[:13]
    Vm_bar_list = map(float, file.readline().split(','))[:13]
    w_list = map(float, file.readline().split(','))[:13]
    A_list = map(float, file.readline().split(','))[:13]
    s_list = map(float, file.readline().split(','))[:13]
    file.close()

    if resolution > resolutions[-1]:
        raise RuntimeError, 'Resolution outside useful range'
    if resolution < resolutions[0]:
        Messenger.log_write('Resolution higher than peak %f -> %f' % \
                            (resolution, resolutions[0]))
        resolution = resolutions[0]
                            

    start = 0

    for start in range(12):
        if resolution > resolutions[start] and \
           resolution < resolutions[start + 1]:
            break

    # can start at start - interpolate

    diff = (resolution - resolutions[start]) / \
           (resolutions[start + 1] - resolutions[start])

    P0 = P0_list[start] + diff * (P0_list[start + 1] - P0_list[start])
    Vm_bar = Vm_bar_list[start] + \
             diff * (Vm_bar_list[start + 1] - Vm_bar_list[start])
    w = w_list[start] + diff * (w_list[start + 1] - w_list[start])
    A = A_list[start] + diff * (A_list[start + 1] - A_list[start])
    s = s_list[start] + diff * (s_list[start + 1] - s_list[start])

    nmols = []
    pdfs = []
    
    nmol = 1
    Vm = volume / (mass * nmol)
    while 1:
        z = (Vm - Vm_bar) / w
        p = P0 + A * math.exp(- math.exp(-z) - z * s + 1)
        nmols.append(nmol)
        pdfs.append(p)
        nmol += 1
        Vm = volume / (mass * nmol)
        if Vm < 1.0:
            break

    return nmols, pdfs

def nmol(cell_a, cell_b, cell_c,
         cell_alpha, cell_beta, cell_gamma,
         spacegroup, resolution, sequence_length):
    '''From some information about the unit cell & symmetry, and the
    length of the sequence and an estimate of the resolution, return
    a likely number of molecules.'''

    # since we have as input the lattice and so on some transformation
    # is needed - first compute unit cell volume

    volume = unit_cell_volume(cell_a, cell_b, cell_c,
                              cell_alpha, cell_beta, cell_gamma)

    # then compute the likely unit of mass within the unit cell - that
    # is, one copy of the molecule per asymmetric unit

    mass = sequence_mass(sequence_length) * \
           spacegroup_number_operators(spacegroup)

    # this returns a list of possible nmols, with another list of the
    # associated probabilities

    nmols, pdfs = compute_nmol(volume, mass, resolution)

    ptot = 0

    # sum the pdfs to give the total probability (= 1.0)

    for i in range(len(nmols)):
        p = pdfs[i]
        ptot += p

    mbest = 0
    pbest = 0.0

    # then pick the most likely probability and return the associated nmol
    # value
    
    for i in range(len(nmols)):
        m = nmols[i]
        p = pdfs[i] / ptot
        if p > pbest:
            pbest = p
            mbest = m

    return mbest

if __name__ == '__main__':

    nmol = nmol(96.0, 96.0, 36.75, 90.0, 90.0, 90.0,
                'P 43 21 2', 1.8, 82)

    if nmol != 2:
        raise RuntimeError, 'error in nmol per asu'

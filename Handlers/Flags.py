#/usr/bin/env python
# Flags.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th May 2007
# 
# A singleton to handle flags, which can be imported more easily
# as it will not suffer the problems with circular references that
# the CommandLine singleton suffers from.

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Environment import get_number_cpus

class _Flags:
    '''A singleton to manage boolean flags.'''

    # by default now switch on smart scaling and chef - after the smart
    # scaling has been reset in the XDS Scaler to be "everything"

    def __init__(self):
        self._quick = False
        self._smart_scaling = True
        self._chef = True
        self._automatch = False
        self._reversephi = False
        self._no_lattice_test = False
        self._fiddle_sd = False
        self._harrison_clock = False
        self._migrate_data = False
        self._trust_timestaps = False
	try:
            self._parallel = get_number_cpus()
        except:
            self._parallel = 0
        self._xparallel = 0
        self._batch_scale = False

        # File from which to copy the FreeR_flag column
        self._freer_file = None

        # or alternatively the fraction, or total number of free
        # reflections
        self._free_fraction = None
        self._free_total = None

        # reference reflection file
        self._reference_reflection_file = None

        # these are development parameters for the XDS implementation
        self._z_min = 0.0
        self._refine = True
        self._remove = True
        self._zero_dose = False
        self._relax = True
        self._no_correct = True

        # options to support the -spacegroup flag - the spacegroup is
        # set from this, the lattice and pointgroup derived from such
        self._spacegroup = None
        self._pointgroup = None
        self._lattice = None

        # scala secondary correction
        self._scala_secondary = 6        

        # options to support the -cell option
        self._cell = None

        # resolution limit flags
        self._resolution_low = None
        self._resolution_high = None

        # and these for the mosflm implementation
        self._cellref_mode = 'dumb'
        self._old_mosflm = False

        # and these are general rejection criteria
        self._rejection_threshold = 1.5
        self._i_over_sigma_limit = 2.0

        # are we working with small molecule data?
        self._small_molecule = False

        # flags relating to fixing specific bugs
        self._fixed_628 = False

        # ISPyB things
        self._ispyb_xml_out = None
        
        return

    def set_batch_scale(self, batch_scale):
        self._batch_scale = batch_scale
        return

    def get_batch_scale(self):
        return self._batch_scale

    def set_cellref_mode(self, cellref_mode):
        if not cellref_mode in ['default', 'parallel',
                                'orthogonal', 'both',
                                'new', 'dumb']:
            raise RuntimeError, 'cellref_mode %s unknown' % cellref_mode

        self._cellref_mode = cellref_mode

        return

    ### SETTING OF RESOLUTION LIMITS #### bug # 3183

    def set_resolution_high(self, resolution):
        self._resolution_high = resolution
        return

    def set_resolution_low(self, resolution):
        self._resolution_low = resolution
        return    

    def get_resolution_high(self):
        return self._resolution_high

    def get_resolution_low(self):
        return self._resolution_low
    
    def set_spacegroup(self, spacegroup):
        '''A handler for the command-line option -spacegroup - this will
        set the spacegroup and derive from this the pointgroup and lattice
        appropriate for such...'''

        from Handlers.Syminfo import Syminfo

        # validate by deriving the pointgroup and lattice...

        pointgroup = Syminfo.get_pointgroup(spacegroup)
        lattice = Syminfo.get_lattice(spacegroup)

        # assign

        self._spacegroup = spacegroup
        self._pointgroup = pointgroup
        self._lattice = lattice

        # debug print

        from Handlers.Streams import Debug

        Debug.write('Derived information from spacegroup flag: %s' % \
                    spacegroup)
        Debug.write('Pointgroup: %s  Lattice: %s' % (pointgroup, lattice))

        return

    def get_spacegroup(self):
        return self._spacegroup

    def get_pointgroup(self):
        return self._pointgroup

    def get_lattice(self):
        return self._lattice

    def set_cell(self, cell):
        self._cell = cell
        return

    def get_cell(self):
        return self._cell

    def get_cellref_mode(self):
        return self._cellref_mode

    def set_quick(self, quick):
        self._quick = quick
        return

    def get_quick(self):
        return self._quick

    def set_smart_scaling(self, smart_scaling):
        self._smart_scaling = smart_scaling
        return

    def get_smart_scaling(self):
        return self._smart_scaling

    def set_chef(self, chef):
        self._chef = chef
        return

    def get_chef(self):
        return self._chef

    def set_automatch(self, automatch):
        self._automatch = automatch
        return

    def get_automatch(self):
        return self._automatch

    def set_reversephi(self, reversephi):
        self._reversephi = reversephi
        return

    def get_reversephi(self):
        return self._reversephi

    def set_no_lattice_test(self, no_lattice_test):
        self._no_lattice_test = no_lattice_test
        return

    def get_no_lattice_test(self):
        return self._no_lattice_test

    def set_fiddle_sd(self, fiddle_sd):
        self._fiddle_sd = fiddle_sd
        return

    def get_fiddle_sd(self):
        return self._fiddle_sd

    def set_harrison_clock(self, harrison_clock):
        self._harrison_clock = harrison_clock
        return

    def get_harrison_clock(self):
        return self._harrison_clock

    def set_relax(self, relax):
        self._relax = relax
        return

    def get_relax(self):
        return self._relax

    def set_migrate_data(self, migrate_data):
        self._migrate_data = migrate_data
        return

    def get_migrate_data(self):
        return self._migrate_data

    def set_trust_timestamps(self, trust_timestamps):
        self._trust_timestamps = trust_timestamps
        return

    def get_trust_timestamps(self):
        return self._trust_timestamps

    def set_old_mosflm(self, old_mosflm):
        self._old_mosflm = old_mosflm
        return

    def get_old_mosflm(self):
        return self._old_mosflm

    def set_small_molecule(self, small_molecule):
        self._small_molecule = small_molecule
        return

    def get_small_molecule(self):
        return self._small_molecule

    def set_parallel(self, parallel):
        self._parallel = parallel
        return

    def get_parallel(self):
        return self._parallel

    def set_xparallel(self, xparallel):
        self._xparallel = xparallel
        return

    def get_xparallel(self):
        return self._xparallel

    def set_z_min(self, z_min):
        self._z_min = z_min
        return

    def get_z_min(self):
        return self._z_min

    def set_scala_secondary(self, scala_secondary):
        self._scala_secondary = scala_secondary
        return

    def get_scala_secondary(self):
        return self._scala_secondary

    def set_freer_file(self, freer_file):

        # mtzdump this file to make sure that there is a FreeR_flag
        # column therein...

        freer_file = os.path.abspath(freer_file)

        if not os.path.exists(freer_file):
            raise RuntimeError, '%s does not exist' % freer_file

        from Modules.FindFreeFlag import FindFreeFlag
        from Handlers.Streams import Debug

        column = FindFreeFlag(freer_file)

        Debug.write('FreeR_flag column in %s found: %s' % \
                    (freer_file, column))

        self._freer_file = freer_file
        return

    def get_freer_file(self):
        return self._freer_file

    def set_free_fraction(self, free_fraction):
        self._free_fraction = free_fraction
        return

    def get_free_fraction(self):
        return self._free_fraction

    def set_free_total(self, free_total):
        self._free_total = free_total
        return

    def get_free_total(self):
        return self._free_total   

    def set_ispyb_xml_out(self, ispyb_xml_out):
        self._ispyb_xml_out = ispyb_xml_out
        return

    def get_ispyb_xml_out(self):
        return self._ispyb_xml_out   

    def set_fixed_628(self):
        self._fixed_628 = True
        return

    def get_fixed_628(self):
        return self._fixed_628   

    def set_reference_reflection_file(self, reference_reflection_file):
        '''Set a new reference reflection file.'''

        reference_reflection_file = os.path.abspath(reference_reflection_file)

        if not os.path.exists(reference_reflection_file):
            raise RuntimeError, '%s does not exist' % reference_reflection_file

        self._reference_reflection_file = reference_reflection_file

        return

    def get_reference_reflection_file(self):
        return self._reference_reflection_file

    def set_rejection_threshold(self, rejection_threshold):
        self._rejection_threshold = rejection_threshold
        return

    def get_rejection_threshold(self):
        return self._rejection_threshold

    def set_i_over_sigma_limit(self, i_over_sigma_limit):
        self._i_over_sigma_limit = i_over_sigma_limit
        return

    def get_i_over_sigma_limit(self):
        return self._i_over_sigma_limit

    def set_refine(self, refine):
        self._refine = refine
        return

    def get_refine(self):
        return self._refine

    def set_remove(self, remove):
        self._remove = remove
        return

    def get_remove(self):
        return self._remove

    def set_zero_dose(self, zero_dose):
        self._zero_dose = zero_dose
        return

    def get_zero_dose(self):
        return self._zero_dose

    def set_no_correct(self, no_correct):
        self._no_correct = no_correct
        return

    def get_no_correct(self):
        return self._no_correct

Flags = _Flags()




    

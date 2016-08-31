#!/usr/bin/env python
#
#   Copyright (C) 2016 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler to manage the data ending up in mmCIF output file
# The idea is to use the information passed to the CIF handler,
# translating CIF entries to mmCIF where appropriate.
#
# Later a facility to add only to mmCIF, to override
# (incl. override-delete) mmCIF entries should be added.

from __future__ import division
import iotbx.cif.model
import xia2.Handlers.CIF

class _mmCIFHandler(object):
  def __init__(self):
    self._parent_cif = xia2.Handlers.CIF.CIF

  def get_translated_model(self):
    self._parent_cif.collate_audit_information()
    model = self._parent_cif.get_cif_model().deepcopy()
    for blockname in model:
      block = model[blockname]
      for key in block.item_keys():
        print "Testing ", key
        if translate_CIF_mmCIF(key):
          print "Translating ", key
          block[translate_CIF_mmCIF(key)] = block[key]
          del(block[key])
        # loops are not yet translated
    model.sort(recursive=True)
    return model

  def write_cif(self):
    '''Write mmCIF to file.'''
    with open('xia2.mmcif', 'w') as fh:
      self.get_translated_model().show(out=fh)

def translate_CIF_mmCIF(key):
  if key == '_diffrn_radiation_wavelength':
    return '_diffrn_radiation_wavelength.wavelength'
  prefixlist = [
    'valence_ref', 'valence_param', 'symmetry_equiv', 'symmetry', 'struct_site_view',
    'struct_site_keywords', 'struct_site_gen', 'struct_site', 'struct_sheet_topology',
    'struct_sheet_range', 'struct_sheet_order', 'struct_sheet_hbond', 'struct_sheet',
    'struct_ref_seq_dif', 'struct_ref_seq', 'struct_ref', 'struct_ncs_oper',
    'struct_ncs_ens_gen', 'struct_ncs_ens', 'struct_ncs_dom_lim', 'struct_ncs_dom',
    'struct_mon_prot_cis', 'struct_mon_prot', 'struct_mon_nucl', 'struct_mon_details',
    'struct_keywords', 'struct_conn_type', 'struct_conn', 'struct_conf_type',
    'struct_conf', 'struct_biol_view', 'struct_biol_keywords', 'struct_biol_gen',
    'struct_biol', 'struct_asym', 'struct', 'space_group_symop', 'space_group',
    'software', 'reflns_shell', 'reflns_scale', 'reflns_class', 'reflns', 'refln_sys_abs',
    'refln', 'refine_occupancy', 'refine_ls_shell', 'refine_ls_restr_type',
    'refine_ls_restr_ncs', 'refine_ls_restr', 'refine_ls_class', 'refine_hist',
    'refine_funct_minimized', 'refine_analyze', 'refine_B_iso', 'refine',
    'publ_manuscript_incl', 'publ_body', 'publ_author', 'publ', 'phasing_set_refln',
    'phasing_set', 'phasing_isomorphous', 'phasing_averaging', 'phasing_MIR_shell',
    'phasing_MIR_der_site', 'phasing_MIR_der_shell', 'phasing_MIR_der_refln',
    'phasing_MIR_der', 'phasing_MIR', 'phasing_MAD_set', 'phasing_MAD_ratio',
    'phasing_MAD_expt', 'phasing_MAD_clust', 'phasing_MAD', 'phasing',
    'ndb_struct_na_base_pair_step', 'ndb_struct_na_base_pair', 'ndb_struct_feature_na',
    'ndb_struct_conf_na', 'ndb_original_ndb_coordinates', 'journal_index', 'journal',
    'geom_torsion', 'geom_hbond', 'geom_contact', 'geom_bond', 'geom_angle', 'geom',
    'exptl_crystal_grow_comp', 'exptl_crystal_grow', 'exptl_crystal_face',
    'exptl_crystal', 'exptl', 'entry_link', 'entry', 'entity_src_nat', 'entity_src_gen',
    'entity_poly_seq', 'entity_poly', 'entity_name_sys', 'entity_name_com', 'entity_link',
    'entity_keywords', 'entity', 'em_vitrification', 'em_virus_entity',
    'em_single_particle_entity', 'em_sample_support', 'em_sample_preparation',
    'em_imaging', 'em_image_scans', 'em_icos_virus_shells', 'em_helical_entity',
    'em_experiment', 'em_euler_angle_distribution', 'em_entity_assembly_list',
    'em_entity_assembly', 'em_electron_diffraction_phase',
    'em_electron_diffraction_pattern', 'em_electron_diffraction', 'em_detector',
    'em_buffer_components', 'em_buffer', 'em_assembly', 'em_3d_reconstruction',
    'em_3d_fitting_list', 'em_3d_fitting', 'em_2d_projection_selection',
    'em_2d_crystal_grow', 'em_2d_crystal_entity', 'diffrn_standards',
    'diffrn_standard_refln', 'diffrn_source', 'diffrn_scale_group', 'diffrn_reflns_class',
    'diffrn_reflns', 'diffrn_refln', 'diffrn_radiation_wavelength', 'diffrn_radiation',
    'diffrn_orient_refln', 'diffrn_orient_matrix', 'diffrn_measurement',
    'diffrn_detector', 'diffrn_attenuator', 'diffrn', 'database_PDB_tvect',
    'database_PDB_rev_record', 'database_PDB_rev', 'database_PDB_remark',
    'database_PDB_matrix', 'database_PDB_caveat', 'database_2', 'database', 'computing',
    'citation_editor', 'citation_author', 'citation', 'chemical_formula',
    'chemical_conn_bond', 'chemical_conn_atom', 'chemical', 'chem_link_tor_value',
    'chem_link_tor', 'chem_link_plane_atom', 'chem_link_plane', 'chem_link_chir_atom',
    'chem_link_chir', 'chem_link_bond', 'chem_link_angle', 'chem_link',
    'chem_comp_tor_value', 'chem_comp_tor', 'chem_comp_plane_atom', 'chem_comp_plane',
    'chem_comp_link', 'chem_comp_chir_atom', 'chem_comp_chir', 'chem_comp_bond',
    'chem_comp_atom', 'chem_comp_angle', 'chem_comp', 'cell_measurement_refln',
    'cell_measurement', 'cell', 'audit_link', 'audit_contact_author', 'audit_conform',
    'audit_author', 'audit', 'atom_type', 'atom_sites_footnote', 'atom_sites_alt_gen',
    'atom_sites_alt_ens', 'atom_sites_alt', 'atom_sites', 'atom_site_anisotrop', 'atom_site'
  ]

  for prefix in prefixlist:
    if key == prefix:
      return False
    if key.startswith('_%s_' % prefix):
      return key.replace('_%s_' % prefix, '_%s.' % prefix, 1)
  return False

mmCIF = _mmCIFHandler()

if __name__ == '__main__':
  mmCIF.write_cif()

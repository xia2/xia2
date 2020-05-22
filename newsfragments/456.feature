Add the option ``multi_sweep_refinement`` to the DIALS pipelines.
This performs the same indexing as ``multi_sweep_indexing`` and additionally refines all sweeps together, rather than refining each sweep individually.
When refining the sweeps together, the unit cell parameters of each sweep are restrained to the mean unit cell during the scan-static refinement.
This is achieved by setting the ``dials.refine`` option ``refinement.parameterisation.crystal.unit_cell.restraints.tie_to_group.sigmas=0.01,0.01,0.01,0.01,0.01,0.01``, but other values and ``tie_to_group``/``tie_to_target`` schemes of ``dials.refine`` may be invoked by passing suitable parameters.
See the various xia2 configuration parameters under ``dials.refine.restraints``, which are identical to the settings one can pass to ``dials.refine`` via its own parameter set ``refinement.parameterisation.crystal.unit_cell.restraints``.
As with the normal behaviour of xia2, the restraints do not apply to the scan-varying refinement step.

Since this is likely to be most useful for small-molecule chemical crystallography, the ``multi_sweep_refinement`` behaviour is made the default when ``small_molecule=True``.

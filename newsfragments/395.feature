Prescale data before dials.symmetry when in multi_sweep_indexing mode

This mirrors the behaviour of the CCP4ScalerA by prescaling the data
with KB scaling to ensure that all experiments are on the same scale
before running dials.symmetry. This should lead to more reliable
results from the symmetry analysis in multi_sweep_indexing mode.

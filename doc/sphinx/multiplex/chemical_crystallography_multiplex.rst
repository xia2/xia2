++++++++++++++++++++++++
Chemical Crystallography
++++++++++++++++++++++++

**Note on DIALS versions:** The ``small_molecule`` feature described is available in DIALS versions >3.29.
DIALS versions 3.29 - 3.26 have the ``composition`` parameter.


Data from small molecule (or chemical crystallography) experiments can also be processed using xia2.multiplex.
To enable relevant options for small molecule data processing, set the parameter ``small_molecule=True``.
This will trigger a full symmetry analysis including glide planes, mirror planes etc., i.e. the space group
will not be restricted to MX-only space groups.
Setting the ``small_molecule`` option will also output SHELX-compatible files.  If a user specified composition
is provided with the ``composition`` parameter (e.g. ``composition=C10H14O4Cu``), this will be written into the SHELX
files.
If no composition is provided, a dummy composition of "CH" will be used.
Running SHELXT on your output files will provide an estimation of the number of atoms,
from which you can assign chemical identity later using your preferred refinement program.
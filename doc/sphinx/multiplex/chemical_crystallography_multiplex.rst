++++++++++++++++++++++++
Chemical Crystallography
++++++++++++++++++++++++

Data from small molecule (or chemical crystallography) experiments can also be processed using xia2.multiplex. Full-featured compatibility is still a work in progress, with future plans to integrate full 
space group determination. In the interim, however, this can be done manually on the output .ins / .hkl files. To output SHELX-compatible files, set the option ``small_molecule.composition``
using your known chemical formula (i.e. ``small_molecule.composition=C10H14O4Cu``). If your chemical formula is unknown, enter a dummy formula (i.e. ``small_molecule.composition=CH``). 
Running SHELXT on your output files will provide an estimation of the number of atoms, from which you can assign chemical identity later using your preferred refinement program. 
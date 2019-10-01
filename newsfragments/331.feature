xia2 with DIALS is now more persistent in searching for an indexing
solution when using xia2 in small molecule mode (i.e. when calling
``xia2.small_molecule`` or when calling ``xia2`` with the option
``small_molecule=True``).  Previously, it would perform a 3-d fast
Fourier transform, falling back on a 1-d FFT strategy.  It now performs
the following indexing strategies in turn until a result is found:
  1. Try the standard 3-d/1-d FFT indexing routine;
  2. Do 1 again with the addition of the option
     ``dials.index.max_cell=20``;
  3. Repeat spot finding with the addition of the option
     ``dials.find_spots.sigma_strong=15``, then do 1 & 2 again.
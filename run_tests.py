from __future__ import absolute_import, division, print_function
from libtbx.test_utils.pytest import discover

tst_list = [
  #["$D/Test/Modules/Refiner/TstDialsRefiner.py", "1"],
  ["$D/Test/Modules/Indexer/TstMosflmIndexer.py", "1"],
  ["$D/Test/Modules/Indexer/TstDialsIndexer.py", "1"],
  "$D/Test/Modules/Indexer/TstLabelitIndexer.py",
  "$D/Test/Modules/Indexer/TstLabelitIndexerII.py",
  ["$D/Test/Modules/Indexer/TstXDSIndexer.py", "1"],
  ["$D/Test/Modules/Indexer/TstXDSIndexerII.py", "1"],
  ["$D/Test/Modules/Scaler/TstCCP4ScalerA.py", "1"],
  ["$D/Test/Modules/Scaler/TstXDSScalerA.py", "1"],
  "$D/Test/Wrappers/Labelit/TstLabelitIndex.py",
] + discover()

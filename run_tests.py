from __future__ import absolute_import, division, print_function

from libtbx.test_utils.pytest import discover

tst_list = [
  #["$D/Test/Modules/Refiner/TstDialsRefiner.py", "1"],
  "$D/Test/Modules/Indexer/TstLabelitIndexer.py",
  "$D/Test/Modules/Indexer/TstLabelitIndexerII.py",
] + discover()

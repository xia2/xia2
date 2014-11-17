# xia2 tests - these may require the xia2_regression or dials_regression
# repositories to be available...

from __future__ import division
from libtbx import test_utils
import libtbx.load_env

tst_list = (
    "$D/Test/Modules/Indexer/TstDialsIndexer.py",
    "$D/Test/Modules/Indexer/TstLabelitIndexer.py",
    "$D/Test/Modules/Indexer/TstLabelitIndexerII.py",
    "$D/Test/Modules/Indexer/TstXDSIndexer.py",
    "$D/Test/Modules/Indexer/TstXDSIndexerII.py",
    "$D/Test/Wrappers/Labelit/TstLabelitIndex.py",
    "$D/Test/Wrappers/Dials/TstDialsWrappers.py",
    "$D/Test/Mosflm/MosflmRefactorTest.py",
)

def run () :
  build_dir = libtbx.env.under_build("xia2")
  dist_dir = libtbx.env.dist_path("xia2")
  test_utils.run_tests(build_dir, dist_dir, tst_list)

if (__name__ == "__main__"):
  run()

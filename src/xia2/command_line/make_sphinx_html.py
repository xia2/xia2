# LIBTBX_SET_DISPATCHER_NAME dev.xia2.make_sphinx_html


import os
import shutil

import procrunner
import xia2

if __name__ == "__main__":
    xia2_dir = os.path.dirname(xia2.__file__)
    dest_dir = os.path.join(xia2_dir, "html")
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.chdir(os.path.join(xia2_dir, "doc", "sphinx"))
    result = procrunner.run(["make", "clean"])
    assert result["exitcode"] == 0, (
        "make clean failed with exit code %d" % result["exitcode"]
    )
    result = procrunner.run(["make", "html"])
    assert result["exitcode"] == 0, (
        "make html failed with exit code %d" % result["exitcode"]
    )
    print("Moving HTML pages to", dest_dir)
    shutil.move("build/html", dest_dir)

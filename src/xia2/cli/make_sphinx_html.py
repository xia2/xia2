from __future__ import annotations

import pathlib
import shutil

import procrunner

import xia2


def run():
    xia2_init_file = pathlib.Path(xia2.__file__)
    xia2_dir = xia2_init_file.parent.parent.parent
    if xia2_dir.name != "xia2":
        exit(f"{xia2_dir} does not appear to be the xia2 directory")
    dest_dir = xia2_dir / "html"
    sphinx_dir = xia2_dir / "doc" / "sphinx"
    if dest_dir.is_dir():
        shutil.rmtree(dest_dir)
    result = procrunner.run(["make", "clean"], working_directory=sphinx_dir)
    if result.returncode:
        exit(f"make clean failed with exit code {result.returncode}")

    result = procrunner.run(["make", "html"], working_directory=sphinx_dir)
    if result.returncode:
        exit(f"make html failed with exit code {result.returncode}")

    print("Moving HTML pages to", dest_dir)
    shutil.move(sphinx_dir / "build" / "html", dest_dir)

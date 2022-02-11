from __future__ import annotations

import inspect
import os
import random
import site
import subprocess
import sys
from pathlib import Path

import dials.precommitbx.nagger
import libtbx

try:
    import pkg_resources
except ModuleNotFoundError:
    pkg_resources = None

dials.precommitbx.nagger.nag()


def _install_xia2_setup():
    """Install xia2 as a regular/editable python package"""
    # Call pip
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--no-deps",
            "-e",
            libtbx.env.dist_path("xia2"),
        ],
        check=True,
    )


def _install_xia2_setup_readonly_fallback():
    """Partially install package in the libtbx build folder."""
    xia2_root_path = Path(libtbx.env.dist_path("xia2"))
    xia2_import_path = xia2_root_path / "src"

    # Install this into a build/xia2 subfolder
    build_path = Path(abs(libtbx.env.build_path))
    xia2_build_path = build_path / "xia2"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--prefix",
            xia2_build_path,
            "--no-build-isolation",
            "--no-deps",
            "-e",
            xia2_root_path,
        ],
        check=True,
    )

    # Get the actual environment being configured (NOT libtbx.env)
    env = _get_real_env_hack_hack_hack()

    # Update the libtbx environment pythonpaths to point to the source
    # location which now has an .egg-info folder; this will mean that
    # the PYTHONPATH is written into the libtbx dispatchers
    rel_path = libtbx.env.as_relocatable_path(str(xia2_import_path))
    if rel_path not in env.pythonpath:
        env.pythonpath.insert(0, rel_path)

    # Update the sys.path so that we can find the .egg-info in this process
    # if we do a full reconstruction of the working set
    if str(xia2_import_path) not in sys.path:
        sys.path.insert(0, str(xia2_import_path))

    # ...and add to the existing pkg_resources working_set
    if pkg_resources:
        pkg_resources.working_set.add_entry(xia2_import_path)


def _test_writable_dir(path: Path) -> bool:
    """Test a path is writable. Based on pip's _test_writable_dir_win."""
    # os.access doesn't work on windows
    # os.access won't always work with network filesystems
    # pip doesn't use tempfile on windows because https://bugs.python.org/issue22107
    basename = "test_site_packages_writable_xia2_"
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(10):
        name = basename + "".join(random.choice(alphabet) for _ in range(6))
        file = path / name
        try:
            fd = os.open(file, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            pass
        except PermissionError:
            return False
        else:
            os.close(fd)
            os.unlink(file)
            return True


def _get_real_env_hack_hack_hack():
    """
    Get the real, currently-being-configured libtbx.env environment.

    See equivalent function in the same place in dxtbx for details.
    """
    for frame in inspect.stack():
        if (
            frame.filename.endswith("env_config.py")
            and frame.function == "refresh"
            and "self" in frame.frame.f_locals
        ):
            return frame.frame.f_locals["self"]

    raise RuntimeError("Could not determine real libtbx.env_config.environment object")


def _show_xia2_version():
    try:
        from xia2.XIA2Version import Version

        # the import implicitly updates the .gitversion file
        print(Version)
    except ModuleNotFoundError:
        print("Can't tell xia2 version")


# Detect case where base python environment is read-only
# e.g. on an LCLS session on a custom cctbx installation where the
# source is editable but the conda_base is read-only
#
# We need to check before trying to install as pip does os.access-based
# checks then installs with --user if it fails. We don't want that.
if _test_writable_dir(Path(site.getsitepackages()[0])):
    _install_xia2_setup()
else:
    print("Python site directory not writable - falling back to tbx install")
    _install_xia2_setup_readonly_fallback()


_show_xia2_version()

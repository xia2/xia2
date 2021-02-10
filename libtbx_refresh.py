import dials.precommitbx.nagger

dials.precommitbx.nagger.nag()

import libtbx.load_env

exit(
    ("=" * 80)
    + """

Your xia2 repository is still tracking 'master',
but the main xia2 branch has been renamed to 'main'.

Please go into your xia2 repository at %s and run the following commands:
  git branch -m master main
  git fetch origin
  git branch -u origin/main main

For more information please see https://github.com/xia2/xia2/issues/557
"""
    % libtbx.env.dist_path("xia2")
)


def _install_xia2_setup():
    """Install xia2 as a regular/editable python package"""
    import subprocess
    import sys

    import libtbx.load_env

    # Call pip
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "-e",
            libtbx.env.dist_path("xia2"),
        ],
        check=True,
    )


def _show_xia2_version():
    try:
        from xia2.XIA2Version import Version

        # the import implicitly updates the .gitversion file
        print(Version)
    except ModuleNotFoundError:
        print("Can't tell xia2 version")


_install_xia2_setup()
_show_xia2_version()

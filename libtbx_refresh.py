import dials.precommitbx.nagger

dials.precommitbx.nagger.nag()


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
            "--no-build-isolation",
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

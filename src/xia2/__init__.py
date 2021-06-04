import pathlib
import subprocess
import sys

if sys.version_info.major == 2:
    sys.exit("Python 2 is no longer supported")

__version__ = "3.6.dev"
__version_string__ = f"XIA2 {__version__}"


def _add_git_information_to_version():
    """Obtain a xia2 version number. For releases this is a fixed string,
    maintained by bumpversion. For development builds this may be modified
    depending on the git repository status."""
    global __version__, __version_string__

    try:
        xia2_root_path = pathlib.Path(__file__).parents[2]
        if not xia2_root_path.joinpath(".git").is_dir():
            return
    except Exception:
        return

    try:
        result = subprocess.run(
            ("git", "rev-parse", "--short", "HEAD"),
            check=True,
            cwd=xia2_root_path,
            encoding="latin-1",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        commit = result.stdout.rstrip()
    except Exception:
        return
    __version__ += f"-{commit}"
    __version_string__ += f"-{commit}"

    try:
        result = subprocess.run(
            ("git", "describe", "--contains", "--all", "HEAD"),
            check=True,
            cwd=xia2_root_path,
            encoding="latin-1",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        branch = result.stdout.rstrip()
        if branch:
            __version_string__ += f" ({branch})"
    except Exception:
        return


_add_git_information_to_version()

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import setuptools

# Version number is determined either by git revision (which takes precendence)
# or a static version number which is updated by bump2version
__version_tag__ = "3.9.dev"

console_scripts = [
    "dev.xia2.check_mosaic=xia2.cli.check_mosaic:run",
    "dev.xia2.create_mask=xia2.cli.create_mask:run",
    "dev.xia2.file_statistics=xia2.cli.file_statistics:run",
    "dev.xia2.make_sphinx_html=xia2.cli.make_sphinx_html:run",
    "dev.xia2.show_mask=xia2.cli.show_mask:run",
    "dev.xia2.show_mtz_cells=xia2.cli.show_mtz_cells:run",
    "xia2.add_free_set=xia2.cli.add_free_set:run",
    "xia2.compare_merging_stats=xia2.cli.compare_merging_stats:run",
    "xia2.delta_cc_half=xia2.cli.delta_cc_half:run",
    "xia2.get_image_number=xia2.cli.get_image_number:run",
    "xia2.html=xia2.cli.xia2_html:run_with_log",
    "xia2.index=xia2.cli.index:run_with_log",
    "xia2.integrate=xia2.cli.integrate:run_with_log",
    "xia2.is_doing=xia2.cli.is_doing:main",
    "xia2.ispyb_json=xia2.cli.ispyb_json:run",
    "xia2.ispyb_xml=xia2.cli.ispyb_xml:run",
    "xia2.merging_statistics=xia2.cli.merging_statistics:run",
    "xia2.multi_crystal_analysis=xia2.cli.multi_crystal_analysis:run_with_log",
    "xia2.multiplex=xia2.cli.multiplex:run",
    "xia2.npp=xia2.cli.npp:run",
    "xia2.overload=xia2.cli.overload:run",
    "xia2.plot_multiplicity=xia2.cli.plot_multiplicity:run",
    "xia2.print=xia2.cli.print:run_with_log",
    "xia2.rebatch=xia2.cli.rebatch:run_with_log",
    "xia2.report=xia2.cli.report:run_with_log",
    "xia2.rescale=xia2.cli.rescale:run_with_log",
    "xia2.setup=xia2.cli.setup:run",
    "xia2.small_molecule=xia2.cli.small_molecule:run",
    "xia2.strategy=xia2.cli.strategy:run_with_log",
    "xia2.table1=xia2.cli.table1:run",
    "xia2.to_shelx=xia2.cli.to_shelx:run",
    "xia2.to_shelxcde=xia2.cli.to_shelxcde:run",
    "xia2=xia2.cli.xia2_main:run",
]


def get_git_revision():
    """Try to obtain the current git revision number"""
    xia2_root_path = Path(os.path.realpath(__file__)).parent

    if not xia2_root_path.joinpath(".git").exists():
        return None

    try:
        result = subprocess.run(
            ("git", "describe", "--tags", "--long", "--first-parent"),
            check=True,
            encoding="latin-1",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        major, minor, patch, count, commit = re.match(
            r"v?(\d+)\.(\d+)\.(dev|\d+)-(\d+)-(.+)", result.stdout.rstrip()
        ).groups()
    except Exception:
        return None

    # Some of our version schemes used vX.Y.0-Z
    if patch == "0":
        patch = count
        count = "0"
    elif patch == "dev":
        patch = f"dev{count}"

    # Get the branch name, if not main
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
        if branch and branch != "main" and not branch.endswith("/main"):
            commit = f"{commit}-{branch.rsplit('/', 1)[-1]}"
    except Exception:
        branch = ""

    version = f"{major}.{minor}.{patch}+{commit}"
    return version


setuptools.setup(
    name="xia2",
    version=get_git_revision() or __version_tag__,
    long_description=Path(__file__).parent.joinpath("README.md").read_text(),
    description="An expert system for automated reduction of X-ray diffraction data from macromolecular crystals",
    author="Diamond Light Source",
    license="BSD-3-Clause",
    author_email="dials-support@lists.sourceforge.net",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "": ["*"],
        "xia2": ["Data/*", "css/*", "templates/*"],
        "xia2.Test": ["Handlers/*", "Modules/*", "regression/expected/*"],
    },
    install_requires=[
        "dials-data>=2.0",
        "Jinja2",
        "procrunner",
        "tabulate",
    ],
    entry_points={
        "console_scripts": console_scripts,
        "libtbx.dispatcher.script": [
            "%s=%s" % (x.split("=")[0], x.split("=")[0]) for x in console_scripts
        ],
        "libtbx.precommit": ["xia2=xia2"],
    },
    test_suite="tests",
    tests_require=[
        "pytest>=3.1",
        "pytest-mock",
    ],
    url="https://github.com/xia2/xia2",
)

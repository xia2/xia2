import os
import subprocess
from setuptools import setup, find_packages

# Version number is determined either by git revision (which takes precendence)
# or a static version number which is updated by bump2version
__version_tag__ = "3.3.dev"


def get_git_revision():
    """Try to obtain the current git revision number"""
    xia2_root_path = os.path.split(os.path.realpath(__file__))[0]

    if not os.path.exists(os.path.join(xia2_root_path, ".git")):
        return None

    try:
        result = subprocess.run(
            ("git", "describe", "--long"),
            check=True,
            cwd=xia2_root_path,
            encoding="latin-1",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        version = result.stdout.rstrip()
    except Exception:
        return None
    if version.startswith("v"):
        version = version[1:].replace(".0-", ".")

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
        if branch != "" and branch != "master" and not branch.endswith("/master"):
            version = version + "-" + branch
    except Exception:
        pass

    return version


setup(
    author="Diamond Light Source",
    author_email="scientificsoftware@diamond.ac.uk",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    description="An expert system for automated reduction of X-Ray diffraction data from macromolecular crystals",
    install_requires=[
        "dials-data>=2.0",
        "Jinja2",
        "procrunner",
        "tabulate",
        'importlib_metadata;python_version<"3.8"',
    ],
    license="BSD-3-Clause",
    include_package_data=True,
    keywords="xia2",
    name="xia2",
    packages=find_packages("src"),
    package_dir={"": "src"},
    project_urls={
        "Changelog": "https://github.com/xia2/xia2/blob/master/CHANGELOG.rst",
        "Issue Tracker": "https://github.com/xia2/xia2/issues",
    },
    python_requires=">=3.6",
    data_files=[
        ("xia2", ["XIA2Version.py", "__init__.py", "libtbx_refresh.py", "conftest.py"])
    ],
    test_suite="tests",
    tests_require=[
        "pytest>=3.1",
        "pytest-mock",
    ],
    url="https://github.com/xia2/xia2",
    version=get_git_revision() or __version_tag__,
    zip_safe=False,
)

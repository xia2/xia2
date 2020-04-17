#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages

requirements = ["dials-data", "Jinja2", "procrunner", "six", "tabulate"]

setup_requirements = []
needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
if needs_pytest:
    setup_requirements.append("pytest-runner")

test_requirements = ["mock", "pytest"]

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
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    description="An expert system for automated reduction of X-Ray diffraction data from macromolecular crystals",
    install_requires=requirements,
    license="BSD license",
    include_package_data=True,
    keywords="xia2",
    name="xia2",
    packages=find_packages(),
    package_dir={"xia2": "../xia2"},
    data_files=[
        ("xia2", ["XIA2Version.py", "__init__.py", "libtbx_refresh.py", "conftest.py"])
    ],
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/xia2/xia2",
    version="0.6.476",
    zip_safe=False,
)

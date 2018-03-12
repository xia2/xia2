from __future__ import absolute_import, division, print_function

import libtbx.pkg_utils
from xia2.XIA2Version import Version

# the import implicitly updates the .gitversion file
print(Version)

libtbx.pkg_utils.require('mock', '>=2.0')
libtbx.pkg_utils.require('pytest', '>=3.1')
libtbx.pkg_utils.require('Jinja2')
libtbx.pkg_utils.require('procrunner')

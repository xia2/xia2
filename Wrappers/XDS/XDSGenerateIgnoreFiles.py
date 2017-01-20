#!/usr/bin/env python
# XDSGenerateIgnoreFiles.py
#   Copyright (C) 2014 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# XDS generates files which look like diffraction images but have well defined
# names. This code fetches the documentation for these files and scrapes out
# a list of the file names, and saves these in XDSFiles.py for future ignoring.
#
# This is not used as part of xia2, it is a developer thing.

from __future__ import absolute_import, division

def remove_tags(text):
  import re
  tag_re = re.compile(r'<[^>]+>')
  return ''.join(tag_re.sub('', text))

def XDSGenerateIgnoreFiles():
  import urllib2
  url = urllib2.urlopen(
      'http://xds.mpimf-heidelberg.mpg.de/html_doc/xds_files.html')
  xds_files = url.read()

  xds_files_text = remove_tags(xds_files)

  xds_files = []

  for token in xds_files_text.split():
    token = token.replace('(', '').replace(')', '')
    token = token.replace(',', '').replace('cbf.', 'cbf')
    if '.cbf' in token and not token in xds_files:
      xds_files.append(token)

  with open('XDSFiles.py', 'w') as fout:
    fout.write('XDSFiles = %s\n' % str(xds_files))

if __name__ == '__main__':
  XDSGenerateIgnoreFiles()

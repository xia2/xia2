#!/usr/bin/env python

from __future__ import absolute_import, division, print_function


def remove_tags(text):
    import re

    tag_re = re.compile(r"<[^>]+>")
    return "".join(tag_re.sub("", text))


def XDSGenerateIgnoreFiles():
    import urllib2

    url = urllib2.urlopen("http://xds.mpimf-heidelberg.mpg.de/html_doc/xds_files.html")
    xds_files = url.read()

    xds_files_text = remove_tags(xds_files)

    xds_files = []

    for token in xds_files_text.split():
        token = token.replace("(", "").replace(")", "")
        token = token.replace(",", "").replace("cbf.", "cbf")
        if ".cbf" in token and not token in xds_files:
            xds_files.append(token)

    with open("XDSFiles.py", "w") as fout:
        fout.write("XDSFiles = %s\n" % str(xds_files))

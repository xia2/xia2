from __future__ import absolute_import, division, print_function

from optparse import SUPPRESS_HELP, OptionParser
import sys

if __name__ == '__main__':
  parser = OptionParser(usage="xia2.fetch_test_data [-h | --help] [-d destination]",
                        description="This program is used to download data files used for xia2 regression tests. "
                                    "These files are not required to run xia2, and are only used in tests.")
  parser.add_option("-?", action="help", help=SUPPRESS_HELP)
  parser.add_option("-d", "--destination", dest="destination", default=None,
                    help="Target directory for files, will be created if not present."
                         "Defaults to <build>/xia2_regression.")
  (options, args) = parser.parse_args(sys.argv[1:])
  if args:
    parser.print_help()
    sys.exit(1)

  from xia2.Test.fetch_test_data import fetch_test_data
  if options.destination:
    print("Downloading into directory %s" % options.destination)
  fetch_test_data(options.destination)

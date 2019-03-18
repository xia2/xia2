# ExampleProgramStandardInput.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 27/MAR/06
#
# An example program to test input, output, job control etc. in the new
# XIA. This program will test the standard input handling. It will write
# "Hello, ${user input}!" over and over until user input is ^D or "quit".

from __future__ import absolute_import, division, print_function

import sys
import time

__doc__ = """A small program which will write output to the standard output
every so often, for testing of the XIA core."""


def ep(message, times, spacing):
    """Write a message $message to the screen $times times with spacing of
  $spacing seconds."""

    for i in range(times):
        sys.stdout.write("%s\n" % message)
        sys.stdout.flush()
        time.sleep(spacing)


def run():
    """Read a line of input then write that out again 10 times, unless line
  is EOF or "quit"."""
    while True:
        input = sys.stdin.readline()[:-1]
        if not input:
            return
        if input == "quit":
            return
        ep("Hello, %s!" % input, 10, 1)


if __name__ == "__main__":
    run()

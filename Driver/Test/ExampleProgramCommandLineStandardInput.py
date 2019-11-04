# An example program to test input, output, job control etc. in the new
# XIA. This one tests command line input.

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


def run(message):
    input = sys.stdin.readline()[:-1]
    if not input:
        return
    if input == "quit":
        return
    ep("Hello, %s!" % message, int(input), 0.1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise RuntimeError("%s message" % sys.argv[0])

    run(sys.argv[1])

from __future__ import absolute_import, division, print_function

from dials.command_line.damage_analysis import run


if __name__ == "__main__":
    print("xia2.chef has been renamed to dials.damage_analysis,")
    print("and xia2.chef will be removed in a future release.")
    run()

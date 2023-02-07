from __future__ import annotations

import sys


def run():
    if "small_molecule=true" not in sys.argv and len(sys.argv) > 1:
        sys.argv.insert(1, "small_molecule=true")
    # clean up command-line so we know what was happening i.e. xia2.small_molecule
    # becomes xia2 small_molecule=true (and other things) but without repeating
    # itself
    import libtbx.load_env

    from xia2.cli import extra_help_lines

    extra_help_lines.append(
        "[chemical_formula=C20H20N2O2Br] (say) - formula for shelxt input fileg\n"
    )
    libtbx.env.dispatcher_name = "xia2"
    import xia2.cli.xia2_main

    xia2.cli.xia2_main.run()

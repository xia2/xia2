import sys

if __name__ == "__main__":
    if "small_molecule=true" not in sys.argv and len(sys.argv) > 1:
        sys.argv.insert(1, "small_molecule=true")
    # clean up command-line so we know what was happening i.e. xia2.small_molecule
    # becomes xia2 small_molecule=true (and other things) but without repeating
    # itself
    import libtbx.load_env

    libtbx.env.dispatcher_name = "xia2"
    from xia2.command_line.xia2_main import run

    run()

from __future__ import absolute_import, division, print_function

# this must be defined in a separate file from xia2setup.py to be
# compatible with easy_mp.parallel_map with method="sge" when
# xia2setup.py is run as the __main__ program.
def get_sweep(args):
    import os
    import traceback
    from xia2.Schema.Sweep import SweepFactory

    assert len(args) == 1
    directory, template = os.path.split(args[0])

    try:
        sweeplist = SweepFactory(template, directory)

    except Exception as e:
        from xia2.Handlers.Streams import Debug

        Debug.write("Exception C: %s (%s)" % (str(e), args[0]))
        Debug.write(traceback.format_exc())
        return None

    return sweeplist

# A jiffy to try and identify the FreeR column in an MTZ file - will look for
# FreeR_flag, then *free*, will check that the column type is 'I' and so
# will be useful when an external reflection file is passed in for copying
# of the FreeR column.


from xia2.Wrappers.CCP4.Mtzdump import Mtzdump


def FindFreeFlag(hklin):
    """Try to find the FREE column in hklin. Raise exception if no column is
    found or if more than one candidate is found."""

    # get the information we need here...

    mtzdump = Mtzdump()
    mtzdump.set_hklin(hklin)
    mtzdump.dump()
    columns = mtzdump.get_columns()

    ctypes = {c[0]: c[1] for c in columns}

    if "FreeR_flag" in ctypes:
        if ctypes["FreeR_flag"] != "I":
            raise RuntimeError("FreeR_flag column found: type not I")

        return "FreeR_flag"

    # ok, so the usual one wasn't there, look for anything with "free"
    # in it...

    possibilities = [c for c in ctypes if "free" in c.lower()]

    if not possibilities:
        raise RuntimeError("no candidate FreeR_flag columns found")

    if len(possibilities) == 1:
        if ctypes[possibilities[0]] != "I":
            raise RuntimeError(
                "FreeR_flag column found (%s): type not I" % possibilities[0]
            )

        return possibilities[0]

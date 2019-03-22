from __future__ import absolute_import, division, print_function


def main():
    import sys

    for argv in sys.argv[1:]:
        print(E4_mtz(argv))


def E4_mtz(hklin, native=True):
    from iotbx import reflection_file_reader

    reflection_file = reflection_file_reader.any_reflection_file(file_name=hklin)
    if reflection_file.file_type() is None:
        raise RuntimeError("error reading %s" % hklin)
    miller_arrays = reflection_file.as_miller_arrays()

    E4s = {}

    for ma in miller_arrays:
        if str(ma.observation_type()) != "xray.intensity":
            continue
        if native and ma.anomalous_flag():
            continue
        E4s[ma.info().label_string()] = E4(ma)

    return E4s


def E4(ma):
    import sys
    from six.moves import cStringIO as StringIO

    cache_stdout = sys.stdout
    sys.stdout = StringIO()
    sg = ma.space_group()
    if sg.is_centric():
        asg = sg.build_derived_acentric_group()
        ma = ma.customized_copy(space_group_info=asg.info())
    from mmtbx.scaling.twin_analyses import twin_analyses

    analysis = twin_analyses(ma)
    sys.stdout = cache_stdout
    return analysis.wilson_moments.acentric_i_ratio


if __name__ == "__main__":
    main()

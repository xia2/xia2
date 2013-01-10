
def main():
    import sys

    for argv in sys.argv[1:]:
        print E4_mtz(argv)

def E4_mtz(hklin, native = True):
    from iotbx import reflection_file_reader
    reflection_file = reflection_file_reader.any_reflection_file(
        file_name = hklin)
    if reflection_file.file_type() is None:
        raise RuntimeError, 'error reading %s' % hklin
    miller_arrays = reflection_file.as_miller_arrays()

    E4s = { } 

    for ma in miller_arrays:
        if str(ma.observation_type()) != 'xray.intensity':
            continue
        if native and ma.anomalous_flag():
            continue
        E4s[ma.info().label_string()] = E4(ma)

    return E4s
    

def E4(ma):
    f = ma.as_intensity_array()
    f = f.array(data=f.data()/f.epsilons().data().as_double())
    f.set_observation_type_xray_intensity()
    f.setup_binner(auto_binning = True)
    sm = f.second_moment(use_binning = True)
    moments = [m for m in [sm.data[j] for j in f.binner().range_used()] if m]
    return sum(moments) / len(moments)

if __name__ == '__main__':
    main()

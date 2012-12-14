
def main():
    import sys
    from iotbx import reflection_file_reader

    for argv in sys.argv[1:]:
        reflection_file = reflection_file_reader.any_reflection_file(
            file_name = argv)
        if reflection_file.file_type() is None:
            continue
        miller_arrays = reflection_file.as_miller_arrays()

        for ma in miller_arrays:
            print ma.info().label_string(), E4(ma)

def E4(ma):
    f = ma.as_intensity_array()
    f = f.array(data=f.data()/f.epsilons().data().as_double())
    f.set_observation_type_xray_intensity()
    f.setup_binner(auto_binning = True)
    sm = f.second_moment(use_binning = True)
    moments = [sm.data[j] for j in f.binner().range_used()]
    return sum(moments) / len(moments)

if __name__ == '__main__':
    main()

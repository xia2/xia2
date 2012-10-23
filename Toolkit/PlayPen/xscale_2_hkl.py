from iotbx.xds.read_ascii import reader
import sys
for n, argv in enumerate(sys.argv[1:]):
    r = reader(open(argv))
    mas = r.as_miller_arrays(merge_equivalents = False)
    assert(len(mas) == 1)
    ma = mas[0].apply_scaling(target_max = 1.0e6)

    i = ma.data()
    s = ma.sigmas()
    hkl = ma.indices()

    for j, h in enumerate(hkl):
        print '%4d%4d%4d%8.2f%8.2f%4d' % (h[0], h[1], h[2], 
                                          i[j], s[j], n + 1)


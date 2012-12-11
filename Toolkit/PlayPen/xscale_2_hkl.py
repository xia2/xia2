from iotbx.xds.read_ascii import reader
import sys
for n, argv in enumerate(sys.argv[1:]):
    r = reader(open(argv))
    mas = r.as_miller_arrays(merge_equivalents = False)
    assert(len(mas) == 1)
    ma = mas[0].apply_scaling(target_max = 9.99e5)

    i = ma.data()
    s = ma.sigmas()
    hkl = ma.indices()

    for j, h in enumerate(hkl):

        _i = ('%f' % i[j])[:7]
        assert('.' in _i)
        _s = ('%f' % s[j])[:7]
        assert('.' in _s)

        if s[j] >= 0.0:
            print '%4d%4d%4d%8s%8s%4d' % (h[0], h[1], h[2], 
                                          _i, _s, n + 1)


def decompose_a(a):
    '''Decompose real-space orientation matrix into quaternion and
    unit cell.'''

    from cctbx import uctbx
    from scitbx import matrix

    _a = matrix.col(a[0:3])
    _b = matrix.col(a[3:6])
    _c = matrix.col(a[6:9])

    unit_cell = uctbx.unit_cell((_a.length(), _b.length(), _c.length(),
                                 _b.angle(_c, deg = True),
                                 _c.angle(_a, deg = True),
                                 _a.angle(_b, deg = True)))

    b = matrix.sqr(unit_cell.fractionalization_matrix())

    ub  = matrix.sqr(a)

    u = ub * b.transpose()

    return u.r3_rotation_matrix_as_unit_quaternion().elems, unit_cell
    
def make_matrix(xparm):
    '''Make a real-space orientation matrix from XDS XPARM file.'''
    
    from scitbx import matrix
    
    tokens = map(float, open(xparm, 'r').read().split())

    assert(len(tokens) == 42)

    return matrix.sqr(tokens[-9:])
    
def compare_ub(a, b):
    '''Compare orientation (UB matrices) a and b by computing rotation
    between them and breaking this down to a unit quaternion.'''

    _a = make_matrix(a)
    decompose_a(_a)
    _b = make_matrix(b)
    decompose_a(_b)

    _r = _b * _a.inverse()

    return _r.r3_rotation_matrix_as_unit_quaternion().elems

if __name__ == '__main__':
    import sys

    assert(len(sys.argv) > 2)

    for a in sys.argv[1:]:
        rot, uc = decompose_a(make_matrix(a))

        print '%6.2f %6.2f %6.2f %6.2f' % rot
        

    

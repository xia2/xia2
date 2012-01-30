import math
import sys

def parse_profile(profile_lines, dx = 9, dy = 9, dz = 9):
    '''Parse profiles to an array of values.'''

    offblock = 2
    offline = 3

    assert(dx == 9)
    assert(dy == 9)
    assert(dz == 9)

    sum_xd = 0.0
    sum_yd = 0.0
    sum_zd = 0.0
    sum_d = 0.0

    for islice in range(dz):
        for irow in range(dy):
            for icol in range(dx):
                iblock = islice / 3
                record = profile_lines[offblock * (1 + iblock) +
                                       dy * iblock + irow]
                ichunk = islice % 3
                itoken = offline * (ichunk + 1) + 3 * dx * ichunk + icol * 3
                token = record[itoken:itoken + 3]

                x = icol - 4
                y = irow - 4
                z = islice - 4

                d = int(token)

                sum_d += d

                sum_xd += x * d
                sum_yd += y * d
                sum_zd += z * d

    return sum_xd / sum_d, sum_yd / sum_d, sum_zd / sum_d

def integrate_compute_com(integrate_lp, dx = 9, dy = 9, dz = 9):
    '''From the records in INTEGRATE.LP, compute the centre of mass as a
    function of block number.'''

    # first get and store the profiles from the log file, which will
    # be indexed on the first, last image, then profile #, then
    # y, then x (i.e. down, then right)

    profiles = { }

    image_block = None
    nref = 0

    records = open(integrate_lp).readlines()

    for j, record in enumerate(records):

        if 'PROCESSING OF IMAGES' in record:
            image_block = tuple(
                map(int, record.replace('...', '').split()[-2:]))

        if 'AVERAGE THREE-DIMENSIONAL PROFILE' in record:
            nref = int(record.split()[5])
            i = j + 1

            profile_text = []

            while not 'REFLECTION INTENSITIES INTEGRATED'in records[i]:
                profile_text.append(records[i])
                i += 1

            profiles[image_block] = profile_text

            print '%4d %4d: ' % image_block, '%5d' % nref, \
                  '%6.3f %6.3f %6.3f' % parse_profile(profile_text)


if __name__ == '__main__':

    integrate_compute_com(sys.argv[1])

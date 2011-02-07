import math
import sys

    

def integrate_compute_com(integrate_lp, dx = 9, dy = 9, dz = 9):
    '''From the records in INTEGRATE.LP, compute the centre of mass as a
    function of block number.'''

    # first get and store the profiles from the log file, which will
    # be indexed on the first, last image, then profile #, then
    # y, then x (i.e. down, then right)

    profiles = { }

    image_block = None

    records = open(integrate_lp).readlines()

    for j, record in enumerate(records):

        if 'PROCESSING OF IMAGES' in record:
            image_block = tuple(
                map(int, record.replace('...', '').split()[-2:]))

            print image_block
        
        if 'AVERAGE THREE-DIMENSIONAL PROFILE' in record:
            i = j + 1

            profile_text = []
            
            while not 'REFLECTION INTENSITIES INTEGRATED'in records[i]:
                profile_text.append(records[i])
                i += 1

            profiles[image_block] = profile_text

            print len(profiles[image_block])

    print profile_text

if __name__ == '__main__':

    integrate_compute_com(sys.argv[1])

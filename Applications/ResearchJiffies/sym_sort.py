# some code to try parsing duncan's dat file

from cctbx.array_family import flex
from cctbx.miller import array
from cctbx.miller import build_set
from cctbx.miller import map_to_asu
from cctbx import crystal
from cctbx import uctbx
from cctbx import sgtbx
import struct
import time

def read_dat(dat_file):
    '''Read the first 4 bytes (which should be an int) interpret this as
    such then read this many times more 8 byte doubles. Put them in a list.'''

    dats = []

    fin = open(dat_file, 'r')

    count_bin = fin.read(4)

    # duh this is in big-endian format from Java...

    ndat = struct.unpack('>i', count_bin)

    print 'Guessed %d reflections' % ndat

    for j in range(ndat[0]):
        chunk = fin.read(64)
        dats.append(struct.unpack('>8d', chunk))

    return dats

def read_hkl(hkl_file):
    '''Read the first 4 bytes (which should be an int) interpret this as
    such then read this many times more 4 byte ints. Put them in a list.'''

    hkls = []

    fin = open(hkl_file, 'r')

    count_bin = fin.read(4)

    # duh this is in big-endian format from Java...

    nhkl = struct.unpack('>i', count_bin)

    print 'Guessed %d reflections' % nhkl

    # then read all of the hkl's in

    for j in range(nhkl[0]):
        chunk = fin.read(12)
        hkls.append(struct.unpack('>3i', chunk))
                        
    return hkls

def read_hits(hits_files):
    '''Just read the whole file: dont know how many hits will be in there
    ab initio. This contains INTS fle number + offset.'''

    hits = { }

    for hits_file in hits_files:

        fin = open(hits_file, 'r')

        while True:
            chunk = fin.read(8)
            if not chunk:
                break
            f, o = struct.unpack('<2I', chunk)
            if not f in hits:
                hits[f] = []
            hits[f].append(o)

    return hits
        
if __name__ == '__main__':

    import sys, math, time, os

    # first read through all of the hits files - assume that these are all
    # of the files passed on the command line which end in .hit

    hits_files = []

    for arg in sys.argv[1:]:
        if arg[-4:] == '.hit':
            hits_files.append(arg)

    hits = read_hits(hits_files)

    sorted_hits = { }

    for f in sorted(hits):
        sorted_hits[f] = sorted(list(set(hits[f])))

    # now read all of the .hkl and .dat files

    hkl_files = []
    dat_files = []
    
    for arg in sys.argv[1:]:
        if arg[-4:] == '.hkl':
            hkl_files.append(arg)
        if arg[-4:] == '.dat':
            dat_files.append(arg)
        
    rtod = 180.0 / math.pi

    # read the XDS xparm file -> get the spacegroup number

    spacegroup_number = -1

    for arg in sys.argv:
        if arg[-4:] == '.XDS':
            data = map(float, open(arg, 'r').read().split())
            spacegroup_number = int(data[26])

    if spacegroup_number == -1:
        raise RuntimeError, 'spacegroup number not found'

    # now generate a space group from this, via hall symbol, then
    # calculate the corresponding reciprocal space asymmetric unit
    
    spacegroup = sgtbx.space_group_symbols(spacegroup_number).hall()
    sg = sgtbx.space_group(spacegroup)
    asu = sgtbx.reciprocal_space_asu(sg.type())

    # and get the list of symmetry operations: these will be needed to
    # reduce the unmerged miller index to the asymmetric unit, as I've
    # not found a better way...

    for hkl_file in hkl_files:

        reflections = []
        
        fileno =int(hkl_file.replace('.hkl', '').split('-')[-1])
        dat_file = '%s.dat' % hkl_file[:-4]
        
        hkls = read_hkl(hkl_file)
        dats = read_dat(dat_file)
        hits = sorted_hits[fileno]

        print 'Found %d hits for file %d' % (len(hits), fileno)
        print 'These go to from %d to %d' % (hits[0], hits[-1])

        # now work out which are not measured

        for j in range(len(hkls)):
            h, k, l = hkls[j]
            o1, x1, y1, z1, o2, x2, y2, z2 = dats[j]
            
            if not 2 * j in hits:
                reflections.append((rtod * o1, h, k, l))

            if not 2 * j + 1 in hits:
                reflections.append((rtod * o2, h, k, l))

        # now need to work through this reflection list and reduce them
        # according to the symmetry... then sort them on the rotation
        # angle...

        # also remove the reflection if it is systematically absent!
        # do this as two passes - first however try replacing this code
        # with smarter stuff from cctbx...

        start = time.time()

        new_reflections = []
        
        fast = flex.miller_index()
        data = flex.double()
        
        for r in reflections:

            # only copy across the ones which should be present
            
            if sg.is_sys_absent([h, k, l]):
                continue

            o, h, k, l = r
            data.append(o)
            fast.append([h, k, l])

        map_to_asu(sg.type(), False, fast, data)

        # now unpack to original data structures

        for j in range(data.size()):
            d = data[j]
            hkl = fast[j]
            new_reflections.append((d, hkl[0], hkl[1], hkl[2]))
            
        # now do something with these symmetry reduced reflections...

        outfile = '%s.sym' % os.path.split(hkl_file)[-1][:-4]
        print 'Writing reflections to %s' % outfile

        fout = open(outfile, 'w')

        for reflection in new_reflections:
            fout.write('%7.3f %d %d %d\n' % reflection)

        fout.close()

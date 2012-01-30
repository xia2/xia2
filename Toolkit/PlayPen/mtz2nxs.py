import sys

from numpy import array

import iotbx.mtz
import h5py

def mtz2nxs(hklin, nxsout):
    '''Read in hklin, get the columns for H K L IMEAN and SIGIMEAN,
    write these out as hdf5 datasets.'''

    mtz_obj = iotbx.mtz.object(hklin)

    h = None
    k = None
    l = None

    i = None
    sigi = None

    for crystal in mtz_obj.crystals():
        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == 'H':
                    h = column.extract_values(not_a_number_substitute = 0.0)
                if column.label() == 'K':
                    k = column.extract_values(not_a_number_substitute = 0.0)
                if column.label() == 'L':
                    l = column.extract_values(not_a_number_substitute = 0.0)
                if column.label() == 'IMEAN':
                    i = column.extract_values(not_a_number_substitute = 0.0)
                if column.label() == 'SIGIMEAN':
                    sigi = column.extract_values(not_a_number_substitute = 0.0)

    # now copy these into a nexus file

    fout = h5py.File(nxsout)

    group = fout.create_group('entry1')
    group.attrs['NX_class'] = 'NXentry'

    data = group.create_group('data')
    data.attrs['NX_class'] = 'NXdata'

    dh = data.create_dataset('H', (len(h),), 'i', data = array(h))
    dk = data.create_dataset('K', (len(k),), 'i', data = array(k))
    dl = data.create_dataset('L', (len(l),), 'i', data = array(l))

    di = data.create_dataset('I', (len(i),), 'f', data = array(i))
    di.attrs['signal'] = 1

    dsigi = data.create_dataset('SIGI', (len(sigi),), 'f', data = array(sigi))

    fout.close()

    return

def obsolete():

    for j in range(len(h)):
        dh[j] = h[j]

    dk = data.create_dataset('K', (len(k),), 'i')
    for j in range(len(k)):
        dk[j] = k[j]

    dl = data.create_dataset('L', (len(l),), 'i')
    for j in range(len(l)):
        dl[j] = l[j]

    di = data.create_dataset('I', (len(i),), 'f')
    di.attrs['signal'] = 1

    for j in range(len(i)):
        di[j] = i[j]

    dsigi = data.create_dataset('SIGI', (len(sigi),), 'f')
    for j in range(len(sigi)):
        dsigi[j] = sigi[j]

    fout.close()

if __name__ == '__main__':

    mtz2nxs(sys.argv[1], sys.argv[2])

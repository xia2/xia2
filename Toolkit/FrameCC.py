def read_image(image_name):
    from scitbx.array_family import flex
    from cbflib_adaptbx import uncompress, compress
    import binascii

    start_tag = binascii.unhexlify('0c1a04d5')

    data = open(image_name, 'rb').read()
    data_offset = data.find(start_tag) + 4
    cbf_header = data[:data_offset - 4]

    fast = 0
    slow = 0
    length = 0
    
    for record in cbf_header.split('\n'):
        if 'X-Binary-Size-Fastest-Dimension' in record:
            fast = int(record.split()[-1])
        elif 'X-Binary-Size-Second-Dimension' in record:
            slow = int(record.split()[-1])
        elif 'X-Binary-Number-of-Elements' in record:
            length = int(record.split()[-1])
            
    assert(length == fast * slow)

    pixel_values = uncompress(packed = data[data_offset:],
                              fast = fast, slow = slow)

    return pixel_values

def read_image(image_name):
    import dxtbx
    return dxtbx.load(image_name).get_raw_data()

def cc(a, b):
    pass

if __name__ == '__main__':
    import sys
    i = read_image(sys.argv[1])
    help(i)

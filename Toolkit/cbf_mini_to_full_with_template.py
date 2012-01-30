#!/usr/bin/env python

import sys
import math
import string
import os

metatemplate = os.path.join(os.environ['XIA2_ROOT'],
                            'Toolkit', 'metatemplate.txt')

def create_template_simple(beamline, xtal_id, detector_id, detector_name,
                           beam, pixel, distance):
    '''Return a cbf template configured for the generation of full cbf
    images. This is the simple version which does not look at previous
    data sets.'''

    template_template = open(metatemplate).read()

    return template_template % {
        "beamline":beamline,
        "xtal_id":xtal_id,
        "detector_id":detector_id,
        "detector_name":detector_name,
        "beam_x":beam[0],
        "beam_y":beam[1],
        "pixel_x":pixel[0],
        "pixel_y":pixel[1],
        "distance":distance
        }

def zoop(beam_pixel, distance):

    beamline = 'dls'
    xtal_id = 'xtal001'
    detector_id = 'Pilatus6M'
    detector_name = 'DLS-I03-P6M'
    pixel = (0.172, 0.172)
    distance_mm = 1000.0 * distance

    beam = (beam_pixel[0] * pixel[0], beam_pixel[1] * pixel[1])

    return create_template_simple(beamline, xtal_id, detector_id,
                                  detector_name, beam, pixel, distance_mm)

def split_header(cbf_file):
    return open(cbf_file).read().split('--CIF-BINARY-FORMAT-SECTION--')[0]

def understand_minicbf(cbf_file):

    Exposure_time = None
    Exposure_period = None
    Start_angle = None
    Angle_increment = None
    Timestamp = None
    Count_cutoff = None
    Compression_type = 'CBF_BYTE_OFFSET'
    X_dimension = 2463
    Y_dimension = 2527
    Wavelength = None
    Detector_distance = None
    Beam_x = None
    Beam_y = None

    cleanup = string.maketrans('(),:', '    ')

    for record in split_header(cbf_file).split('\n'):
        if not '#' in record:
            continue

        if len(record.split()) == 2 and '-' in record and ':' in record:
            Timestamp = record.split()[1]
            month = {'Jan':1, 'Feb':2, 'Mar':3,
                     'Apr':4, 'May':5, 'Jun':6,
                     'Jul':7, 'Aug':8, 'Sep':8,
                     'Oct':10, 'Nov':11, 'Dec':12}
            for k in month:
                Timestamp = Timestamp.replace(k, '%d' % month[k])

        tokens = record.translate(cleanup).strip().split()[1:]

        name = tokens[0]

        if name == 'Exposure_time':
            Exposure_time = float(tokens[1])
        elif name == 'Exposure_period':
            Exposure_period = float(tokens[1])
        elif name == 'Start_angle':
            Start_angle = float(tokens[1])
        elif name == 'Angle_increment':
            Angle_increment = float(tokens[1])
        elif name == 'Timestamp':
            Timestamp = float(tokens[1])
        elif name == 'Count_cutoff':
            Count_cutoff = int(tokens[1])
        elif name == 'X_dimension':
            X_dimension = float(tokens[1])
        elif name == 'Y_dimension':
            Y_dimension = float(tokens[1])
        elif name == 'Wavelength':
            Wavelength = float(tokens[1])
        elif name == 'Detector_distance':
            Detector_distance = float(tokens[1])
        elif name == 'Beam_xy':
            Beam_x = float(tokens[1])
            Beam_y = float(tokens[2])

    template = zoop((Beam_x, Beam_y), Detector_distance)

    map1 = {'Exposure_time':Exposure_time,
            'Exposure_period':Exposure_period,
            'Start_angle':Start_angle,
            'Angle_increment':Angle_increment,
            'Timestamp':Timestamp,
            'Count_cutoff':Count_cutoff,
            'Compression_type':Compression_type,
            'X_dimension':X_dimension,
            'Y_dimension':Y_dimension,
            'Wavelength':Wavelength,
            'Beam_x':Beam_x,
            'Beam_y':Beam_y}

    map2 = { }

    for record in template.split('\n'):
        if not '@' in record[:1]:
            continue
        tokens = record.split()[1:]
        map2[tokens[0]] = tokens[1]

    map3 = { }

    for name in map2:
        map3[map2[name]] = map1[name]

    for name in map3:
        template = template.replace(name, str(map3[name]))

    template = template.replace('@', '#')

    template = template.replace('--- End of preamble', '').strip()

    header = ''

    for record in template.split('\n'):

        if '###CBF' in record[:6]:
            header += '%s\r\n' % record.strip()
            header += '\r\n%s\r\n' % 'data_image_1'
        if '#' in record[:1]:
            continue
        header += '%s\r\n' % record.strip()

    template = header

    chunk = '''\r\n_array_data.array_id ARRAY1\r\n_array_data.binary_id 1\r\n_array_data.data\r\n;\r\n--CIF-BINARY-FORMAT-SECTION--'''
    rest = '''--CIF-BINARY-FORMAT-SECTION----\r\n;\r\n'''

    return template + chunk + open(cbf_file).read().split(
        '--CIF-BINARY-FORMAT-SECTION--')[1] + rest

if __name__ == '__main__':

    if os.path.exists(sys.argv[2]):
        raise RuntimeError, 'will not overwrite %s' % sys.argv[2]

    open(sys.argv[2], 'wb').write(understand_minicbf(sys.argv[1]))

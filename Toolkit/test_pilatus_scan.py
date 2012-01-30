import os
import sys
import math
import pycbf

def failover_cbf(cbf_file):
    '''CBF files from the latest update to the PILATUS detector cause a
    segmentation fault in diffdump. This is a workaround.'''

    header = { }

    header['two_theta'] = 0.0

    for record in open(cbf_file):

        if '_array_data.data' in record:
            break

        if 'PILATUS 2M' in record:
            header['detector_class'] = 'pilatus 2M'
            header['detector'] = 'dectris'
            header['size'] = (1679, 1475)
            continue

        if 'PILATUS 6M' in record:
            header['detector_class'] = 'pilatus 6M'
            header['detector'] = 'dectris'
            header['size'] = (2527, 2463)
            continue

        if 'Start_angle' in record:
            header['phi_start'] = float(record.split()[-2])
            continue

        if 'Angle_increment' in record:
            header['phi_width'] = float(record.split()[-2])
            continue

        if 'Filter_transmission' in record:
            header['transmission'] = float(record.split()[-1])
            continue

        if 'Exposure_period' in record:
            header['exposure_time'] = float(record.split()[-2])
            continue

        if 'Detector_distance' in record:
            header['distance'] = 1000 * float(record.split()[2])
            continue

        if 'Wavelength' in record:
            header['wavelength'] = float(record.split()[-2])
            continue

        if 'Pixel_size' in record:
            header['pixel'] = 1000 * float(record.split()[2]), \
                              1000 * float(record.split()[5])
            continue

        if 'Beam_xy' in record:

            # N.B. this is swapped again for historical reasons

            beam_pixels = map(float, record.replace('(', '').replace(
                ')', '').replace(',', '').split()[2:4])
            header['beam'] = beam_pixels[1] * header['pixel'][1], \
                             beam_pixels[0] * header['pixel'][0]
            header['raw_beam'] = beam_pixels[1] * header['pixel'][1], \
                                 beam_pixels[0] * header['pixel'][0]
            continue

        # try to get the date etc. literally.

        try:
            datestring = record.split()[-1].split('.')[0]
            format = '%Y-%b-%dT%H:%M:%S'
            struct_time = time.strptime(datestring, format)
            header['date'] = time.asctime(struct_time)
            header['epoch'] = time.mktime(struct_time)

        except:
            pass

        try:

            if not 'date' in header:
                datestring = record.split()[-1].split('.')[0]
                format = '%Y-%m-%dT%H:%M:%S'
                struct_time = time.strptime(datestring, format)
                header['date'] = time.asctime(struct_time)
                header['epoch'] = time.mktime(struct_time)

        except:
            pass

        try:

            if not 'date' in header:
                datestring = record.replace('#', '').strip().split('.')[0]
                format = '%Y/%b/%d %H:%M:%S'
                struct_time = time.strptime(datestring, format)
                header['date'] = time.asctime(struct_time)
                header['epoch'] = time.mktime(struct_time)

        except:
            pass

    # clean up to cope with ESRF header randomisation
    header['phi_end'] = header['phi_start'] + header['phi_width']

    return header

def failover_full_cbf(cbf_file):
    '''Use pycbf library to read full cbf file description.'''

    header = { }

    cbf_handle = pycbf.cbf_handle_struct()
    cbf_handle.read_file(cbf_file, pycbf.MSG_DIGEST)

    cbf_handle.rewind_datablock()

    detector = cbf_handle.construct_detector(0)

    # FIXME need to check that this is doing something sensible...!

    header['beam'] = tuple(map(math.fabs, detector.get_beam_center()[2:]))
    detector_normal = tuple(detector.get_detector_normal())

    gonio = cbf_handle.construct_goniometer()

    axis = tuple(gonio.get_rotation_axis())
    angles = tuple(gonio.get_rotation_range())

    header['distance'] = detector.get_detector_distance()
    header['pixel'] = (detector.get_inferred_pixel_size(1),
                       detector.get_inferred_pixel_size(2))

    header['phi_start'], header['phi_width'] = angles
    header['phi_end'] = header['phi_start'] + header['phi_width']

    year, month, day, hour, minute, second, x = cbf_handle.get_datestamp()
    struct_time = datetime.datetime(year, month, day,
                                    hour, minute, second).timetuple()

    header['date'] = time.asctime(struct_time)
    header['epoch'] = cbf_handle.get_timestamp()[0]
    header['size'] = tuple(cbf_handle.get_image_size(0))
    header['exposure_time'] = cbf_handle.get_integration_time()
    header['wavelength'] = cbf_handle.get_wavelength()
    header['two_theta'] = 0.0

    # find the direct beam vector - takes a few steps
    cbf_handle.find_category('axis')

    # find record with equipment = source
    cbf_handle.find_column('equipment')
    cbf_handle.find_row('source')

    # then get the vector and offset from this

    beam_direction = []

    for j in range(3):
        cbf_handle.find_column('vector[%d]' % (j + 1))
        beam_direction.append(cbf_handle.get_doublevalue())

    detector.__swig_destroy__(detector)
    del(detector)

    gonio.__swig_destroy__(gonio)
    del(gonio)

    return header

def test_pilatus_scan(list_of_minicbf_files):

    minicbf_headers = [failover_cbf(minicbf_file) for minicbf_file in
                       list_of_minicbf_files]

    # assertions:
    #
    # 1: all of the images have the same oscillation width and exposure time
    # 2: all of the images are adjacent i.e. start(n + 1) = start(n) + width
    # 3: wavelength, beam_xy, distance, threshold are uniform
    # 4: exposure times and periods make sense

    # check Angle_increment

    Angle_increments = [header['phi_width'] for header in minicbf_headers]

    if (max(Angle_increments) - min(Angle_increments)) < 0.001:
        print '%40s OK' % 'Angle_increments'.ljust(40)
    else:
        print '%40s FAIL (%.3f to %.3f)' % ('Angle_increments'.ljust(40),
                                            min(Angle_increments),
                                            max(Angle_increments))

    # check Start_angle and Angle_increment

    Start_angles = [header['phi_start'] for header in minicbf_headers]

    Start_angles_ok = True

    for j in range(1, len(Start_angles)):
        if math.fabs(Start_angles[j] -
                     (Start_angles[j - 1] + Angle_increments[j - 1])) < 0.001:
            continue
        else:
            Start_angles_ok = False

    if Start_angles_ok:
        print '%40s OK' % 'Start_angles'.ljust(40)
    else:
        print '%40s FAIL' % 'Start_angles'.ljust(40)

    # check Detector_distance

    Detector_distances = [header['distance'] for header in minicbf_headers]

    if (max(Detector_distances) - min(Detector_distances)) < 0.001:
        print '%40s OK' % 'Detector_distances'.ljust(40)
    else:
        print '%40s FAIL (%.3f to %.3f)' % ('Detector_distances'.ljust(40),
                                            min(Detector_distances),
                                            max(Detector_distances))

    # check Wavelength

    Wavelengths = [header['wavelength'] for header in minicbf_headers]

    if (max(Wavelengths) - min(Wavelengths)) < 0.001:
        print '%40s OK' % 'Wavelengths'.ljust(40)
    else:
        print '%40s FAIL (%.3f to %.3f)' % ('Wavelengths'.ljust(40),
                                            min(Wavelengths),
                                            max(Wavelengths))

    # check Exposure_period

    Exposure_periods = [header['exposure_time'] for header in minicbf_headers]

    if (max(Exposure_periods) - min(Exposure_periods)) < 0.001:
        print '%40s OK' % 'Exposure_periods'.ljust(40)
    else:
        print '%40s FAIL (%.3f to %.3f)' % ('Exposure_periods'.ljust(40),
                                            min(Exposure_periods),
                                            max(Exposure_periods))

    # check Filter_transmission

    Filter_transmissions = [header['transmission'] for header in \
                            minicbf_headers]

    if (max(Filter_transmissions) - min(Filter_transmissions)) < 0.001:
        print '%40s OK' % 'Filter_transmissions'.ljust(40)
    else:
        print '%40s FAIL (%.3f to %.3f)' % ('Filter_transmissions'.ljust(40),
                                            min(Filter_transmissions),
                                            max(Filter_transmissions))


if __name__ == '__main__':

    test_pilatus_scan(sys.argv[1:])

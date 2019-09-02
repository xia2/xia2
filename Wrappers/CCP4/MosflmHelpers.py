#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import math


def detector_class_to_mosflm(detector_class):
    """Get the mosflm detector type from the detector class."""

    if "adsc" in detector_class:
        return "adsc"
    if "mar" in detector_class and "ccd" in detector_class:
        return "marccd"
    if "mar" in detector_class:
        return "mar"
    if "pilatus" in detector_class:
        return "pilatus"
    if "raxis" in detector_class:
        return "raxis4"
    if "saturn" in detector_class:
        return "saturn"

    raise RuntimeError('unknown detector class "%s"' % detector_class)


def _resolution_estimate(ordered_pair_list, cutoff):
    """Come up with a linearly interpolated estimate of resolution at
    cutoff cutoff from input data [(resolution, i_sigma)]."""

    x = []
    y = []

    for o in ordered_pair_list:
        x.append(o[0])
        y.append(o[1])

    if max(y) < cutoff:
        # there is no point where this exceeds the resolution
        # cutoff
        return -1.0

    # this means that there is a place where the resolution cutof
    # can be reached - get there by working backwards

    x.reverse()
    y.reverse()

    if y[0] >= cutoff:
        # this exceeds the resolution limit requested
        return x[0]

    j = 0
    while y[j] < cutoff:
        j += 1

    resolution = x[j] + (cutoff - y[j]) * (x[j - 1] - x[j]) / (y[j - 1] - y[j])

    return resolution


def _parse_mosflm_integration_output(integration_output_list):
    """Parse mosflm output from integration, passed in as a list of
    strings."""

    length = len(integration_output_list)

    per_image_stats = {0: {}}

    current_image = 0

    pixel_size = 0.0

    for i in range(length):
        record = integration_output_list[i]

        if "Pixel size of" in record:
            pixel_size = float(record.replace("mm", " ").split()[3])

        if "Pixel size in the" in record:
            pixel_size = float(record.replace("mm", " ").split()[-1])

        if "Processing Image" in record:
            current_image = int(record.replace("Image", "Image ").split()[2])

            if current_image not in per_image_stats:
                per_image_stats[current_image] = {"scale": 1.0}

        if "Integrating Image" in record:
            current_image = int(record.replace("Image", "Image ").split()[2])

        if "XCEN    YCEN  XTOFRA   XTOFD" in record:
            data = map(float, integration_output_list[i + 1].split())
            beam = (data[0], data[1])
            distance = data[3]

            per_image_stats[current_image]["beam"] = beam
            per_image_stats[current_image]["distance"] = distance

        if "Smoothed value for refined mosaic spread" in record:
            mosaic = float(record.split()[-1])
            per_image_stats[current_image]["mosaic"] = mosaic

        if "Final rms residual:" in record:
            if "*****" in record:
                per_image_stats[current_image]["rmsd_pixel"] = 99.999
                per_image_stats[current_image]["rmsd_phi"] = 0.0
            else:
                residual = float(record.replace("mm", " ").split()[3])
                # FIXME to do this need to be able to compute the
                # residual in pixels...
                rmsd = residual / pixel_size
                per_image_stats[current_image]["rmsd_pixel"] = rmsd
                per_image_stats[current_image]["rmsd_phi"] = 0.0
                if "Weighted residual" in record:
                    weighted_residual = float(record.split()[-1])
                    per_image_stats[current_image][
                        "weighted_residual"
                    ] = weighted_residual

        if "Real cell parameters" in record:
            cell = map(float, integration_output_list[i + 1].split())
            per_image_stats[current_image]["cell"] = cell

        if "Spots measured on this image" in record:
            spots = int(record.split()[0])
            # FIXME this is misnamed because it matches a name in the
            # XDS version of this parser.
            per_image_stats[current_image]["strong"] = spots

        if "are OVERLOADS" in record:
            overloads = int(record.replace(",", " ").split()[4])
            per_image_stats[current_image]["overloads"] = overloads

        if "Number of bad spots" in record:
            bad = int(record.replace("=", "").split()[-1])
            # FIXME also with the name...
            per_image_stats[current_image]["rejected"] = bad

        # look for BLANK images (i.e. those with no strong spots)

        if "Analysis of Intensities" in record:
            numbers = map(int, integration_output_list[i + 3].split()[1:])

            # define: if more than 95 % of the measurements are in the
            # lowest two bins, the image is BLANK? here record the fraction
            # of number in bins 0, 1, 2 (i.e. very negative, weak negative,
            # weak positive) divided by the total number.

            if sum(numbers):
                fraction_weak = float(sum(numbers[:3])) / float(sum(numbers))
            else:
                fraction_weak = 1.0

            per_image_stats[current_image]["fraction_weak"] = fraction_weak

        if (
            "Analysis as a function of resolution." in record
            and "Maximum Intensity" in integration_output_list[i - 3]
        ):
            # then get out the resolution information, spot counts and
            # so on, and generate some kind of resolution estimate
            # from this...
            #
            # (1) compute I/sigma vs. resolution curve
            # (2) analyse to find where I/sigma gets to 1.0
            #
            # report this as a sensible resolution limit for that image
            # these will be collated in some mysterious way to give an
            # appropriate resolution limit to integrate the data set to.

            resolution = map(float, integration_output_list[i + 1].split()[2:-1])
            number_full = map(
                int, integration_output_list[i + 3].replace("Number", "").split()[:-1]
            )
            sigma_full = map(
                float,
                integration_output_list[i + 6].replace("<I/sigma>", "").split()[:-1],
            )
            number_partial = map(
                int, integration_output_list[i + 8].replace("Number", "").split()[:-1]
            )
            sigma_partial = map(
                float,
                integration_output_list[i + 11].replace("<I/sigma>", "").split()[:-1],
            )

            resolution_list = []

            for j in range(len(resolution)):
                if number_full[j] + number_partial[j]:
                    sigma = (
                        number_full[j] * sigma_full[j]
                        + number_partial[j] * sigma_partial[j]
                    ) / (number_full[j] + number_partial[j])
                else:
                    sigma = 0.0
                resolution_list.append((resolution[j], sigma))

            # this was 1.0 - lowering for testing with broader resolution
            # limit tests...
            resolution = _resolution_estimate(resolution_list, 0.5)

            per_image_stats[current_image]["resolution"] = resolution

    per_image_stats.pop(0, None)

    return per_image_stats


def _print_integrate_lp(integrate_lp_stats):
    """Print the contents of the integrate.lp dictionary."""

    images = sorted(integrate_lp_stats.keys())

    for i in images:
        data = integrate_lp_stats[i]
        print(
            "%4d %5.3f %5d %5d %5d %4.2f %6.2f %5.2f"
            % (
                i,
                data["scale"],
                data["strong"],
                data["overloads"],
                data["rejected"],
                data.get("mosaic", 0.0),
                data["distance"],
                data["resolution"],
            )
        )


def decide_integration_resolution_limit(mosflm_integration_output):
    """Define the resolution limit for integration, where I/sigma
    for individual reflections is about 1.0."""

    stats = _parse_mosflm_integration_output(mosflm_integration_output)

    resolutions = []

    for k in stats.keys():
        resol = stats[k].get("resolution", -1.0)
        if resol > 0.0:
            resolutions.append(resol)

    return min(resolutions)


def _parse_mosflm_index_output(index_output_list):
    """Parse the output text from autoindexing to build up a picture
    of the solutions."""

    collect_solutions = False

    solutions = {}

    correct_number = 0

    for i in range(len(index_output_list)):
        output = index_output_list[i]

        if "No PENALTY SDCELL" in output:
            collect_solutions = not collect_solutions

        if collect_solutions:
            try:
                number = int(output.split()[0])
                solutions[number] = output[:-1]
            except Exception:
                pass

        # this will not be in the file if Mosflm doesn't think you have
        # the right answer (and often it doesn't have a clue...)
        # FIXME this sometimes has "transformed from" following...
        if "Suggested Solution" in output:
            correct_number = int(output.split()[2])

        # this will at least be there! - unless the input solution has
        # been set...
        if "Mosflm has chosen solution" in output:
            correct_number = int(output.split()[4])

        if "Solution" in output and "has been chosen from the list" in output:
            correct_number = int(output.split()[1])

    if correct_number == 0:
        # cannot find what Mosflm considers the correct answer
        raise RuntimeError("cannot determine correct answer")

    keys = sorted(solutions.keys())

    solutions_by_lattice = {}

    # FIXME 25/OCT/06 also need to take the penalty into account slightly
    # because this goes very wrong for TS02/PEAK - add this to the rms
    # times a small magic number (0.5% at the moment)

    acceptable_rms = 0.0

    for k in keys:
        if not "unrefined" in solutions[k]:
            list = solutions[k].split()
            penalty = float(list[1])
            number = int(list[0])
            rms = float(list[2]) + 0.005 * penalty
            latt = list[4]
            frc = float(list[3])
            cell = map(float, list[5:11])

            # decide what we consider a reasonable rms deviation
            if number == correct_number:
                acceptable_rms = 1.1 * rms

            if latt in solutions_by_lattice:
                if solutions_by_lattice[latt]["rms"] <= rms:
                    continue

            solutions_by_lattice[latt] = {
                "rms": rms,
                "cell": cell,
                "frc": frc,
                "number": number,
            }

    # find what we think is an acceptable solution... this now moved above
    # acceptable_rms = 0.0

    # for k in solutions_by_lattice.keys():
    # if solutions_by_lattice[k]['number'] == correct_number:
    # acceptable_rms = 1.1 * solutions_by_lattice[k]['rms']

    # this should raise a HorribleIndexingException or something

    if acceptable_rms == 0.0:
        raise RuntimeError("something horribly bad has happened in indexing")

    # then print those which should be ok...

    results = {}

    lattice_to_spacegroup = {
        "aP": 1,
        "mP": 3,
        "mC": 5,
        "oP": 16,
        "oC": 20,
        "oF": 22,
        "oI": 23,
        "tP": 75,
        "tI": 79,
        "hP": 143,
        "hR": 146,
        "cP": 195,
        "cF": 196,
        "cI": 197,
    }

    for k in solutions_by_lattice.keys():
        if solutions_by_lattice[k]["rms"] < acceptable_rms:
            cell = solutions_by_lattice[k]["cell"]

            # record this only if it is a standard setting!
            if k in lattice_to_spacegroup.keys():
                results[k] = {"cell": cell, "goodness": solutions_by_lattice[k]["rms"]}

    return results


def _parse_mosflm_index_output_all(index_output_list):
    """Parse the output text from autoindexing to build up complete list
    of the solutions."""

    collect_solutions = False

    solutions = {}

    for i in range(len(index_output_list)):
        output = index_output_list[i]

        if "No PENALTY SDCELL" in output:
            collect_solutions = not collect_solutions

        if collect_solutions:
            try:
                number = int(output.split()[0])
                solutions[number] = output[:-1]
            except Exception:
                pass

    keys = sorted(solutions.keys())

    results = {}

    for k in keys:
        if not "unrefined" in solutions[k]:
            list = solutions[k].split()
            penalty = float(list[1])
            number = int(list[0])
            rms = float(list[2]) + 0.005 * penalty
            latt = list[4]
            frc = float(list[3])
            cell = map(float, list[5:11])
            results[k] = {
                "rms": rms,
                "cell": cell,
                "frc": frc,
                "number": number,
                "lattice": latt,
                "penalty": penalty,
            }

    return results


def _get_indexing_solution_number(index_output_list, target_cell, target_lattice):
    """Given a list of autoindexing solutions, return the solution
    number for the provided unit cell and lattice."""

    # get the indexing results from the standard output
    all_autoindex_results = _parse_mosflm_index_output_all(index_output_list)

    # then select the one closest to the target cell - recording the
    # solution number

    best = 0
    difference = 60.0

    for k in all_autoindex_results.keys():
        if all_autoindex_results[k]["lattice"] == target_lattice:
            cell = all_autoindex_results[k]["cell"]
            diff = 0.0
            for j in range(6):
                diff += math.fabs(cell[j] - target_cell[j])
            if diff < difference:
                best = k
                difference = diff

    # return the solution number

    return best


def standard_mask(detector):
    """Return a list of standard mask commands for the given detector."""
    assert len(detector) == 1
    size_fast, size_slow = detector[0].get_pixel_size()

    exclude = []
    for f0, s0, f1, s1 in detector[0].get_mask():
        exclude.append(
            "LIMITS EXCLUDE %s %s %s %s"
            % (size_fast * f0, size_fast * f1, size_slow * s0, size_slow * s1)
        )

    return exclude

    ## ADSC Q210 2x2 binned

    # if 'adsc q210' in detector:
    # return ['LIMITS EXCLUDE 104.6 0.1 105.1 209.0',
    #'LIMITS EXCLUDE 0.1 104.6 209.0 105.1']

    # if 'adsc q315' in detector:
    # return ['LIMITS EXCLUDE 104.8 0.1 105.3 314.6',
    #'LIMITS EXCLUDE 209.8 0.1 210.4 314.6',
    #'LIMITS EXCLUDE 0.1 104.8 314.6 105.3',
    #'LIMITS EXCLUDE 0.1 209.8 314.6 210.4']

    # if 'pilatus 6M' in detector:
    # if True:
    # return []

    # return ['LIMITS EXCLUDE 83.9 85.0 0.2 434.6',
    #'LIMITS EXCLUDE 168.9 169.9 0.2 434.6',
    #'LIMITS EXCLUDE 253.9 254.9 0.2 434.6',
    #'LIMITS EXCLUDE 338.8 339.9 0.2 434.6',
    #'LIMITS EXCLUDE 0.2 423.6 33.7 36.5',
    #'LIMITS EXCLUDE 0.2 423.6 70.2 72.9',
    #'LIMITS EXCLUDE 0.2 423.6 106.6 109.4',
    #'LIMITS EXCLUDE 0.2 423.6 143.1 145.9',
    #'LIMITS EXCLUDE 0.2 423.6 179.6 182.3',
    #'LIMITS EXCLUDE 0.2 423.6 216.0 218.8',
    #'LIMITS EXCLUDE 0.2 423.6 252.5 255.2',
    #'LIMITS EXCLUDE 0.2 423.6 289.0 291.7',
    #'LIMITS EXCLUDE 0.2 423.6 325.4 328.2',
    #'LIMITS EXCLUDE 0.2 423.6 361.9 364.6',
    #'LIMITS EXCLUDE 0.2 423.6 398.4 401.1']

    # if 'pilatus 2M' in detector:
    # if True:
    # return []
    # return ['LIMITS EXCLUDE 83.9 85.0 0.2 288.8',
    #'LIMITS EXCLUDE 168.9 169.9 0.2 288.8',
    #'LIMITS EXCLUDE 0.2 253.7 33.7 36.5',
    #'LIMITS EXCLUDE 0.2 253.7 70.2 72.9',
    #'LIMITS EXCLUDE 0.2 253.7 106.6 109.4',
    #'LIMITS EXCLUDE 0.2 253.7 143.1 145.9',
    #'LIMITS EXCLUDE 0.2 253.7 179.6 182.3',
    #'LIMITS EXCLUDE 0.2 253.7 216.0 218.8',
    #'LIMITS EXCLUDE 0.2 253.7 252.5 255.2']

    ## unknown detector

    # return []


def _parse_summary_file(filename):
    """Parse the results of postrefinement &c. from a summary file to a
    dictionary keyed by the image number."""

    loggraph = {}

    output = open(filename).read()

    tokens = output.split("$$")

    assert len(tokens) == 9

    result = {}

    refined_columns = tokens[1].split()
    refined_values = map(float, tokens[3].replace("******", " 0.0 ").split())

    ncol = len(refined_columns)

    keys = [column.lower() for column in refined_columns]

    for j in range(len(refined_values) // ncol):
        image = int(round(refined_values[j * ncol]))

        d = {}

        for k in range(1, ncol):
            d[keys[k]] = refined_values[j * ncol + k]

        result[image] = d

    postref_columns = tokens[5].split()
    postref_values = map(float, tokens[7].replace("******", " 0.0 ").split())

    ncol = len(postref_columns)

    keys = [column.lower() for column in postref_columns]

    for j in range(len(postref_values) // ncol):
        image = int(round(postref_values[j * ncol]))

        d = {}

        for k in range(1, ncol):
            d[keys[k]] = postref_values[j * ncol + k]

        result[image].update(d)

    return result

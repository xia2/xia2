def get_correlation_coefficients_and_group(xscale_lp):
    """Get and group correlation coefficients between data sets from the
    xscale log file. Also access the reflection file names to show which ones
    should be scaled together."""

    ccs = {}

    file_names = {}

    xmax = 0

    with open(xscale_lp) as fh:
        records = fh.readlines()

    # first scan through to get the file names...

    for j, record in enumerate(records):
        if "NUMBER OF UNIQUE REFLECTIONS" in record:

            k = j + 5

            while len(records[k].split()) == 5:
                values = records[k].split()
                file_names[int(values[0])] = values[-1]

                k += 1

            break

    if not file_names:
        for j, record in enumerate(records):
            if "SET# INTENSITY  ACCEPTED REJECTED" in record:

                k = j + 1

                while len(records[k].split()) == 5:
                    values = records[k].split()
                    file_names[int(values[0])] = values[-1]

                    k += 1

                break

    for j, record in enumerate(records):

        if "CORRELATIONS BETWEEN INPUT DATA SETS" in record:

            k = j + 5

            while len(records[k].split()) == 6:
                values = records[k].split()

                _i = int(values[0])
                _j = int(values[1])
                _n = int(values[2])
                _cc = float(values[3])

                ccs[(_i, _j)] = (_n, _cc)
                ccs[(_j, _i)] = (_n, _cc)

                xmax = _i + 1

                k += 1

            break

    used = []
    groups = {}

    for j in range(xmax):
        test_file = file_names[j + 1]
        if test_file in used:
            continue
        used.append(test_file)
        groups[test_file] = [test_file]
        for k in range(j + 1, xmax):
            if ccs[(j + 1, k + 1)][1] > 0.9:
                groups[test_file].append(file_names[k + 1])
                used.append(file_names[k + 1])

    return groups

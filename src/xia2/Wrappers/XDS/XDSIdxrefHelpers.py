from xia2.Experts.LatticeExpert import ApplyLattice


def _parse_idxref_lp_distance_etc(lp_file_lines):
    """Parse the LP file for refined distance, beam centre and so on..."""

    beam = None
    distance = None

    for line in lp_file_lines:
        if "DETECTOR COORDINATES" in line and "DIRECT BEAM" in line:
            beam = tuple(map(float, line.split()[-2:]))
        if "CRYSTAL TO DETECTOR" in line:
            distance = float(line.split()[-1])
            if distance < 0:
                distance *= -1

    return beam, distance


def _parse_idxref_index_origin(lp_file_lines):
    """Parse the LP file for the possible index origin etc."""

    origins = {}

    i = 0
    while i < len(lp_file_lines):
        line = lp_file_lines[i]
        i += 1
        if "INDEX_" in line and "QUALITY" in line and "DELTA" in line:
            while "SELECTED" not in line:
                line = lp_file_lines[i]
                i += 1
                try:
                    hkl = tuple(map(int, line.split()[:3]))
                    quality, delta, xd, yd = tuple(map(float, line.split()[3:7]))
                    origins[hkl] = quality, delta, xd, yd
                except Exception:
                    pass

            return origins

    raise RuntimeError("should never reach this point")


def _parse_idxref_lp(lp_file_lines):
    """Parse the list of lines from idxref.lp."""

    lattice_character_info = {}

    i = 0

    mosaic = 0.0

    while i < len(lp_file_lines):
        line = lp_file_lines[i]
        i += 1

        # get the mosaic information

        if "CRYSTAL MOSAICITY" in line:
            mosaic = float(line.split()[-1])

        # get the lattice character information - coding around the
        # non-standard possibility of mI, by simply ignoring it!
        # bug # 2355

        if "CHARACTER  LATTICE     OF FIT      a      b      c" in line:
            # example line (note potential lack of white space between b and c cell parameters):
            #     9        hR        999.0    3966.3 5324.610528.6  85.6  64.6 132.0
            j = i + 1
            while lp_file_lines[j].strip() != "":
                l = lp_file_lines[j].replace("*", " ")
                character = int(l[:12].strip())
                lattice = l[12:23].strip()
                fit = float(l[23:32].strip())
                cell = tuple(
                    float(c)
                    for c in (
                        l[32:39],
                        l[39:46],
                        l[46:53],
                        l[53:59],
                        l[59:65],
                        l[65:71],
                    )
                )

                # FIXME need to do something properly about this...
                # bug # 2355

                if lattice == "mI":
                    j += 1
                    continue

                # reindex_card = tuple(map(int, record[9:]))
                reindex_card = ()  # XXX need example where this is present in the IDXREF.LP
                constrained_cell = ApplyLattice(lattice, cell)[0]

                lattice_character_info[character] = {
                    "lattice": lattice,
                    "fit": fit,
                    "cell": constrained_cell,
                    "mosaic": mosaic,
                    "reidx": reindex_card,
                }

                j += 1

    return lattice_character_info


def _parse_idxref_lp_subtree(lp_file_lines):

    subtrees = {}

    i = 0

    while i < len(lp_file_lines):
        line = lp_file_lines[i]
        i += 1

        if line.split() == ["SUBTREE", "POPULATION"]:
            j = i + 1
            line = lp_file_lines[j]
            while line.strip():
                subtree, population = tuple(map(int, line.split()))
                subtrees[subtree] = population
                j += 1
                line = lp_file_lines[j]

    return subtrees


def _parse_idxref_lp_quality(lp_file_lines):
    fraction = None
    rmsd = None
    rmsphi = None

    for record in lp_file_lines:
        if "OUT OF" in record and "SPOTS INDEXED" in record:
            fraction = float(record.split()[0]) / float(record.split()[3])
        if "STANDARD DEVIATION OF SPOT    POSITION" in record:
            rmsd = float(record.split()[-1])
        if "STANDARD DEVIATION OF SPINDLE POSITION" in record:
            rmsphi = float(record.split()[-1])

    return fraction, rmsd, rmsphi

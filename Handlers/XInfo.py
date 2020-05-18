# xia2 information / input file reader


from collections import OrderedDict


class XInfo:
    """A class to represent all of the input to the xia2dpa system, with
    enough information to allow structure solution, as parsed from a
    .xinfo file, an example of which is in the source code."""

    def __init__(self, xinfo_file, sweep_ids=None, sweep_ranges=None):
        """Initialise myself from an input .xinfo file."""

        # first initialise all of the data structures which will hold the
        # information...

        self._project = None
        self._crystals = OrderedDict()

        if sweep_ids is not None:
            sweep_ids = [s.lower() for s in sweep_ids]
        if sweep_ranges is not None:
            assert sweep_ids is not None
            assert len(sweep_ids) == len(sweep_ranges)
        self._sweep_ids = sweep_ids
        self._sweep_ranges = sweep_ranges

        # read the contents of the xinfo file

        self._parse_project(xinfo_file)

        self._validate()

    def get_output(self):
        """Generate a string representation of the project."""

        text = "Project %s\n" % self._project
        for crystal in self._crystals:
            text += "Crystal %s\n" % crystal
            text += "%s\n" % self._crystals[crystal].get_output()

        # remove a trailing newline...

        return text[:-1]

    def get_project(self):
        return self._project

    def get_crystals(self):
        return self._crystals

    def _validate(self):
        """Validate the structure of this object, ensuring that
        everything looks right... raise exception if I find something
        wrong."""

        return True

    def _parse_project(self, xinfo_file):
        """Parse & validate the contents of the .xinfo file. This parses the
        project element (i.e. the whole thing..)"""

        project_records = []

        with open(xinfo_file) as fh:
            for r in fh.readlines():
                record = r.strip()
                if record and record[0] not in ("!", "#"):
                    # then it may contain something useful...
                    project_records.append(record)

        # so now we have loaded the whole file into memory stripping
        # out the crud... let's look for something useful

        for i in range(len(project_records)):
            record = project_records[i]
            if "BEGIN PROJECT" in record:
                pname = record.replace("BEGIN PROJECT", "").strip()
                if len(pname.split()) != 1:
                    raise RuntimeError("project name contains white space: %s" % pname)
                self._project = pname
            if "END PROJECT" in record:
                if not self._project == record.replace("END PROJECT", "").strip():
                    raise RuntimeError("error parsing END PROJECT record")

            # next look for crystals
            if "BEGIN CRYSTAL " in record:
                crystal_records = [record]
                while True:
                    i += 1
                    record = project_records[i]
                    crystal_records.append(record)
                    if "END CRYSTAL " in record:
                        break

                self._parse_crystal(crystal_records)

            # that's everything, because parse_crystal handles
            # the rest...

    def _parse_crystal(self, crystal_records):
        """Parse the interesting information out of the crystal
        description."""

        crystal = ""

        for i in range(len(crystal_records)):
            record = crystal_records[i]
            if "BEGIN CRYSTAL " in record:

                # we should only ever have one of these records in
                # a call to this method

                if crystal != "":
                    raise RuntimeError("error in BEGIN CRYSTAL record")

                crystal = record.replace("BEGIN CRYSTAL ", "").strip()
                if len(crystal.split()) != 1:
                    raise RuntimeError(
                        "crystal name contains white space: %s" % crystal
                    )
                if crystal in self._crystals:
                    raise RuntimeError("crystal %s already exists" % crystal)

                # cardinality:
                #
                # sequence - exactly one, a long string
                # wavelengths - a dictionary of data structures keyed by the
                #               wavelength id
                # sweeps - a dictionary of data structures keyed by the
                #          sweep id
                # ha_info - exactly one dictionary containing the heavy atom
                #           information

                self._crystals[crystal] = {
                    "sequence": "",
                    "wavelengths": OrderedDict(),
                    "samples": OrderedDict(),
                    "sweeps": OrderedDict(),
                    "ha_info": OrderedDict(),
                    "crystal_data": OrderedDict(),
                }

            # next look for interesting stuff in the data structure...
            # starting with the sequence

            if "BEGIN AA_SEQUENCE" in record:
                sequence = ""
                i += 1
                record = crystal_records[i]
                while record != "END AA_SEQUENCE":
                    if "#" not in record or "!" in record:
                        sequence += record.strip()

                    i += 1
                    record = crystal_records[i]

                if self._crystals[crystal]["sequence"] != "":
                    raise RuntimeError("error two SEQUENCE records found")

                self._crystals[crystal]["sequence"] = sequence

            # look for heavy atom information

            if "BEGIN HA_INFO" in record:
                i += 1
                record = crystal_records[i]
                while record != "END HA_INFO":
                    key = record.split()[0].lower()
                    value = record.split()[1]
                    # things which are numbers are integers...
                    if "number" in key:
                        value = int(value)
                    self._crystals[crystal]["ha_info"][key] = value
                    i += 1
                    record = crystal_records[i]

            if "BEGIN SAMPLE" in record:
                sample = record.replace("BEGIN SAMPLE ", "").strip()
                i += 1
                record = crystal_records[i]
                while "END SAMPLE" not in record:
                    i += 1
                    record = crystal_records[i]
                self._crystals[crystal]["samples"][sample] = {}

            # look for wavelength definitions
            # FIXME need to check that there are not two wavelength
            # definitions with the same numerical value for the wavelength -
            # unless this is some way of handling RIP? maybe a NOFIXME.

            # look for data blocks

            if "BEGIN CRYSTAL_DATA" in record:
                i += 1
                record = crystal_records[i]
                while "END CRYSTAL_DATA" not in record:
                    key = record.split()[0].lower()
                    value = record.replace(record.split()[0], "").strip()
                    self._crystals[crystal]["crystal_data"][key] = value
                    i += 1
                    record = crystal_records[i]

            if "BEGIN WAVELENGTH " in record:
                wavelength = record.replace("BEGIN WAVELENGTH ", "").strip()
                if len(wavelength.split()) != 1:
                    raise RuntimeError(
                        "wavelength name contains white space: %s" % wavelength
                    )
                # check that this is a new wavelength definition
                if wavelength in self._crystals[crystal]["wavelengths"]:
                    raise RuntimeError(
                        "wavelength %s already exists for crystal %s"
                        % (wavelength, crystal)
                    )

                self._crystals[crystal]["wavelengths"][wavelength] = {}
                i += 1
                record = crystal_records[i]

                # populate this with interesting things
                while "END WAVELENGTH" not in record:

                    # deal with a nested WAVELENGTH_STATISTICS block

                    if "BEGIN WAVELENGTH_STATISTICS" in record:
                        self._crystals[crystal]["wavelengths"][wavelength][
                            "statistics"
                        ] = {}
                        i += 1
                        record = crystal_records[i]
                        while "END WAVELENGTH_STATISTICS" not in record:
                            key, value = tuple(record.split())
                            self._crystals[crystal]["wavelengths"][wavelength][
                                "statistics"
                            ][key.lower()] = float(value)
                            i += 1
                            record = crystal_records[i]

                    # else deal with the usual tokens

                    key = record.split()[0].lower()

                    if key == "resolution":

                        lst = record.split()

                        if len(lst) < 2 or len(lst) > 3:
                            raise RuntimeError("resolution dmin [dmax]")

                        if len(lst) == 2:
                            dmin = float(lst[1])

                            self._crystals[crystal]["wavelengths"][wavelength][
                                "dmin"
                            ] = dmin

                        else:
                            dmin = min(float(x) for x in lst[1:])
                            dmax = max(float(x) for x in lst[1:])

                            self._crystals[crystal]["wavelengths"][wavelength][
                                "dmin"
                            ] = dmin

                            self._crystals[crystal]["wavelengths"][wavelength][
                                "dmax"
                            ] = dmax

                        i += 1
                        record = crystal_records[i]
                        continue

                    if len(record.split()) == 1:
                        raise RuntimeError(
                            "missing value for token %s" % record.split()[0]
                        )

                    try:
                        value = float(record.split()[1])
                    except ValueError:
                        value = record.replace(record.split()[0], "").strip()

                    self._crystals[crystal]["wavelengths"][wavelength][key] = value
                    i += 1
                    record = crystal_records[i]

            # next look for sweeps, checking that the wavelength
            # definitions match up...

            if "BEGIN SWEEP" in record:
                sweep = record.replace("BEGIN SWEEP", "").strip()

                if self._sweep_ids is not None and sweep.lower() not in self._sweep_ids:
                    continue

                elif self._sweep_ranges is not None:
                    start_end = self._sweep_ranges[self._sweep_ids.index(sweep.lower())]
                else:
                    start_end = None

                if sweep in self._crystals[crystal]["sweeps"]:
                    raise RuntimeError(
                        f"sweep {sweep} already exists for crystal {crystal}"
                    )

                self._crystals[crystal]["sweeps"][sweep] = {}
                self._crystals[crystal]["sweeps"][sweep]["excluded_regions"] = []

                if start_end is not None:
                    self._crystals[crystal]["sweeps"][sweep]["start_end"] = start_end

                # in here I expect to find IMAGE, DIRECTORY, WAVELENGTH
                # and optionally BEAM

                # FIXME 30/OCT/06 this may not be the case, for instance
                # if an INTEGRATED_REFLECTION_FILE record is in there...
                # c/f XProject.py, XSweep.py

                i += 1
                record = crystal_records[i]

                # populate this with interesting things
                while "END SWEEP" not in record:
                    # allow for WAVELENGTH_ID (bug # 2358)
                    if "WAVELENGTH_ID" == record.split()[0]:
                        record = record.replace("WAVELENGTH_ID", "WAVELENGTH")

                    if "WAVELENGTH" == record.split()[0]:
                        wavelength = record.replace("WAVELENGTH", "").strip()
                        if wavelength not in self._crystals[crystal]["wavelengths"]:
                            raise RuntimeError(
                                "wavelength %s unknown for crystal %s"
                                % (wavelength, crystal)
                            )
                        self._crystals[crystal]["sweeps"][sweep][
                            "wavelength"
                        ] = wavelength

                    elif "SAMPLE" == record.split()[0]:
                        sample = record.replace("SAMPLE ", "").strip()
                        if sample not in list(
                            self._crystals[crystal]["samples"].keys()
                        ):
                            raise RuntimeError(
                                f"sample {sample} unknown for crystal {crystal}"
                            )
                        self._crystals[crystal]["sweeps"][sweep]["sample"] = sample

                    elif "BEAM" == record.split()[0]:
                        beam = [float(x) for x in record.split()[1:]]
                        self._crystals[crystal]["sweeps"][sweep]["beam"] = beam

                    elif "DISTANCE" == record.split()[0]:
                        distance = float(record.split()[1])
                        self._crystals[crystal]["sweeps"][sweep]["distance"] = distance

                    elif "EPOCH" == record.split()[0]:
                        epoch = int(record.split()[1])
                        self._crystals[crystal]["sweeps"][sweep]["epoch"] = epoch

                    elif "REVERSEPHI" == record.split()[0]:
                        self._crystals[crystal]["sweeps"][sweep]["reversephi"] = True

                    elif "START_END" == record.split()[0]:
                        if "start_end" not in self._crystals[crystal]["sweeps"][sweep]:
                            start_end = [int(x) for x in record.split()[1:]]
                            if len(start_end) != 2:
                                raise RuntimeError(
                                    'START_END requires two parameters (start and end), not "%s"'
                                    % record
                                )
                            self._crystals[crystal]["sweeps"][sweep][
                                "start_end"
                            ] = start_end

                    elif "EXCLUDE" == record.split()[0]:
                        if record.split()[1].upper() == "ICE":
                            self._crystals[crystal]["sweeps"][sweep]["ice"] = True
                        else:
                            excluded_region = [float(x) for x in record.split()[1:]]
                            if len(excluded_region) != 2:
                                raise RuntimeError(
                                    'EXCLUDE upper lower, not "%s". \
                       eg. EXCLUDE 2.28 2.22'
                                    % record
                                )
                            if excluded_region[0] <= excluded_region[1]:
                                raise RuntimeError(
                                    'EXCLUDE upper lower, where upper \
                       must be greater than lower (not "%s").\n\
                       eg. EXCLUDE 2.28 2.22'
                                    % record
                                )
                            self._crystals[crystal]["sweeps"][sweep][
                                "excluded_regions"
                            ].append(excluded_region)

                    else:
                        key = record.split()[0]
                        value = record.replace(key, "").strip()
                        self._crystals[crystal]["sweeps"][sweep][key] = value

                    i += 1
                    record = crystal_records[i]

            # now look for one-record things

            if "SCALED_MERGED_REFLECTION_FILE" in record:
                self._crystals[crystal][
                    "scaled_merged_reflection_file"
                ] = record.replace("SCALED_MERGED_REFLECTION_FILE", "").strip()

            if "REFERENCE_REFLECTION_FILE" in record:
                self._crystals[crystal]["reference_reflection_file"] = record.replace(
                    "REFERENCE_REFLECTION_FILE", ""
                ).strip()

            if "FREER_FILE" in record:

                # free file also needs to be used for indexing reference to
                # make any sense at all...

                self._crystals[crystal]["freer_file"] = record.replace(
                    "FREER_FILE", ""
                ).strip()
                self._crystals[crystal]["reference_reflection_file"] = record.replace(
                    "FREER_FILE", ""
                ).strip()

            # user assigned spacegroup and cell constants
            if "USER_SPACEGROUP" in record:
                self._crystals[crystal]["user_spacegroup"] = record.replace(
                    "USER_SPACEGROUP", ""
                ).strip()

            if "USER_CELL" in record:
                self._crystals[crystal]["user_cell"] = tuple(
                    float(x) for x in record.split()[1:]
                )

import logging
import math
import os
import xml.dom.minidom

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

# this was rather complicated - now simpler!
from xia2.lib.SymmetryLib import (
    clean_reindex_operator,
    lauegroup_to_lattice,
    spacegroup_name_xHM_to_old,
)

logger = logging.getLogger("xia2.Wrappers.CCP4.Pointless")


def mend_pointless_xml(xml_file):
    """Repair XML document"""

    with open(xml_file) as fh:
        text = fh.read().split("\n")
    result = []
    for record in text:
        if "CenProb" not in record:
            result.append(record)
            continue
        if "/CenProb" in record:
            result.append(record)
            continue
        tokens = record.split("CenProb")
        assert len(tokens) == 3
        result.append("%sCenProb%s/CenProb%s" % tuple(tokens))
    with open(xml_file, "w") as fh:
        fh.write("\n".join(result))


def Pointless(DriverType=None):
    """A factory for PointlessWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class PointlessWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Pointless, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "pointless"))

            self._input_laue_group = None

            self._pointgroup = None
            self._spacegroup = None
            self._reindex_matrix = None
            self._reindex_operator = None
            self._spacegroup_reindex_matrix = None
            self._spacegroup_reindex_operator = None
            self._confidence = 0.0
            self._hklref = None
            self._xdsin = None
            self._probably_twinned = False
            self._allow_out_of_sequence_files = False

            # pname, xname, dname stuff for when we are copying reflections
            self._pname = None
            self._xname = None
            self._dname = None

            # space to store all possible solutions, to allow discussion of
            # the correct lattice with the indexer... this should be a
            # list containing e.g. 'tP'
            self._possible_lattices = []

            self._lattice_to_laue = {}

            # all "likely" spacegroups...
            self._likely_spacegroups = []

            # and unit cell information
            self._cell_info = {}
            self._cell = None

            # and scale factors to use in conversion
            self._scale_factor = 1.0

        def set_scale_factor(self, scale_factor):
            self._scale_factor = scale_factor

        def set_hklref(self, hklref):
            self._hklref = hklref

        def set_allow_out_of_sequence_files(self, allow=True):
            self._allow_out_of_sequence_files = allow

        def set_project_info(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname

        def set_xdsin(self, xdsin):
            self._xdsin = xdsin

        def get_xdsin(self):
            return self._xdsin

        def set_correct_lattice(self, lattice):
            """In a rerunning situation, set the correct lattice, which will
            assert a correct lauegroup based on the previous run of the
            program..."""

            if self._lattice_to_laue == {}:
                raise RuntimeError("no lattice to lauegroup mapping")

            if lattice not in self._lattice_to_laue:
                raise RuntimeError("lattice %s not possible" % lattice)

            self._input_laue_group = self._lattice_to_laue[lattice]

        def sum_mtz(self, summedlist):
            """Sum partials in an MTZ file from Mosflm to a text file."""

            self.add_command_line("-c")
            self.check_hklin()

            self.start()
            self.input("output summedlist %s" % summedlist)
            self.close_wait()

            # get out the unit cell - we will need this...

            output = self.get_all_output()

            cell = None

            for j, line in enumerate(output):
                if "Space group from HKLIN file" in line:
                    cell = tuple(map(float, output[j + 1].split()[1:]))

            return cell

        def limit_batches(self, first, last):
            """Replacement for rebatch, removing batches."""

            self.check_hklin()
            self.check_hklout()

            self.add_command_line("-c")

            self.start()
            if first > 1:
                self.input("exclude batch %d to %d" % (0, first - 1))
            self.input("exclude batch %d to %d" % (last + 1, 9999999))
            self.close_wait()

        def xds_to_mtz(self):
            """Use pointless to convert XDS file to MTZ."""

            if not self._xdsin:
                raise RuntimeError("XDSIN not set")

            self.check_hklout()

            # -c for copy - just convert the file to MTZ multirecord
            self.add_command_line("-c")

            self.start()

            if self._pname and self._xname and self._dname:
                self.input(
                    "name project %s crystal %s dataset %s"
                    % (self._pname, self._xname, self._dname)
                )

            self.input("xdsin %s" % self._xdsin)

            if self._scale_factor:
                logger.debug("Scaling intensities by factor %e" % self._scale_factor)

                self.input("multiply %e" % self._scale_factor)

            self.close_wait()

            # FIXME need to check the status and so on here

            if self._xdsin:
                from xia2.Wrappers.XDS import XDS

                XDS.add_xds_version_to_mtz_history(self.get_hklout())

        def decide_pointgroup(self, ignore_errors=False, batches=None):
            """Decide on the correct pointgroup for hklin."""

            if not self._xdsin:
                self.check_hklin()
                self.set_task(
                    "Computing the correct pointgroup for %s" % self.get_hklin()
                )

            else:
                logger.debug("Pointless using XDS input file %s" % self._xdsin)

                self.set_task(
                    "Computing the correct pointgroup for %s" % self.get_xdsin()
                )

            # FIXME this should probably be a standard CCP4 keyword

            if self._xdsin:
                self.add_command_line("xdsin")
                self.add_command_line(self._xdsin)

            self.add_command_line("xmlout")
            self.add_command_line("%d_pointless.xml" % self.get_xpid())

            if self._hklref:
                self.add_command_line("hklref")
                self.add_command_line(self._hklref)

            self.start()

            if self._allow_out_of_sequence_files:
                self.input("allow outofsequencefiles")

            # https://github.com/xia2/xia2/issues/125 pass in run limits for this
            # HKLIN file - prevents automated RUN determination from causing errors
            if batches:
                self.input("run 1 batch %d to %d" % tuple(batches))

            self.input("systematicabsences off")
            self.input("setting symmetry-based")
            if self._hklref:
                dev = PhilIndex.params.xia2.settings.developmental
                if dev.pointless_tolerance > 0.0:
                    self.input("tolerance %f" % dev.pointless_tolerance)

            # may expect more %age variation for small molecule data
            if PhilIndex.params.xia2.settings.small_molecule:
                if self._hklref:
                    self.input("tolerance 5.0")
            if PhilIndex.params.xia2.settings.symmetry.chirality is not None:
                self.input(
                    "chirality %s" % PhilIndex.params.xia2.settings.symmetry.chirality
                )

            if self._input_laue_group:
                self.input("lauegroup %s" % self._input_laue_group)

            self.close_wait()

            # check for errors
            self.check_for_errors()

            # check for fatal errors
            output = self.get_all_output()

            fatal_error = False

            for j, record in enumerate(output):
                if "FATAL ERROR message:" in record:
                    if ignore_errors:
                        fatal_error = True
                    else:
                        raise RuntimeError(
                            "Pointless error: %s" % output[j + 1].strip()
                        )
                if (
                    "Resolution range of Reference data and observed data do not"
                    in record
                    and ignore_errors
                ):
                    fatal_error = True
                if "All reflection pairs rejected" in record and ignore_errors:
                    fatal_error = True
                if (
                    "Reference data and observed data do not overlap" in record
                    and ignore_errors
                ):
                    fatal_error = True

            hklin_spacegroup = ""

            # split loop - first seek hklin symmetry then later look for everything
            # else

            for o in self.get_all_output():
                if "Spacegroup from HKLIN file" in o:
                    hklin_spacegroup = spacegroup_name_xHM_to_old(
                        o.replace("Spacegroup from HKLIN file :", "").strip()
                    )
                if "Space group from HKLREF file" in o:
                    hklref_spacegroup = spacegroup_name_xHM_to_old(
                        o.replace("Space group from HKLREF file :", "").strip()
                    )

            # https://github.com/xia2/xia2/issues/115
            if fatal_error:
                assert hklref_spacegroup

                self._pointgroup = hklref_spacegroup
                self._confidence = 1.0
                self._totalprob = 1.0
                self._reindex_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
                self._reindex_operator = "h,k,l"
                return "ok"

            for o in self.get_all_output():
                if "No alternative indexing possible" in o:
                    # then the XML file will be broken - no worries...

                    self._pointgroup = hklin_spacegroup
                    self._confidence = 1.0
                    self._totalprob = 1.0
                    self._reindex_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
                    self._reindex_operator = "h,k,l"

                    return "ok"

                if "**** Incompatible symmetries ****" in o:
                    raise RuntimeError(
                        "reindexing against a reference with different symmetry"
                    )

                if "***** Stopping because cell discrepancy between files" in o:
                    raise RuntimeError("incompatible unit cells between data sets")

                if "L-test suggests that the data may be twinned" in o:
                    self._probably_twinned = True

            # parse the XML file for the information I need...

            xml_file = os.path.join(
                self.get_working_directory(), "%d_pointless.xml" % self.get_xpid()
            )
            mend_pointless_xml(xml_file)
            # catch the case sometimes on ppc mac where pointless adds
            # an extra .xml on the end...

            if not os.path.exists(xml_file) and os.path.exists("%s.xml" % xml_file):
                xml_file = "%s.xml" % xml_file

            if not self._hklref:

                dom = xml.dom.minidom.parse(xml_file)

                try:
                    best = dom.getElementsByTagName("BestSolution")[0]
                except IndexError:
                    raise RuntimeError("error getting solution from pointless")
                self._pointgroup = (
                    best.getElementsByTagName("GroupName")[0].childNodes[0].data
                )
                self._confidence = float(
                    best.getElementsByTagName("Confidence")[0].childNodes[0].data
                )
                self._totalprob = float(
                    best.getElementsByTagName("TotalProb")[0].childNodes[0].data
                )
                self._reindex_matrix = list(
                    map(
                        float,
                        best.getElementsByTagName("ReindexMatrix")[0]
                        .childNodes[0]
                        .data.split(),
                    )
                )
                self._reindex_operator = clean_reindex_operator(
                    best.getElementsByTagName("ReindexOperator")[0]
                    .childNodes[0]
                    .data.strip()
                )

            else:

                # if we have provided a HKLREF input then the xml output
                # is changed...

                # FIXME in here, need to check if there is the legend
                # "No possible alternative indexing" in the standard
                # output, as this will mean that the index scores are
                # not there... c/f oppf1314, with latest pointless build
                # 1.2.14.

                dom = xml.dom.minidom.parse(xml_file)

                try:
                    best = dom.getElementsByTagName("IndexScores")[0]
                except IndexError:
                    logger.debug("Reindex not found in xml output")

                    # check for this legend then
                    found = False
                    for record in self.get_all_output():
                        if "No possible alternative indexing" in record:
                            found = True
                            break

                    if not found:
                        raise RuntimeError("error finding solution")

                    best = None

                hklref_pointgroup = ""

                # FIXME need to get this from the reflection file HKLREF
                reflection_file_elements = dom.getElementsByTagName("ReflectionFile")

                for rf in reflection_file_elements:
                    stream = rf.getAttribute("stream")
                    if stream == "HKLREF":
                        hklref_pointgroup = (
                            rf.getElementsByTagName("SpacegroupName")[0]
                            .childNodes[0]
                            .data.strip()
                        )

                if hklref_pointgroup == "":
                    raise RuntimeError("error finding HKLREF pointgroup")

                self._pointgroup = hklref_pointgroup

                self._confidence = 1.0
                self._totalprob = 1.0

                if best:

                    index = best.getElementsByTagName("Index")[0]

                    self._reindex_matrix = list(
                        map(
                            float,
                            index.getElementsByTagName("ReindexMatrix")[0]
                            .childNodes[0]
                            .data.split(),
                        )
                    )
                    self._reindex_operator = clean_reindex_operator(
                        index.getElementsByTagName("ReindexOperator")[0]
                        .childNodes[0]
                        .data.strip()
                    )
                else:

                    # no alternative indexing is possible so just
                    # assume the default...

                    self._reindex_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

                    self._reindex_operator = "h,k,l"

            if not self._input_laue_group and not self._hklref:

                scorelist = dom.getElementsByTagName("LaueGroupScoreList")[0]
                scores = scorelist.getElementsByTagName("LaueGroupScore")

                for s in scores:
                    lauegroup = (
                        s.getElementsByTagName("LaueGroupName")[0].childNodes[0].data
                    )
                    netzc = float(
                        s.getElementsByTagName("NetZCC")[0].childNodes[0].data
                    )

                    # record this as a possible lattice if its Z score is positive

                    lattice = lauegroup_to_lattice(lauegroup)
                    if lattice not in self._possible_lattices:
                        if netzc > 0.0:
                            self._possible_lattices.append(lattice)

                        # do we not always want to have access to the
                        # solutions, even if they are unlikely - this will
                        # only be invoked if they are known to
                        # be right...

                        self._lattice_to_laue[lattice] = lauegroup

            return "ok"

        def decide_spacegroup(self):
            """Given data indexed in the correct pointgroup, have a
            guess at the spacegroup."""

            if not self._xdsin:

                self.check_hklin()
                self.set_task(
                    "Computing the correct spacegroup for %s" % self.get_hklin()
                )

            else:
                logger.debug("Pointless using XDS input file %s" % self._xdsin)
                self.set_task(
                    "Computing the correct spacegroup for %s" % self.get_xdsin()
                )

            # FIXME this should probably be a standard CCP4 keyword

            if self._xdsin:
                self.add_command_line("xdsin")
                self.add_command_line(self._xdsin)

            self.add_command_line("xmlout")
            self.add_command_line("%d_pointless.xml" % self.get_xpid())

            self.add_command_line("hklout")
            self.add_command_line("pointless.mtz")

            self.start()

            self.input("lauegroup hklin")
            self.input("setting symmetry-based")

            if PhilIndex.params.xia2.settings.symmetry.chirality is not None:
                self.input(
                    "chirality %s" % PhilIndex.params.xia2.settings.symmetry.chirality
                )

            self.close_wait()

            # check for errors
            self.check_for_errors()

            xml_file = os.path.join(
                self.get_working_directory(), "%d_pointless.xml" % self.get_xpid()
            )
            mend_pointless_xml(xml_file)

            if not os.path.exists(xml_file) and os.path.exists("%s.xml" % xml_file):
                xml_file = "%s.xml" % xml_file

            dom = xml.dom.minidom.parse(xml_file)

            sg_list = dom.getElementsByTagName("SpacegroupList")[0]
            sg_node = sg_list.getElementsByTagName("Spacegroup")[0]
            best_prob = float(
                sg_node.getElementsByTagName("TotalProb")[0].childNodes[0].data.strip()
            )

            # FIXME 21/NOV/06 in here record a list of valid spacegroups
            # (that is, those which are as likely as the most likely)
            # for later use...

            self._spacegroup = (
                sg_node.getElementsByTagName("SpacegroupName")[0]
                .childNodes[0]
                .data.strip()
            )
            self._spacegroup_reindex_operator = (
                sg_node.getElementsByTagName("ReindexOperator")[0]
                .childNodes[0]
                .data.strip()
            )
            self._spacegroup_reindex_matrix = tuple(
                map(
                    float,
                    sg_node.getElementsByTagName("ReindexMatrix")[0]
                    .childNodes[0]
                    .data.split(),
                )
            )

            # get a list of "equally likely" spacegroups

            for node in sg_list.getElementsByTagName("Spacegroup"):
                prob = float(
                    node.getElementsByTagName("TotalProb")[0].childNodes[0].data.strip()
                )
                name = (
                    node.getElementsByTagName("SpacegroupName")[0]
                    .childNodes[0]
                    .data.strip()
                )

                if math.fabs(prob - best_prob) < 0.01:
                    # this is jolly likely!
                    self._likely_spacegroups.append(name)

            # now parse the output looking for the unit cell information -
            # this should look familiar from mtzdump

            output = self.get_all_output()

            a = 0.0
            b = 0.0
            c = 0.0
            alpha = 0.0
            beta = 0.0
            gamma = 0.0

            self._cell_info["datasets"] = []
            self._cell_info["dataset_info"] = {}

            for i, line in enumerate(output):
                line = line[:-1]

                if "Dataset ID, " in line:
                    block = 0
                    while output[block * 5 + i + 2].strip():
                        dataset_number = int(output[5 * block + i + 2].split()[0])
                        project = output[5 * block + i + 2][10:].strip()
                        crystal = output[5 * block + i + 3][10:].strip()
                        dataset = output[5 * block + i + 4][10:].strip()
                        cell = list(
                            map(float, output[5 * block + i + 5].strip().split())
                        )
                        wavelength = float(output[5 * block + i + 6].strip())

                        dataset_id = f"{project}/{crystal}/{dataset}"

                        self._cell_info["datasets"].append(dataset_id)
                        self._cell_info["dataset_info"][dataset_id] = {}
                        self._cell_info["dataset_info"][dataset_id][
                            "wavelength"
                        ] = wavelength
                        self._cell_info["dataset_info"][dataset_id]["cell"] = cell
                        self._cell_info["dataset_info"][dataset_id][
                            "id"
                        ] = dataset_number
                        block += 1

            for dataset in self._cell_info["datasets"]:
                cell = self._cell_info["dataset_info"][dataset]["cell"]
                a += cell[0]
                b += cell[1]
                c += cell[2]
                alpha += cell[3]
                beta += cell[4]
                gamma += cell[5]

            n = len(self._cell_info["datasets"])
            self._cell = (a / n, b / n, c / n, alpha / n, beta / n, gamma / n)

            if self._xdsin:
                from xia2.Wrappers.XDS import XDS

                XDS.add_xds_version_to_mtz_history(self.get_hklout())

            return "ok"

        def get_reindex_matrix(self):
            return self._reindex_matrix

        def get_reindex_operator(self):
            return self._reindex_operator

        def get_pointgroup(self):
            return self._pointgroup

        def get_spacegroup(self):
            return self._spacegroup

        def get_cell(self):
            return self._cell

        def get_probably_twinned(self):
            return self._probably_twinned

        def get_spacegroup_reindex_operator(self):
            return self._spacegroup_reindex_operator

        def get_spacegroup_reindex_matrix(self):
            return self._spacegroup_reindex_matrix

        def get_likely_spacegroups(self):
            return self._likely_spacegroups

        def get_confidence(self):
            return self._confidence

        def get_possible_lattices(self):
            return self._possible_lattices

    return PointlessWrapper()

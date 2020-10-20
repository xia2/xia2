# A handler to manage the data which needs to end up in the ISPyB xml out
# file.


import os
import time

from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex


def sanitize(path):
    """Replace double path separators with single ones."""

    double = os.sep * 2
    return path.replace(double, os.sep)


class ISPyBXmlHandler:
    def __init__(self, project):
        self._crystals = {}
        self._per_crystal_data = {}
        self._project = project

        self._name_map = {
            "High resolution limit": "resolutionLimitHigh",
            "Low resolution limit": "resolutionLimitLow",
            "Completeness": "completeness",
            "Multiplicity": "multiplicity",
            "CC half": "ccHalf",
            "Anomalous completeness": "anomalousCompleteness",
            "Anomalous correlation": "ccAnomalous",
            "Anomalous multiplicity": "anomalousMultiplicity",
            "Total observations": "nTotalObservations",
            "Total unique": "nTotalUniqueObservations",
            "Rmerge(I+/-)": "rMerge",
            "Rmeas(I)": "rMeasAllIPlusIMinus",
            "Rmeas(I+/-)": "rMeasWithinIPlusIMinus",
            "Rpim(I)": "rPimAllIPlusIMinus",
            "Rpim(I+/-)": "rPimWithinIPlusIMinus",
            "Partial Bias": "fractionalPartialBias",
            "I/sigma": "meanIOverSigI",
        }

    def add_xcrystal(self, xcrystal):
        if not xcrystal.get_name() in self._crystals:
            self._crystals[xcrystal.get_name()] = xcrystal

        # should ideally drill down and get the refined cell constants for
        # each sweep and the scaling statistics for low resolution, high
        # resolution and overall...

    @staticmethod
    def write_date(fout):
        """Write the current date and time out as XML."""

        fout.write(
            "<recordTimeStamp>%s</recordTimeStamp>\n"
            % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )

    @staticmethod
    def write_cell(fout, cell):
        """Write out a UNIT CELL as XML..."""

        fout.write("<cell_a>%f</cell_a>" % cell[0])
        fout.write("<cell_b>%f</cell_b>" % cell[1])
        fout.write("<cell_c>%f</cell_c>" % cell[2])
        fout.write("<cell_alpha>%f</cell_alpha>" % cell[3])
        fout.write("<cell_beta>%f</cell_beta>" % cell[4])
        fout.write("<cell_gamma>%f</cell_gamma>" % cell[5])

    @staticmethod
    def write_refined_cell(fout, cell):
        """Write out a REFINED UNIT CELL as XML..."""

        fout.write("<refinedCell_a>%f</refinedCell_a>" % cell[0])
        fout.write("<refinedCell_b>%f</refinedCell_b>" % cell[1])
        fout.write("<refinedCell_c>%f</refinedCell_c>" % cell[2])
        fout.write("<refinedCell_alpha>%f</refinedCell_alpha>" % cell[3])
        fout.write("<refinedCell_beta>%f</refinedCell_beta>" % cell[4])
        fout.write("<refinedCell_gamma>%f</refinedCell_gamma>" % cell[5])

    def write_scaling_statistics(self, fout, scaling_stats_type, stats_dict):
        """Write out the SCALING STATISTICS block..."""

        fout.write("<AutoProcScalingStatistics>\n")

        fout.write(
            "<scalingStatisticsType>%s</scalingStatisticsType>\n" % scaling_stats_type
        )

        for name in stats_dict:
            if name not in self._name_map:
                continue

            out_name = self._name_map[name]

            if out_name in ["nTotalObservations", "nTotalUniqueObservations"]:
                fout.write("<%s>%d</%s>" % (out_name, int(stats_dict[name]), out_name))
            else:
                fout.write("<%s>%s</%s>" % (out_name, stats_dict[name], out_name))

        fout.write("</AutoProcScalingStatistics>\n")

    def write_xml(self, file, command_line="", working_phil=None):
        if working_phil is not None:
            PhilIndex.merge_phil(working_phil)
        params = PhilIndex.get_python_object()

        fout = open(file, "w")

        fout.write('<?xml version="1.0"?>')
        fout.write("<AutoProcContainer>\n")

        for crystal in sorted(self._crystals):
            xcrystal = self._crystals[crystal]

            cell = xcrystal.get_cell()
            spacegroup = xcrystal.get_likely_spacegroups()[0]

            fout.write("<AutoProc><spaceGroup>%s</spaceGroup>" % spacegroup)
            self.write_refined_cell(fout, cell)
            fout.write("</AutoProc>")

            fout.write("<AutoProcScalingContainer>")
            fout.write("<AutoProcScaling>")
            self.write_date(fout)
            fout.write("</AutoProcScaling>")

            statistics_all = xcrystal.get_statistics()
            reflection_files = xcrystal.get_scaled_merged_reflections()

            for key in statistics_all:
                pname, xname, dname = key

                # FIXME should assert that the dname is a
                # valid wavelength name

                keys = [
                    "High resolution limit",
                    "Low resolution limit",
                    "Completeness",
                    "Multiplicity",
                    "I/sigma",
                    "Rmerge(I+/-)",
                    "CC half",
                    "Anomalous completeness",
                    "Anomalous correlation",
                    "Anomalous multiplicity",
                    "Total observations",
                    "Total unique",
                    "Rmeas(I)",
                    "Rmeas(I+/-)",
                    "Rpim(I)",
                    "Rpim(I+/-)",
                    "Partial Bias",
                ]

                stats = [k for k in keys if k in statistics_all[key]]

                xwavelength = xcrystal.get_xwavelength(dname)
                sweeps = xwavelength.get_sweeps()

                for j, name in enumerate(["overall", "innerShell", "outerShell"]):
                    statistics_cache = {}

                    for s in stats:
                        if isinstance(statistics_all[key][s], type([])):
                            statistics_cache[s] = statistics_all[key][s][j]
                        elif isinstance(statistics_all[key][s], type(())):
                            statistics_cache[s] = statistics_all[key][s][j]

                    # send these to be written out
                    self.write_scaling_statistics(fout, name, statistics_cache)

                for sweep in sweeps:
                    fout.write("<AutoProcIntegrationContainer>\n")
                    if "#" in sweep.get_template():
                        image_name = sweep.get_image_name(0)
                    else:
                        image_name = os.path.join(
                            sweep.get_directory(), sweep.get_template()
                        )
                    fout.write(
                        "<Image><fileName>%s</fileName>" % os.path.split(image_name)[-1]
                    )
                    fout.write(
                        "<fileLocation>%s</fileLocation></Image>"
                        % sanitize(os.path.split(image_name)[0])
                    )
                    fout.write("<AutoProcIntegration>\n")
                    cell = sweep.get_integrater_cell()
                    self.write_cell(fout, cell)

                    # FIXME this is naughty
                    intgr = sweep._get_integrater()

                    start, end = intgr.get_integrater_wedge()

                    fout.write("<startImageNumber>%d</startImageNumber>" % start)

                    fout.write("<endImageNumber>%d</endImageNumber>" % end)

                    # FIXME this is naughty
                    indxr = sweep._get_indexer()

                    fout.write(
                        "<refinedDetectorDistance>%f</refinedDetectorDistance>"
                        % indxr.get_indexer_distance()
                    )

                    beam = indxr.get_indexer_beam_centre_raw_image()

                    fout.write("<refinedXBeam>%f</refinedXBeam>" % beam[0])
                    fout.write("<refinedYBeam>%f</refinedYBeam>" % beam[1])

                    fout.write("</AutoProcIntegration>\n")
                    fout.write("</AutoProcIntegrationContainer>\n")

            fout.write("</AutoProcScalingContainer>")

            # file unpacking nonsense

            if not command_line:
                from xia2.Handlers.CommandLine import CommandLine

                command_line = CommandLine.get_command_line()

            pipeline = params.xia2.settings.pipeline
            fout.write("<AutoProcProgramContainer><AutoProcProgram>")
            fout.write(
                "<processingCommandLine>%s</processingCommandLine>"
                % sanitize(command_line)
            )
            fout.write("<processingPrograms>xia2 %s</processingPrograms>" % pipeline)
            fout.write("</AutoProcProgram>")

            data_directory = self._project.path / "DataFiles"
            log_directory = self._project.path / "LogFiles"

            for k in reflection_files:
                reflection_file = reflection_files[k]

                if not isinstance(reflection_file, type("")):
                    continue

                reflection_file = FileHandler.get_data_file(
                    self._project.path, reflection_file
                )

                basename = os.path.basename(reflection_file)
                if data_directory.joinpath(basename).exists():
                    # Use file in DataFiles directory in preference (if it exists)
                    reflection_file = str(data_directory.joinpath(basename))

                fout.write("<AutoProcProgramAttachment><fileType>Result")
                fout.write(
                    "</fileType><fileName>%s</fileName>"
                    % os.path.split(reflection_file)[-1]
                )
                fout.write(
                    "<filePath>%s</filePath>"
                    % sanitize(os.path.split(reflection_file)[0])
                )
                fout.write("</AutoProcProgramAttachment>\n")

            g = log_directory.glob("*merging-statistics.json")
            for merging_stats_json in g:
                fout.write("<AutoProcProgramAttachment><fileType>Graph")
                fout.write(
                    "</fileType><fileName>%s</fileName>"
                    % os.path.split(str(merging_stats_json))[-1]
                )
                fout.write("<filePath>%s</filePath>" % sanitize(str(log_directory)))
                fout.write("</AutoProcProgramAttachment>\n")

            # add the xia2.txt file...

            fout.write("<AutoProcProgramAttachment><fileType>Log")
            fout.write("</fileType><fileName>xia2.txt</fileName>")
            fout.write("<filePath>%s</filePath>" % sanitize(os.getcwd()))
            fout.write("</AutoProcProgramAttachment>\n")

            fout.write("</AutoProcProgramContainer>")

        fout.write("</AutoProcContainer>\n")
        fout.close()

    def json_object(self, command_line=""):

        result = {}

        for crystal in sorted(self._crystals):
            xcrystal = self._crystals[crystal]

            cell = xcrystal.get_cell()
            spacegroup = xcrystal.get_likely_spacegroups()[0]

            result["AutoProc"] = {}
            tmp = result["AutoProc"]

            tmp["spaceGroup"] = spacegroup
            for name, value in zip(["a", "b", "c", "alpha", "beta", "gamma"], cell):
                tmp["refinedCell_%s" % name] = value

            result["AutoProcScalingContainer"] = {}
            tmp = result["AutoProcScalingContainer"]
            tmp["AutoProcScaling"] = {
                "recordTimeStamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }

            statistics_all = xcrystal.get_statistics()
            reflection_files = xcrystal.get_scaled_merged_reflections()

            for key in list(statistics_all.keys()):
                pname, xname, dname = key

                # FIXME should assert that the dname is a
                # valid wavelength name

                keys = [
                    "High resolution limit",
                    "Low resolution limit",
                    "Completeness",
                    "Multiplicity",
                    "I/sigma",
                    "Rmerge(I+/-)",
                    "CC half",
                    "Anomalous completeness",
                    "Anomalous correlation",
                    "Anomalous multiplicity",
                    "Total observations",
                    "Total unique",
                    "Rmeas(I)",
                    "Rmeas(I+/-)",
                    "Rpim(I)",
                    "Rpim(I+/-)",
                    "Partial Bias",
                ]
                stats = [k for k in keys if k in statistics_all[key]]

                xwavelength = xcrystal.get_xwavelength(dname)
                sweeps = xwavelength.get_sweeps()

                tmp["AutoProcScalingStatistics"] = []
                tmp2 = tmp["AutoProcScalingStatistics"]

                for j, name in enumerate(["overall", "innerShell", "outerShell"]):
                    statistics_cache = {"scalingStatisticsType": name}

                    for s in stats:

                        if s in self._name_map:
                            n = self._name_map[s]
                        else:
                            continue

                        if isinstance(statistics_all[key][s], type([])):
                            statistics_cache[n] = statistics_all[key][s][j]
                        elif isinstance(statistics_all[key][s], type(())):
                            statistics_cache[n] = statistics_all[key][s][j]

                    tmp2.append(statistics_cache)

                tmp["AutoProcIntegrationContainer"] = []
                tmp2 = tmp["AutoProcIntegrationContainer"]
                for sweep in sweeps:
                    if "#" in sweep.get_template():
                        image_name = sweep.get_image_name(0)
                    else:
                        image_name = os.path.join(
                            sweep.get_directory(), sweep.get_template()
                        )
                    cell = sweep.get_integrater_cell()
                    intgr_tmp = {}
                    for name, value in zip(
                        ["a", "b", "c", "alpha", "beta", "gamma"], cell
                    ):
                        intgr_tmp["cell_%s" % name] = value

                    # FIXME this is naughty
                    indxr = sweep._get_indexer()
                    intgr = sweep._get_integrater()

                    start, end = intgr.get_integrater_wedge()

                    intgr_tmp["startImageNumber"] = start
                    intgr_tmp["endImageNumber"] = end

                    intgr_tmp["refinedDetectorDistance"] = indxr.get_indexer_distance()

                    beam = indxr.get_indexer_beam_centre_raw_image()

                    intgr_tmp["refinedXBeam"] = beam[0]
                    intgr_tmp["refinedYBeam"] = beam[1]

                    tmp2.append(
                        {
                            "Image": {
                                "fileName": os.path.split(image_name)[-1],
                                "fileLocation": sanitize(os.path.split(image_name)[0]),
                            },
                            "AutoProcIntegration": intgr_tmp,
                        }
                    )

            # file unpacking nonsense
            result["AutoProcProgramContainer"] = {}
            tmp = result["AutoProcProgramContainer"]
            tmp2 = {}

            if not command_line:
                from xia2.Handlers.CommandLine import CommandLine

                command_line = CommandLine.get_command_line()

            tmp2["processingCommandLine"] = sanitize(command_line)
            tmp2["processingProgram"] = "xia2"

            tmp["AutoProcProgram"] = tmp2
            tmp["AutoProcProgramAttachment"] = []
            tmp2 = tmp["AutoProcProgramAttachment"]

            data_directory = self._project.path / "DataFiles"

            for k in reflection_files:
                reflection_file = reflection_files[k]

                if not isinstance(reflection_file, type("")):
                    continue

                reflection_file = FileHandler.get_data_file(
                    self._project.path, reflection_file
                )
                basename = os.path.basename(reflection_file)

                if data_directory.joinpath(basename).exists():
                    # Use file in DataFiles directory in preference (if it exists)
                    reflection_file = str(data_directory.joinpath(basename))

                tmp2.append(
                    {
                        "fileType": "Result",
                        "fileName": os.path.split(reflection_file)[-1],
                        "filePath": sanitize(os.path.split(reflection_file)[0]),
                    }
                )

            tmp2.append(
                {
                    "fileType": "Log",
                    "fileName": "xia2.txt",
                    "filePath": sanitize(os.getcwd()),
                }
            )

        return result

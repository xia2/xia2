# Code to help the scaler along - this will basically be a bunch of jiffy
# functions...


import logging
import os

from xia2.lib.bits import auto_logfiler
from xia2.Wrappers.CCP4.Pointless import Pointless as _Pointless

logger = logging.getLogger("xia2.Modules.Scaler.XDSScalerHelpers")


class XDSScalerHelper:
    """A class which contains functions which will help the XDS Scaler
    with its work. This is implemented as a class to allow properties
    like working directories and so on to be maintained."""

    def __init__(self):
        self._working_directory = os.getcwd()

    def Pointless(self):
        """Create a Pointless wrapper from _Pointless - set working directory
        and log file stuff as a part of this..."""
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory

    def get_working_directory(self):
        return self._working_directory

    @staticmethod
    def parse_xscale_ascii_header(xds_ascii_file):
        """Parse out the input reflection files which contributed to this
        reflection file."""

        file_map = {}

        with open(xds_ascii_file) as fh:
            for line in fh.readlines():
                if not line[0] == "!":
                    break

                if "ISET" in line and "INPUT_FILE" in line:
                    set = int(line.split()[2].strip())
                    input_file = line.split("=")[2].strip()

                    file_map[set] = input_file

                    logger.debug("Set %d is from data %s", set, input_file)

        return file_map

    def _split_xscale_ascii_file(self, xds_ascii_file, prefix):
        """Split the output of XSCALE to separate reflection files for
        each run. The output files will be called ${prefix}${input_file}."""

        file_map = self.parse_xscale_ascii_header(xds_ascii_file)
        file_content = {k: [] for k in file_map}

        # copy the header to all of the files
        with open(xds_ascii_file) as fh:
            for line in fh.readlines():
                if not line[0] == "!":
                    break

                for k in file_map:
                    if "ISET" in line and int(line.split("ISET=")[1].split()[0]) != k:
                        continue

                    file_content[k].append(line)

        # next copy the appropriate reflections to each file
        with open(xds_ascii_file) as fh:
            for line in fh.readlines():
                if line[0] == "!":
                    continue

                # FIXME this will not be correct if zero-dose correction
                # has been used as this applies an additional record at
                # the end... though it should always be #9
                k = int(line.split()[9])
                file_content[k].append(line)

        # then add the tailer
        for k in file_map:
            file_content[k].append("!END_OF_DATA\n")

        # and finally actually write the files
        for k in file_map:
            with open(
                os.path.join(
                    self.get_working_directory(), "%s%s" % (prefix, file_map[k])
                ),
                "w",
            ) as fh:
                fh.write("".join(file_content[k]))

        return {filename: "%s%s" % (prefix, filename) for filename in file_map.values()}

    def split_and_convert_xscale_output(
        self, input_file, prefix, project_info, scale_factor=1.0
    ):
        """Split (as per method above) then convert files to MTZ
        format via pointless. The latter step will add the
        pname / xname / dname things from the dictionary supplied."""

        data_map = self._split_xscale_ascii_file(input_file, prefix)

        for token in data_map:
            if token not in project_info:
                raise RuntimeError("project info for %s not available" % token)

            hklin = os.path.join(self.get_working_directory(), data_map[token])
            hklout = os.path.join(self.get_working_directory(), "%s.mtz" % hklin[:-4])

            pname, xname, dname = project_info[token]

            p = self.Pointless()
            p.set_xdsin(hklin)
            p.set_hklout(hklout)
            p.set_project_info(pname, xname, dname)
            p.set_scale_factor(scale_factor)
            p.xds_to_mtz()

            data_map[token] = hklout

        return data_map

    def limit_batches(self, input_file, output_file, start, end):
        with open(input_file) as infile, open(output_file, "w") as outfile:
            for line in infile.readlines():
                if line.startswith("!"):
                    outfile.write(line)
                else:
                    tokens = line.split()
                    assert len(tokens) == 12
                    z = float(tokens[7])
                    if z >= start and z < end:
                        outfile.write(line)

#!/usr/bin/env python
# Files.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A manager for files - this will record temporary and output files from
# xia2, which can be used for composing a dump of "useful" files at the end
# if processing.
#
# This will also be responsible for migrating the data - that is, when
# the .xinfo file is parsed the directories referred to therein may be
# migrated to a local disk. This will use a directory created by
# tempfile.mkdtemp().

from __future__ import absolute_import, division, print_function

import os
import shutil
import tempfile

from xia2.Handlers.Environment import Environment


def get_mosflm_commands(lines_of_input):
    """Get the commands which were sent to Mosflm."""

    result = []

    for line in lines_of_input:
        if "===>" in line:
            result.append(line.replace("===>", "").strip())
        if "MOSFLM =>" in line:
            result.append(line.replace("MOSFLM =>", "").strip())

    return result


def get_xds_commands(lines_of_input):
    """Get the command input to XDS - that is, all of the text between
  the line which goes ***** STEP ***** and **********. Love FORTRAN."""

    collecting = False

    result = []

    for l in lines_of_input:
        if "*****" in l and not collecting:
            collecting = True
            continue

        if "*****" in l:
            break

        if collecting:
            if l.strip():
                result.append(l.strip())

    return result


def get_ccp4_commands(lines_of_input):
    """Get the commands which were sent to a CCP4 program."""

    # first look through for hklin / hklout

    logicals = {}

    for line in lines_of_input:
        if "Logical Name:" in line:
            token = line.split(":")[1].split()[0]
            value = line.split(":")[-1].strip()
            logicals[token] = value

    # then look for standard input commands

    script = []

    for line in lines_of_input:
        if "Data line---" in line:
            script.append(line.replace("Data line---", "").strip())

    return script, logicals


class _FileHandler(object):
    """A singleton class to manage files."""

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

        self._log_files = {}
        self._log_file_keys = []

        self._xml_files = {}
        self._xml_file_keys = []

        self._html_files = {}
        self._html_file_keys = []

        # for putting the reflection files somewhere nice...
        self._data_files = []

        # same mechanism as log files - I want to rename files copied to the
        # DataFiles directory
        self._more_data_files = {}
        self._more_data_file_keys = []

    def cleanup(self):
        out = open("xia2-files.txt", "w")
        for f in self._temporary_files:
            try:
                os.remove(f)
                out.write("Deleted: %s\n" % f)
            except Exception as e:
                out.write("Failed to delete: %s (%s)\n" % (f, str(e)))

        for f in self._output_files:
            out.write("Output file (%s): %s\n" % f)

        # copy the log files
        log_directory = Environment.generate_directory("LogFiles")

        for f in self._log_file_keys:
            filename = os.path.join(log_directory, "%s.log" % f.replace(" ", "_"))
            shutil.copyfile(self._log_files[f], filename)
            out.write("Copied log file %s to %s\n" % (self._log_files[f], filename))

        for f in self._xml_file_keys:
            filename = os.path.join(log_directory, "%s.xml" % f.replace(" ", "_"))
            shutil.copyfile(self._xml_files[f], filename)
            out.write("Copied xml file %s to %s\n" % (self._xml_files[f], filename))

            for f in self._html_file_keys:
                filename = os.path.join(log_directory, "%s.html" % f.replace(" ", "_"))
                shutil.copyfile(self._html_files[f], filename)
                out.write(
                    "Copied html file %s to %s\n" % (self._html_files[f], filename)
                )

        # copy the data files
        data_directory = Environment.generate_directory("DataFiles")
        for f in self._data_files:
            filename = os.path.join(data_directory, os.path.split(f)[-1])
            shutil.copyfile(f, filename)
            out.write("Copied data file %s to %s\n" % (f, filename))

        for tag, ext in self._more_data_file_keys:
            filename_out = os.path.join(
                data_directory, "%s.%s" % (tag.replace(" ", "_"), ext)
            )
            filename_in = self._more_data_files[(tag, ext)]
            shutil.copyfile(filename_in, filename_out)
            out.write("Copied extra data file %s to %s\n" % (filename_in, filename_out))

        out.close()

    def record_output_file(self, filename, type):
        self._output_files.append((type, filename))

    def record_log_file(self, tag, filename):
        """Record a log file."""
        self._log_files[tag] = filename
        if not tag in self._log_file_keys:
            self._log_file_keys.append(tag)

    def record_xml_file(self, tag, filename):
        """Record an xml file."""
        self._xml_files[tag] = filename
        if not tag in self._xml_file_keys:
            self._xml_file_keys.append(tag)

    def record_html_file(self, tag, filename):
        """Record an html file."""
        self._html_files[tag] = filename
        if not tag in self._html_file_keys:
            self._html_file_keys.append(tag)

    def record_data_file(self, filename):
        """Record a data file."""
        if not filename in self._data_files:
            assert os.path.isfile(filename), "Required file %s not found" % filename
            self._data_files.append(filename)

    def record_more_data_file(self, tag, filename):
        """Record an extra data file."""
        ext = os.path.splitext(filename)[1][1:]
        key = (tag, ext)
        self._more_data_files[key] = filename
        if not tag in self._more_data_file_keys:
            self._more_data_file_keys.append(key)

    def get_data_file(self, filename):
        """Return the point where this data file will end up!"""

        if not filename in self._data_files:
            return filename

        data_directory = Environment.generate_directory("DataFiles")
        return os.path.join(data_directory, os.path.split(filename)[-1])

    def record_temporary_file(self, filename):
        # allow for file overwrites etc.
        if not filename in self._temporary_files:
            self._temporary_files.append(filename)


FileHandler = _FileHandler()


def cleanup():
    FileHandler.cleanup()


if __name__ == "__main__":
    FileHandler.record_temporary_file("noexist.txt")
    open("junk.txt", "w").write("junk!")
    FileHandler.record_temporary_file("junk.txt")

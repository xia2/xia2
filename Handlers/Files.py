# A manager for files - this will record temporary and output files from
# xia2, which can be used for composing a dump of "useful" files at the end
# if processing.
#
# This will also be responsible for migrating the data - that is, when
# the .xinfo file is parsed the directories referred to therein may be
# migrated to a local disk.

from __future__ import absolute_import, division, print_function

import contextlib
import os
import shutil


class _FileHandler(object):
    """A singleton class to manage files."""

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

        self._html_files = {}
        self._log_files = {}
        self._xml_files = {}

        # for putting the reflection files somewhere nice...
        self._data_files = []

        # same mechanism as log files - I want to rename files copied to the
        # DataFiles directory
        self._more_data_files = {}

    def cleanup(self, base_path):
        with open("xia2-files.txt", "w") as out:
            for f in self._temporary_files:
                try:
                    os.remove(f)
                    out.write("Deleted: %s\n" % f)
                except Exception as e:
                    out.write("Failed to delete: %s (%s)\n" % (f, str(e)))

            for f in self._output_files:
                out.write("Output file (%s): %s\n" % f)

            # copy the log files
            log_directory = base_path.joinpath("LogFiles")
            log_directory.mkdir(parents=True, exist_ok=True)
            log_directory = str(log_directory)

            for tag, source in self._log_files.items():
                filename = os.path.join(log_directory, "%s.log" % tag.replace(" ", "_"))
                shutil.copyfile(source, filename)
                out.write("Copied log file %s to %s\n" % (source, filename))

            for tag, source in self._xml_files.items():
                filename = os.path.join(log_directory, "%s.xml" % tag.replace(" ", "_"))
                shutil.copyfile(source, filename)
                out.write("Copied xml file %s to %s\n" % (source, filename))

            for tag, source in self._html_files.items():
                filename = os.path.join(
                    log_directory, "%s.html" % tag.replace(" ", "_")
                )
                shutil.copyfile(source, filename)
                out.write("Copied html file %s to %s\n" % (source, filename))

            # copy the data files
            data_directory = base_path.joinpath("DataFiles")
            data_directory.mkdir(parents=True, exist_ok=True)
            data_directory = str(data_directory)
            for f in self._data_files:
                filename = os.path.join(data_directory, os.path.split(f)[-1])
                shutil.copyfile(f, filename)
                out.write("Copied data file %s to %s\n" % (f, filename))

            for tag, ext in self._more_data_files:
                filename_out = os.path.join(
                    data_directory, "%s.%s" % (tag.replace(" ", "_"), ext)
                )
                filename_in = self._more_data_files[(tag, ext)]
                shutil.copyfile(filename_in, filename_out)
                out.write(
                    "Copied extra data file %s to %s\n" % (filename_in, filename_out)
                )

    def record_log_file(self, tag, filename):
        """Record a log file."""
        self._log_files[tag] = filename

    def record_xml_file(self, tag, filename):
        """Record an xml file."""
        self._xml_files[tag] = filename

    def record_html_file(self, tag, filename):
        """Record an html file."""
        self._html_files[tag] = filename

    def record_data_file(self, filename):
        """Record a data file."""
        if filename not in self._data_files:
            assert os.path.isfile(filename), "Required file %s not found" % filename
            self._data_files.append(filename)

    def record_more_data_file(self, tag, filename):
        """Record an extra data file."""
        ext = os.path.splitext(filename)[1][1:]
        key = (tag, ext)
        self._more_data_files[key] = filename

    def get_data_file(self, base_path, filename):
        """Return the point where this data file will end up!"""

        if filename not in self._data_files:
            return filename

        data_directory = base_path.joinpath("DataFiles")
        data_directory.mkdir(parents=True, exist_ok=True)
        return str(data_directory.joinpath(os.path.split(filename)[-1]))

    def record_temporary_file(self, filename):
        # allow for file overwrites etc.
        if filename not in self._temporary_files:
            self._temporary_files.append(filename)


FileHandler = _FileHandler()


@contextlib.contextmanager
def cleanup(base_path):
    try:
        yield
    finally:
        FileHandler.cleanup(base_path)

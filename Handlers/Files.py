# A manager for files - this will record temporary and output files from
# xia2, which can be used for composing a dump of "useful" files at the end
# if processing.
#
# This will also be responsible for migrating the data - that is, when
# the .xinfo file is parsed the directories referred to therein may be
# migrated to a local disk.


import contextlib
import logging
import os
import shutil

logger = logging.getLogger("xia2.Handlers.Files")


class _FileHandler:
    """A singleton class to manage files."""

    def __init__(self):
        self._temporary_files = []

        self._html_files = {}
        self._log_files = {}
        self._xml_files = {}

        # for putting the reflection files somewhere nice...
        self._data_files = []

        # same mechanism as log files - I want to rename files copied to the
        # DataFiles directory
        self._more_data_files = {}

    def cleanup(self, base_path):
        for f in self._temporary_files:
            try:
                os.remove(f)
                logger.debug("Deleted: %s", f)
            except Exception as e:
                logger.debug("Failed to delete: %s (%s)", f, str(e), exc_info=True)

        # copy the log files
        log_directory = base_path.joinpath("LogFiles")
        log_directory.mkdir(parents=True, exist_ok=True)

        for tag, source in self._log_files.items():
            filename = log_directory.joinpath("%s.log" % tag.replace(" ", "_"))
            shutil.copyfile(source, filename)
            logger.debug(f"Copied log file {source} to {filename}")

        for tag, source in self._xml_files.items():
            filename = log_directory.joinpath("%s.xml" % tag.replace(" ", "_"))
            shutil.copyfile(source, filename)
            logger.debug(f"Copied xml file {source} to {filename}")

        for tag, source in self._html_files.items():
            filename = log_directory.joinpath("%s.html" % tag.replace(" ", "_"))
            shutil.copyfile(source, filename)
            logger.debug(f"Copied html file {source} to {filename}")

        # copy the data files
        data_directory = base_path.joinpath("DataFiles")
        data_directory.mkdir(parents=True, exist_ok=True)
        for f in self._data_files:
            filename = data_directory.joinpath(os.path.split(f)[-1])
            shutil.copyfile(f, filename)
            logger.debug(f"Copied data file {f} to {filename}")

        for tag, ext in self._more_data_files:
            filename_out = data_directory.joinpath(
                "{}.{}".format(tag.replace(" ", "_"), ext)
            )
            filename_in = self._more_data_files[(tag, ext)]
            shutil.copyfile(filename_in, filename_out)
            logger.debug(f"Copied extra data file {filename_in} to {filename_out}")

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

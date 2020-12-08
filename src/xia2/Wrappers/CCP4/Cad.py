import logging
import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Modules.FindFreeFlag import FindFreeFlag
from xia2.Wrappers.CCP4.Mtzdump import Mtzdump

logger = logging.getLogger("xia2.Wrappers.CCP4.Cad")


def Cad(DriverType=None):
    """A factory for CadWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class CadWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Cad, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "cad"))

            self._hklin_files = []

            self._new_cell_parameters = None
            self._new_column_suffix = None

            self._pname = None
            self._xname = None
            self._dname = None

            # stuff to specifically copy in the freer column...
            self._freein = None
            self._freein_column = "FreeR_flag"

        def add_hklin(self, hklin):
            """Add a reflection file to the list to be sorted together."""
            self._hklin_files.append(hklin)

        def set_freein(self, freein):

            # I guess I should check in here that this file actually
            # exists... - also that it has a sensible FreeR column...

            if not os.path.exists(freein):
                raise RuntimeError("reflection file does not exist: %s" % freein)

            cname = FindFreeFlag(freein)

            logger.debug("FreeR_flag column identified as %s", cname)

            self._freein = freein
            self._freein_column = cname

        def set_project_info(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname

        def set_new_suffix(self, suffix):
            """Set a column suffix for this dataset."""
            self._new_column_suffix = suffix

        def merge(self):
            """Merge multiple reflection files into one file."""

            if not self._hklin_files:
                raise RuntimeError("no hklin files defined")

            self.check_hklout()

            hklin_counter = 0

            # for each reflection file, need to gather the column names
            # and so on, to put in the cad input here - also check to see
            # if the column names clash... check also that the spacegroups
            # match up...

            spacegroup = None
            column_names = []
            column_names_by_file = {}

            for hklin in self._hklin_files:
                md = Mtzdump()
                md.set_working_directory(self.get_working_directory())
                md.set_hklin(hklin)
                md.dump()
                columns = md.get_columns()
                spag = md.get_spacegroup()

                if spacegroup is None:
                    spacegroup = spag

                if spag != spacegroup:
                    raise RuntimeError("spacegroups do not match")

                column_names_by_file[hklin] = []

                for c in columns:
                    name = c[0]
                    if name in ["H", "K", "L"]:
                        continue
                    if name in column_names:
                        raise RuntimeError("duplicate column names")
                    column_names.append(name)
                    column_names_by_file[hklin].append(name)

            # if we get to here then this is a good set up...

            # create the command line

            hklin_counter = 0
            for hklin in self._hklin_files:
                hklin_counter += 1
                self.add_command_line("hklin%d" % hklin_counter)
                self.add_command_line(hklin)

            self.start()

            hklin_counter = 0

            for hklin in self._hklin_files:
                column_counter = 0
                hklin_counter += 1
                labin_command = "labin file_number %d" % hklin_counter
                for column in column_names_by_file[hklin]:
                    column_counter += 1
                    labin_command += " E%d=%s" % (column_counter, column)

                self.input(labin_command)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError as e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass
                raise e

            return self.get_ccp4_status()

        def update(self):
            """Update the information for one reflection file."""

            if not self._hklin_files:
                raise RuntimeError("no hklin files defined")

            if len(self._hklin_files) > 1:
                raise RuntimeError("can have only one hklin to update")

            hklin = self._hklin_files[0]

            self.check_hklout()

            column_names_by_file = {}
            dataset_names_by_file = {}

            md = Mtzdump()
            md.set_hklin(hklin)
            md.dump()
            columns = md.get_columns()

            column_names_by_file[hklin] = []
            dataset_names_by_file[hklin] = md.get_datasets()

            # get a dataset ID - see FIXME 03/NOV/06 below...

            dataset_ids = [md.get_dataset_info(d)["id"] for d in md.get_datasets()]

            for c in columns:
                name = c[0]
                if name in ["H", "K", "L"]:
                    continue

                column_names_by_file[hklin].append(name)

            self.add_command_line("hklin1")
            self.add_command_line(hklin)
            self.start()

            dataset_id = dataset_ids[0]

            if self._pname and self._xname and self._dname:
                self.input(
                    "drename file_number 1 %d %s %s"
                    % (dataset_id, self._xname, self._dname)
                )
                self.input("dpname file_number 1 %d %s" % (dataset_id, self._pname))

            column_counter = 0
            labin_command = "labin file_number 1"
            for column in column_names_by_file[hklin]:
                column_counter += 1
                labin_command += " E%d=%s" % (column_counter, column)

            self.input(labin_command)

            # FIXME perhaps - ASSERT that we want only the information from
            # the first dataset here...

            dataset_id = dataset_ids[0]

            if self._new_cell_parameters:
                a, b, c, alpha, beta, gamma = self._new_cell_parameters
                self.input(
                    "dcell file_number 1 %d %f %f %f %f %f %f"
                    % (dataset_id, a, b, c, alpha, beta, gamma)
                )

            if self._new_column_suffix:
                suffix = self._new_column_suffix
                column_counter = 0
                labout_command = "labout file_number 1"
                for column in column_names_by_file[hklin]:
                    column_counter += 1
                    labout_command += " E%d=%s_%s" % (column_counter, column, suffix)

                self.input(labout_command)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError as e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass
                raise e

            return self.get_ccp4_status()

        def copyfree(self):
            """Copy the free column from freein into hklin -> hklout."""

            if not self._hklin_files:
                raise RuntimeError("no hklin files defined")

            if len(self._hklin_files) > 1:
                raise RuntimeError("can have only one hklin to update")

            hklin = self._hklin_files[0]

            # get the resolution limit to give as a limit for the FreeR
            # column

            md = Mtzdump()
            md.set_working_directory(self.get_working_directory())
            md.set_hklin(hklin)
            md.dump()
            resolution_range = md.get_resolution_range()

            self.check_hklout()
            if self._freein is None:
                raise RuntimeError("freein not defined")
            if self._freein_column is None:
                raise RuntimeError("freein column not defined")

            self.add_command_line("hklin1")
            self.add_command_line(self._freein)
            self.add_command_line("hklin2")
            self.add_command_line(hklin)
            self.start()

            self.input("labin file_number 1 E1=%s" % self._freein_column)
            self.input("resolution file_number 1 %f %f" % resolution_range)
            self.input("labin file_number 2 all")

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError as e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass
                raise e

            return self.get_ccp4_status()

    return CadWrapper()

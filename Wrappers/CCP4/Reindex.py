import logging
import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Syminfo import Syminfo

logger = logging.getLogger("xia2.Wrappers.CCP4.Reindex")


def Reindex(DriverType=None):
    """A new factory for ReindexWrapper classes, which will actually use
    pointless."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class ReindexWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Reindex, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "pointless"))

            # reindex specific things
            self._spacegroup = None

            # this should be of the form e.g. k, l, h
            self._operator = None

            # results
            self._cell = None

        def set_spacegroup(self, spacegroup):
            """Set the spacegroup to reindex the reflections to."""

            self._spacegroup = spacegroup

        def set_operator(self, operator):
            """Set the reindexing operator for mapping from in to out."""

            # pointless doesn't like reindex operators with '*'
            if operator is not None:
                operator = operator.replace("*", "")
            self._operator = operator

        def get_cell(self):
            return self._cell

        def reindex_old(self):
            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "reindex"))
            self.check_hklin()
            self.check_hklout()

            if not self._spacegroup and not self._operator:
                raise RuntimeError("reindex requires spacegroup or operator")

            self.start()

            # look up the space group number to cope with complex symbols
            # that old fashioned CCP4 reindex does not understand...
            from cctbx.sgtbx import space_group, space_group_symbols

            sg_t = space_group(space_group_symbols(str(self._spacegroup))).type()

            if self._operator:
                self.input("reindex %s" % str(self._operator))
            if self._spacegroup:
                self.input("symmetry %d" % sg_t.number())
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()

            except RuntimeError as e:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

                raise e

            output = self.get_all_output()

            for j, o in enumerate(output):
                if "Cell Dimensions : (obsolete" in o:
                    self._cell = list(map(float, output[j + 2].split()))

            return "OK"

        def cctbx_reindex(self):
            from xia2.Modules.MtzUtils import reindex

            reindex(
                self._hklin, self._hklout, self._operator, space_group=self._spacegroup
            )
            return "OK"

        def reindex(self):
            """Actually perform the reindexing."""

            if PhilIndex.params.ccp4.reindex.program == "reindex":
                return self.reindex_old()

            elif PhilIndex.params.ccp4.reindex.program == "cctbx":
                return self.cctbx_reindex()

            self.check_hklin()
            self.check_hklout()

            if not self._spacegroup and not self._operator:
                raise RuntimeError("reindex requires spacegroup or operator")

            if self._operator:
                self._operator = self._operator.replace("[", "").replace("]", "")

            logger.debug("Reindex... %s %s", self._spacegroup, self._operator)

            self.start()

            if self._spacegroup:

                if isinstance(self._spacegroup, type(0)):
                    spacegroup = Syminfo.spacegroup_number_to_name(self._spacegroup)
                elif self._spacegroup[0] in "0123456789":
                    spacegroup = Syminfo.spacegroup_number_to_name(
                        int(self._spacegroup)
                    )
                else:
                    spacegroup = self._spacegroup

                self.input("spacegroup '%s'" % spacegroup)

            if self._operator:
                # likewise
                self.input("reindex '%s'" % self._operator)
            else:
                self.input("reindex 'h,k,l'")

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()

            except RuntimeError as e:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

                raise e

            output = self.get_all_output()

            for j, o in enumerate(output):
                if "Cell Dimensions : (obsolete" in o:
                    self._cell = list(map(float, output[j + 2].split()))
                elif "ReindexOp: syntax error in operator" in o:
                    raise RuntimeError(o)

            return "OK"

    return ReindexWrapper()

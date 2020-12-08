# A handler to manage the data ending up in CIF output file


import datetime

import iotbx.cif.model
import xia2.Handlers.Citations
import xia2.XIA2Version


class _CIFHandler:
    def __init__(self, mmCIFsemantics=False):
        self._cif = iotbx.cif.model.cif()
        self._outfile = "xia2.cif" if not mmCIFsemantics else "xia2.mmcif"

        # CIF/mmCIF key definitions
        self._keyname = (
            {
                "audit.method": "_audit_creation_method",
                "audit.date": "_audit_creation_date",
                "sg.system": "_space_group_crystal_system",
                "sg.number": "_space_group_IT_number",
                "sw.reduction": "_computing_data_reduction",
                "symm.ops": "_symmetry_equiv_pos_as_xyz",
                "symm.sgsymbol": "_symmetry_space_group_name_H-M",
                "cell.Z": "_cell_formula_units_Z",
                "wavelength": "_diffrn_radiation_wavelength",
                "wavelength.id": "_diffrn_radiation_wavelength_id",
                "references": "_publ_section_references",
            }
            if not mmCIFsemantics
            else {
                "audit.method": "_audit.creation_method",
                "audit.date": "_audit.creation_date",
                "sg.system": "_space_group.crystal_system",
                "sg.number": "_space_group.IT_number",
                "sw.reduction": "_computing.data_reduction",
                "symm.ops": "_symmetry_equiv.pos_as_xyz",
                "symm.sgsymbol": "_symmetry.space_group_name_H-M",
                "cell.Z": "_cell.formula_units_Z",
                "wavelength": "_diffrn_radiation_wavelength.wavelength",
                "wavelength.id": "_diffrn_radiation_wavelength.id",
                "references": "_publ.section_references",
            }
        )
        # prepopulate audit fields, so they end up at the top of the file
        self.collate_audit_information()

    def set_spacegroup(self, spacegroup, blockname=None):
        sg = spacegroup.group()

        loop = iotbx.cif.model.loop()
        symm_ops = []
        for i in range(sg.n_smx()):
            rt_mx = sg(0, 0, i)
            if rt_mx.is_unit_mx():
                continue
            symm_ops.append(str(rt_mx))
        loop[self._keyname["symm.ops"]] = symm_ops

        block = self.get_block(blockname)
        block[self._keyname["symm.sgsymbol"]] = spacegroup.lookup_symbol()
        block[self._keyname["sg.system"]] = sg.crystal_system().lower()
        block[self._keyname["sg.number"]] = spacegroup.number()
        block[self._keyname["cell.Z"]] = sg.order_z()
        block.add_loop(loop)

    def set_wavelengths(self, wavelength, blockname=None):
        block = self.get_block(blockname)
        if isinstance(wavelength, dict):
            if self._keyname["wavelength"] in block:
                del block[self._keyname["wavelength"]]
            loop = iotbx.cif.model.loop(
                header=[self._keyname["wavelength.id"], self._keyname["wavelength"]],
                data=[s for item in wavelength.items() for s in item],
            )
            block.add_loop(loop)
        else:
            if len(wavelength) == 1:
                block[self._keyname["wavelength"]] = wavelength[0]
            else:
                block[self._keyname["wavelength"]] = wavelength

    def __str__(self):
        """Return CIF as string representation."""
        # update audit information for citations
        self.collate_audit_information()
        return str(self._cif)

    def write_cif(self, path):
        """Write CIF to file."""
        # update audit information for citations
        self.collate_audit_information()

        path.mkdir(parents=True, exist_ok=True)
        with open(str(path.joinpath(self._outfile)), "w") as fh:
            self._cif.show(out=fh)

    def get_block(self, blockname=None):
        """Create (if necessary) and return named CIF block"""
        if blockname is None:
            blockname = "xia2"
        assert blockname, "invalid block name"
        if blockname not in self._cif:
            self._cif[blockname] = iotbx.cif.model.block()
        return self._cif[blockname]

    def set_block(self, blockname, iotbxblock):
        """Store a block object, overwrite existing block if necessary"""
        self._cif[blockname] = iotbxblock

    def collate_audit_information(self, blockname=None):
        block = self.get_block(blockname)
        block[self._keyname["audit.method"]] = xia2.XIA2Version.Version
        block[self._keyname["audit.date"]] = datetime.date.today().isoformat()

        xia2.Handlers.Citations.Citations.cite("xia2")
        programs = []
        for program in xia2.Handlers.Citations.Citations.get_programs():
            citations = []
            for citation in xia2.Handlers.Citations.Citations.find_citations(program):
                if "acta" in citation:
                    if ")" in citation["acta"]:
                        citations.append(
                            citation["acta"][0 : citation["acta"].index(")")].replace(
                                " (", ", "
                            )
                        )
                    else:
                        citations.append(citation["acta"])
            if program == "xia2":
                program = xia2.XIA2Version.Version
            elif program == "dials":
                import dials.util.version

                program = dials.util.version.dials_version()
            if citations:
                program = program + " (%s)" % ("; ".join(citations))
            programs.append(program)
        block[self._keyname["sw.reduction"]] = "\n".join(programs)

        block[self._keyname["references"]] = "\n".join(
            xia2.Handlers.Citations.Citations.get_citations_acta()
        )


CIF = _CIFHandler()
mmCIF = _CIFHandler(mmCIFsemantics=True)

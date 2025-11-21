# A handler to manage the data ending up in CIF output file

from __future__ import annotations

import bz2
import datetime

import iotbx.cif.model

import xia2.Handlers.Citations
from xia2.Handlers.Versions import versions

mmcif_software_header = (
    "_software.pdbx_ordinal",
    "_software.citation_id",
    "_software.name",  # as defined at [1]
    "_software.version",
    "_software.type",
    "_software.classification",
    "_software.description",
    "_software.pdbx_reference_DOI",
)

mmcif_citations_header = (
    "_citation.id",
    "_citation.journal_abbrev",
    "_citation.journal_volume",
    "_citation.journal_issue",
    "_citation.page_first",
    "_citation.page_last",
    "_citation.year",
    "_citation.title",
)


class _CIFHandler:
    def __init__(self, mmCIFsemantics=False):
        self._cif = iotbx.cif.model.cif()
        self._outfile = "xia2.cif" if not mmCIFsemantics else "xia2.mmcif.bz2"
        self._mmCIFsemantics = mmCIFsemantics
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
        if self._mmCIFsemantics:
            loop["_symmetry_equiv.id"] = list(range(1, len(symm_ops) + 1))
        loop[self._keyname["symm.ops"]] = symm_ops

        block = self.get_block(blockname)
        if self._mmCIFsemantics:
            block["_symmetry.entry_id"] = block["_entry.id"]
        block[self._keyname["symm.sgsymbol"]] = spacegroup.lookup_symbol()
        if self._mmCIFsemantics:
            block["_space_group.id"] = 1  # category needs an 'id'
        block[self._keyname["sg.system"]] = sg.crystal_system().lower()
        block[self._keyname["sg.number"]] = spacegroup.number()
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
        if self._outfile.endswith(".bz2"):
            open_fn = bz2.open
        else:
            open_fn = open
        with open_fn(str(path.joinpath(self._outfile)), "wt") as fh:
            self._cif.show(out=fh)

    def get_block(self, blockname=None):
        """Create (if necessary) and return named CIF block"""
        if blockname is None:
            blockname = "xia2"
        assert blockname, "invalid block name"
        if blockname not in self._cif:
            self._cif[blockname] = iotbx.cif.model.block()
            self._cif[blockname]["_entry.id"] = blockname
        return self._cif[blockname]

    def set_block(self, blockname, iotbxblock):
        """Store a block object, overwrite existing block if necessary"""
        self._cif[blockname] = iotbxblock

    def collate_audit_information(self, blockname=None):
        block = self.get_block(blockname)
        block["_audit.revision_id"] = 1
        block[self._keyname["audit.method"]] = versions["xia2"]
        block[self._keyname["audit.date"]] = datetime.date.today().isoformat()

        if self._mmCIFsemantics:
            if "_software" not in block.loop_keys():
                block.add_loop(iotbx.cif.model.loop(header=mmcif_software_header))
                block.add_loop(iotbx.cif.model.loop(header=mmcif_citations_header))
            software_loop = block.get_loop("_software")
            citations_loop = block.get_loop("_citation")
            # clear rows to avoid repeated row writing for multiple calls to
            # collate_audit_information
            for _ in range(0, software_loop.n_rows()):
                software_loop.delete_row(0)
                citations_loop.delete_row(0)
            count = 1
            for citation in xia2.Handlers.Citations.Citations.get_citations_dicts():
                if "software_type" in citation:
                    bibtex_data = xia2.Handlers.Citations.Citations._parse_bibtex(
                        citation["bibtex"]
                    )
                    software_loop.add_row(
                        (
                            count,
                            count,
                            citation["software_name"],
                            versions[citation["software_name"].lower()],
                            citation["software_type"],
                            citation["software_classification"],
                            citation["software_description"],
                            bibtex_data["doi"],
                        )
                    )
                    citations_loop.add_row(
                        (
                            count,
                            bibtex_data["journal"],
                            bibtex_data["volume"],
                            bibtex_data["number"],
                            bibtex_data["pages"].split("--")[0],
                            bibtex_data["pages"].split("--")[1],
                            bibtex_data["year"],
                            bibtex_data["title"].replace("\\it ", ""),
                        )
                    )
                    count += 1
        else:
            programs = []
            for program in xia2.Handlers.Citations.Citations.get_programs():
                citations = []
                for citation in xia2.Handlers.Citations.Citations.find_citations(
                    program
                ):
                    if "acta" in citation:
                        if ")" in citation["acta"]:
                            citations.append(
                                citation["acta"][
                                    0 : citation["acta"].index(")")
                                ].replace(" (", ", ")
                            )
                        else:
                            citations.append(citation["acta"])
                if program == "xia2":
                    program = versions["xia2"]
                elif program == "dials":
                    program = versions["dials"]
                if citations:
                    program = program + " (%s)" % ("; ".join(citations))
                programs.append(program)
            block[self._keyname["sw.reduction"]] = "\n".join(programs)

            block[self._keyname["references"]] = "\n".join(
                xia2.Handlers.Citations.Citations.get_citations_acta()
            )


CIF = _CIFHandler()
mmCIF = _CIFHandler(mmCIFsemantics=True)

# [1] http://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_software.name.html

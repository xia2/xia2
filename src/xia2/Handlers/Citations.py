from __future__ import annotations

import itertools
import pathlib

import yaml


class _Citations:
    """A class to track citations."""

    def __init__(self):
        self._cited = []

        citations_yaml = (
            pathlib.Path(__file__).parent.parent / "Data" / "citations.yaml"
        )
        self._citations = yaml.safe_load(citations_yaml.read_text())
        for citation_list in self._citations.values():
            for citation_data in citation_list:
                if "acta" not in citation_data:
                    # construct Acta style reference if necessary
                    citation_data["acta"] = self._bibtex_to_acta(
                        citation_data["bibtex"]
                    )

                if "url" not in citation_data:
                    # obtain URL from bibtex entry if possible
                    bibtex_data = self._parse_bibtex(citation_data["bibtex"])
                    if "url" in bibtex_data:
                        citation_data["url"] = bibtex_data["url"]
                    elif "doi" in bibtex_data:
                        citation_data["url"] = "https://doi.org/" + bibtex_data["doi"]

    def cite(self, program):
        """Cite a given program."""

        if program not in self._cited:
            self._cited.append(program)

    def get_programs(self):
        """Get a list of all of the programs which have been cited."""
        return sorted(self._cited)

    def get_citations(self):
        """Get a list of bibtex records of citations."""

        return [cit["bibtex"] for cit in self.get_citations_dicts()]

    def get_citations_dicts(self):
        """Get a list of citations dictionary objects."""

        return list(
            itertools.chain.from_iterable(
                self._citations.get(program, []) for program in self._cited
            )
        )

    def get_citations_acta(self):
        """Return a list of strings of Acta style references."""

        # want them in alphabetical order
        return sorted(cit["acta"] for cit in self.get_citations_dicts())

    def find_citations(self, program=None, acta=None):
        """Return a list of citations for a program name or an Acta style reference."""

        results = []

        if program:
            results.extend(self._citations.get(program, []))

        if acta:
            results.extend(
                citation
                for citations in self._citations.values()
                for citation in citations
                if citation.get("acta") == acta
            )

        return results

    def _parse_bibtex(self, bibtex):
        """A jiffy to parse a bibtex entry."""

        contents = {"volume": ""}

        for token in bibtex.split("\n"):
            if "=" in token:
                name, value = tuple(token.split("="))

                # clean up the value...
                value = value.replace("{", "").replace("}", "")
                value = value.replace('"', "")

                value = value.strip()
                if value[-1] == ",":
                    value = value[:-1]

                contents[name.strip()] = value

        return contents

    def _bibtex_to_acta(self, bibtex):
        """Construct an Acta-like formatted reference from a bibtex entry."""

        data = self._parse_bibtex(bibtex)
        actaformat = "%(author)s (%(year)s) %(journal)s %(volume)s."

        # drop every 'and' but the last
        data["author"] = data["author"].replace(
            " and ", ", ", data["author"].count(" and ") - 1
        )

        if "pages" in data:
            data["pages"] = data["pages"].replace("--", "-")
            actaformat = "%(author)s (%(year)s) %(journal)s %(volume)s, %(pages)s."

        return actaformat % data


Citations = _Citations()

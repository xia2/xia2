#!/usr/bin/env python
# Citations.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler for management of program citations. This should initialise
# from a citations.xml file which can be found in a number of places...
# in particular $HOME or $USERDIR (I think, on Windows) .xia2,
# data etc...
#
# That would be %USERPROFILE%

import os
import xml.dom.minidom

class _Citations(object):
  '''A class to track citations.'''

  def __init__(self):
    self._citations = {}
    self._cited = []

    # set up the citations list...

    dom = xml.dom.minidom.parse(os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..',
        'Data', 'citations.xml')))
    citations = dom.getElementsByTagName(
        'citations')[0].getElementsByTagName('citation')
    for citation in citations:
      program = str(citation.attributes['program'].value)
      bibtex = str(citation.childNodes[0].data)

      if program not in self._citations:
        self._citations[program] = []
      self._citations[program].append(bibtex)

    return

  def cite(self, program):
    '''Cite a given program.'''

    if not program in self._cited:
      self._cited.append(program)

    return

  def get_programs(self):
    '''Get a list of all of the programs which have been cited.'''

    result = [c for c in self._cited]
    result.sort()
    return result

  def get_citations(self):
    '''Get a list of bibtex records of citations.'''

    result = []

    for c in self._cited:
      for b in self._citations.get(c, []):
        result.append(b)

    return result

  def get_citations_acta(self):
    '''Return a list of strings of Acta style references.'''

    results = []

    bibtex_list = self.get_citations()

    for bibtex in bibtex_list:
      data = self._parse_bibtex(bibtex)
      if 'pages' in data:
        results.append(
            '%(author)s (%(year)s) %(journal)s %(volume)s, %(pages)s' % \
            data)
      else:
        results.append(
            '%(author)s (%(year)s) %(journal)s %(volume)s' % \
            data)

    # want them in alohabetical order

    results.sort()

    return results

  def _parse_bibtex(self, bibtex):
    '''A jiffy to parse a bibtex entry.'''

    contents = { }

    # default values
    contents['volume'] = ''

    for token in bibtex.split('\n'):
      if '=' in token:
        name, value = tuple(token.split('='))

        # clean up the value...
        value = value.replace('{', '').replace('}', '')
        value = value.replace('"', '')

        value = value.strip()
        if value[-1] == ',':
          value = value[:-1]

        contents[name.strip()] = value

    return contents


Citations = _Citations()

if __name__ == '__main__':
  Citations.cite('labelit')
  Citations.cite('denzo')
  Citations.cite('mosflm')
  Citations.cite('xds')
  Citations.cite('xia2')

  for citation in Citations.get_citations_acta():
    print citation

  print Citations.get_programs()

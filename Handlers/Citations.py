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

from __future__ import absolute_import, division, print_function

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
      citation_data = {}
      for entry in citation.childNodes:
        if entry.nodeType == entry.ELEMENT_NODE:
          citation_data[entry.nodeName] = entry.childNodes[0].data

      if 'acta' not in citation_data:
        # construct Acta style reference if necessary
        citation_data['acta'] = self._bibtex_to_acta(citation_data['bibtex'])

      if 'url' not in citation_data:
        # obtain URL from bibtex entry if possible
        bibtex_data = self._parse_bibtex(citation_data['bibtex'])
        if 'url' in bibtex_data:
          citation_data['url'] = bibtex_data['url']
        elif 'doi' in bibtex_data:
          citation_data['url'] = 'http://dx.doi.org/' + bibtex_data['doi']

      if program not in self._citations:
        self._citations[program] = []
      self._citations[program].append(citation_data)

  def cite(self, program):
    '''Cite a given program.'''

    if program not in self._cited:
      self._cited.append(program)

  def get_programs(self):
    '''Get a list of all of the programs which have been cited.'''
    return sorted(self._cited)

  def get_citations(self):
    '''Get a list of bibtex records of citations.'''

    return [ cit['bibtex'] for cit in self.get_citations_dicts() ]

  def get_citations_dicts(self):
    '''Get a list of citations dictionary objects.'''

    result = []

    for c in self._cited:
      for b in self._citations.get(c, []):
        result.append(b)

    return result

  def get_citations_acta(self):
    '''Return a list of strings of Acta style references.'''

    # want them in alphabetical order
    return sorted([ cit['acta'] for cit in self.get_citations_dicts() ])

  def find_citations(self, program=None, acta=None):
    '''Return a list of citations for a program name or an Acta style reference.'''

    results = []

    if program:
      results.extend(self._citations.get(program, []))

    if acta:
      results.extend(citation \
          for citations in self._citations.itervalues() \
          for citation in citations \
          if citation.get('acta') == acta)

    return results

  def _parse_bibtex(self, bibtex):
    '''A jiffy to parse a bibtex entry.'''

    contents = {}

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

  def _bibtex_to_acta(self, bibtex):
    '''Construct an Acta-like formatted reference from a bibtex entry.'''

    data = self._parse_bibtex(bibtex)
    actaformat = '%(author)s (%(year)s) %(journal)s %(volume)s.'

    # drop every 'and' but the last
    data['author'] = data['author'].replace(' and ', ', ', data['author'].count(' and ')-1)

    if 'pages' in data:
      data['pages'] = data['pages'].replace('--', '-')
      actaformat = '%(author)s (%(year)s) %(journal)s %(volume)s, %(pages)s.'

    return actaformat % data


Citations = _Citations()

if __name__ == '__main__':
  print(Citations.find_citations(program='xia2'))
  print(Citations.find_citations(acta='Winter, G. (2010) J. Appl. Cryst. 43, 186-190.'))

  Citations.cite('labelit')
  Citations.cite('denzo')
  Citations.cite('mosflm')
  Citations.cite('xds')
  Citations.cite('xia2')

  for citation in Citations.get_citations_acta():
    print(citation)

  print(Citations.get_programs())

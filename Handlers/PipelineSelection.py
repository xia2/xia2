#!/usr/bin/env python
# PipelineSelection.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A handler to manage the selection of pipelines through which to run xia2,
# for instance what indexer to use, what integrater and what scaler.
# This will look for a file preferences.xia in ~/.xia2 or equivalent,
# and the current working directory.

import os
import sys

def search_for_preferences():
    '''Search for a preferences file, first in HOME then here.'''

    if os.name == 'nt':
        homedir = os.path.join(os.environ['HOMEDRIVE'],
                               os.environ['HOMEPATH'])
        xia2dir = os.path.join(homedir, 'xia2')
    else:
        homedir = os.environ['HOME']
        xia2dir = os.path.join(homedir, '.xia2')

    preferences = { }

    if os.path.exists(os.path.join(xia2dir, 'preferences.xia')):
        preferences = parse_preferences(
            os.path.join(xia2dir, 'preferences.xia'), preferences)

    # look also in current working directory

    if os.path.exists(os.path.join(os.getcwd(), 'preferences.xia')):
        preferences = parse_preferences(
            os.path.join(os.getcwd(), 'preferences.xia'), preferences)

    return preferences

def parse_preferences(file, preferences):
    '''Parse preferences to the dictionary.'''

    for line in open(file, 'r').readlines():

        # all lower case
        line = line.lower()

        # ignore comment lines    
        if line[0] == '!' or line[0] == '#':
            continue

        preferences[line.split(':')[0]] = line.split(':')[1].split()[0]

    return preferences

if __name__== '__main__':

    print search_for_preferences()

    

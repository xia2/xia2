#!/usr/bin/env python
# xia2.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 21/SEP/06
#
# A top-level interface to the whole of xia2, for data processing & analysis.
# 
# FIXED 28/NOV/06 record the total processing time to Chatter.
#
# FIXME 28/NOV/06 be able to e-mail someone with the job once finished.
#
# FIXME 17/JAN/07 check environment before startup.
# 

import sys
import os
import time
import exceptions
import traceback

sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter
from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from eHTPX.EHTPXXmlHandler import EHTPXXmlHandler
from xia2setup import write_xinfo

def check_environment():
    '''Check the environment we are running in...'''

    version = sys.version_info

    if version[0] < 2:
        raise RuntimeError, 'Python 1.x not supported'

    if version[0] == 2 and version[1] < 4:
        raise RuntimeError, 'Python 2.x before 2.4 not supported'

    xia2_keys = ['XIA2_ROOT', 'XIA2CORE_ROOT']

    ccp4_keys = ['CCP4', 'CLIBD', 'BINSORT_SCR']

    Chatter.write('Environment configuration...')
    for k in xia2_keys:
        if not os.environ.has_key(k):
            raise RuntimeError, '%s not defined - is xia2 set up?'
        if not os.environ[k] == os.environ[k].strip():
            raise RuntimeError, 'spaces around "%s"' % os.environ[k]
        Chatter.write('%s => %s' % (k, os.environ[k]))

    for k in ccp4_keys:
        if not os.environ.has_key(k):
            raise RuntimeError, '%s not defined - is CCP4 set up?'
        if not os.environ[k] == os.environ[k].strip():
            raise RuntimeError, 'spaces around "%s"' % os.environ[k]
        Chatter.write('%s => %s' % (k, os.environ[k]))

    try:
        if os.name == 'nt':
            hostname = os.environ['COMPUTERNAME'].split('.')[0]
        else:
            hostname = os.environ['HOSTNAME'].split('.')[0]

        Chatter.write('Host: %s' % hostname)
    except KeyError, e:
        pass

    return

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

def check():
    '''Check that the set-up is ok...'''

    sys.path.append(os.path.join((os.environ['XIA2CORE_ROOT']),
                                 'Python'))

    from TestPython import test_python_setup
    
    test_python_setup()

    return

def xia2():
    '''Actually process something...'''
    
    # print the version
    Chatter.write(Version)

    start_time = time.time()

    from Handlers.CommandLine import CommandLine
    
    if not CommandLine.get_xinfo():
        # write an xinfo file then
        xinfo = os.path.join(os.getcwd(), 'automatic.xinfo')

        argv = sys.argv[1:]

        path = argv.pop()

        while not os.path.exists(path):
            try:
                path = '%s %s' % (argv.pop(), path)
            except IndexError, e:
                raise RuntimeError, 'directory not found in arguments: %s' % \
                      path

        if not os.path.isabs(path):
            path = os.path.abspath(path)

        # in here check that this is a directory

        if not os.path.isdir(path):
            raise RuntimeError, '%s must be a directory' % path
            
        write_xinfo(xinfo, path)

        CommandLine.set_xinfo(xinfo)

    # check that something useful has been assigned for processing...
    xtals = CommandLine.get_xinfo().get_crystals()

    no_images = True

    for name in xtals.keys():
        xtal = xtals[name]

        if not xtal.get_all_image_names():
            
            Chatter.write('-----------------------------------' + \
                          '-' * len(name))
            Chatter.write('| No images assigned for crystal %s |' % name)
            Chatter.write('-----------------------------------' + '-' \
                          * len(name))
        else:
            no_images = False
    
    # this actually gets the processing started...
    Chatter.write(str(CommandLine.get_xinfo()))

    duration = time.time() - start_time

    # write out the time taken in a human readable way
    Chatter.write('Processing took %s' % \
                  time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

    # delete all of the temporary mtz files...
    cleanup()

    # write out the e-htpx XML, perhaps
    if CommandLine.get_ehtpx_xml_out():
        EHTPXXmlHandler.write_xml(CommandLine.get_ehtpx_xml_out())

    # tell the user which programs were used...
    used = ''
    for program in Citations.get_programs():
        used += ' %s' % program

    Chatter.write('XIA2 used... %s' % used)
    Chatter.write(
        'Here are the appropriate citations (BIBTeX in xia-citations.bib.)')

    for citation in Citations.get_citations_acta():
        Chatter.write(citation)

    # and write the bibtex versions
    out = open('xia-citations.bib', 'w')

    for citation in Citations.get_citations():
        out.write('%s\n' % citation)

    out.close()
    
    return

def help():
    '''Print out some help for xia2.'''

    sys.stdout.write('\nCommand-line options to xia2:\n')
    sys.stdout.write('[-parallel 4] (say, for XDS usage)\n')
    sys.stdout.write('[-resolution 2.8] (say, applies to all sweeps)\n')
    sys.stdout.write('[-ehtpx_xml_out foo.xml]\n')
    sys.stdout.write('[-freer_file free.mtz]\n')
    sys.stdout.write('[-quick]\n')
    sys.stdout.write('[-reversephi]\n')
    sys.stdout.write('[-migrate_data]\n')
    sys.stdout.write('[-2d] or [-3d] or [-3dii]\n')
    sys.stdout.write('[-xinfo foo.xinfo] or [/path/to/images]\n\n')

    sys.stdout.write('Deprecated command-line options to xia2:\n')
    sys.stdout.write('[-lattice mP] (say)\n')
    sys.stdout.write('[-resolution 2.4] (say)\n')
    sys.stdout.write('[-atom se] (say) - this is for xia2setup\n')
    sys.stdout.write('[-project foo] (say) - this is for xia2setup\n')
    sys.stdout.write('[-crystal bar] (say) - this is for xia2setup\n\n')
    
    sys.stdout.write('Develper options - do not use these ...\n')
    sys.stdout.write(
        '[-z_min 50] (minimum Z value for rejecting reflections)\n')
    sys.stdout.write('[-trust_timestamps]\n')
    sys.stdout.write('[-debug]\n')
    sys.stdout.write('[-relax]\n')
    sys.stdout.write('[-zero_dose]\n')
    sys.stdout.write('[-norefine]\n\n')

    sys.stdout.write('Sensible command lines:\n')
    sys.stdout.write('xia2 (-2d|-3d) -xinfo foo.xinfo\n')
    sys.stdout.write('xia2 -project foo -crystal bar (-2d|-3d) /data/path\n')

if __name__ == '__main__':

    try:
        check_environment()
        check()
    except exceptions.Exception, e:
        traceback.print_exc(file = open('xia2.error', 'w'))
        Chatter.write('Error: %s' % str(e))
        Chatter.write('Do you have Python 2.4 installed?')

    if len(sys.argv) < 2 or '-help' in sys.argv:
        help()
        sys.exit()

    try:
        xia2()
        Chatter.write('Status: normal termination')
    except exceptions.Exception, e:
        traceback.print_exc(file = open('xia2.error', 'w'))
        Chatter.write('Status: error "%s"' % str(e))

    

#!/usr/bin/env python
# RegistryHelpers.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Things to help the ImageFormat registry to work.

import os

def InheritsFromFormat(PutativeFormatClass):
    '''Check that the PutativeFormatClass inherits on some level from a class
    named Format. This is aimed at making sure it should play nice with the
    ImageFormat registry etc.'''

    if PutativeFormatClass.__bases__:
        for base in PutativeFormatClass.__bases__:
            if InheritsFromFormat(base):
                return True

    if PutativeFormatClass.__name__ == 'Format':
        return True

    return False

def LookForFormatClasses():
    '''Look for files named Format(something).py in the sensible places (i.e.
    in the xia2 distribution and in the users home area) and return a list of
    paths. N.B. the class names themselves must be unique (otherwise there
    is no hope of importing them!)'''

    assert('XIA2_ROOT' in os.environ)

    format_classes = []
    file_names = []

    xia2_format_dir = os.path.join(os.environ['XIA2_ROOT'], 'Toolkit',
                                   'ImageFormat')

    if os.name == 'nt':
        home = os.path.join(os.environ['HOMEDRIVE'],
                            os.environ['HOMEPATH'])
    else:
        home = os.environ['HOME']

    user_format_dir = os.path.join(home, '.xia2')

    for f in os.listdir(xia2_format_dir):
        if 'Format' in f[:6] and '.py' in f[-3:]:
            assert(not f in file_names)
            file_names.append(f)
            format_classes.append(os.path.join(xia2_format_dir, f))

    if os.path.exists(user_format_dir):
        for f in os.listdir(user_format_dir):
            if 'Format' in f[:6] and '.py' in f[-3:]:
                assert(not f in file_names)
                file_names.append(f)
                format_classes.append(os.path.join(user_format_dir, f))

    return format_classes

if __name__ == '__main__':

    import imp

    for f in LookForFormatClasses():
        print f

        name = os.path.split(f)[-1][:-3]
        path = os.path.split(f)[0]

        m, p, d = imp.find_module(name, [path])

        try:
            print imp.load_module(name, m, p, d)
        except:
            pass
        finally:
            m.close()
            




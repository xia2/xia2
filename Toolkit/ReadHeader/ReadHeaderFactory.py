# how is this going to work?
#
# open file: is SMV? -> delegate to smv parser, then interrogate header to ID
# the format. return
#
# is cbf format (real) -> check header (minicbf, cbf) then look for real cbf
# tokens. return
#
# then check for mar image plate
# then check for raxis image plate
# then check for mar ccd
#
# then that's everyone

def ReadHeaderFactory(image):
    '''Interrogate image, return a ReadHeader implementation suitable for this
    type.'''

    pass

# then helpers

def is_smv(filename):
    # file begins { newline HEADER_BYTES

    pass

def is_marcd(filename):

    pass

def is_smv_adsc(filename):
    pass

def is_smv_rigaku(filename):
    pass

def is_raxis(filename):
    pass

def is_real_cbf(filename):
    pass

def is_mini_cbf(filename):
    pass

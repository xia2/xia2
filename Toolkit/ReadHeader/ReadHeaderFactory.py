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

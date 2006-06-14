#!/bin/csh

# add the test programs to the path

set platform `uname`
if ( "$platform" == "Linux" ) then
  setenv PATH ${PATH}:${DPA_ROOT}/binaries/linux_386
else
  setenv PATH ${PATH}:${DPA_ROOT}/binaries/mac_386
endif

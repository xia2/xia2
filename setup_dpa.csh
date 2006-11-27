#!/bin/csh

# add the test programs to the path

# FIXME this needs to account for mac_ppc

set platform `uname`
if ( "$platform" == "Linux" ) then
  setenv PATH ${PATH}:${DPA_ROOT}/binaries/linux_386
else
  set arch `uname -a | awk '{print $NF}'`
  if ( "$arch" == "powerpc" ) then
    setenv PATH ${PATH}:${DPA_ROOT}/binaries/mac_ppc
  else
    setenv PATH ${PATH}:${DPA_ROOT}/binaries/mac_386
endif

setenv PATH ${PATH}:${DPA_ROOT}/Applications

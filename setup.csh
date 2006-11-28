#!/bin/csh

# add the test programs to the path

# FIXME this needs to account for mac_ppc

setenv platform `uname`
if ( "$platform" == "Linux" ) then
  setenv PATH ${PATH}:${XIA2_ROOT}/binaries/linux_386
else
  setenv arch `uname -a | awk '{print $NF}'`
  if ( "$arch" == "powerpc" ) then
    setenv PATH ${PATH}:${XIA2_ROOT}/binaries/mac_ppc
  else
    setenv PATH ${PATH}:${XIA2_ROOT}/binaries/mac_386
endif

setenv PATH ${PATH}:${XIA2_ROOT}/Applications




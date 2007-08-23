#!/bin/csh

# add the test programs to the path

# FIXME this needs to account for mac_ppc

setenv host_platform `uname`
if ( "$host_platform" == "Linux" ) then
  setenv PATH ${XIA2_ROOT}/binaries/linux_386:${PATH}
else
  setenv arch `uname -a | awk '{print $NF}'`
  if ( "$arch" == "powerpc" ) then
    setenv PATH ${XIA2_ROOT}/binaries/mac_ppc:${PATH}
  else
    setenv PATH ${XIA2_ROOT}/binaries/mac_386:${PATH}
  endif
endif

setenv PATH ${PATH}:${XIA2_ROOT}/Applications
setenv besthome ${XIA2_ROOT}/binaries/best



#!/bin/csh

# add the test programs to the path

# FIXME this needs to account for mac_ppc

setenv host_platform `uname`
if ( "$host_platform" == "Linux" ) then
  setenv PATH ${XIA2_ROOT}/binaries/linux_386:${PATH}
else if ( "$host_platform" == "Darwin" ) then
  setenv arch `uname -a | awk '{print $NF}'`
  if ( "$arch" == "powerpc" ) then
    setenv PATH ${XIA2_ROOT}/binaries/mac_ppc:${PATH}
    setenv DYLD_LIBRARY_PATH ${XIA2_ROOT}/binaries/mac_ppc:${DYLD_LIBRARY_PATH}
  else
    setenv PATH ${XIA2_ROOT}/binaries/mac_386:${PATH}
    setenv DYLD_LIBRARY_PATH ${XIA2_ROOT}/binaries/mac_386:${DYLD_LIBRARY_PATH}
  endif
else
  echo "Platform $host_platform not supported"
endif

setenv PATH ${PATH}:${XIA2_ROOT}/Applications
setenv besthome ${XIA2_ROOT}/binaries/best

setenv GFORTRAN_UNBUFFERED_ALL 1



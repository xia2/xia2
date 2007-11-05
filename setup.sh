#!/bin/bash

# add the test programs to the path

host_platform=`uname`

# FIXME this needs to account for Darwin on 386 & ppc.

if [ "$host_platform" = "Darwin" ]; then
  arch=`uname -a | awk '{print $NF}'`
  if [ "$arch" = "powerpc" ]; then
    export PATH=${XIA2_ROOT}/binaries/mac_ppc:${PATH}
  elif [ "$arch" = "i386" ]; then
    export PATH=${XIA2_ROOT}/binaries/mac_386:${PATH}
    export DYLD_LIBRARY_PATH=${XIA2_ROOT}/binaries/mac_386:${DYLD_LIBRARY_PATH}
  fi
elif [ "$host_platform" = "Linux" ]; then
  export PATH=${XIA2_ROOT}/binaries/linux_386:${PATH}
fi

export PATH=${PATH}:${XIA2_ROOT}/Applications
export besthome=${XIA2_ROOT}/binaries/best



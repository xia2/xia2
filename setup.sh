#!/bin/bash

# add the test programs to the path

platform=`uname`

# FIXME this needs to account for Darwin on 386 & ppc.

if [ "$platform" = "Darwin" ]; then
  arch=`uname -a | awk '{print $NF}'`
  if [ "$arch" = "powerpc" ]; then
    export PATH=${PATH}:${XIA2_ROOT}/binaries/mac_ppc
  elif [ "$arch" = "i386" ]; then
    export PATH=${PATH}:${XIA2_ROOT}/binaries/mac_386  
  fi
elif [ "$platform" = "Linux" ]; then
  export PATH=${PATH}:${XIA2_ROOT}/binaries/linux_386
fi

export PATH=${PATH}:${XIA2_ROOT}/Applications



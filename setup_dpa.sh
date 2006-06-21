#!/bin/bash

# add the test programs to the path

platform=`uname`

if [ "$platform" = "Darwin" ]; then
  export PATH=${PATH}:${DPA_ROOT}/binaries/mac_386
elif [ "$platform" = "Linux" ]; then
  export PATH=${PATH}:${DPA_ROOT}/binaries/linux_386
fi

export PATH=${PATH}:${DPA_ROOT}/Applications



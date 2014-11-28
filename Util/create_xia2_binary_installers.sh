#!/bin/sh
#
# BuildBot (etc.) harvesting for xia2 binary installer.  This assumes that the
# nightly build is complete and ready for packaging.  The first argument,
# BUILD_DIR, should be a directory with the following contents:
#   base/ : Python and friends
#   build/ : compiled libraries and executables
#   modules/ : source code, etc.
#
# The intention is to make this as independent of specific setup at each site,
# but some customization is recommended, e.g. via a thin wrapper script.
#
if [ -z "${XIA2_DEST_DIR}" ]; then
  # XXX This should be defined to wherever installers live, minus version
  XIA2_DEST_DIR=""
fi
if [ -z "${XIA2_DEBUG}" ]; then
  XIA2_DEBUG=0
fi
#
# Stuff below here should be site-independent...
#
XIA2_VERSION=$1
HOST_TAG=$2
if [ -z "$XIA2_VERSION" ]; then
  echo "XIA2_VERSION must be first argument!"
  exit 1
fi
if [ -z "$HOST_TAG" ]; then
  echo "HOST_TAG must be second argument!"
  exit 1
fi
XIA2="`libtbx.find_in_repositories xia2`"
MISC_OPTIONS=""
if [ ! -z "${XIA2_DEST_DIR}" ]; then
  MISC_OPTIONS="--destination=${XIA2_DEST_DIR}"
fi
if [ "${XIA2_DEBUG}" != "0" ]; then
  MISC_OPTIONS="${MISC_OPTIONS} --debug"
fi
libtbx.make_dist \
  --version=${XIA2_VERSION} \
  --host-tag=${HOST_TAG} \
  ${MISC_OPTIONS} \
  ${XIA2}/make_dist.phil
if [ $? -ne 0 ]; then
  echo "Fatal error assembling installer"
  exit 1
fi

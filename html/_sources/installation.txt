++++++++++++
Installation
++++++++++++

The current version, 0.3.8.0 can be obtained by following these links:

* `Windows (as .zip file) <http://www.ccp4.ac.uk/xia/xia2-0.3.8.0.zip>`_
* `Unix (as .tar.bz2 file) <http://www.ccp4.ac.uk/xia/xia2-0.3.8.0.tar.bz2>`_
* `Unix (as .tar.gz file) <http://www.ccp4.ac.uk/xia/xia2-0.3.8.0.tar.gz>`_

All of the files are the same, simply packed for different platforms.

Since everything is Python using cctbx, the only requirement is to export
:samp:`XIA2_ROOT` to point to the directory where xia2 was unpacked
(including the xia2-0.3.6.0 bit) and then
:samp:`source $XIA2_ROOT/setup.(c)sh`.

xia2 depends critically on having CCP4 and CCTBX available. However to
get access to the full functionality you will also need XDS and Phenix (which
includes Labelit and CCTBX.) Therefore for a “standard” xia2 installation I
would recommend:

* Install CCP4 include updated versions of Pointless and Aimless from ftp://ftp.mrc-lmb.cam.ac.uk/pub/pre
* Download XDS from http://xds.mpimf-heidelberg.mpg.de/ and add this to your path [1]_
* Download PHENIX from http://www.phenix-online.org and be sure to source the setup for this after CCP4
* Download xia2 from http://xia2.sf.net and tweak the setup file to reflect where it’s installed

By and large, if these instruction are followed you should end up with a
happy xia2 installation. If you find any problems it’s always worth checking
the blog (http://xia2.blogspot.com) or sending an email to xia2.support@gmail.com.


Experimental xia2/DIALS installers
==================================

We are currently testing new xia2/DIALS installers for mac/linux which provide
a self-contained xia2/cctbx/DIALS installation. Instructions on downloading
and installing these bundles can be found at
http://dials.diamond.ac.uk/doc/installation.html. Once installed, simply
sourcing the dials_env.sh script in the installation directory will make
available all xia2 and DIALS commands in the current terminal. You will also
need CCP4 available - but make sure to source the dials_env.sh script after
the CCP4 setup script. You can also try out the new xia2 -dials option, which
will use the new software DIALS to index and integrate your data, followed by
scaling and merging with Aimless. As always, please send any feedback to
xia2.support@gmail.com.

.. [1] To use :samp:`-xparallel` you will need to fiddle with forkintegrate in the XDS distribution

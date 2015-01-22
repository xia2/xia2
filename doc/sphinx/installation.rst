+++++++++++++++
Installing xia2
+++++++++++++++

xia2 depends critically on having CCP4 and CCTBX available. However to
get access to the full functionality you will also need XDS and Phenix (which
includes Labelit and CCTBX.) Therefore for a “standard” xia2 installation I
would recommend:

* Install CCP4 include updated versions of Pointless and Aimless from ftp://ftp.mrc-lmb.cam.ac.uk/pub/pre
* Download XDS from http://xds.mpimf-heidelberg.mpg.de/ and add this to your path [8]_
* Download PHENIX from http://www.phenix-online.org and be sure to source the setup for this after CCP4
* Download xia2 from http://xia2.sf.net and tweak the setup file to reflect where it’s installed

By and large, if these instruction are followed you should end up with a
happy xia2 installation. If you find any problems it’s always worth checking
the blog (http://xia2.blogspot.com) or sending an email to xia2.support@gmail.com.

.. [8] To use :samp:`-xparallel` you will need to fiddle with forkintegrate in the XDS distribution

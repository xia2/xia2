++++++++++++
Installation
++++++++++++

The recommended way of obtaining the latest xia2 is to install the latest
xia2/DIALS bundle which can be obtained
`here <http://dials.github.io/installation.html>`_.

xia2 depends critically on having CCP4 available. The ``dials`` and ``2d``
pipelines will work with only xia2 and CCP4 installed. In order to use the
``3d``, ``3di`` and ``3dii`` pipelines you will also need XDS. Optionally
xia2 can make use of `LABELIT`_ which requires installation of LABELIT or
`PHENIX`_ (the latter includes the former).

The standard recommended procedure for installing xia2 is therefore:

* Install CCP4 from http://www.ccp4.ac.uk/download/. This now includes xia2/DIALS
  as part of the installation.
* Optionally download the latest xia2/DIALS bundle from http://dials.github.io/installation.html.
  Once installed, simply sourcing the dials_env.sh script in the installation
  directory will make available all xia2 and DIALS commands in the current
  terminal. Make sure to source the dials_env.sh script after the CCP4 setup
  script
* Optionally download XDS from http://xds.mpimf-heidelberg.mpg.de/ and add this to your path [1]_
* Optionally download PHENIX from http://www.phenix-online.org or LABELIT from
  http://cci.lbl.gov/labelit/ and source the relevant setup script

By and large, if these instruction are followed you should end up with a
happy xia2 installation. If you find any problems it’s always worth checking
the `blog`_ or sending an email to xia2.support@gmail.com.


.. [1] To use :samp:`xparallel=True` you will need to fiddle with forkintegrate in the XDS distribution


.. _`DIALS`: http://dials.diamond.ac.uk/
.. _`LABELIT`: http://cci.lbl.gov/labelit/
.. _`PHENIX`: http://www.phenix-online.org/
.. _`blog`: http://xia2.blogspot.com/

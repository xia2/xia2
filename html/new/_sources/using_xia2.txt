++++++++++
Using xia2
++++++++++

As mentioned in the :doc:`quick start guide </quick_start>`, to get started simply run::

  xia2 -2d /here/are/my/images

or::

  xia2 -3d /here/are/my/images

or::

  xia2 -dials /here/are/my/images

The program is used from the command-line; there is no GUI. The four
most important command-line options are as follows:

  =======  =====
  Option   Usage
  =======  =====
  -atom X  tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling
  -2d      tell xia2 to use MOSFLM_ and Aimless_
  -3d      tell xia2 to use XDS_ and XSCALE_
  -3dii    tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images
  -dials   tell xia2 to use DIALS_ and Aimless_
  =======  =====

These specify in the broadest possible terms to the program the manner
in which you would like the processing performed. The program will then
read all of the image headers found in :samp:`/here/are/my/data` to organise the
data, first into sweeps, then into wavelengths, before assigning all of these
wavelengths to a crystal.

The data from the experiment is understood as follows. The SWEEP,
which corresponds to one "scan", is the basic unit of indexing and integration.
These are contained by WAVELENGTH objects which correspond to
CCP4 MTZ datasets, and will ultimately have unique Miller indices. For
example, a low and high dose pass will be merged together. A CRYSTAL
however contains all of the data from the experiment and is the basic unit of
data for scaling. This description of the experiment is written automatically
to an instruction file, an example of which is shown in below::

  BEGIN PROJECT AUTOMATIC
  BEGIN CRYSTAL DEFAULT

  BEGIN HA_INFO
  ATOM Ba
  END HA_INFO

  BEGIN WAVELENGTH SAD
  WAVELENGTH 0.979500
  END WAVELENGTH SAD

  BEGIN SWEEP SWEEP1
  WAVELENGTH SAD
  DIRECTORY /dls/i02/data/2011/mx1234-5
  IMAGE K5_M1S3_3_001.img
  START_END 1 450
  END SWEEP SWEEP1

  END CRYSTAL DEFAULT
  END PROJECT AUTOMATIC

The input file to the program, which is generated automatically,
shows how the input data are understood. This may be adjusted and the
program rerun, which will be covered in more detail later in the manual.

.. _MOSFLM: http://www.mrc-lmb.cam.ac.uk/harry/mosflm/
.. _DIALS: http://dials.sourceforge.net/
.. _XDS: http://xds.mpimf-heidelberg.mpg.de/
.. _XSCALE: http://xds.mpimf-heidelberg.mpg.de/html_doc/xscale_program.html
.. _aimless: http://www.ccp4.ac.uk/html/aimless.html

+++++++++++++++++
Quick start guide
+++++++++++++++++

If you don’t like reading manuals and just want to get started, try::

  xia2 -dials /here/are/my/images

or::

  xia2 -2d /here/are/my/images

or::

  xia2 -3d /here/are/my/images

(remembering of course -atom X if you want anomalous pairs separating
in scaling.) If this appears to do something sensible then you may well be
home and dry. Some critical options:

  =======  =====
  Option   Usage
  =======  =====
  -atom X  tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling
  -dials   tell xia2 to use DIALS_ and Aimless_
  -2d      tell xia2 to use MOSFLM_ and Aimless_
  -3d      tell xia2 to use XDS_ and XSCALE_
  -3dii    tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images
  =======  =====

If this doesn’t hit the spot, you’ll need to read the rest of the documentation.


.. _MOSFLM: http://www.mrc-lmb.cam.ac.uk/harry/mosflm/
.. _DIALS: http://dials.sourceforge.net/
.. _XDS: http://xds.mpimf-heidelberg.mpg.de/
.. _XSCALE: http://xds.mpimf-heidelberg.mpg.de/html_doc/xscale_program.html
.. _aimless: http://www.ccp4.ac.uk/html/aimless.html

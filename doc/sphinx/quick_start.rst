+++++++++++++++++
Quick start guide
+++++++++++++++++

If you don’t like reading manuals and just want to get started, try::

  xia2 pipeline=dials /here/are/my/images

or::

  xia2 pipeline=3d /here/are/my/images

(remembering of course atom=X if you want anomalous pairs separating
in scaling.) If this appears to do something sensible then you may well be
home and dry. Some critical options:

  ======================= =====
  Option                  Usage
  ======================= =====
  atom= X                 tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling
  pipeline=dials          tell xia2 to use DIALS_
  pipeline=dials-aimless  tell xia2 to use DIALS_ and Aimless_
  pipeline=3d             tell xia2 to use XDS_ and XSCALE_
  pipeline=3dii           tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images
  ======================= =====

If this doesn’t hit the spot, you’ll need to read the rest of the documentation.


.. _DIALS: http://dials.github.io/
.. _XDS: http://xds.mpimf-heidelberg.mpg.de/
.. _XSCALE: http://xds.mpimf-heidelberg.mpg.de/html_doc/xscale_program.html
.. _aimless: http://www.ccp4.ac.uk/html/aimless.html

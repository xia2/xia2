+++++++++++++++
Parameters
+++++++++++++++

Commonly used program options
-----------------------------

There are a number of program options used on a daily basis in xia2, which
are:

  ============================ ==============

  atom=X                       tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling
  pipeline=2d                  tell xia2 to use MOSFLM_ and Aimless_
  pipeline=3d                  tell xia2 to use XDS_ and XSCALE_
  pipeline=3dii                tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images
  pipeline=dials               tell xia2 to use DIALS_ and Aimless_
  xinfo=some.xinfo             modified.xinfo use specific input file
  image=/path/to/an/image.img  process specific scan
  small_molecule=true          process in manner more suited to small molecule data
  space_group=sg               set the spacegroup, e.g. P21
  unit_cell=a,b,c,α,β,γ        set the cell constants
  ============================ ==============

Resolution limits
-----------------

The subject of resolution limits is one often raised - by default in xia2 they
are:

  * :math:`CC_{\frac{1}{2}} > 0.5`
  * Merged :math:`\frac{I}{\sigma_I} > 1`
  * Unmerged :math:`\frac{I}{\sigma_I} > 0.25`

However you can override these with :samp:`cc_half=...`, :samp:`misigma=...`, :samp:`isigma=...`

Phil parameters
---------------


.. note::
  We have now moved towards moving `PHIL (Python-based Hierarchial Interchange Language)`_
  for specifying xia2 program parameters,
  which will in the long run help the documentation, but in the mean time you may see some
  warnings as certain parameters were changed from :samp:`-param` style parameters to
  :samp:`param=` style PHIL parameters. If you see, e.g.:

    :samp:`Warning: -spacegroup option deprecated: please use space_group='P422' instead`

    :samp:`Warning: -resolution option deprecated: please use d_min=1.5 instead`

    :samp:`Command line option -3d is deprecated. Please use pipeline=3d instead`

  don't panic - this is to be expected - but you may want to change the way you run xia2
  or your scripts. More of a warning for beamline / automation people! The outcome of this
  should however be automated generation of command-line documentation and the ability to
  keep "recipes" for running xia2 in tidy files.

Here is a comprehensive list of PHIL parameters used by xia2:

.. phil:: xia2.Handlers.Phil.master_phil
   :expert-level: 0
   :attributes-level: 0


.. _PHIL (Python-based Hierarchial Interchange Language): http://cctbx.sourceforge.net/libtbx_phil.html
.. _MOSFLM: http://www.mrc-lmb.cam.ac.uk/harry/mosflm/
.. _DIALS: http://dials.github.io/
.. _XDS: http://xds.mpimf-heidelberg.mpg.de/
.. _XSCALE: http://xds.mpimf-heidelberg.mpg.de/html_doc/xscale_program.html
.. _aimless: http://www.ccp4.ac.uk/html/aimless.html

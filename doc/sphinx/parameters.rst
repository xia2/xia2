+++++++++++++++
Parameters
+++++++++++++++

Commonly used program options
-----------------------------

There are a number of program options used on a daily basis in xia2, which
are:

  =========================================  ==============
  ``atom=X``                                 Tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling.
  ``pipeline=2d``                            Tell xia2 to use MOSFLM_ and Aimless_.
  ``pipeline=3d``                            Tell xia2 to use XDS_ and XSCALE_.
  ``pipeline=3dii``                          Tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images.
  ``pipeline=dials``                         Tell xia2 to use DIALS_ and Aimless_.
  ``xinfo=some.xinfo``                       Use specific modified .xinfo input file.
  ``image=/path/to/an/image.img``            Process a specific scan.  Pass multiple ``image=`` parameters to include multiple scans.
  ``image=/path/to/an/image.img:start:end``  Process a specific image range within a scan.  ``start`` and ``end`` are numbers denoting the image range, e.g. ``image=/path/to/an/image.img:1:100`` processes images 1–100 inclusive.  As above, one can pass multiple ``image=`` parameters.
  ``small_molecule=true``                    Process in manner more suited to small molecule data.
  ``space_group=sg``                         Set the spacegroup, e.g. ``P21``.
  ``unit_cell=a,b,c,α,β,γ``                  Set the cell constants.
  =========================================  ==============

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

+++++++++++++++
Parameters
+++++++++++++++

Commonly used program options
-----------------------------

There are a number of program options used on a daily basis in xia2, which
are:

  =========================================  ==============
  ``atom=X``                                 Tell xia2 to separate anomalous pairs i.e. I(+) :math:`\neq` I(−) in scaling.
  ``pipeline=3d``                            Tell xia2 to use XDS_ and XSCALE_.
  ``pipeline=3dii``                          Tell xia2 to use XDS_ and XSCALE_, indexing with peaks found from all images.
  ``pipeline=dials``                         Tell xia2 to use DIALS_.
  ``pipeline=dials-aimless``                 Tell xia2 to use DIALS_ but scale with Aimless_.
  ``xinfo=some.xinfo``                       Use specific modified .xinfo input file.
  ``image=/path/to/an/image.img``            Process a specific scan.  Pass multiple ``image=`` parameters to include multiple scans.
  ``image=/path/to/an/image.img:start:end``  Process a specific image range within a scan.  ``start`` and ``end`` are numbers denoting the image range, e.g. ``image=/path/to/an/image.img:1:100`` processes images 1–100 inclusive.  As above, one can pass multiple ``image=`` parameters.
  ``small_molecule=true``                    Process in manner more suited to small molecule data.
  ``space_group=sg``                         Set the spacegroup, e.g. ``P21``.
  ``unit_cell=a,b,c,α,β,γ``                  Set the cell constants.
  =========================================  ==============

Resolution limits
-----------------

xia2 uses ``dials.estimate_resolution`` to estimate the resolution limit, sharing the
same parameters and defaults.
The default behaviour (``cc_half=0.3``) can be overridden with e.g.:

.. code-block:: bash

    xia2 [options] cc_half=None misigma=1 isigma=0.25

See the dials.estimate_resolution_ documentation for further details.

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
.. _DIALS: http://dials.github.io/
.. _XDS: http://xds.mpimf-heidelberg.mpg.de/
.. _XSCALE: http://xds.mpimf-heidelberg.mpg.de/html_doc/xscale_program.html
.. _aimless: http://www.ccp4.ac.uk/html/aimless.html
.. _dials.estimate_resolution: https://dials.github.io/documentation/programs/dials_estimate_resolution.html
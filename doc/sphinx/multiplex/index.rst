++++++++++++++++++++++++++++++++++++++++++++++++
Multi-crystal data reduction with xia2.multiplex
++++++++++++++++++++++++++++++++++++++++++++++++

xia2.multiplex is a DIALS-based data reduction pipeline for combining integrated data from hundreds of
small-wedge rotation datasets. The input to the pipeline is DIALS integrated datafiles
(i.e. ``integrated.expt`` and ``integrated.refl`` files). As of DIALS version 3.25, XDS integrated data can also
be processed if each ``INTEGRATE.HKL`` file is converted using ``dials.import_xds``.

xia2.multiplex performs the following routine: unit cell filtering, Laue group analysis, unit cell
refinement, scaling, resolution analysis, space group analysis and merging. Additional non-isomorphism analysis is performed and
dataset statistics and clustering are presented in the ``xia2.multiplex.html`` report.
For full details, see the publication at https://doi.org/10.1107/S2059798322004399 .

Although xia2.multiplex will automatically determine the resolution and space group, these can be manually overridden by setting the options
``resolution.d_min`` and ``symmetry.space_group``.

One feature of xia2.multiplex is the ability to optionally trigger further processing of subsets of the data. 
This guide provides an updated description of the different clustering options, which have been updated to use more intuitively named
options in xia2/DIALS versions greater than 3.22, as well as incorporating some additional features developed since this initial publication.

Tutorials for ``xia2.multiplex``:

.. toctree::
   :maxdepth: 1

   basic_usage
   intensity_based_clustering
   custom_clustering_via_html
   multiplex_filtering
   chemical_crystallography_multiplex
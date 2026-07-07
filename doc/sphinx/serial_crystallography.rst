**********************************************************************
Processing serial synchrotron crystallography (SSX) datasets with xia2
**********************************************************************

xia2 is able to processes serial synchrotron data through a SSX
pipeline built upon data analysis programs from DIALS, using the xia2.ssx
pipeline.

To process serial data from images to a merged MTZ file, the
minimal recommended example command is::

    xia2.ssx image=../lyso_1.nxs space_group=P43212 \
      unit_cell=79.1,79.1,38.2,90,90,90

i.e. the minimal required information is the location of the images, the expected
space group and unit cell.
For large datasets, quick scaling can be achieved by providing a reference file
containing a reference set of intensities or pdb model (:samp:`.mtz, .cif, .pdb`).
For full processing, it is recommended that data is scaled without reference intensities
or pdb model.
Typically, a reference geometry and mask should also be provided, as described below.

======================================================
Table of contents of xia2.ssx processing documentation
======================================================

| :ref:`DataIntegration`
| :ref:`DataReduction`
| :ref:`GeometryRefinement`
| :ref:`MergingInGroups`
| :ref:`ExportingUnmerged`


.. _DataIntegration:

================
Data Integration
================
To integrate data, the images must be provided, plus the space group to use for
processing and an estimate of the unit cell.
If the space group or unit cell are not known, the pipeline can be initially
run without these; spotfinding and indexing will be performed, and the most
populous unit cell clusters will be presented to the user.

The location of the image data must be specified by using one of the options
:samp:`image=`, :samp:`template=` or :samp:`directory=` (multiple instances of
one option is allowed). Here :samp:`image` corresponds to an image file
(e.g. :samp:`.cbf` or :samp:`.h5/.nxs`), :samp:`template` is a file template for a
sequence of images (e.g. for files :samp:`lyso_1_001.cbf` to :samp:`lyso_1_900.cbf`, the matching
template is :samp:`lyso_1_###.cbf`), and :samp:`directory` is a path to a
directory containing image files.
For data in h5 format, the option :samp:`image=/path/to/image_master.h5` is recommended.
For single-file-per-image formats (e.g. cbf), the file template option is recommended, e.g.::

    xia2.ssx template=../lyso_1_###.cbf space_group=P43212 \
      unit_cell=79.1,79.1,38.2,90,90,90

The overall sequence of the data integration part of the pipeline is as follows.
In the absence of an explicitly provided reference geometry, spotfinding and
indexing will be run on batches of 1000 images at a time, until a threshold number
of crystals have been indexed (250 by default, as specified by the
:samp:`geometry_refinement.n_crystals` parameter). Then joint refinement of the
detector geometry is run to determine an improved geometry model. Following this,
the refined geometry is used to perform spotfinding, indexing and integration of
all images, with feedback provided on batches of 1000 images at a time. This batch
size can be adjusted with the :samp:`batch_size` parameter. The number of available
processes will be determined automatically (optionally a value for :samp:`nproc` can be given),
and parallel processing will be performed within the batch.

A DIALS reference geometry file (:samp:`refined.expt`) can be provided as input
with the option :samp:`reference_geometry=`, which will be used instead of
performing a joint refinement on the data. A mask file created from the DIALS
image viewer can also be provided with the option :samp:`mask=`, which will be
used in spotfinding and integration. A few other common options to set are the
:samp:`max_lattices` parameter, which determines the number of lattices to search
for on each image in indexing, and :samp:`d_min` which controls the resolution
limit for spotfinding and integration.

To see the full list of options and their descriptions, run :samp:`xia2.ssx -ce2 -a1`.
Change the number after :samp:`-ce` to a value from 0 to 3 to see different
"expert levels" of program parameters. Note that a phil options file can be
provided for each of the DIALS programs, to allow further customisation of the
options for the individual programs. Additionally, stepwise processing can be
performed by running the program multiple times with the option :samp:`steps=find_spots`,
then :samp:`steps=index` and finally :samp:`steps=integrate`.

.. _DataReduction:

==============
Data Reduction
==============
Following data integration, data reduction (reindexing, scaling and merging) will
be performed. The data reduction can be run separately to the full pipeline through
the command :samp:`xia2.ssx_reduce`, taking integrated data as input, e.g.::

    xia2.ssx_reduce ../xia2_ssx/batch_*/integrated*.{expt,refl}

To run only the data integration without reduction, use the option
:samp:`steps=find_spots+index+integrate` (i.e. omit :samp:`+reduce`) when running :samp:`xia2.ssx`.

The data reduction process consists of unit cell filtering, followed by indexing
ambiguity resolution in batches (if ambiguities are possible due to lattice
and space group symmetries), followed by scaling and merging. The output are typically two
merged MTZ files - one cut at the estimated resolution limit of the data and one containing
all data to the full resolution limit of the detector.

-----------------------------------
Scaling with or without a reference
-----------------------------------
For scaling, there is a distinction in the workflow depending on if a reference is used.
Using a reference enables quicker parallel scaling, which is beneficial for quick feedback when
datasets are large, however this could introduce bias. Scaling without a reference is
recommended for the final processing.

If a reference dataset/PDB model is provided with the option :samp:`reference=`, then reindexing and scaling is performed
in parallel in batches of at least :samp:`reduction_batch_size` crystals, using intensities
extracted/generated from the reference as a reference when reindexing and scaling.
If using a reference for quick scaling of large datasets, it is recommended to use a
high-quality reference set of intensities in preference to genering
a set of intensities from a PDB model, to give a higher accuracy. If generating intensities
from a PDB model, the default bulk solvent parameters (:samp:`k_sol` and :samp:`b_sol`) should
be adjusted to suitable values.

-----------------------------
Indexing ambiguity resolution
-----------------------------

-----------------
Important options
-----------------
- :samp:`anomalous=True/False`: if True, anomalous pairs are separated in scaling.
- :samp:`d_min`: The resolution limit to apply to the data in scaling. A single MTZ file will be produced to this resolution. If omitted, a resolution limit will be estimated at the point of merging.
- :samp:`deltacchalf=True/False`: if True, ΔCC1/2 filtering will be performed as part of scaling, to remove the crystals with worst agreement with the rest of the dataset.

The xia2.ssx.log file will indicate whether indexing ambiguity resolution was triggered.
This can be triggered based on symmetry or if cell parameters are close such that axes could
be mislabelled.
To evaluate the success of indexing ambiguity resolution, it is important to inspect
the html output from dials.cosym jobs in the :samp:`data_reduction\\reindex` folder.
To see the full list of data reduction parameters and their descriptions,
run :samp:`xia2.ssx_reduce -ce3 -a2`.

---------------------------------
Quick remerging of processed data
---------------------------------
``xia2.ssx_reduce`` also supports quick remerging of already processed data by using the option
``steps=merge``. This can be useful for aggregating multiple processing jobs processed
using the same reference model, or generating MTZ files with specified resolution
cutoffs e.g.::

    xia2.ssx_reduce ../xia2_ssx_reduce/DataFiles/scaled*.{expt,refl} steps=merge d_min=1.8

    xia2.ssx_reduce steps=merge ../{chip1,chip2}/DataFiles/scaled*.{expt,refl}

.. _GeometryRefinement:

==============================================
Overcoming difficulties in geometry refinement
==============================================
The first step of processing with :samp:`xia2.ssx` is to improve the detector geometry in order to
improve the indexing rate. The starting assumption is that the initial geometry is good enough to
successfully index a fraction of the images. When this is not the case, it will be necessary to
change some of the program parameters. Examples and suggestions of how to tackle trickier
processing cases are described in the link below.

.. toctree::
  Overcoming problems with the detector geometry <xia2-ssx-geometry-refinement>


.. _MergingInGroups:

=================
Merging in groups
=================

``xia2.ssx_reduce`` also supports merging in groups to handle more complex experiments such
as dose series experiments. This is described in more detail in the links below.

.. toctree::
  Dose-series experiments and merging in groups <xia2-ssx-dose-series>

.. _ExportingUnmerged:

=======================
Exporting unmerged data
=======================

Merged data (in MTZ format) is the standard output of ``xia2.ssx``, however unmerged scaled data files
(in mmCIF format) can be generated using the tools from DIALS (note that this requires a
DIALS version later than v3.20).

If data were reduced with a reference, there may be more than one set of scaled reflection and experiment files.
In this case, these must first be combined with ``dials.combine_experiments``, before using ``dials.export`` to
export to mmcif format::

    dials.combine_experiments data_reduction/scale/scaled*.{expt,refl}
    dials.export combined.* format=mmcif

If data were not reduced with a reference, then one can just use ``dials.export``::

    dials.export data_reduction/scale/scaled.{expt,refl} format=mmcif

mmCIF is a standardised format that is able to describe unmerged diffraction data, and the output scaled.cif file conforms to the v5
standard https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Index/. Note that during export to mmcif, the overall scale of the data
can change to avoid large negative intensity values, which may be present (with comparably large sigmas) for data scaled against a reference.
The unmerged mmcif data file can be understood with the gemmi program. For example, it can be converted to unmerged MTZ with gemmi and sorted with CCP4's sortmtz for
further analysis::

    gemmi cif2mtz scaled.cif scaled.mtz
    echo H K L M/ISYM |sortmtz HKLIN scaled HKLOUT sorted

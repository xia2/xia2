++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Processing serial synchrotron crystallography (SSX) datasets with xia2
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

xia2 is able to processes serial synchrotron data through a SSX
pipeline built upon data analysis programs from DIALS.

To process serial data from images to a merged MTZ file, the
minimal recommended example command is::

    xia2.ssx template=../lyso_1_###.cbf space_group=P43212 \
      unit_cell=79.1,79.1,38.2,90,90,90  model=../lyso.pdb

i.e. the minimal required information is the location of the images, the expected
space group and unit cell. A suitable pdb model file is also recommended to enable
data reduction using a reference. Typically, a reference geometry and mask should
also be provided, as described below.



----------------
Data Integration
----------------
To integrate data, the images must be provided, plus the space group to use for
processing and an estimate of the unit cell.
If the space group or unit cell are not known, the pipeline can be initially
run without these; spotfinding and indexing will be performed, and the most
populous unit cell clusters will be presented to the user.

The location of the image data must be specified by using one of the options
:samp:`image=`, :samp:`template=` or :samp:`directory=` (multiple instances of
one option is allowed). Here :samp:`image` corresponds to an image file
(e.g. :samp:`.cbf` or :samp:`.h5`), :samp:`template` is a file template for a
sequence of images (e.g. for files :samp:`lyso_1_001.cbf` to :samp:`lyso_1_900.cbf`, the matching
template is :samp:`lyso_1_###.cbf`), and :samp:`directory` is a path to a
directory containing image files.
For data in h5 format, the option :samp:`image=/path/to/image_master.h5` is recommended.
For cbf data, the file template option is recommended, e.g.::

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

--------------
Data Reduction
--------------
Following data integration, data reduction (reindexing, scaling and merging) will
be performed. The data reduction can be run separately to the full pipeline through
the command :samp:`xia2.ssx_reduce`, taking integrated data as input, e.g.::

    xia2.ssx_reduce ../xia2_ssx/batch_*/integrated*.{expt,refl}

To run only the data integration without reduction, use the option
:samp:`steps=find_spots+index+integrate` (i.e. omit :samp:`+reduce`) when running :samp:`xia2.ssx`.

The data reduction process consists of unit cell filtering, followed by indexing
ambiguity resolution in batches (if ambiguities are possible due to lattice
and space group symmetries), followed by scaling and merging. If a reference dataset/PDB model is
provided with the option :samp:`reference=`, then reindexing and scaling is performed
in parallel in batches of at least :samp:`reduction_batch_size` crystals, using intensities
generated from the reference as a reference when reindexing and scaling.
If there is no reference given, the scaling is not performed in parallel. Other important
options are setting :samp:`anomalous=True/False` and specifying a :samp:`d_min` value.
To evaluate the success of indexing ambiguity resolution, it is important to inspect
the html output from dials.cosym jobs in the :samp:`data_reduction\\reindex` folder.
To see the full list of data reduction parameters and their descriptions,
run :samp:`xia2.ssx_reduce -ce3 -a2`. The output of the data reduction pipeline
is a merged MTZ file which can be taken onwards for structure determination.

``xia2.ssx_reduce`` also supports quick remerging of already processed data by using the option
``steps=merge``. This can be useful for aggregating multiple processing jobs processed
using the same reference model, or generating MTZ files with specified resolution
cutoffs e.g.::

    xia2.ssx_reduce ../xia2_ssx_reduce/DataFiles/scaled*.{expt,refl} steps=merge d_min=1.8

    xia2.ssx_reduce steps=merge ../{chip1,chip2}/DataFiles/scaled*.{expt,refl}

-----------------
Merging in groups
-----------------

``xia2.ssx_reduce`` also supports merging in groups to handle more complex experiments such
as dose series experiments. This is described in more detail in the links below.

.. toctree::
  Dose-series experiments and merging in groups <xia2-ssx-dose-series>

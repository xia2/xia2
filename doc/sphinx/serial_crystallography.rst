++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Processing serial synchrotron crystallography (SSX) datasets with xia2
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

xia2 is able to processes serial synchrotron data through a developmental SSX
pipeline built upon data analysis programs/APIs from DIALS.

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

    dev.xia2.ssx space_group=P43212 unit_cell=79.1.79.1,38.2,90,90,90 template=../lyso_1_###.cbf

The overall sequence of the data integration part of the pipeline is as follows.
First spotfinding, indexing and joint refinement are run on the first 1000 images,
in order to determine an improved geometry model for the detector. Following this,
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
:samp:`max_lattices` parameter, which determines the number of lattice to search
for on each image in indexing, and :samp:`d_min` which controls the resolution
limit for spotfinding and integration.

To see the full list of options and their descriptions, run :samp:`dev.xia2.ssx -ce2 -a1`.
Change the number after :samp:`-ce` to a value from 0 to 3 to see different
"expert levels" of program parameters. Note that a phil options file can be
provided for each of the DIALS programs, to allow further customisation of the
options for the individual programs. Additionally, stepwise processing can be
performed by running the program multiple times with the option steps=find_spots,
then steps=index and finally steps=integrate.

--------------
Data Reduction
--------------

Coming soon...

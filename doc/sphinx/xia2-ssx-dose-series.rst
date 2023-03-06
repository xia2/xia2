++++++++++++++++++++++++++++++++++++
Merging SSX data in groups with xia2
++++++++++++++++++++++++++++++++++++

The default behaviour of ``xia2.ssx`` / ``xia2.ssx_reduce`` is to merge all data into one
merged MTZ file. However there are options to produce separate merged datasets based on
metadata, which can be used for experiments such as dose series experiments.
The most efficient way to process such data in xia2/DIALS is to integrate the data as
standard and then use the features available in ``xia2.ssx_reduce`` to split the images
at the point of merging.

---------------------------------------------
Dose series - the *dose_series_repeat* option
---------------------------------------------
For dose series data, the option ``dose_series_repeat=`` can be used to trigger merging into
*n* groups based on the image number, e.g.::

    xia2.ssx_reduce ../xia2-ssx/batch_*/integrated*.{expt,refl} dose_series_repeat=5

This covers the use case of an experiment where a repeat of *n* measurements are
made at each location, before moving to the next location and repeating, thus creating a 
dataset where each block of *n* images form a dose series for a particular location/crystal
(and the images are stored sequentially in this manner).
Before merging, the image filepaths from the experiment files are inspected, and the experiments
split accordingly based on their image index from the filepath (the
formula for splitting is ``image-index modulo repeat = dose``).
For ``dose_series_repeat=5``, the following directory structure would be created for the merging::

    - data_reduction
        - merge
            - dose_1
            - dose_2
            - dose_3
            - dose_4
            - dose_5

with each ``dose`` folder containing a merged MTZ, the dials.merge output, as well as experiment
and reflection files for the images for that particular dose. The experiment and reflection files
can be used as input for subsequent merging jobs, for example with a specified resolution cutoff::

    xia2.ssx_reduce steps=merge ../reduce/data_reduction/merge/dose_1/group*.{expt,refl} d_min=2.5

The experiment files can also be used to verify which images were split into which dose group.

-----------------------------------------
Dose series - using a *grouping.yml* file
-----------------------------------------

``xia2.ssx`` also supports more generalised merging, to support the wide variety of experiments possible
in serial crystallography, which can be specified using a YAML file with formalised definitions. An 
equivalent example to the above case is the example yaml file::

    metadata:
      dose_point:                                      ## <- user-defined metadata name
        "path/to/example/image.h5" : "repeat=5"        ## <- the format here is image-file : value
    grouping:
      merge_by:                                        ## <- indicator to xia2 that the following definitions are for merging
        values:
          - dose_point                                 ## <- reference to the user-defined metadata name above

In the grouping section, the specification is that the ``dose_point`` metadata item should be used for grouping.
The metadata section specifies how the metadata is related to the image file, in this case a sequence
that repeats every 5 images.
To use this form of specifying the groupings, if the above were contained in the file ``grouping.yml``,
the command would be::

    xia2.ssx_reduce ../xia2-ssx/batch_*/integrated*.{expt,refl} grouping=grouping.yml

Note that for grouping images with a file template, the general image template should be provided, with hashes
replacing the image numbers, e.g. the 'image-file' specified in the YAML file would be "path/to/example/image\_#####.cbf".

The resulting directory structure is similar to above, with each grouping merged in a separate subfolder::

    - data_reduction
        - merge
            - group_1
            - group_2
            - group_3
            - group_4
            - group_5

--------------------------------------
Generalised merge grouping on metadata
--------------------------------------

By formally defining the merge groupings with YAML file, one can generalise to more complicated
groupings and options. An example use case is data in HDF5 format with a metadata array which can
be used for grouping. The example below demonstates a few valid ways of specifying metadata::

    metadata:
      dose:                                     
        "path/to/example/image1.h5" : "path/to/example/image1.h5:/entry/dose" ## <- format is image-file: file:/path/to/metadata/array
        "path/to/example/image2.h5" : "meta2.h5:/entry/dose"                  ## <- metadata array does not need to be in the image file
        "path/to/example/image3.h5" : 0.0                                     ## <- all images at a dose value of 0.
    grouping:
      merge_by:                                       
        values:
          - dose
        tolerances:
          - 0.1

Note that for prcoessing a dataset containing images from multiple files, each file must have valid definition
in the metadata section. The metadata for image1 is an array from the image file, however there
is not a strict requirement for the metadata to be contained in the image file. As shown in the
definition for image2, the metadata can be contained in a separate H5 file, the only requirement is
that the length of the metadata array matches the number of images. The definition for image3 shows a
case where the metadata is a constant value for that image file. Although not shown in this example,
it is also possible to group by more than one metadata value, if they are specified in the values and
metadata sections.

The more formalised definition of merge groupings is intended to support integration into automated
processing infrastructure: experiment control software can write metadata into the image files and generate
the ``grouping.yml`` to be input to ``xia2.ssx`` to correctly group the data in merging. It also facilities
the integration of custom classification of images for merging into processing scripts.

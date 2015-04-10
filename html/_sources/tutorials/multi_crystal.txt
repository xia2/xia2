===========================
xia2 multi-crystal tutorial
===========================

In this tutorial we are going to process several 5° wedges of thermolysin
data, taken from multiple crystals, first using xia2 to process the images
using the XDS pipeline, and then use BLEND_ on the resulting processed
reflection files to analyse the datasets for non-isomorphism.

First we need to type several commands in order to make available all the
software we need for the tutorial::

  # make XDS available
  module load XDS

  # get the latest version of CCP4
  module load ccp4

  # get latest combined DIALS/xia2
  module load dials/dev-228

  # needed by BLEND
  module load R

Next we have the xia2 command to run. Below we explain in detail the meaning
of each parameter::

  xia2 -3dii -failover \
    mode=parallel njob=4 nproc=1 \
    trust_beam_centre=True read_all_image_headers=False \
    unit_cell="92.73  92.73 128.13  90.00  90.00 120.00" \
    space_group=P6122 -atom X \
    /dls/mx-scratch/mx_bag_training/thermolysin/

This command will run all the processing on a single computer. Assuming the
computer has 4 processors available, we have set ``njob=4``. If the computer we
are using has more processors available, we may increase either ``njob`` or
``nproc``, whilst ensuring that ``nproc x njob`` is less than or equal to the
total number of processors available. Alternatively,
we can take advantage of the cluster to process our data more quickly, by
using the xia2 parameter ``type=qsub``, which tells xia2 to submit individual
jobs to the cluster using the ``qsub`` command. Since we are using the cluster,
and not a single computer, we can increase the ``nproc`` parameter, e.g. to
``nproc=12`` which will now use 12 processors per sweep. We can also increase
``njob=20`` to process all 20 sweeps simultaneously. We also need to add an
extra ``module load global/cluster`` command to make the cluster available::

  module load global/cluster
  module load XDS
  module load ccp4
  module load dials/dev-228

  xia2 -3dii -failover \
    mode=parallel njob=20 nproc=12 type=qsub\
    trust_beam_centre=True read_all_image_headers=False \
    unit_cell="92.73  92.73 128.13  90.00  90.00 120.00" \
    space_group=P6122 -atom X \
    /dls/mx-scratch/mx_bag_training/thermolysin/

+----------------------------------+-------------------------------------------+
| Parameter                        |  Description                              |
+==================================+===========================================+
| ``-3dii``                        | Use the 3D (XDS) pipeline, using all      |
|                                  | images in indexing                        |
+----------------------------------+-------------------------------------------+
| ``-failover``                    | If processing fails for any sweeps,       |
|                                  | ignore and just use those sweeps that     |
|                                  | processed successfully                    |
+----------------------------------+-------------------------------------------+
| ``mode=parallel``                | Process multiple sweeps in parallel,      |
|                                  | rather than serially                      |
+----------------------------------+-------------------------------------------+
| ``njob=4``                       | In conjunction with mode=parallel,        |
|                                  | process 4 sweeps simultaneously           |
+----------------------------------+-------------------------------------------+
| ``nproc=1``                      | Use 1 processor per job (sweep)           |
+----------------------------------+-------------------------------------------+
| ``type=qsub``                    | Submit individual processing jobs to      |
|                                  | cluster using qsub                        |
+----------------------------------+-------------------------------------------+
| ``trust_beam_centre=True``       | Don't run labelit beam centre search      |
+----------------------------------+-------------------------------------------+
| ``read_all_image_headers=False`` | Skip reading all image headers - just     |
|                                  | read the first one for each sweep         |
+----------------------------------+-------------------------------------------+
| ``unit_cell=``                   | Provide a target unit cell to help        |
|                                  | indexing                                  |
+----------------------------------+-------------------------------------------+
| ``space_group=``                 | Provide a target space group to help      |
|                                  | indexing                                  |
+----------------------------------+-------------------------------------------+
| ``-atom X``                      | Anomalous flag: don't merge Friedel pairs |
+----------------------------------+-------------------------------------------+

Once xia2 has finished processing all the data, the final merging statistics
reported by xia2 are as follows::

  For AUTOMATIC/DEFAULT/SAD
  High resolution limit                    1.29    5.63    1.29
  Low resolution limit                    68.02   68.02    1.33
  Completeness                            67.2    99.6     2.8
  Multiplicity                             6.5     9.2     1.1
  I/sigma                                 16.1    27.6     4.3
  Rmerge                                 0.124   0.136   0.000
  Rmeas(I)                               0.144   0.162   0.608
  Rmeas(I+/-)                            0.138   0.149   0.000
  Rpim(I)                                0.047   0.052   0.430
  Rpim(I+/-)                             0.058   0.060   0.000
  CC half                                0.988   0.956   0.823
  Wilson B factor                        18.807
  Anomalous completeness                  53.6    97.9     0.2
  Anomalous multiplicity                   2.8     4.9     1.0
  Anomalous correlation                   0.208   0.328   0.000
  Anomalous slope                        1.303   0.000   0.000
  dF/F                                   0.076
  dI/s(dI)                               1.056
  Total observations                     356049  10633   187
  Total unique                           55180   1161    176
  Assuming spacegroup: P 61 2 2
  Unit cell:
  92.620  92.620 128.330
  90.000  90.000 120.000

These merging statistics are for all the data from all 20 sweeps
merged together. Depending upon the quality of the particular datasets, and
what exactly we want to do with the processed data in the next step, this may
well be good enough, however in some cases we may want to analyse the
individual datasets for non-isomorphism using BLEND_ with the hope of finding
a subset of the data that gives a better quality merged dataset than merging
the all of the data together. We can run BLEND_ in *analysis* mode on the
integrated reflection files output by XDS as follows::

  find `pwd` -name "INTEGRATE.HKL" > data.txt
  blend –a data.txt

Because we are not running with keywords, press enter while it’s running then
check the resulting dendrogram::

  display tree.png

.. image:: /figures/thermolysin_blend_tree.png

If we wish we can now run BLEND_ in *synthesis* or *combination* mode to
scale together and merge subsets of the data, for example to get the merged
dataset for the second highest node in the dendrogram::

  blend -s 10 5

pressing enter several times as before. This gives the resulting merging
statistics as reported by BLEND_::

  ********* Cluster 18, composed of datasets 1 2 3 5 6 7 8 9 11 13 14 15 16 18 19 20 *********
  Collating multiple mtz into a single mtz ...
  Running AIMLESS on the unscaled file ...
   Statistics for this group:
             Rmeas  Rpim Completeness Multiplicity LowRes HighRes
  Overall    0.133 0.074         86.4          2.6  50.15    2.48
  InnerShell 0.175 0.096         85.2          2.7  50.15    8.93
  OuterShell 0.171 0.096         87.9          2.6   2.58    2.48

For more information on using BLEND_ see the `BLEND tutorials`_.

.. _BLEND: http://www.ccp4.ac.uk/html/blend.html
.. _BLEND tutorials: http://www.ccp4.ac.uk/tutorials/tutorial_files/blend_tutorial/BLEND_tutorial.html

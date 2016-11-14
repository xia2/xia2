+++++++++++++++++++++++++++++++++++++++++++
Processing multi-crystal datasets with xia2
+++++++++++++++++++++++++++++++++++++++++++

xia2 is ideally suited to processing multi-crystal (or multi-sweep) datasets,
and is able to process more than one dataset simultaneously, providing many
features that can make the processing of such datasets both easier and faster.
Examples include (but not limited to):

* Merging multiple datasets taken from multiple crystals
* Merging multiple datasets taken from a single crystal
* Scaling together, but merging individually multiple wavelength datasets
* Inverse beam experiments

Images or directories can be passed on the command line, as with a normal
xia2 job processing a single sweep. Xia2 now allows passing multiple directories
on the command line, or passing multiple images via the :samp:`image=` parameter::

  xia2 pipeline=dials /path/to/images/dataset_1 /path/to/images/dataset_2

  xia2 pipeline=dials image=/path/to/images/sweep_1_0001.cbf image=/path/to/images/sweep_2_0001.cbf

Alternatively, you can specify exactly which images you wish to process in an
.xinfo file::

  BEGIN PROJECT AUTOMATIC
  BEGIN CRYSTAL DEFAULT

  BEGIN WAVELENGTH NATIVE
  WAVELENGTH 0.979500
  END WAVELENGTH NATIVE

  BEGIN SWEEP SWEEP1
  WAVELENGTH NATIVE
  DIRECTORY /path/to/images/
  IMAGE sweep_1_0001.cbf
  START_END 1 450
  END SWEEP SWEEP1

  BEGIN SWEEP SWEEP2
  WAVELENGTH NATIVE
  DIRECTORY /path/to/images/
  IMAGE sweep_2_0001.cbf
  START_END 1 450
  END SWEEP SWEEP2

  END CRYSTAL DEFAULT
  END PROJECT AUTOMATIC

When processing many datasets simultaneously, it may happen that some datasets
will process successfully, but xia2 will fail to process others. By default,
xia2 will stop with an error message if any error is encountered, however if
the :samp:`failover=True` is set on the command line, then xia2 will
ignore any failed sweeps and continue processing with only those sweeps that
processed successfully.

When xia2 is given a particularly large number of images to process, it may
take some time before it appears to start processing the data. This may be for
a couple of reasons:

#. On start up, xia2 reads all the image headers to ensure that it understands
   them correctly. A speedup can be obtained with the parameter
   :samp:`read_all_image_headers=False`, which tells xia2 to only read the
   first image header for each set of files with a matching template, and
  infer the rest of the sweep from the first image header.

#. If available, xia2 will run a beam centre search on each sweep using
   labelit.index. This step can be disabled using the parameter
   :samp:`trust_beam_centre=True`

Furthermore, xia2 may not make the same conclusion as to the symmetry for each
sweep, leading it to process the final dataset in the lowest common symmetry.
Sometimes indexing for a given sweep may fail altogether, and specifying the
:samp:`unit_cell=` and :samp:`space_group=` parameters (if known) on the
command line can help in both these situations.


+----------------------------------+---------------------------------------+
| Parameter                        |  Description                          |
+==================================+=======================================+
| ``failover=True``                | If processing fails for any sweeps,   |
|                                  | ignore and just use those sweeps that |
|                                  | processed successfully                |
+----------------------------------+---------------------------------------+
| ``trust_beam_centre=True``       | Don't run labelit beam centre search  |
+----------------------------------+---------------------------------------+
| ``read_all_image_headers=False`` | Skip reading all image headers - just |
|                                  | read the first one for each sweep     |
+----------------------------------+---------------------------------------+
| ``unit_cell=``                   | Provide a target unit cell to help    |
|                                  | indexing                              |
+----------------------------------+---------------------------------------+
| ``space_group=``                 | Provide a target space group to help  |
|                                  | indexing                              |
+----------------------------------+---------------------------------------+


Parallel data processing
------------------------

By default, xia2 processes each sweep sequentially, using :samp:`nproc`
processors. When processing multiple datasets, it may be more efficient to
process the sweeps in parallel, by specifying
:samp:`multiprocessing.mode=parallel` and
using :samp:`multiprocessing.njob` to indicate how many sweeps should be
processed simultaneously, using :samp:`multiprocessing.nproc` processors
per sweep::

  xia2 pipeline=dials /path/to/images multiprocessing.mode=parallel \
    multiprocessing.njob=2 multiprocessing.nproc=4

.. note::

  This will use a total of :samp:`njob` :math:`*` :samp:`nproc` processors,
  i.e. :math:`2 * 4 = 8` processors, which should be less than or equal to the total
  number of processors available on your machine.

Additionally, xia2 can utilise the processing power of a cluster where
available (currently we only support qsub) by specifying the parameter
:samp:`multiprocessing.type=qsub`. The parameter
:samp:`multiprocessing.qsub_command` may be used (if needed) to e.g. specify
which queue jobs should be submitted to::

  xia2 pipeline=dials /path/to/images multiprocessing.mode=parallel \
    multiprocessing.type=qsub multiprocessing.qsub_command="qsub -q low.q" \
    multiprocessing.njob=10 multiprocessing.nproc=16


+---------------------------------------+--------------------------------------+
| Parameter                             |  Description                         |
+=======================================+======================================+
| ``multiprocessing.mode=parallel``     | Process multiple sweeps in parallel, |
|                                       | rather than serially                 |
+---------------------------------------+--------------------------------------+
| ``multiprocessing.njob=4``            | In conjunction with mode=parallel,   |
|                                       | process 4 sweeps simultaneously      |
+---------------------------------------+--------------------------------------+
| ``multiprocessing.nproc=1``           | Use 1 processor per job (sweep)      |
+---------------------------------------+--------------------------------------+
| ``multiprocessing.type=qsub``         | Submit individual processing jobs to |
|                                       | cluster using qsub                   |
+---------------------------------------+--------------------------------------+
| ``multiprocessing.type=qsub_command`` | The command to use to submit qsub    |
|                                       | jobs                                 |
+---------------------------------------+--------------------------------------+

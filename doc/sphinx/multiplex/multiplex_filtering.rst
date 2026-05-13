+++++++++++++++++++
Multiplex Filtering
+++++++++++++++++++
---------------------
Scaling and filtering
---------------------
An alternative means of filtering data within xia2.multiplex is to use :math:`{\Delta}CC1/2` filtering, as described in the publication.
This is separate to any cos-angle or correlation clustering analysis and is also optional, not being run by default. 
To trigger this, use the option ``filtering.method=deltacchalf``. In this method, the :math:`{\Delta}CC1/2` is calculated for a group of images: groups with a :math:`{\Delta}CC1/2`
below ``deltacchalf.stdcutoff`` are removed (standard deviations below the mean, default value 4.0). A group is either a group of images or an individual dataset, the choice is made
with the parameter ``deltacchalf.mode=dataset`` or ``deltacchalf.mode=image_group`` (dataset is the default). If using the ``image_group`` mode, one must choose the number of images in each group with
the ``deltacchalf.group_size`` parameter (default value 10).
The filtering starts on the combined scaled dataset, and several cycles of repeated scaling and filtering are performed. This stops when one of the following criteria are met:

1. The number of cycles reaches ``deltacchalf.max_cycles`` (default 6).
2. The percentage of reflections removed exceeds ``deltacchalf.max_percent_removed`` (default 10).
3. The completess drops below ``deltacchalf.min_completeness`` (default 0).
4. No groups are removed in the latest cycle of filtering.

A merging statistics report for filtered dataset will be generated and displayed in the **Filtered** tab in the ``xia2.multiplex.html`` report.
Plots of changes in statistics during the scaling and filtering cycles can be found in the **Scaling and filtering plots** section in the **Summary** tab.

**Key points:**

- Turn on cycles of :math:`{\Delta}CC1/2` filtering + scaling with the option ``filtering.method=deltacchalf``.
- The ``deltacchalf.stdcutoff`` parameter is the main way to control the amount of data that is filtered out. Setting this to a lower number means that more data is filtered at each step.
- In the case of radiation damage towards the end of sweeps, it may be better to just exclude the end of sweeps rather than full sweeps; this is an ideal use case for the ``deltacchalf.mode=image_group`` option.

------------------------
xia2.multiplex_filtering
------------------------
A commandline program now exists to run the filtering algorithms in ``xia2.multiplex`` on an existing processing directory. The filtering available in ``xia2.multiplex`` can be
slow to run, so it is not always recommended for large datasets where an initial result is needed for fast feedback. In such a case, ``xia2.multiplex`` would be run on the data first
without filtering, then, if the statistics show room for improvement, ``xia2.multiplex_filtering`` would be run on the same directory. 

To run ``xia2.multiplex_filtering``, simply run the command:

::

    xia2.multiplex_filtering path/to/multiplex/dir

By default, ``filtering.method=deltacchalf`` in ``dataset`` mode will be used if not specified; however, all filtering options discussed above are available to tailor in this command.

**It is important that xia2.multiplex has finished running before you use xia2.multiplex_filtering!**

Specifically, ``xia2.multiplex_filtering`` requires the following files from ``xia2.multiplex``:

* models.expt
* observations.refl
* scaled.mtz 
* xia2-multiplex-working.phil 
* xia2.multiplex.json

The HTML output will contain the filtering plots mentioned above, and also copies the data processing statistics for the unfiltered
data reduction as well as any clusters that are output for easy comparison in the same file. 
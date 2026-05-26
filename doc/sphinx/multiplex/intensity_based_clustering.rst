++++++++++++++++++++++++++
Intensity-based Clustering
++++++++++++++++++++++++++
---------------------------------------
Scaling and merging of dataset clusters
---------------------------------------
*To trigger further scaling and merging of clusters, set the xia2.multiplex option*
``output_clusters=True``.
Note that the clustering options described here can also be run standalone with the ``xia2.cluster_analysis`` program, using the xia2.multiplex scaled
data files (``scaled.expt``, ``scaled.refl``) as input, but each cluster will not be further scaled and merged.

Dataset clustering can be performed based on a hierarchical dendrogram analysis (``clustering.method=hierarchical``)
or on density-based analysis of the cosym coordinates (``clustering.method=coordinate``). See the publication at https://doi.org/10.1107/S2059798325004589 for
more details of the density-based analysis.

Both methods share some common criteria when deciding which clusters to be output. These are tailorable via command-line input.

1. They have at least a completeness of ``min_completeness`` (default value 0).
2. They have at least a multiplicity of ``min_multiplicity`` (default value 0).
3. The number of datasets in the cluster is at least ``min_cluster_size`` (default value 5).

------------------------------
Coordinate clustering analysis
------------------------------

.. tip::
    You can also output custom sub-sets of data by interacting with ``xia2.multiplex.html`` in DIALS >= 3.28.0. See :doc:`here <custom_clustering_via_html>`.

Density based clustering algorithms are a separate class of clustering algorithms compared to hierarchical clustering algorithms.
In xia2.multiplex, density-based clustering can be performed on the cosym coordinates, which reflect the systematic and random
non-isomorphism within the data. 
If ``clustering.method=coordinate``, the OPTICS clustering algorithm from scikit-learn is used to determine density-based clusters
(these clusters will always be distinct and not share any individual datasets).
Clusters that meet the ``min_multiplicity``, ``min_completeness`` and ``min_cluster_size`` thresholds will be individually scaled and merged.

--------------------------------
Hierarchical clustering analysis
--------------------------------

.. tip::
    You can also output specific hierarchical clusters by interacting with ``xia2.multiplex.html`` in DIALS >= 3.28.0. See :doc:`here <custom_clustering_via_html>`.

Hierarchical clustering can be performed on one of two metrics; correlation coefficient clustering, based on pairwise
correlations between datasets, and 'cos-angle' clustering, based on angular separation of datasets
in the cosym coordinate space.
The hierarchical clustering method is controlled by the parameter ``hierarchical.method``, which can be set to ``cos_angle``, ``correlation`` or ``cos_angle+correlation``.
For the method(s) chosen, a number of clusters up to ``max_output_clusters`` (default value 10) will be scaled and merged, if they meet the above criteria.
Additionally, which clusters are output are controlled by a further parameter ``max_cluster_height`` (default value 100). This is the maximum allowed height of the cluster on the dendrogram as shown in the xia2.multiplex clustering output.

If the clustering method is set to ``cos_angle+correlation``, then the max height for the two clustering methods are controlled individually with the parameters ``max_cluster_height_cc`` and ``max_cluster_height_cos``.

The default ``max_cluster_height`` values are large, such that the output clusters will typically be the `n=` ``max_output_clusters`` largest clusters. The dendrogram height values will be dataset specific, to choose
a particular value one can look at the **Intensity Clustering** section of a ``xia2.multiplex.html`` report:

.. image:: ../figures/multiplex-dendrogram.png

As shown in this image, the height of a cluster is the point at which it separates into two smaller clusters in the dendrogram. So in this
example, the largest cluster splits at a height of 0.072, and these two clusters each split again around a height of 0.018.
So if clustering was run with ``max_output_clusters=2``, one would get the two largest clusters (clusters 13 and 14 here). But if the ``max_cluster_height`` were set to a value just below 0.018, one would obtain
the two smaller clusters with heights 0.0075 and 0.0032 (clusters 12 and 11).

After the clusters have been selected, each cluster is then individually scaled and merged.

-------------------------
Distinct cluster analysis
-------------------------
The analysis described above does not guarantee that clusters will not share some individual datasets; this is not necessarily a problem, a typical use case for xia2.multiplex is generating a number
of similar clusters containing similar datasets, to compare the effects of removing a number of outlier datasets on the overall statistics.
An alternative use case is where one is interested in distinct clusters of datasets, i.e. clusters that do not share any individual datasets, which may correspond to distinct crystal structures
(this is the kind of clustering structure demonstrated in the image above). While this can be handled using the options above for small or simple cases, for large datasets the dendrogram structure
becomes very complex, with many dendrogram substructures and branches. As such, the options above do not guarantee selection and evaluation of distinct clusters in a timely manner.

To generate output containing distinct clusters `instead` of the output above, one can use the option ``hierarchical.distinct_clusters=True``.
In this case, individual clusters must still meet the four criteria above, then an analysis is performed to determine distinct clusters that do not share any individual datasets.
These clusters are then individually scaled and merged.

------------------------------------------
Allowed tolerance for unit cell parameters
------------------------------------------
The tolerance for accepted unit cell parameters in xia2.multiplex is set to be reasonably strict. The default value for ``symmetry.cosym.relative_length_tolerance`` is 0.05, which means that any datasets with unit
cell lengths outside of this relative tolerance range will be rejected. For unit cell angles, the default value for ``symmetry.cosym.absolute_angle_tolerance`` is 2, meaning all unit cell angles that fall outside
of this absolute tolerance range will also be rejected. These ranges are evaluated based on the best median unit cell established through dials.cosym (run within xia2.multiplex). 

These tolerance values have been found effective where the goal of the multi-crystal data collection is a single, high quality dataset. In the case where multiple distinct crystal structures may be present, these
tolerance values can be increased to permit more data through into the clustering analysis. For instance, one recommended option to look for other distinct states without permitting data through that are too different
is to set ``symmetry.cosym.relative_length_tolerance=0.1``.
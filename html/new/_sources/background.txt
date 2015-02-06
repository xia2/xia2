++++++++++
Background
++++++++++

Users of macromolecular crystallography (MX) are well served in terms of
data reduction software, with packages such as HKL2000, Mosflm [1]_,
XDS [2]_ and d*TREK often available and commonly used. In the main, however,
these programs require that the user makes sensible decisions about the
data analysis to ensure that a useful result is reached. This manual describes
a package, xia2, which makes use of some of the aforementioned
software to reduce diffraction data automatically from images to scaled intensities
and structure factor amplitudes, with no user input.
In 2005, when the xia2 project was initiated as part of the UK BBSRC
e-Science project e-HTPX, multi-core machines were just becoming common,
detectors were getting faster and synchrotron beamlines were becoming
brighter. Against this background the downstream analysis (e.g. structure
solution and refinement) was streamlined and the level of expertise
needed to use MX as a technique was reducing. At the same time mature
software packages such as Mosflm, Scala [3]_, CCP4 [4]_ and XDS were available
and a new synchrotron facility was being built in the UK. The ground
was therefore fertile for for the development of automated data reduction
tools. Most crucially, however, the author was told that this was impossible
and a waste of time - sufficient motivation for anyone.


.. [1] A.G.W. Leslie, Acta Cryst. (2006) D62, 48-57
.. [2] W. Kabsch, Acta Cryst. (2010) D66, 125-132
.. [3] P. Evans, Acta Cryst. (2006) D62, 72-82
.. [4] CCP4, Acta Cryst. (1994) D50, 760-763

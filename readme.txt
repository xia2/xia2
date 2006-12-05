xia2ss - the XiA for Structure Solution
---------------------------------------

This goes along with xia2dc, xia2dpa to provide a complete suite of 
"expert" crystallography programs. Should all work through the .xinfo
file.

DPA
---

This is the new repository for the DPA component of XiA, which depends on 
XIACore. Have intentionally not called this XIA-DPA, since that is what you
get when you include XIA and DPA together in one package.

Directory structure:

Wrappers - wrapper classes for individual programs
Interfaces - interfaces to external systems e.g. DNA e-htpx
Modules - chunks of code which do something useful in an atomic way
Applications - things you can actually run
Test - unit tests
Schema - the data model
Handlers - things (mostly singletons) for handling things
Experts - components which are "clever"
Data - test data
Doc - the documentation...
Interfaces - interfaces for external systems e.g. ccp4i, e-HTPX


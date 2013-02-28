XIACore Readme
27/MAR/06
Graeme Winter

Updated for version 0.0.2 7/JUN/06

Introduction
------------

This is the core module of XIA2 - essentially the second major development 
release of the XIA - "Crystallographic Infrastructure for
Automation", or "eXpertise In Automation", depending on your mood.

The structure of this is different. In place of having a single huge CVS
archive, the core is being separated out from the rest, to allow it to be used
more easily in other projects. 

Requirements
------------

For this version, the following requirements have been identified:
 - Portability to Windows and Macintosh OS X
 - Small & light
 - More flexible
 - More reliable e.g. checking the system path for a program before trying
   to start it.

Functionality
-------------

Components within this module provide the functionality to:
 - Start, stop and kill processes
 - Read output & write input to those processes
 - Get return values

Getting It Working
------------------

export XIA2CORE_ROOT=/path/to/the/directory/this/readme/is/in
setenv XIA2CORE_ROOT /path/to/the/directory/this/readme/is/in

XIA2CORE_ROOT = "xia 2 core root"

Debugging & Testing
-------------------

There are a number of "platform neutral" programs to be found in XIA2CORE_ROOT/Test
which can be run as:

ExampleProgram
ExampleProgramCommandLine
ExampleProgramLooseLoop
ExampleProgramRaiseException
ExampleProgramStandardInput
ExampleProgramTightLoop

These are shell/batch scripts which run python (.py) programs. In all cases a 
python executable needs to be in the path.

There are also a small number of compiled executables for testing things like
segmentation violations and the like. To build these you'll need compilers - 
on windows visual studio and on linux/mac os x gcc. To build these go to

/Test/Compiled

and bash build.sh or run build.bat.

Testing
-------

To test that everything is hunky-dory, export the environment as above, and
source the setup script in $XIA2CORE_ROOT:

. setup.sh (unix derivatives)
setup.bat  (windows)

Then go to Python and run the appropriate run_tests script as bash 
run_tests.sh or run_tests.bat. This will run a set of unit tests (9)
which should run and produce output like:

.........
----------------------------------------------------------------------
Ran 9 tests in 124.018s

OK

If it does, then you're onto a winner. Some of the tests rely on CCP4 
programs, so they can take a moment or two. If any programs are missing 
helpful message will tell you all about it.



Documentation
-------------

There is a fair amount of documentation to be had - look first in

$XIA2CORE_ROOT/Doc

and 

$XIA2CORE_ROOT/Python/Doc

for pdf files.


Help
----

For any more information contact Graeme Winter on g.winter@dl.ac.uk

Driver class for Python
-----------------------

Graeme Winter
27/MAR/06

Design
------

The design of this class is intentionally lightweight. The plan is to have
two standard modes of operation - interactive or batch. Interactive jobs
pass the input provided by the input() method immediately. Batch jobs will
store these input commands until the close_input() method is called. This will
then write a script or run the task interactively, depending on the context.

Note well that care should be taken when running genuinely interactive tasks,
since internal buffering may prevent the standard output from reaching the
screen immediately.

This design is to allow for tasks running non-interactively, that is over
batch queuing systems.


Environment
-----------

XIA2CORE_DRIVERTYPE - if set, this will define the default driver type.

Driver Types
------------

The following types are currently implemented:

"simple" - interactive operation via pipes (Windows/OS X/Linux)
"script" - run via scripts - records input & output (Windows/OS X/Linux)
"interactive" - simple but with more interactive job control (Linux)
"qsub" - for sun grid engine queuing systems (Linux)

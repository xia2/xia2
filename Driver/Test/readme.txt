This directory will contain example programs for testing specific functions
of the XIA core. In particular they can be used for testing out exception
mechanisms for timing out, setting command line input & so on - part of the
specification framework.

ExampleProgram
--------------

Simplest example, takes no input, nor command line arguments,
writes "Hello, World!" to the command line 10 times, once
per second.

ExampleProgramLooseLoop
-----------------------

Never exits.

ExampleProgramRaiseException
----------------------------

Program fails to start with an exception. c/f missing .so file for instance.

ExampleProgramStandardInput
---------------------------

An example program which reads commands from the standard input until a
"quit" is reached. Or EOF.

ExampleProgramCommandLine
-------------------------

An example program which reads information from the command line.

Portability
-----------

All of these programs have been tested on Mac OS X Tiger, SuSE linux & Windows
XP. This means that they are probably reasonably portable. Note well that by
OS X I refer to the Darwin side of things - double clicking no work!

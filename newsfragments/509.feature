Report more useful error message if given Eiger data file not master file, including suggestions of possible master files in the same directory e.g.

::

  Command line: xia2 image=/Users/graeme/data/i04-eiger-small/Therm_6_2_000001.h5
  Provided input files not master files:
    /Users/graeme/data/i04-eiger-small/Therm_6_2_000001.h5
  do you mean one of:
    /Users/graeme/data/i04-eiger-small/Therm_6_1_master.h5
    /Users/graeme/data/i04-eiger-small/Therm_6_2_master.h5
  or:
    /Users/graeme/data/i04-eiger-small/Therm_6_2.nxs
    /Users/graeme/data/i04-eiger-small/Therm_6_1.nxs

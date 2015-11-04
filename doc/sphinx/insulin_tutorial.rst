++++++++++++++++
Insulin tutorial
++++++++++++++++

This tutorial uses test images which are available from the links below.
Thanks to John Cowan for providing this test data!

* `Windows (as .zip file) <http://www.ccp4.ac.uk/xia/demo.zip>`_
* `Unix (as .tar.bz2 file) <http://www.ccp4.ac.uk/xia/demo.tar.bz2>`_
* `Unix (as .tar.gz file) <http://www.ccp4.ac.uk/xia/demo.tar.gz>`_

There are two ways of running xia2 - with and without an input file, an
example of which follows below. If you just run::

  xia2 /my/data/are/here

xia2 will do something sensible - in this case process all of the data, scale
all measurements as if they are from a single crystal and merge the data from
each wavelength separately. If only one wavelength is present xia2 will assume
that the data are a native data set - to separate anomalous pairs provide a
heavy atom (at this time it doesn't matter what it is...) i.e.::

  xia2 -atom se /my/data/are/here

Other options are (type just xia2 to get this list)::

  Command-line options to xia2:
  [-2d] or [-3d] or [-3dii]
  [-parallel 4] (say, for XDS usage)
  [-resolution 2.8] (say, applies to all sweeps)
  [-freer_file free.mtz]
  [-quick]
  [-atom se] (say)
  [-reversephi]
  [-migrate_data]
  [-beam x,y]

Running ths way some assumptions are made:

* All images are from one crystal only.

* The scan, if present, was the one used to select the wavelengths for data
  collection. If more than one is present, the alphabetically latest one will
  be used.

* The sequence file, if present, should be in the one letter form and all
  comment lines should begin with a character not in A-Z. Again the
  alphabetically latest sequence file will be used.

* If the sequence file is provided, and the atom is "se", then xia2setup will
  assume that you are doing a SeMet experiment and will provide an appropriate
  number of atoms per monomer - though you will still have to uncomment this
  to include it, in case it has guessed wrong.

* If you want to combine data from a number of crystals in the same .xinfo
  file, then you will need to copy out all text from
  :samp:`BEGIN CRYSTAL` to :samp:`END CRYSTAL` from one .xinfo file to the
  other.

You should then load automatic.xinfo in your favourite editor, and check that
the sequence looks correct and that the names are sensible as well as checking
that the epoch numbers are set correctly and also that the wavelengths and
beam centres are correct. If you provided a heavy atom there is a place to
say how many to look for.

Finally, if you have labelit installed xia2 will run this to update the beam
positions. If this happens, you will see a comment to this effect above the
BEAM records in the sweeps.

The other mechanism for running xia2 is via a xinfo file, which explains the
layout of the data set to xia2 explicitly. This is helpful if you wish to only
process a subset of the measurements, or want to process data for an RIP
experiment. A simple example of xinfo file follows below, and more complex
examples can be found here:

* :download:`Native data <files/NATIVE.xinfo>`
* :download:`SAD data <files/SAD.xinfo>`
* :download:`MAD data <files/MAD.xinfo>`

::

  ! This is a demonstration .xinfo file which illustrates how to cope
  ! with a simple case - this example is a native cubic insulin data
  ! set measured on 14.2 at the SRS

  BEGIN PROJECT DEMONSTRATION

  BEGIN CRYSTAL INSULIN

  BEGIN AA_SEQUENCE

  ! this is only really needed at the moment for assessing the solvent
  ! content and number of residues in the asu

  GIVEQCCASVCSLYQLENYCN
  FVNQHLCGSHLVEALYLVCGERGFFYTPKA

  END AA_SEQUENCE

  BEGIN WAVELENGTH NATIVE

  ! this doesn't have to be here - if it is
  ! not included then the values from
  ! the image headers will be used - however
  ! if it is there then it should
  ! be correct!

  WAVELENGTH 0.979000

  ! in here you can also have
  ! F' value
  ! F'' value

  END WAVELENGTH NATIVE

  BEGIN SWEEP NATIVE
  WAVELENGTH NATIVE
  IMAGE insulin_1_001.img

  ! you will probably need to change this -
  ! this is the only thing which
  ! you will need to change for the
  ! demonstration data set

  DIRECTORY /media/data1/graeme/demo/

  ! additionally you can add the following
  ! information - if it is wrong in the headers
  ! BEAM x y (mm)
  ! DISTANCE z (mm)

  ! this describes the order in which
  ! the sweeps were collected -
  ! it usually comes from the image header
  ! if that information is in there
  ! EPOCH 5

  ! you can also add this to only reduce
  ! a subset of the data
  ! START_END 1 30 (image numbers)

  END SWEEP

  END CRYSTAL INSULIN

  END PROJECT DEMONSTRATION

#     Xia2html.py: turn Xia2 output into HTML
#     Copyright (C) Diamond 2009 Peter Briggs
#
########################################################################
#
# Xia2html.py
#
########################################################################

"""Xia2html: extract data xia2 output and generate a HTML report

Overview

The Xia2html module provides an application which generates a HTML
report of a xia2 run.

Running Xia2html

It can be run using the command line:

python /path/to/Xia2Log.py [<xia2_output_dir>]

where the optional <xia2_output_dir> parameter specifies the location
of the xia2.txt file and the rest of the xia2 output (i.e. the LogFiles
and DataFiles directories). If no <xia2_output_dir> is specified then
the application looks for the xia2 output in the current working
directory.

Output

Xia2html creates a xia2.html file in the current directory, plus a
xia2_html subdirectory which holds associated files (PNGs, html
versions of log files etc). Where possible relative paths are used for
links from xia2.html to external files, so it should be possible to
copy the files to another location and still have functional links.

Requirements

The XIA2HTMLDIR environment variable needs to be set to the directory
where this file (and supporting modules etc) are held. Xia2html expects
to find icons in the 'icons' subdirectory of XIA2HTMLDIR.

Updating and extending

1. To add new citations or modify existing ones, edit the Citations
   class.

2. To add new log files or modify existing ones, edit the PipelineInfo
   class.

3. To update the regular expressions used to extract data from xia2.txt
   look at the addPattern() and addBlock() calls.

More detail on how Xia2html works

The basic procedure in Xia2html is:

1. Populate a data structure (provided by the Xia2run class in this module)
   with data extracted from the xia2.txt file and LogFiles directory.

2. Build a HTML document (done by the Xia2doc class) using the data
   organised in the Xia2run class.

This module contains a number of classes to support gathering, organising
and writing out the data:

PipelineInfo and Citations classes hold 'external' data about log files
and citations respectively. The data in these classes may need to be
updated or extended as xia2's output evolves.

Crystal, Dataset, Sweep and Integration run classes are used within
Xia2run to organise the data regarding these data from the run. The
LogFile and ReflectionFile classes organise the data regarding these
two types of file.

Xia2doc class is used to build the output HTML document, and
IntegrationStatusReporter class is used to help with generating HTML
specific to the sweeps."""

__cvs_id__ = "$Id$"
__version__ = "0.0.5"

#######################################################################
# Import modules that this module depends on
#######################################################################
import sys
import os
import shutil
import time
import tarfile
import Magpie
import Canary
import smartie
import baubles

#######################################################################
# Class definitions
#######################################################################

#######################################################################
# Classes with hardcoded data
#######################################################################

# PipelineInfo
#
# Store and recover information about logfiles and associated
# data such as ordering, program associations etc
class PipelineInfo:
  """Information on log files within the xia2 'pipeline'

  Provides lookup etc for identifying and associating data
  (such as source program, processing stage, description etc)
  with log files output from the xia2.

  To add a new log file to the list of files, put a new
  addLogInfo() method call in the __populate method with
  information about the new log file. Note that the order in
  which addLogInfo calls occur also defines the order that
  the logs will be sorted into on output.

  Note regarding the 'XDS pipeline':

  At the time of writing xia2 supports at least two different
  notional pipelines, one using XDS and one without. By default
  the PipelineInfo class is set up to return data appropriate for
  the non-XDS pipeline. To change a PipelineInfo object to
  represent the XDS pipeline, invoke the 'setXDSPipeline' method.

  Developers modifying the PipelineInfo should therefore also
  consider changes to the 'setXDSPipeline' method if their
  modifications relate to the use of XDS in xia2."""

  def __init__(self):
    """Create and initialise Pipeline object

    Note that the order that log file references appear
    implicitly defines the order that logs will be sorted into"""
    self.__pipeline = []
    # Set up log file definitions
    #
    # *** THE ORDER OF THE addLogInfo CALLS BELOW IS SIGNIFICANT ***
    #
    # Integration stage
    self.addLogInfo(
        "INTEGRATE",
        "xds",
        "Integration",
        "Integration of each sweep",
        "<PROJECT>_<CRYSTAL>_<DATASET>_<SWEEP>_INTEGRATE.log",
        False)
    self.addLogInfo(
        "CORRECT",
        "xds",
        "Integration",
        "Postrefinement and correction for each sweep",
        "<PROJECT>_<CRYSTAL>_<DATASET>_<SWEEP>_CORRECT.log")
    self.addLogInfo(
        "_mosflm_integrate",
        "mosflm",
        "Integration",
        "Full logs for the integration of each wavelength",
        "<SWEEP>_<PROJECT>_<CRYSTAL>_<DATASET>_mosflm_integrate.log")
    self.addLogInfo(
        "_postrefinement",
        "mosflm",
        "Integration",
        "Results of postrefinement",
        "<SWEEP>_<PROJECT>_<CRYSTAL>_<DATASET>_postrefinement.log",
        baublize=True)
    # Spacegroup determination
    self.addLogInfo(
        "_pointless",
        "pointless",
        "Spacegroup Determination",
        "Decision making for the spacegroup assignment",
        "<PROJECT>_<CRYSTAL>_pointless.log",
        baublize=True)
    # Scaling and merging
    self.addLogInfo(
        "XSCALE",
        "xscale",
        "Scaling and merging",
        "Scaling together all the data for this crystal",
        "<PROJECT>_<CRYSTAL>_XSCALE.log")
    self.addLogInfo(
        "_aimless",
        "aimless",
        "Scaling and merging",
        "Scaling and correction of all measurements on the crystal",
        "<PROJECT>_<CRYSTAL>_aimless.log",
        baublize=True)
    # Analysis
    self.addLogInfo(
        "_truncate",
        "truncate",
        "Analysis",
        "Intensity analysis for each wavelength of data",
        "<PROJECT>_<CRYSTAL>_<DATASET>_truncate.log",
        baublize=True)
    # *** Note for Chef log files ***
    # There is one entry for each chef log corresponding
    # to the different possible groups
    self.addLogInfo(
        "chef_1",
        "chef",
        "Analysis",
        "Cumulative radiation damage analysis",
        "<CRYSTAL>_chef_1.log",
        baublize=True)
    self.addLogInfo(
        "chef_2",
        "chef",
        "Analysis",
        "Cumulative radiation damage analysis",
        "<CRYSTAL>_chef_2.log",
        baublize=True)
    self.addLogInfo(
        "chef_3",
        "chef",
        "Analysis",
        "Cumulative radiation damage analysis",
        "<CRYSTAL>_chef_3.log",
        baublize=True)

  def setXDSPipeline(self):
    """Update pipeline data for XDS pipeline

    Invoke this to make changes to the pipeline information
    to make it consistent with xia2 running in the notional
    'XDS pipeline' mode."""
    self.updateLogInfo(
        "_aimless",
        new_description=
        "Merging results for all of the data for the crystal")

  def addLogInfo(self,logname,program,stage,description,template,
                 baublize=False):
    """Add information about a log file

    'logname' is part of the log file name which is used to
    identify it, for example: for truncate log files, a typical
    file name would be 'TS01_13140_LREM_truncate.log', so
    '_truncate' is used to recognise all truncate log files.

    'program' is the source program name, for example 'xds'.

    'stage' is the name of the processing stage that the file
    belongs to, for example 'Spacegroup Determination'.

    'description' is generic text that describes what the function
    of the log file is, for example 'Intensity analysis for each
    wavelength of data'.

    'template' is a string that provides a template for building
    the file name. The following placeholders are used to show
    where project, crystal, dataset and sweep names should be
    substituted:
    <PROJECT> - project name
    <CRYSTAL> - crystal name
    <DATASET> - dataset name
    <SWEEP>   - sweep name
    For example: <PROJECT>_<CRYSTAL>_pointless.log

    'baublize' is a logical value indicating whether the log
    can be baublized.

    NOTE 1: the template is similar but distinct to the logname.
    The template can't be used instead of the logname since it
    is possible for project, crystal and dataset names to also
    contain underscores.

    NOTE 2: the lookup functions below will be confused by
    log file names which have project, crystal or dataset names
    which match one of the program names. There is no fix to
    address this situation."""
    self.__pipeline.append({
            'logname': logname,
            'program': program,
            'stage': stage,
            'description': description,
            'template': template,
            'baublize': baublize})

  def updateLogInfo(self,logname,
                    new_program=None,
                    new_stage=None,
                    new_description=None,
                    new_template=None,
                    new_baublize=None):
    """Update the information associated with a log file

    Allows the modification of information previously associated
    with a log file name via addLogInfo. One or more attributes
    can be changed by providing values for the appropriate
    parameters.

    See the addLogInfo method for descriptions of each of the
    attributes."""
    data = self.lookupLogInfo(logname)
    if data:
      if new_program:
        data['program'] = new_program
      if new_stage:
        data['stage'] = new_stage
      if new_description:
        data['description'] = new_description
      if new_template:
        data['template'] = new_template
      if not new_baublize is None:
        data['baublize'] = new_baublize

  def lookupLogInfo(self,logfile):
    """Lookup the stored information for the named log file

    Attempts to match the logfile name against the stored name
    fragments; if a match is found then returns the stored
    dictionary.

    Applications should not call this method directly; instead
    use the other methods to get specific information e.g. the
    associated program name."""
    basename = os.path.basename(logfile)
    for item in self.__pipeline:
      if basename.find(item['logname']) > -1:
        return item
    # Nothing found
    return {}

  def program(self,logfile):
    """Get the program name associated with a logfile"""
    data = self.lookupLogInfo(logfile)
    if data:
      return data['program']
    return None

  def stage(self,logfile):
    """Get the processing stage associated with a logfile"""
    data = self.lookupLogInfo(logfile)
    if data:
      return data['stage']
    return None

  def description(self,logfile):
    """Get the description associated with a logfile"""
    data = self.lookupLogInfo(logfile)
    if data:
      return data['description']
    return None

  def template(self,logfile):
    """Get the template associated with a logfile"""
    data = self.lookupLogInfo(logfile)
    if data:
      return data['template']
    return ""

  def baublize(self,logfile):
    """Get the value of the baublize flag for a logfile

    Returns a boolean value depending on whether baubles
    can be run on this log file (True) or not (False)."""
    data = self.lookupLogInfo(logfile)
    if data:
      return data['baublize']
    return False

  def stageForProgram(self,program):
    """Get the processing stage for a program"""
    for name in self.listNames():
      log_info = self.lookupLogInfo(name)
      if log_info['program'] == program:
        return log_info['stage']
    # No match
    return None

  def listNames(self):
    """Return a list of the log file name fragments in pipeline order

    'Pipeline order' is the order in which the log file
    information was added to the PipelineInfo object (i.e. the
    order in which the addLogInfo calls were made)."""
    names = []
    for item in self.__pipeline:
      names.append(item['logname'])
    return names

  def compareLogfilesByOrder(self,logfile1,logfile2):
    """Compare logfile names by pipeline position

    Provides a comparision function that can be used in a sorting
    function to compare two log file names 'logfile1' and 'logfile2',
    and return an integer value indicating the order that the
    log files should be according to the pipeline definition.

    Returns -1 if logfile1 appears before logfile2, 1 if logfile2
    appears after logfile1, and 0 otherwise."""
    # Locate the keywords in the list for both file names
    keywords = self.listNames()
    for i in range(0,len(keywords)):
      k = logfile1.find(keywords[i])
      if k > -1: break
    for j in range(0,len(keywords)):
      k = logfile2.find(keywords[j])
      if k > -1: break
    # Return value indicates order
    if i < j: return -1
    if i == j: return 0
    if i > j: return 1

# Citations
#
# Store and recover citation info
class Citations:
  """Information on citations

  Stores and retrieves additional information on links for citations in
  the xia2.txt file.

  Use the getCitation method to look up the URL associated with a
  citation.

  To add information on a new citation, add a new call to the
  addCitation method in __init__.
  Note that the citation text supplied in addCitation this must
  exactly match the text in the xia2.txt file for the associated
  link (if any) to be returned."""

  def __init__(self):
    """Create and initialise Citations object.

    Makes a new Citations object, and populates with information
    about citations for which there are associated URLs. No
    information is added for citations without associated URLs."""
    # Initialise storage of citation information
    self.__citations = []
    # CCP4
    self.addCitation(
        'ccp4',
        '(1994) Acta Crystallogr. D 50, 760--763',
        'http://journals.iucr.org/d/issues/1994/05/00/ad0004/ad0004.pdf')
    # Scala, pointless (same paper)
    self.addCitation(
        'pointless',
        'Evans, Philip (2006) Acta Crystallographica Section D 62, 72--82',
        'http://journals.iucr.org/d/issues/2006/01/00/ba5084/index.html')
    self.addCitation(
      'aimless',
      'P.R. Evans and G.N. Murshudov (2013) Acta Cryst. (2013). D69 1204--1214',
      'http://journals.iucr.org/d/issues/2013/07/00/ba5190/index.html')
    # Mosflm
    self.addCitation(
        'mosflm',
        'Leslie, Andrew G. W. (2006) Acta Crystallographica Section D 62, 48--57',
        'http://journals.iucr.org/d/issues/2006/01/00/ba5082/index.html')
    # labelit
    self.addCitation(
        'labelit',
        'Sauter, Nicholas K. and Grosse-Kunstleve, Ralf W. and Adams, Paul D. (2004) Journal of Applied Crystallography 37, 399--409',
        'http://journals.iucr.org/j/issues/2004/03/00/dd5008/index.html')
    # distl
    self.addCitation(
        'distl',
        'Zhang, Z. and Sauter, N.K. and van den Bedem, H. and Snell, G. and Deacon, A.M. (2006) J. Appl. Cryst 39, 112--119',
        'http://journals.iucr.org/j/issues/2006/01/00/ea5046/index.html')
    # XDS
    self.addCitation(
        'xds',
        'Kabsch, W. (1988) Journal of Applied Crystallography 21, 67--72',
        'http://journals.iucr.org/j/issues/1988/01/00/wi0022/wi0022.pdf')
    self.addCitation(
        'xds',
        'Kabsch, W. (1988) Journal of Applied Crystallography 21, 916--924',
        'http://journals.iucr.org/j/issues/1988/06/00/wi0031/wi0031.pdf')
    self.addCitation(
        'xds',
        'Kabsch, W. (1993) Journal of Applied Crystallography 26, 795--800',
        'http://journals.iucr.org/j/issues/1993/06/00/wi0124/wi0124.pdf')
    self.addCitation(
        'xia2',
        'Winter, G. (2010) Journal of Applied Crystallography 43',
        'http://journals.iucr.org/j/issues/2010/01/00/ea5113/index.html')

  def addCitation(self,program,citation,link):
    """Add citation info

    'program' is the name of the program that the citation
    refers to (not currently used).

    'citation' is the citation text - this must match exactly the
    text for the citation produced by xia2, for example
    'Winter, G. (2010) Journal of Applied Crystallography 43'.

    'link' is the URL link for the citation/paper, for example
    'http://journals.iucr.org/j/issues/2010/01/00/ea5113/index.html'.
    This can be set to None if there is no associated URL."""
    self.__citations.append({ "program": program,
                              "citation": citation,
                              "link": link })

  def getCitationLink(self,citation_text):
    """Get link for citation text

    Returns the stored URL associated with the supplied
    citation text, or None if the citation is not found."""
    for citation in self.__citations:
      if citation['citation'] == citation_text:
        return citation['link']
    # No match
    return None

#######################################################################
# Classes for organising data about the xia2 run
#######################################################################

# Xia2run
#
# Store information about a run of xia2
class Xia2run:
  """Xia2 run information

  The Xia2run object gathers information about a run of xia2
  from xia2.txt (like the LogFiles directory) and organises it
  into a data structure that can then be accessed for
  reporting purposes.

  Upon instantiation the Xia2run object will automatically
  attempt to gather the data from xia2.txt (by calling the
  __process_xia2dottxt method) and then organise these data
  (by calling the __populate method). Update these two methods
  to extend or modify the data that Xia2run gathers and stores.

  Use the 'complete' method to check if a Xia2run object
  successfully processed the data, and the 'finished' method to
  determine if xia2 actually completed.

  The data is organised into a hierarchy of crystals, datasets,
  sweeps and integration runs, with separate classes representing
  each level of the hierarchy. The 'crystals' method returns
  a list of Crystal objects, from where other levels of the
  hierarchy can be accessed.

  In addition other methods access information about the xia2 run
  (such as version, termination status, programs used and so on).
  The 'has_anomalous', 'multi_crystal' and 'xds_pipeline' methods
  give 'meta-information' about the run.

  Finally the 'logfiles' and 'refln_files' methods return lists
  of objects representing log files and reflections respectively."""

  def __init__(self,xia2_dir):
    """Create new Xia2run object

    'xia2_dir' is the directory containing the xia2 output
    (either relative or absolute)."""
    self.__xia2      = None
    self.__xia2_dir  = xia2_dir
    self.__version   = '' # xia2 version
    self.__cmd_line  = '' # Command line
    self.__run_time  = '' # Processing time
    self.__termination_status = '' # Termination status
    self.__xia2_journal = None # Journal file
    self.__log_dir   = None # Logfile directory
    self.__project_name= '' # Project name
    self.__datasets    = [] # List of datasets
    self.__crystals    = [] # List of crystals
    self.__logfiles    = [] # List of log files
    self.__refln_files = [] # List of reflection data files
    self.__programs_used = [] # List of programs/software used
    self.__citations   = [] # List of citations
    self.__has_anomalous = False # Anomalous data?
    self.__xds_pipeline  = False # XDS pipeline used?
    self.__multi_crystal = False # Run has multiple crystals?
    self.__pipeline_info = PipelineInfo() # Data about logfiles
    self.__int_status_key = '' # Text with key for integration status
    self.__run_finished = False # Whether run finished or not
    try:
      # Populate the object with data
      self.__process_xia2dottxt()
      self.__populate()
      self.__complete = True
    except:
      # Some problem
      print "Xia2run: processing/population failed"
      self.__complete = False

  def __process_xia2dottxt(self):
    """Internal: run text processor on xia2.txt

    Create a Magpie text processor object and use this to
    process the xia2.txt file."""
    self.__xia2 = Magpie.Magpie(verbose=False)
    # Define patterns
    # Each time a pattern is matched in the source document
    # a data item is created with the name attached to that
    # pattern
    #
    # xia2_version pattern
    #
    # An example of a matching line is:
    #XIA2 0.3.1.0
    self.__xia2.addPattern('xia2_version',
                           "XIA2 ([0-9.]+)$",
                           ['version'])
    # project_name pattern
    #
    # An example of a matching line is:
    #Project: AUTOMATIC
    self.__xia2.addPattern('project_name',"Project: (.*)$",['name'])
    #
    # sequence pattern
    #
    # An example of a matching line is:
    #Sequence: GIVEQCCASVCSLYQLENYCNFVNQHLCGSHLVEALYLVCGERGFFYTPKA
    self.__xia2.addPattern('sequence',"Sequence: ?(.*)$",['sequence'])
    #
    # wavelength pattern
    #
    # An example of a matching set of lines is:
    #Wavelength name: NATIVE
    #Wavelength 0.97900
    self.__xia2.addPattern('wavelength',
                           "Wavelength name: ([^\n]*)\nWavelength (.*)$",
                           ['name','lambda'])
    # xia2_used pattern
    #
    # An example of a matching line is:
    #XIA2 used...  ccp4 mosflm pointless scala xia2
    self.__xia2.addPattern('xia2_used',
                           "XIA2 used... ([^\n]*)",
                           ['software'])
    # processing_time pattern
    #
    # An example of a matching line is:
    #Processing took 00h 14m 24s
    self.__xia2.addPattern('processing_time',
                           "Processing took ([0-9]+h [0-9]+m [0-9]+s)",
                           ['time'])
    # xia2_status
    #
    # An example of a matching line is:
    #Status: normal termination
    self.__xia2.addPattern('xia2_status',
                           "Status: ([^\n]*)",
                           ['status'])
    # twinning pattern
    #
    # An example of a matching set of lines:
    #Overall twinning score: 1.86
    #Ambiguous score (1.6 < score < 1.9)
    self.__xia2.addPattern('twinning',
                           "Overall twinning score: ([^\n]+)\n([^\n]+)",
                           ['score','report'])
    # asu_and_solvent pattern
    #
    # An example of a matching set of lines:
    #Likely number of molecules in ASU: 1
    #Giving solvent fraction:        0.64
    self.__xia2.addPattern('asu_and_solvent',
                           "Likely number of molecules in ASU: ([0-9]+)\nGiving solvent fraction:        ([0-9.]+)",
                           ['molecules_in_asu','solvent_fraction'])
    # unit_cell pattern
    #
    # An example of a matching set of lines:
    #Unit cell:
    #78.013  78.013  78.013
    #90.000  90.000  90.000
    self.__xia2.addPattern('unit_cell',
                           "Unit cell:\n([0-9.]+) +([0-9.]+) +([0-9.]+)\n([0-9.]+) +([0-9.]+) +([0-9.]+)",
                    ['a','b','c','alpha','beta','gamma'])
    # command_line pattern
    #
    # An example of a matching line:
    #Command line: /home/pjb/xia2/Applications/xia2.py -xinfo demo.xinfo
    self.__xia2.addPattern('command_line',
                           "Command line: (.*)$",
                           ['cmd_line'])
    # scaled_refln_file patterns
    #
    # Pair of patterns with the same name but match slightly
    # different instances of the same information (reflection files)
    #
    # Example of first instance:
    #mtz format:
    #Scaled reflections: /path/to/xia2/DataFiles/blah_blah_free.mtz
    #
    # Example of second instance:
    #Scaled reflections (NATIVE): /path/to/xia2/DataFiles/blah_blah_scaled.sca
    self.__xia2.addPattern('scaled_refln_file',
                           '(mtz|sca|sca_unmerged) format:\nScaled reflections ?\(?([^\):]*)\)?: (.+)$',
                           ['format','dataset','filename'])
    self.__xia2.addPattern('scaled_refln_file',
                           "Scaled reflections ?\(?([^\):]*)\)?: (.+)$",
                           ['dataset','filename','format'])
    # sweep_to_dataset pattern
    #
    # An example of a matching line:
    # SWEEP NATIVE [WAVELENGTH NATIVE]
    self.__xia2.addPattern('sweep_to_dataset',
                           "SWEEP ([^ ]+) \[WAVELENGTH ([^\]]+)\]",
                           ['sweep','dataset'])
    # Block definitions
    #
    # A block is a contigious set of lines in the input text file
    # Block definitions consist of a name, and a pair of strings which
    # mark the beginning and end of the block
    # Optionally the lines containing the start and end delimiters
    # can be omitted from the block
    #
    # Each time a block is matched in the source document
    # a data item is created with the name attached to the definition
    self.__xia2.defineBlock('dataset_summary',
                            "For ",
                            "Total unique",
                            pattern="For ([^\n]*)\n(.+)",
                            pattern_keys=['dataset','table'])
    # assumed_spacegroup block
    #
    # An example of this is:
    #
    #Assuming spacegroup: I 2 3
    #Other likely alternatives are:
    #I 21 3
    #Unit cell:
    self.__xia2.defineBlock('assumed_spacegroup',
                            "Assuming spacegroup",
                            "Unit cell:",Magpie.EXCLUDE_END)
    # citations block
    #
    # An example might look like this:
    #
    #Here are the appropriate citations (BIBTeX in xia-citations.bib.)
    #(1994) Acta Crystallogr. D 50, 760--763
    #<snipped>
    #Winter, G. (2010) Journal of Applied Crystallography 43
    #Status: normal termination
    self.__xia2.defineBlock('citations',
                            "Here are the appropriate citations",
                            "Status",Magpie.EXCLUDE)
    # integration_status_per_image block
    #
    # An example of this is shown below, although there can be
    # some variation in the preamble:
    #
    #-------------------- Integrating SWEEP1 --------------------
    #Processed batches 1 to 90
    #Weighted RMSD: 0.89 (0.09)
    #Integration status per image (60/record):
    #oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
    #oooooooooooooooooooooooooooooo
    self.__xia2.defineBlock('integration_status_per_image',
                            "--- Integrating","ok",Magpie.EXCLUDE_END)
    # integration_status_key
    #
    # An example of this looks like:
    #
    #"o" => good        "%" => ok        "!" => bad rmsd
    #"O" => overloaded  "#" => many bad  "." => weak
    #"@" => abandoned
    self.__xia2.defineBlock('integration_status_key',"ok","abandoned")
    # interwavelength_analysis block
    #
    # There are two block definitions here with the same name
    # Example of "old style" table:
    #
    #Inter-wavelength B and R-factor analysis:
    #WAVE1   0.0 0.00 (ok)
    #WAVE2  -0.1 0.08 (ok)
    #WAVE3  -0.4 0.14 (ok)
    #
    self.__xia2.defineBlock('interwavelength_analysis',
                            "Inter-wavelength B and R-factor analysis",
                            "",Magpie.EXCLUDE)
    # Example of "new style" table:
    #
    #------------------ Local Scaling DEFAULT -------------------
    #WAVE1   0.0 0.00 (ok)
    #WAVE2  -0.3 0.08 (ok)
    #WAVE3  -2.5 0.15 (ok)
    #------------------------------------------------------------
    self.__xia2.defineBlock('interwavelength_analysis',
                            "-- Local Scaling ",
                            "--",Magpie.EXCLUDE)
    # radiation_damage
    #
    # Chef radiation damage analysis. An example of this looks
    # like:
    #
    #Group 1: 2-wedge data collection
    #Significant radiation damage detected:
    #Rd analysis (DEFAULT/WAVE1): 4.55
    #Conclusion: cut off after DOSE ~ 2161.5
    #
    # FIXME: This is commented out for now (and see also notes below)
    ##self.__xia2.defineBlock('radiation_damage',
    ##                        "Group",
    ##                        "Conclusion")
    # Say that in future the radiation damage analysis was
    # surrounded by a 'header' and 'footer' markup, e.g.:
    #
    #------------- Radiation Damage Analysis XTAL ---------------
    #Group 1: 2-wedge data collection
    #Significant radiation damage detected:
    #Rd analysis (DEFAULT/WAVE1): 4.55
    #Conclusion: cut off after DOSE ~ 2161.5
    #------------------------------------------------------------
    #
    # Then the following block definition would capture it:
    ##self.__xia2.defineBlock('radiation_damage',
    ##                        "-- Radiation Damage Analysis",
    ##                        "--")
    #
    # Process the xia2.txt file
    self.__xia2.processFile(os.path.join(self.__xia2_dir,"xia2.txt"))

  def __populate(self):
    """Internal: populate the data structure

    Attempt to populate the Xia2run object with the data extracted
    by __process_xia2dottxt, plus scanning of the LogFiles directory."""
    print "POPULATE> STARTED"
    xia2 = self.__xia2
    # xia2 and run information
    print "POPULATE> XIA2 INFO"
    # Termination status
    try:
      self.__termination_status = xia2['xia2_status'][0]['status']
      self.__run_finished = True
    except IndexError:
      # xia2 is still running or else terminated prematurely
      self.__termination_status = "incomplete"
      self.__run_finished = False
    # xia2 version
    try:
      self.__version = xia2['xia2_version'][0]['version']
    except IndexError:
      self.__version = "unknown"
    # Command line
    try:
      self.__cmd_line = xia2['command_line'][0]['cmd_line']
    except IndexError:
      self.__cmd_line = "unavailable"
    # Run time
    try:
      self.__run_time = xia2['processing_time'][0]['time']
    except IndexError:
      self.__run_time = 'unavailable'
    # Project name
    print "POPULATE> PROJECT NAME"
    self.__project_name = xia2['project_name'][0]['name']
    # Datasets
    print "POPULATE> DATASETS"
    for dataset in xia2['dataset_summary']:
      print "DATASETS> dataset: "+str(dataset.value('dataset'))
      self.__datasets.append(Dataset(dataset.value('dataset'),
                                     dataset.value('table')))
    # Assign wavelength (i.e. lambda) value to dataset
    print "POPULATE> WAVELENGTHS"
    for wavelength in xia2['wavelength']:
      for dataset in self.__datasets:
        if dataset.datasetName() == wavelength['name']:
          dataset.setWavelength(wavelength['lambda'])
          print "WAVELENGTHS> "+dataset.crystalName()+"/" +\
              dataset.datasetName()+": "+dataset.wavelength()
          break
    # Anomalous data?
    # Look for the "anomalous_completeness" data item in
    # the dataset summary table
    print "POPULATE> ANOMALOUS DATA"
    for dataset in self.__datasets:
      try:
        x = dataset['Anomalous completeness']
        self.__has_anomalous = True
        break
      except KeyError:
        pass
    # Crystals
    print "POPULATE> CRYSTALS"
    xtal_list = []
    for dataset in self.__datasets:
      xtal = dataset.crystalName()
      try:
        xtal_list.index(xtal)
      except ValueError:
        # Crystal not in list, add it
        xtal_list.append(xtal)
        # Create and store a crystal object
        self.__crystals.append(Crystal(xtal))
    # Associate crystal-specific data (e.g. unit cell etc)
    # with each crystal object
    nxtals = len(self.__crystals)
    for i in range(0,nxtals):
      crystal = self.__crystals[i]
      crystal.setUnitCellData(xia2['unit_cell'][i])
      crystal.setSpacegroupData(xia2['assumed_spacegroup'][i])
      crystal.setTwinningData(xia2['twinning'][i])
      crystal.setSequence(xia2['sequence'][i]['sequence'])
      try:
        crystal.setASUData(xia2['asu_and_solvent'][i])
      except IndexError:
        # Assume that this wasn't found
        pass
    # Assign datasets to crystals
    print "POPULATE> ASSIGN DATASETS TO CRYSTALS"
    for crystal in self.__crystals:
      for dataset in self.__datasets:
        if dataset.crystalName() == crystal.name():
          crystal.addDataset(dataset)
    # Sweeps and integration runs
    print "POPULATE> SWEEPS"
    # Assign (empty) sweeps to datasets
    for sweep_to_dataset in xia2['sweep_to_dataset']:
      dataset = self.__get_dataset(sweep_to_dataset['dataset'])
      this_sweep = sweep_to_dataset['sweep']
      new_sweep = True
      for sweep in dataset.sweeps():
        if sweep.name() == this_sweep:
          # Already exists
          new_sweep = False
          break
      if new_sweep:
        dataset.addSweep(Sweep(this_sweep))
        print "SWEEPS> new sweep "+this_sweep+" added to "+ \
            dataset.name()
    # Add integration runs to sweeps
    print "SWEEPS> "+str(xia2.count('integration_status_per_image'))+\
        " sweep integration records found"
    for int_status in xia2['integration_status_per_image']:
      # Create an integration run object
      integration_run = IntegrationRun(int_status)
      # Locate the Sweep object to assign this to
      for crystal in self.crystals():
        for dataset in crystal.datasets():
          for sweep in dataset.sweeps():
            if sweep.name() == integration_run.name():
              sweep.addIntegrationRun(integration_run)
              print "SWEEPS> run assigned to sweep "+sweep.name()
              break
    # Store the raw text of the key to the symbols
    print "POPULATE> INTEGRATION STATUS KEY"
    if xia2.count('integration_status_key'):
      self.__int_status_key = str(xia2['integration_status_key'][0])
    # Assign interwavelength analysis data
    # Only crystals with more than one dataset will also
    # have this information
    print "POPULATE> INTERWAVELENGTH ANALYSIS"
    i = 0
    for crystal in self.__crystals:
      # Assign interwavelength analysis data
      if len(crystal.datasets()) > 1:
        crystal.setInterwavelengthAnalysis(
            xia2['interwavelength_analysis'][i])
        i = i+1
    # Assign radiation damage analysis to crystals
    print "POPULATE> RADIATION DAMAGE ANALYSIS"
    if not xia2.count('radiation_damage'):
      print "No radiation damage analyses found"
    for analysis in xia2['radiation_damage']:
      radiation_damage = RadiationDamageAnalysis(analysis)
      # Assign to crystal
      for crystal in self.__crystals:
        if crystal.name() == radiation_damage.xtal_name():
          print "Assigned to "+crystal.name()
          crystal.setRadiationDamage(radiation_damage)
          break
    # Assign multi-crystal flag
    if nxtals > 1: self.__multi_crystal = True
    # Logfiles
    # Look in the xia2 LogFiles directory
    print "POPULATE> LOGFILES"
    self.__log_dir = os.path.abspath(os.path.join(xia2dir,"LogFiles"))
    logdir = get_relative_path(self.__log_dir)
    # Process logfiles
    try:
      files = self.__list_logfiles()
      for filen in files:
        print "LOGFILES> "+str(filen)
        log = LogFile(os.path.join(logdir,filen),
                      self.__pipeline_info)
        if log.isLog():
          # Store the log file
          self.__logfiles.append(log)
        else:
          print "LOGFILES> "+log.basename()+ \
                " not a log file, ignored"
    except OSError:
      # Possibly the LogFiles directory doesn't exist
      if not os.path.isdir(logdir):
        print "LOGFILES> LogFiles directory not found"
      else:
        raise
    # Assign log files to crystals, datasets (and sweeps)
    print "POPULATE> ASSIGN LOG FILES TO CRYSTALS, DATASETS ..."

    for log in self.__logfiles:
      print "LOGFILE> checking "+str(log.basename())
      # Fetch the template
      template = self.__pipeline_info.template(log.basename())
      # Test name combinations until we find a match
      for crystal in self.__crystals:
        for dataset in crystal.datasets():
          for sweep in dataset.sweeps():
            # Kludge to skip template matching if the crystal
            # has already been assigned
            if log.crystal():
              continue
            # Substitute names and look for a match
            name = template. \
                replace("<PROJECT>",self.__project_name). \
                replace("<CRYSTAL>",crystal.name()). \
                replace("<DATASET>",dataset.datasetName()). \
                replace("<SWEEP>",sweep.name())
            if log.basename() == name:
              # Found a match
              assign_project = None
              assign_crystal = None
              assign_dataset = None
              assign_sweep = None
              if template.count("<PROJECT>"):
                assign_project = self.__project_name
              if template.count("<CRYSTAL>"):
                assign_crystal = crystal.name()
              if template.count("<DATASET>"):
                assign_dataset = dataset.datasetName()
              if template.count("<SWEEP>"):
                assign_sweep = sweep.name()
              log.assign(assign_project,
                         assign_crystal,
                         assign_dataset,
                         assign_sweep)
              print "LOGFILE> assigned: "+str(assign_project)+\
                  " "+str(assign_crystal)+\
                  " "+str(assign_dataset)+\
                  " "+str(assign_sweep)
    # Reflection files
    print "POPULATE> REFLECTION FILES"
    refln_formats = []
    refln_files = {}
    refln_format = None
    for refln_file in xia2['scaled_refln_file']:
      filen = refln_file.value('filename')
      print "REFLN_FILE> file   : "+filen
      if refln_file.value('format'):
        # Format is already defined so collect it
        refln_format = refln_file.value('format')
        # Store locally by format so that we can build a
        # single list sorted by format later
        if not refln_formats.count(refln_format):
          refln_formats.append(refln_format)
          refln_files[refln_format] = []
      print "REFLN_FILE> format : "+refln_format
      refln_dataset = refln_file.value('dataset')
      print "REFLN_FILE> dataset: "+str(refln_dataset)
      # Store the data by format for now
      refln_files[refln_format].append(ReflectionFile(filen,
                                                      refln_format,
                                                      refln_dataset))
    # Put all the data together into a single list
    # This is implicitly sorted into format/crystal/dataset order
    for format in refln_formats:
      for refln_file in refln_files[format]:
        self.__refln_files.append(refln_file)
    # Journal file xia2-journal.txt
    print "POPULATE> JOURNAL_FILE"
    self.__xia2_journal = os.path.join(self.__xia2_dir,
                                       "xia2-journal.txt")
    if not os.path.isfile(self.__xia2_journal):
      self.__xia2_journal = None
    # List of programs/software used
    print "POPULATE> SOFTWARE USED"
    for prog in xia2['xia2_used'][0]['software'].split():
      self.__programs_used.append(prog)
    # List of citations
    print "POPULATE> CITATIONS"
    for line in str(xia2['citations'][0]).split('\n'):
      citation = line.strip()
      if citation != "":
        self.__citations.append(citation)
    # XDS pipeline flag
    print "POPULATE> XDS PIPELINE"
    if self.programs_used().count('xds'):
      # If xds is listed as a program then update flags etc
      self.__xds_pipeline = True
      self.__pipeline_info.setXDSPipeline()
    print "POPULATE> FINISHED"

  def __get_dataset(self,dataset_name):
    """Internal: lookup a Dataset object with the supplied name

    'dataset_name' can be either the 'long' version of the name
    (which includes project and crystal qualifiers) or the 'short'
    version (which only has the dataset name).

    Note that an assumption is made that dataset names are unique
    across crystals.

    Returns None if no match was located."""
    for xtal in self.crystals():
      for dataset in xtal.datasets():
        if dataset.name() == dataset_name:
          # Matched long name (including project and crystal)
          return dataset
        elif  dataset.datasetName() == dataset_name:
          # Matched short name (no crystal qualifier)
          return dataset
    # No match
    return None

  def __list_logfiles(self):
    """Internal: get list of xia2 log files in pipeline order

    This fetches a list of the files in the LogFiles directory,
    sorted into order according to the comparision function
    in the PipelineInfo object."""
    # Get unsorted list of file names
    files = os.listdir(self.__log_dir)
    # Sort list on order of file names within the pipeline
    files.sort(self.__pipeline_info.compareLogfilesByOrder)
    return files

  def xia2_dir(self):
    """Return the directory where xia2.txt was found

    Returns the name of the directory supplied on instantiation,
    where the xia2 output is located."""
    return self.__xia2_dir

  def version(self):
    """Return the xia2 version from xia2.txt"""
    return self.__version

  def run_time(self):
    """Return the processing time from xia2.txt"""
    return self.__run_time

  def termination_status(self):
    """Return the termination status from xia2.txt"""
    return self.__termination_status

  def cmd_line(self):
    """Return the command line from xia2.txt"""
    return self.__cmd_line

  def programs_used(self):
    """Return the list of programs/software used in the run from xia2.txt"""
    return self.__programs_used

  def citations(self):
    """Return the list of citations from xia2.txt"""
    return self.__citations

  def complete(self):
    """Check if the Xia2run object is complete

    If there were any errors during processing then this
    method will return False, otherwise this will return
    True."""
    return self.__complete

  def has_anomalous(self):
    """Check whether anomalous data is available

    Returns True if anomalous statistics were found for at
    least one dataset, False otherwise."""
    return self.__has_anomalous

  def xds_pipeline(self):
    """Check whether the run used the 'XDS pipeline'

    Returns True if XDS was identified as one of the programs
    used in the xia2 run."""
    return self.__xds_pipeline

  def multi_crystal(self):
    """Check whether the run contains multiple crystals

    Returns True if the run contained data from more than
    one crystal. (To find out how many crystals do e.g.
    len(Xia2run.crystals()).)"""
    return self.__multi_crystal

  def finished(self):
    """Check whether the run completed or not

    Returns True if a termination status line was found in
    xia2.txt (indicating that xia2 completed)."""
    return self.__run_finished

  def log_dir(self):
    """Return location of the xia2 LogFiles directory

    This is the absolute path for the xia2 logfile directory."""
    return self.__log_dir

  def project_name(self):
    """Return the project name extracted from the xia2.txt file"""
    return self.__project_name

  def crystals(self):
    """Return Crystals for the run

    This returns a list of the Crystal objects representing
    crystals that were found in the output. See the Crystal
    class for information on its methods."""
    return self.__crystals

  def logfiles(self):
    """Return LogFiles for the run

    Returns a list of the LogFile objects representing the
    log files found in the xia2 LogFiles directory. See the
    LogFile class for information on its methods."""
    return self.__logfiles

  def refln_files(self):
    """Return ReflectionFiles for the run

    Returns a list of the ReflectionFile objects representing
    the reflection data files referenced in xia2.txt. See the
    ReflectionFile class for information on its methods."""
    return self.__refln_files

  def journal_file(self):
    """Return name of the journal file for the run

    Returns the full path of the xia2-journal.txt file, if one
    exists - otherwise returns None."""
    return self.__xia2_journal

  def integration_status_key(self):
    """Return the text for the key of integration status icons

    The key is the block of text from xia2.txt which identifies
    the possible integration status symbols and their meanings,
    e.g 'o' => good etc"""
    return self.__int_status_key

# Crystal
#
# Store information about a crystal
class Crystal:
  """Xia2 crystal information

  Store and retrieve the information associated with a crystal,
  specifically: unit cell, spacegroup information, twinning
  analysis, ASU content, sequence, interwavelength analysis and
  radiation damage analysis.

  Also store references to the datasets measured from the
  crystal."""

  def __init__(self,name):
    """Create a new Crystal object

    'name' is the name associated with the crystal in the
    xia2 run. Other data are added subsequently using the
    'set...Data' methods (e.g. 'setUnitCellData').

    Dataset objects are attached to the Crystal using
    addDataset. The list of Dataset objects can be retrieved
    using the 'dataset' method."""
    self.__name = str(name)
    self.__unit_cell  = None
    self.__spacegroup = None
    self.__alt_spacegroups = []
    self.__twinning_score = None
    self.__twinning_report = ''
    self.__mols_in_asu = None
    self.__solvent_frac = None
    self.__sequence = None
    self.__interwavelength_analysis = None
    self.__radiation_damage_analyses = []
    self.__datasets = []

  def name(self):
    """Return the crystal name"""
    return self.__name

  def spacegroup(self):
    """Return the assumed spacegroup"""
    return self.__spacegroup

  def alt_spacegroups(self):
    """Return the list of alternative spacegroups"""
    return self.__alt_spacegroups

  def unit_cell(self):
    """Return the unit cell data

    This returns the Magpie.Data object supplied via the
    setUnitCellData call. The individual unit cell
    parameters can be accessed using e.g.:

    a    = Crystal.unit_cell()['a']
    beta = Crystal.unit_cell()['beta']

    etc."""
    return self.__unit_cell

  def twinning_score(self):
    """Return the twinning score"""
    return self.__twinning_score

  def twinning_report(self):
    """Return the twinning report

    This is text of the form 'Your data does not appear to be
    twinned', as extracted from the xia2.txt file."""
    return self.__twinning_report

  def molecules_in_asu(self):
    """Return the number of molecules in the ASU"""
    return self.__mols_in_asu

  def solvent_fraction(self):
    """Return the solvent fraction"""
    return self.__solvent_frac

  def sequence(self):
    """Return the sequence"""
    return self.__sequence

  def interwavelength_analysis(self):
    """Return the interwavelength analysis data"""
    return self.__interwavelength_analysis

  def radiation_damage_analyses(self):
    """Return the radiation damage analysis data

    This is a list of RadiatioDamageAnalysis objects that
    have been assigned to the crystal. The list will be
    empty if no analyses were assigned."""
    return self.__radiation_damage_analyses

  def datasets(self):
    """Return the list of Dataset objects"""
    return self.__datasets

  def setUnitCellData(self,unit_cell):
    """Set the unit cell data

    'unit_cell' should be the Magpie.Data object with the
    unit cell data collected from xia2.txt."""
    self.__unit_cell = unit_cell

  def setSpacegroupData(self,spacegroup_data):
    """Set the spacegroup data

    'spacegroup_data' is the text extracted from xia2.txt
    pertaining to the spacegroup determination. It is
    reprocessed and the results can be accessed via the
    spacegroup() and alt_spacegroups() methods."""
    # Post-process the assumed spacegroup block using a text-based
    # Magpie processor specifically for this block
    spg_processor = Magpie.Magpie()
    spg_processor.addPattern('spacegroup',
                             "Assuming spacegroup: (.*)$",['name'])
    spg_processor.addPattern('alternative',
                             "([PCFI/abcdmn0-9\- ]+)$",['name'])
    spg_processor.processText(str(spacegroup_data))
    # Set the appropriate class properties
    self.__spacegroup = spg_processor['spacegroup'][0].value('name')
    self.__alt_spacegroups = []
    for alt in spg_processor['alternative']:
      self.__alt_spacegroups.append(alt.value('name'))
    return

  def setTwinningData(self,twinning_data):
    """Set the twinning data

    'twinning_data' is the Magpie.Data object with the
    twinning information extracted from xia2.txt."""
    self.__twinning_score = twinning_data['score']
    self.__twinning_report = twinning_data['report']

  def setASUData(self,asu_data):
    """Set the asymmetric unit data

    'asu_data' is the Magpie.Data object with the ASU
    data (i.e. number of molecules in the ASU and solvent
    fraction) extracted from xia2.txt."""
    self.__mols_in_asu = asu_data['molecules_in_asu']
    self.__solvent_frac = asu_data['solvent_fraction']

  def setSequence(self,sequence):
    """Store the sequence data

    'sequence' is the sequence string from the 'sequence'
    Magpie.Data object."""
    self.__sequence = sequence

  def setInterwavelengthAnalysis(self,interwavelength_analysis):
    """Store the interwavelength analysis table

    'interwavelength_analysis' is an 'interwavelength_analysis'
    Magpie.Data object."""
    self.__interwavelength_analysis = str(interwavelength_analysis)

  def setRadiationDamage(self,radiation_damage):
    """Store the radiation damage analysis from chef

    'radiation_damage' is a populated RadiationDamageAnalysis
    object."""
    self.__radiation_damage_analyses.append(radiation_damage)

  def addDataset(self,dataset):
    """Add a Dataset object to the Crystal

    'dataset' is an existing Dataset object, which is added to
    the list of Dataset objects associated with the crystal.
    Retrieve the list of Dataset objects using the datasets()
    method."""
    self.__datasets.append(dataset)

# Dataset
#
# Store information about a dataset
class Dataset(Magpie.Tabulator):
  """Xia2 dataset information

  Store the data about a dataset from the xia2 run, and provide
  methods to access that data.

  The Dataset class is a subclass of Magpie.Tabulator. After the
  Dataset object has been instantiated with the statistics table
  from xia2.txt, the 'rows' of the table are made available as
  elements of the Dataset object.

  For example, if the statistics table includes the following rows:
  ...
  High resolution limit                       1.21    5.41    1.21
  Low resolution limit                        39.15   39.15   1.24
  ...

  then these can be accessed using:

  Dataset['High resolution limit']
  Dataset['Low resolution limit']

  and individual values in the row can be accessed using positional
  indices. For example:

  Dataset['High resolution'][1]

  will return '1.21'. Dataset.keys() will return a list of the keys
  for each of the table, in the order that they appear in the table.

  Additionally the Dataset object also stores:

  * Wavelength associated with the dataset,
  * List of sweeps,
  * Associated project and crystal names."""

  def __init__(self,name,statistics_table):
    """Create and initialise a Dataset object

    'name' is the fully qualified name of the dataset from xia2.txt,
    i.e. with the leading project and crystal names (for example,
    'TS01/13140/LREM').

    'statistics_table' is the table of statistics from Aimless
    for the dataset (reproduced in xia2.txt), which typically
    starts:
    High resolution limit                           1.21    5.41    1.21
    Low resolution limit                            39.15   39.15   1.24
    Completeness                                    89.0    96.0    25.1
    ..etc etc.."""
    self.__name = str(name)
    self.__wavelength = None
    self.__statistics_table = statistics_table
    # List of Sweep objects
    self.__sweeps = []
    # Instantiate the base class and populate the data structure
    Magpie.Tabulator.__init__(self,self.__statistics_table)

  def name(self):
    """Return the full name

    The fully qualified dataset name, which includes the project
    and crystal names prepended to the dataset name, i.e.
    project/crystal/dataset"""
    return self.__name

  def setWavelength(self,wavelength):
    """Set the wavelength for the dataset"""
    self.__wavelength = wavelength

  def wavelength(self):
    """Return the wavelength (lambda)"""
    return self.__wavelength

  def datasetName(self):
    """Return the dataset name

    This is the dataset name without the leading project/crystal
    part (i.e. the trailing part of the full name)."""
    names = self.__name.split('/')
    dataset_name = names[-1]
    return dataset_name

  def crystalName(self):
    """Return the crystal name

    The name of the crystal that the dataset is associated with.
    This is the middle part of the fully qualified dataset name.

    NB if there are fewer than 3 components in the fully qualified
    name then None is returned."""
    names = self.__name.split('/')
    if len(names) == 3:
      crystal_name = names[1]
    else:
      crystal_name = None
    return crystal_name

  def projectName(self):
    """Return the project name

    This is the leading part of the full name
    (which we expect has the form project/crystal/dataset)

    NB if there are fewer than 3 components in the fully qualified
    name then None is returned."""
    names = self.__name.split('/')
    if len(names) == 3:
      project_name = names[0]
    else:
      project_name = None
    return project_name

  def statistics_table(self):
    """Return the table of statistics

    Invokes the 'table' method provided by the Tabulator
    superclass to return the 'raw' table that was supplied
    when the Dataset object was instantiated."""
    return self.table()

  def addSweep(self,sweep):
    """Add a sweep to the dataset

    'sweep' is a Sweep object.

    Note: the sweeps are automatically sorted into
    alphanumerical order."""
    self.__sweeps.append(sweep)
    self.__sweeps.sort(self.__cmp_sweeps_by_name)

  def sweeps(self):
    """Return the list of sweeps

    This is a list of Sweep objects that have been associated
    with the Dataset via addSweep method calls."""
    return self.__sweeps

  def __cmp_sweeps_by_name(self,sweep1,sweep2):
    """Internal: comparision function for sorting sweeps

    Compares the two Sweep objects 'sweep1' and 'sweep2'
    and returns an integer value depending on the ordering
    of the names.

    Used to put the Sweeps in order inside the Dataset."""
    if sweep1.name() <  sweep2.name(): return -1
    if sweep1.name() == sweep2.name(): return 0
    if sweep1.name() >  sweep2.name(): return 1
    return

# Sweep
#
# Store information about an individual sweep
class Sweep:
  """Store information about a sweep reported in the xia2 output

  In xia2 a dataset consists of one or more 'sweeps' of data,
  and each sweep may be integrated multiple times.

  In Xia2html each Sweep object is essentially a container for
  the integration runs (represented by a list of IntegrationRun
  objects) performed on the data."""

  def __init__(self,name):
    """Create a new Sweep object

    'name' is the name of the sweep as it appears in the xia2
    output."""
    self.__name = name
    self.__integration_runs = []

  def name(self):
    """Return the name of the sweep"""
    return self.__name

  def addIntegrationRun(self,integration_run):
    """Append an integration run to this Sweep

    'integration_run' is a populated IntegrationRun object
    which is appended to the list of runs for this
    sweep."""
    self.__integration_runs.append(integration_run)

  def last_integration_run(self):
    """Return the last integration run

    Returns the last IntegrationRun object added to the
    sweep."""
    if len(self.__integration_runs):
      return self.__integration_runs[-1]
    return None

# IntegrationRun
#
# Store and manage information about an integration run for a sweep
class IntegrationRun:
  """Store information about an integration run for a sweep

  Each sweep of data may be integrated multiple times by xia2.
  The IntegrationRun class stores information about one of
  these integration passes, specifically: associated sweep name,
  the start and end batch numbers and the 'image status line' (i.e.
  the lines of characters representineg the status of each image)."""

  def __init__(self,sweep_data):
    """Create and populate a new IntegrationRun object

    'sweep_data' is a Magpie.Data object for the
    'integration_status_per_image' pattern. The data in
    this object is automatically extracted and stored in
    the new IntegrationRun object."""
    self.__name = None
    self.__start_batch = '0'
    self.__end_batch = '0'
    self.__image_status = ''
    self.__symbol_key = {}
    self.__symbol_list = []
    # Extract and store the sweep data using a Magpie processor
    # to break up the supplied data
    status_processor = Magpie.Magpie()
    status_processor.addPattern('sweep',
                                "-+ Integrating ([^ ]*) -+",
                                ['name'])
    status_processor.addPattern('batch',
                                "Processed batches ([0-9]+) to ([0-9]+)",
                                ['start','end'])
    status_processor.addPattern('status_per_image',
                                "([oO%#!@]+)$")
    # Reprocess the supplied text
    status_processor.processText(str(sweep_data))
    # Extract and store the data
    self.__name = status_processor['sweep'][0]['name']
    try:
      self.__start_batch = status_processor['batch'][0]['start']
      self.__end_batch = status_processor['batch'][0]['end']
    except IndexError:
      # Couldn't get batch numbers
      pass
    # Symbols showing image status
    for line in status_processor['status_per_image']:
      self.__image_status += str(line) + "\n"
    self.__image_status = self.__image_status.strip('\n')

  def name(self):
    """Return the name of the sweep associated with the integration run"""
    return self.__name

  def start_batch(self):
    """Return the start batch number"""
    return self.__start_batch

  def end_batch(self):
    """Return the end batch number"""
    return self.__end_batch

  def image_status(self):
    """Return the image status line

    This is the string of symbols representing the integration
    status of each image in the run as found in the xia2.txt file,
    for example:

    oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
    oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
    oooooooooo%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    """
    return self.__image_status

  def countSymbol(self,symbol):
    """Return the number of times a symbol appears

    Given a 'symbol' (e.g. 'o','%' etc), returns the number of
    times that symbol appears in the status line for this
    integration run"""
    return self.__image_status.count(symbol)

# LogFile
#
# Store information about a log file and provide tools for
# analysis, annotation etc
class LogFile:
  """Xia2 log file information

  Stores and retrieves information about a log file associated with
  a xia2 run."""

  def __init__(self,logfile,pipeline_info):
    """Create a new LogFile object.

    'filen' is the name and path of the log file.

    'pipeline_info' is a PipelineInfo object which is
    used to look up data such as the associated program,
    description, processing stage and so on."""
    self.__filen = logfile
    # Smartie log object
    self.__smartie_log = None
    # PipelineInfo object
    self.__pipeline = pipeline_info
    # Crystal etc assignment
    self.__project = None
    self.__crystal = None
    self.__dataset = None
    self.__sweep   = None

  def assign(self,project,crystal,dataset,sweep):
    """Set the project, crystal, dataset and sweep names

    Stores the names supplied for the associated project, crystal,
    dataset and sweep. If no sweep or dataset is associated with
    the log file then 'None' should be specified for that name.

    The 'crystal', 'dataset' and 'sweep' are used to retrieve the
    assigned names."""
    self.__project = project
    self.__crystal = crystal
    self.__dataset = dataset
    self.__sweep = sweep

  def basename(self):
    """Return the filename without any leading directory"""
    return os.path.basename(self.__filen)

  def fullFileName(self):
    """Return the full filename with the leading (absolute) path"""
    return os.path.join(self.absoluteDirPath(),self.basename())

  def relativeName(self):
    """Return the filename relative to the current directory"""
    return os.path.join(self.relativeDirPath(),self.basename())

  def dir(self):
    """Return directory that the log file is in"""
    return os.path.dirname(self.__filen)

  def absoluteDirPath(self):
    """Return the absolute directory for the log file"""
    return os.path.abspath(self.dir())

  def relativeDirPath(self):
    """Return the directory for the log file relative to cwd"""
    return get_relative_path(self.absoluteDirPath())

  def isLog(self):
    """Test whether file is a log file

    The test is very basic: if the file name ends with a .log
    extension then it's assumed to be a log file, otherwise its
    not.

    Return True if file is a log file by this test, False if not."""
    return os.path.splitext(self.__filen)[1] == ".log"

  def program(self):
    """Return program name associated with this log file"""
    return self.__pipeline.program(self.__filen)

  def description(self):
    """Return log file description associated with the name"""
    return self.__pipeline.description(self.__filen)

  def processing_stage(self):
    """Return the processing stage that this log file belongs to"""
    return self.__pipeline.stage(self.__filen)

  def crystal(self):
    """Return crystal name associated with this log file"""
    return self.__crystal

  def dataset(self):
    """Return dataset name associated with this log file"""
    return self.__dataset

  def sweep(self):
    """Return sweep name associated with this log file"""
    return self.__sweep

  def smartieLog(self):
    """Return the smartie logfile object

    Returns the smartie logfile object (it may have to
    generate it first) if appropriate; otherwise, return None"""
    if not self.__pipeline.baublize(self.__filen):
      # Don't run baubles on this log
      print "Not running smartie for "+self.basename()
      return None
    if not self.__smartie_log:
      # Create and store a smartie logfile object
      print "Creating smartie logfile object for "+str(self.basename())
      self.__smartie_log = smartie.parselog(self.__filen)
      # Check for errors with table parsing
      nprograms = self.__smartie_log.nfragments()
      for i in range(0,nprograms):
        prog = self.__smartie_log.fragment(i)
        for tbl in prog.tables():
          if tbl.parse_error():
            prog.addkeytext(name="Warning",
                            message="Badly formed table: "+
                            tbl.title())
            print "*** TABLE PARSE ERROR DETECTED ***"
    return self.__smartie_log

  def baublize(self,target_dir=None):
    """Generate baublized HTML version of the log

    Returns the name of the HTML file, or None if the
    log wasn't baublized.

    The baublized file will be created in 'target_dir'
    if specified, or in the current working directory
    otherwise."""
    smartie_log = self.smartieLog()
    if not smartie_log: return None
    htmlfile = os.path.join(target_dir,
                            os.path.splitext(self.basename())[0]+
                            ".html")
    try:
      # Set the location of the Jloggraph applet explicitly
      baubles.setJLoggraphCodebase('.')
      # Run baubles on the processed log
      baubles.baubles(smartie_log,htmlfile)
      return htmlfile
    except:
      # Some baubles error - return None
      print "Error running baubles on "+str(self.__filen)
      return None

  def warnings(self):
    """Return list of warnings from smartie log file"""
    smartie_log = self.smartieLog()
    if not smartie_log: return []
    warnings = []
    nkeytexts = smartie_log.nkeytexts()
    for i in range(0,nkeytexts):
      if smartie_log.keytext(i).name() == "Warning":
        warnings.append(smartie_log.keytext(i))
    return warnings

# ReflectionFile
#
# Store information about a reflection data file
class ReflectionFile:
  """Reflection data file reference

  Store the information pertaining to a reflection data file
  referenced in the xia2 output."""

  def __init__(self,filename,format,dataset_name):
    """Create a ReflectionFile object

    'filename' is the name of the reflection data file,
    'format' is the format (e.g. mtz) and 'dataset_name'
    identifies the dataset that it relates to.

    Note: if 'dataset_name' is given as None or an empty
    string then the stored name will be 'All datasets'."""
    self.__filename = filename
    self.__format = format
    if not dataset_name:
      self.__dataset_name = "All datasets"
    else:
      self.__dataset_name = dataset_name
    # Internal data
    self.__format_useful_for = { "mtz": "CCP4 and Phenix",
                                 "sca": "AutoSHARP etc",
                                 "sca_unmerged": "XPREP and Shelx C/D/E" }

  def filename(self):
    """Return the filename that was supplied on creation"""
    return self.__filename

  def basename(self):
    """Return the basename of the file i.e. no leading directory"""
    return os.path.basename(self.__filename)

  def format(self):
    """Return the format of the reflection file"""
    return self.__format

  def dataset(self):
    """Return the dataset name that the file belongs to"""
    return self.__dataset_name

  def crystal(self):
    """Return the crystal that the file belongs to

    This is extracted from the file name, which is assumed to be
    of the form <project>_<crystal>_..."""
    return self.basename().split('_')[1]

  def useful_for(self):
    """Return description of the what the file can be used for

    This returns a text description of what the file can be
    used for.

    NB The descriptions are taken from a look-up table that is
    internal to the ReflectionFile class. To modify see the
    __init__ method of this class."""
    return self.__format_useful_for[self.format()]

# RadiatioDamageAnalysis
#
# Process and store information about radiation damage analysis
class RadiationDamageAnalysis:
  """Process an radiation damage analysis report and store data

  Given 'raw' radiation damage analysis data from xia2.txt, this
  class extracts information and makes it available for retrieval."""

  def __init__(self,radiation_damage):
    """Create a new RadiationDamageAnalysis object

    'radiation_damage' is the Magpie.Data object with the 'raw'
    radiation damage analysis data from xia2.txt."""
    self.__xtal_name = None
    self.__dataset_names = []
    self.__group_ids = []
    self.__group_descriptions = []
    self.__report = ''
    self.__conclusion = ''
    self.__table = None
    # Process the radiation damage report using a text-based
    # Magpie processor specifically for this block
    print "Radiation damage = "+str(radiation_damage)
    processor = Magpie.Magpie(verbose=False)
    # Set up patterns to match the text
    #
    # group
    # matches lines like:
    # Group 1: 2-wedge data collection
    processor.addPattern('group',
                         "Group ([0-9]):(.*)",
                         ['id','description'])
    # analysis_report
    # matches lines like:
    # Significant radiation damage detected:
    processor.addPattern('analysis_report',
                         "(No s|S)ignificant radiation damage detected(:?)")
    # analysis_row
    # matches lines like:
    #Rd analysis (DEFAULT/WAVE1): 4.55
    processor.addPattern('analysis_row',
                         "Rd analysis \(([^/]+)/([^\)]+)\): ([0-9.]+)",
                         ['xtal','dataset','value'])
    # conclusion
    # matches lines like:
    #Conclusion: cut off after DOSE ~ 2161.5
    processor.addPattern('conclusion',
                         "Conclusion: (.*)",
                         ['conclusion'])
    # Do the processing and set the class properties based
    # on extracted data
    processor.processText(str(radiation_damage))
    # Set the appropriate class properties
    for group in processor['group']:
      self.__group_ids.append(group['id'])
      self.__group_descriptions.append(group['description'])
    self.__report = str(processor['analysis_report'][0])
    self.__conclusion = processor['conclusion'][0]['conclusion']
    try:
      # Build a raw text table of the analysis
      tbl = ''
      for row in processor['analysis_row']:
        tbl += str(row['xtal'])+"\t"+\
               str(row['dataset'])+"\t"+\
               str(row['value'])+"\n"
        # Also store crystal and dataset names
        self.__xtal_name = str(row['xtal'])
        self.__dataset_names.append(str(row['dataset']))
        print "XTAL: "+self.xtal_name()+" DATASET: "+\
            self.dataset_names()[-1]
      self.__table = tbl.strip("\n")
    except KeyError:
      # No analysis rows found - skip
      pass

  def xtal_name(self):
    """Return the associated crystal name for this analysis"""
    return self.__xtal_name

  def dataset_names(self):
    """Return a list of the associated dataset names"""
    return self.__dataset_names

  def ids(self):
    """Return the group ids"""
    return self.__group_ids

  def descriptions(self):
    """Return the group descriptions"""
    return self.__group_descriptions

  def report(self):
    """Return the report from the radiation damage analysis"""
    return self.__report

  def conclusion(self):
    """Return the conclusion of the radiation damage analysis"""
    return self.__conclusion

  def table(self):
    """Return text-based table from radiation damage analysis"""
    return self.__table

#######################################################################
# Classes for generating the output HTML document
#######################################################################

# Xia2doc
#
# Build the xia2.html document
class Xia2doc:
  """Class for generating the output xia2.html report

  Upon instantiation this class will automatically try to generate
  the xia2.html report as well as the xia2_html output directory
  and HTML versions of log files, It will also copy the Jloggraph.jar
  and icon files to the xia2_html directory.

  The content of the report will be generated by an automatic
  invocation of either the reportRun() method (if the xia2 run appeared
  to be successful) or reportIncompleteRun() method (if it appeared to
  fail).

  The reportRun method populates the document skeleton (which is
  created by initialiseDocument) by calling various report...
  methods (e.g. reportXtallographicData) which generate content
  for individual sections. (Some of these report... methods
  themselves call other report... methods to generate content
  for subsections.)

  Sections within the document appear in the order that they are
  created (similarly, subsections within individual sections appear in
  the order that they are added to the section, and so on).
  Reordering sections within a document therefore require changes
  either in InitialiseDocument (where the skeleton document is
  created), or else within reportRun/report<thing> cascade of methods.

  The HTML document building is done using the Document class from
  the Canary module. The Xia2doc class also has some utility methods
  to add warnings and informational sections, and for making new
  document sections and internal anchors.

  Once the Xia2doc object has been instantiated, the status() method
  can be used to determine whether a report was generated for a
  successful or unsuccessful run. (Note that a run that is in progress
  is likely to be reported as 'unsuccessful' by the Xia2doc object.)"""

  def __init__(self,xia2run):
    """Create a new Xia2doc object

    'xia2run' is a populated Xia2run object which stores the
    data from a run of xia2."""
    # Store Xia2run object
    self.__xia2run = xia2run
    # Collect the XIA2HTML environment variable setting
    self.__xia2htmldir = os.environ['XIA2HTMLDIR']
    print "XIA2HTMLDIR => %s" % self.__xia2htmldir
    # Relative and absolute paths for xia2_html directory
    self.__xia2_html_dir = "xia2_html"
    self.__xia2_html = os.path.join(os.getcwd(),self.__xia2_html_dir)
    if not os.path.isdir(self.__xia2_html):
      # Try to make the directory
      print "Making output subdirectory %s" % self.__xia2_html
      os.mkdir(self.__xia2_html)
    # Source directory where icons are located
    self.__icondir = os.path.join(self.__xia2htmldir,"icons")
    # HTML code for warning and info icons
    self.__warning_icon = Canary.MakeImg(
        os.path.join(self.__xia2_html_dir,"warning.png"))
    self.__info_icon = Canary.MakeImg(
        os.path.join(self.__xia2_html_dir,"info.png"))
    # Integration status reporter
    self.__int_status_reporter = IntegrationStatusReporter(
        self.__xia2_html_dir,self.__xia2run.integration_status_key())
    # Dictionary to store anchors within the report
    self.__anchor = {}
    # Local pipeline info object
    self.__pipeline = PipelineInfo()
    if self.__xia2run.xds_pipeline(): self.__pipeline.setXDSPipeline()
    # Initialise the document
    self.initialiseDocument()
    # Check whether the run completed
    if xia2run.complete():
      self.reportRun()
      self.__status = True
    else:
      # Report an incomplete run
      self.reportIncompleteRun()
      self.__status = False
    # Copy icon files and jloggraph etc
    self.copyFiles()
    # Spit out the HTML
    self.__xia2doc.renderFile('xia2.html')

  def initialiseDocument(self):
    """Initialise the HTML document

    Create a new Canary.Document object and make a 'skeleton'
    document by adding empty sections which are subsequently
    populated by other methods.

    A reference to each section object is also stored internally
    to the Xia2doc object, to enable 'forward linking' from an
    earlier to a later section in the document."""
    # Make a new Canary HTML document
    self.__xia2doc = Canary.Document("xia2 Processing Report: "+
                                     self.__xia2run.project_name())
    # Add reference to style sheet
    self.__xia2doc.addStyle(os.path.join(self.__xia2htmldir,"xia2.css"),
                            Canary.INLINE)
    # Create document skeleton
    if not self.__xia2run.complete():
      # Don't make a skeleton if the run didn't complete
      return
    # Preamble
    self.__preamble = self.addSection()
    # Initial summary table
    self.__summary_table = self.__xia2doc.addTable()
    # Index section
    self.__index = self.addSection()
    # Crystallographic parameters
    self.__xtal_parameters = self.addSection("Crystallographic parameters")
    # Output files sections
    self.__output_files = self.addSection("Output files")
    self.__refln_files = self.__output_files. \
        addSubsection("Reflection data files")
    self.__logfiles = self.__output_files.addSubsection("Log files")
    # Integration status per image for each sweep
    self.__integration_status = self.addSection(
        "Integration status per image")
    # Detailed statistics
    self.__statistics = self.addSection(
        "Detailed statistics for each dataset")
    # Credits section
    self.__credits = self.addSection("Credits")

  def reportRun(self):
    """Populate the document with content from the xia2 run

    This method populates the output document by invoking the
    methods required to populate the individual document
    sections.

    Note that the order that the sections appear in the final
    rendered document is not determined by the order of the
    invocations here, but by the order in which the sections
    were created in the initialiseDocument method."""
    # Write the preamble
    self.addPreamble(self.__preamble)
    # Report the output files
    self.reportReflectionFiles(self.__refln_files)
    self.reportLogFiles(self.__logfiles)
    self.reportJournalFile()
    # Add the crystallographic data
    self.reportXtallographicData(self.__xtal_parameters)
    # Radiation damage analysis
    # FIXME commented out for now
    ##self.reportRadiationDamage(self.__xtal_parameters)
    # Interwavelength analysis
    self.reportInterwavelengthAnalyses(self.__xtal_parameters)
    # Report the integration status per image
    self.reportIntegrationStatus(self.__integration_status)
    # Report the detailed statistics and summary table
    self.reportStatistics(self.__statistics)
    self.reportSummaryTable(self.__summary_table)
    # Credits/citations
    self.reportCredits(self.__credits)
    # Index and footer
    self.addIndex(self.__index)
    self.addFooter()

  def reportIncompleteRun(self):
    """Generate a report for incomplete processing of the run data

    For 'incomplete' runs (i.e. a xia2 run that the Xia2run instance
    couldn't process fully), this writes a document explaining the
    error and some possible reasons.

    It also attempts to create a .tar file in the xia2_html directory
    with diagnostic files (e.g. xia2.txt, xia2-debug.txt...) and
    gives a link to this file so that it can be emailed to the
    xia2 developer."""
    self.addWarning(self.__xia2doc,
                    "Xia2html failed to process the output from this run"+
                    " in directory<br />"+
                    Canary.MakeLink(self.__xia2run.xia2_dir(),
                                    relative_link=True))
    # Check to see if the run finished
    if self.__xia2run.finished():
      # Run finished - was there an error?
      xia2_status = self.__xia2run.termination_status()
      if xia2_status.startswith("error:"):
        self.__xia2doc.addPara("xia2 terminated with an error:")
      else:
        self.__xia2doc.addPara("xia2 terminated with the message:")
      self.__xia2doc.addList().addItem(xia2_status)
    else:
      # Run doesn't appear to have finished - offer suggestions
      self.__xia2doc.addPara(
          "It's not clear why this has happened but possible reasons "+
          "for the failure include:")
      self.__xia2doc.addList(). \
          addItem("xia2 is still running"). \
          addItem("xia2 failed unexpectedly"). \
          addItem("xia2 completed successfully but Xia2html failed")
    # Make a tar file with xia2.txt, xia2.error and xia2-debug.txt
    archive = os.path.join(self.__xia2_html,"xia2-fail.tar")
    tf = tarfile.open(archive,'w')
    for filen in ("xia2.txt","xia2.error","xia2-debug.txt"):
      if os.path.exists(filen):
        tf.add(filen)
    tf.close()
    self.__xia2doc.addPara(
        "A tar file with diagnostic information has been created:")
    self.__xia2doc.addList().addItem(Canary.MakeLink(archive))
    self.__xia2doc.addPara(
        "Please report the error and send this tar file to "+
        Canary.MakeLink("mailto:graeme.winter@diamond.ac.uk",
                        "graeme.winter@diamond.ac.uk"))
    # Finish off the document with xia2 info and footer
    self.reportXia2Info(self.__xia2doc)
    self.addFooter()

  def addSection(self,title=None):
    """Add a new section to the document"""
    return self.__xia2doc.addSection(title)

  def makeAnchor(self,xtal_name,data_name):
    """Make an anchor in the document

    This creates and returns a Canary.Anchor object.
    A reference to the anchor is stored by 'xtal_name'
    and 'data_name' so that it can be retrieved later
    using the fetchAnchor method."""
    anchor = Canary.Anchor(self.__xia2doc,xtal_name+"_"+data_name)
    try:
      anchors = self.__anchor[xtal_name]
    except KeyError:
      # Create the dictionary first
      self.__anchor[xtal_name] = {}
      anchors = self.__anchor[xtal_name]
    anchors[data_name] = anchor
    return anchor

  def fetchAnchor(self,xtal_name,data_name):
    """Return a stored anchor"""
    return self.__anchor[xtal_name][data_name]

  def addInfo(self,section,message):
    """Add an info message to a section"""
    section.addPara(self.__info_icon+" "+message,css_class="info")

  def addWarning(self,section,message):
    """Add a warning message to a section"""
    warning = "<div class='warning'>"+\
        self.__warning_icon+" "+message+"</div>"
    section.addContent(warning)

  def addPreamble(self,section):
    """Add the preamble to the document"""
    section.addPara("XIA2 version %s completed with status '%s'" % \
                        (self.__xia2run.version(),
                         self.__xia2run.termination_status())). \
                         addPara("Read output from %s" % \
                                 Canary.MakeLink(self.__xia2run.xia2_dir(),
                                                 relative_link=True))

  def addIndex(self,section):
    """Add an index to the rest of the document"""
    # Put in some forwarding linking from the index
    section.addPara("Contents of the rest of this document:")
    forward_links = section.addList()
    forward_links.addItem(Canary.MakeLink(self.__refln_files,
                                 "Reflection files output from xia2"))
    forward_links.addItem(Canary.MakeLink(self.__statistics,
                                 "Full statistics for each wavelength"))
    forward_links.addItem(Canary.MakeLink(self.__logfiles,
                                 "Log files from individual stages"))
    forward_links.addItem(Canary.MakeLink(self.__integration_status,
                   "Integration status for images by wavelength and sweep"))
    forward_links.addItem(Canary.MakeLink(self.__credits,
                                 "Lists of programs and citations"))

  def reportXtallographicData(self,section):
    """Add the report of crystallographic data for all crystals"""
    # Create the subsections for each type of data
    self.__unit_cell   = section.addSubsection("Unit cell")
    self.__spacegroup  = section.addSubsection("Spacegroup")
    self.__twinning    = section.addSubsection("Twinning analysis")
    self.__asu_content = section.addSubsection("Asymmetric unit contents")
    # Loop over all crystals to report the data
    for xtal in xia2run.crystals():
      if xia2run.multi_crystal():
        # For multicrystal run, create a new subsection for
        # the data for each crystal
        xtal_name = "Crystal "+xtal.name()
        unit_cell = self.__unit_cell.addSubsection(xtal_name)
        spacegroup = self.__spacegroup.addSubsection(xtal_name)
        twinning = self.__twinning.addSubsection(xtal_name)
        asu_content = self.__asu_content.addSubsection(xtal_name)
      else:
        # Single crystal run, use sections already created
        unit_cell = self.__unit_cell
        spacegroup = self.__spacegroup
        twinning = self.__twinning
        asu_content = self.__asu_content
      # Report the data
      self.reportUnitCell(xtal,unit_cell)
      self.reportSpacegroup(xtal,spacegroup)
      self.reportTwinning(xtal,twinning)
      self.reportASUContents(xtal,asu_content)
    # Add information for each section as appropriate
    self.addInfo(self.__unit_cell,
                 "The unit cell parameters are the average for "+
                 "all measurements")
    self.addInfo(self.__twinning,
                 "The twinning score is the value of "+
                 "&lt;E<sup>4</sup>&gt;/&lt;I<sup>2</sup>&gt; "+
                 "reported by sfcheck "+
                 Canary.MakeLink("http://www.ccp4.ac.uk/html/sfcheck.html#Twinning%20test",
                                 "(see documentation)"))

  def reportUnitCell(self,xtal,section):
    """Add the report of unit cell data to a section"""
    # Get the unit cell data for the crystal
    unit_cell = xtal.unit_cell()
    # Add a table to the section with the parameters
    section.addTable(['a','b','c',
                      '&alpha;','&beta;','&gamma;']). \
                      addRow([unit_cell['a']+'&nbsp;',
                              unit_cell['b']+'&nbsp;',
                              unit_cell['c']+'&nbsp;',
                              unit_cell['alpha']+'&nbsp;',
                              unit_cell['beta']+'&nbsp;',
                              unit_cell['gamma']+'&nbsp;'])

  def reportSpacegroup(self,xtal,section):
    """Add the report of the spacegroup to a section"""
    section.addPara("Spacegroup: "+htmlise_sg_name(xtal.spacegroup()))
    if xtal.alt_spacegroups():
      section.addPara("Other possibilities could be:")
      alt_spg_list = section.addList()
      for alt_spg in xtal.alt_spacegroups():
        if alt_spg:
          alt_spg_list.addItem(htmlise_sg_name(alt_spg))
    else:
      section.addPara("No likely alternatives to this spacegroup")
    # Link to the pointless log file if possible
    try:
      # Look up the processing stage for pointless
      stage = self.__pipeline.stageForProgram('pointless')
      info = "The spacegroup was determined using pointless "+\
          self.fetchAnchor(xtal.name(),stage).link("(see log file)")
    except KeyError:
      info = "The spacegroup determination was made using pointless"
    self.addInfo(self.__spacegroup,info)

  def reportTwinning(self,xtal,section):
    """Add the report of twinning analysis to a section"""
    section.addPara("Overall twinning score: "+xtal.twinning_score())
    section.addPara(xtal.twinning_report())

  def reportASUContents(self,xtal,section):
    """Add the report of ASU contents to a section"""
    nmols = xtal.molecules_in_asu()
    solvent = xtal.solvent_fraction()
    if not nmols is None and not solvent is None:
      # Create a table
      asu_tbl = section.addTable()
      seq_html = ''
      for line in splitlines(xtal.sequence(),60):
        seq_html += line+"<br />"
      seq_html = "<span class='sequence'>"+\
          seq_html.strip("<br />")+\
          "</span>"
      asu_tbl.addRow(['Sequence',seq_html])
      asu_tbl.addRow(['Likely number of molecules in ASU',nmols])
      asu_tbl.addRow(['Resulting solvent fraction',solvent])
      asu_tbl.addClass('xia2_info')
    else:
      message = "No information on ASU contents"
      if not len(xtal.sequence()):
        message += " (because no sequence information was supplied?)"
      self.addInfo(section,message)

  def reportInterwavelengthAnalyses(self,section):
    """Add the interwavelength analyses report to a section"""
    # Only make section for the report if there is at least one
    # table to dispaly
    self.__interwavelength_analysis = None
    for xtal in self.__xia2run.crystals():
      if xtal.interwavelength_analysis():
        # There is at least one table to report
        self.__interwavelength_analysis = section. \
            addSubsection("Inter-wavelength B and R-factor analysis")
        break
    if not self.__interwavelength_analysis:
      # No interwavelength analysis to report
      return
    # Loop over all crystals to report the data
    for xtal in xia2run.crystals():
      if not xtal.interwavelength_analysis():
        # No table for this crystal, skip to the next one
        continue
      if xia2run.multi_crystal():
        # For multicrystal run, create a new subsection for
        # the data for each crystal
        xtal_name = "Crystal "+xtal.name()
        interwavelength_section = self.__interwavelength_analysis. \
            addSubsection(xtal_name)
      else:
        interwavelength_section = self.__interwavelength_analysis
      # Make a table to display the data
      interwavelength_tbl = Canary.MakeMagicTable(
          xtal.interwavelength_analysis(),' ')
      interwavelength_tbl.setHeader(['Wavelength',
                                     'B-factor',
                                     'R-factor',
                                     'Status'])
      # Add the table to the section
      interwavelength_section.addContent(interwavelength_tbl)

  def reportRadiationDamage(self,section):
    """Add a report of the radiation damage analysis to the section"""
    # Loop over all crystals to report the analysis for each
    radiation_damage = section.addSubsection("Radiation damage analysis")
    for xtal in xia2run.crystals():
      if xia2run.multi_crystal():
        # For multicrystal run, create a new subsection for
        # the data for each crystal
        xtal_name = "Crystal "+xtal.name()
        radiation_damage_section = radiation_damage. \
            addSubsection(xtal_name)
      else:
        radiation_damage_section = radiation_damage
      # Report the analysis and conclusion
      n_analyses = len(xtal.radiation_damage_analyses())
      if not n_analyses:
        # Assume no analysis was found
        self.addInfo(radiation_damage_section,
                     "No radiation damage analysis found")
        continue
      i = 0
      for analysis in xtal.radiation_damage_analyses():
        if n_analyses > 1:
          # Multiple analyses - write a title
          i += 1
          radiation_damage_section.addPara("Analysis "+str(i))
        # Report the groups
        for j in range(0,len(analysis.ids())):
          radiation_damage_section.addPara("Group "+
                                           analysis.ids()[j]+
                                           ": "+
                                           analysis.descriptions()[j])
        # Report other data from the analysis
        radiation_damage_section.addPara(analysis.report())
        if analysis.table():
          radiation_damage_section.addContent(
              Canary.MakeMagicTable(analysis.table()))
        radiation_damage_section.addPara("Conclusion:"+
                                         analysis.conclusion())

  def reportReflectionFiles(self,section):
    """Add a report of the reflection files to a section"""
    refln_files = self.__xia2run.refln_files()
    if not len(refln_files):
      self.addWarning(section,"No reflection data files found")
      section.addPara("No information on the reflection files was found "+
                      "in the xia2.txt file.")
      self.addInfo("Note to xia2 developer: check the pattern "+
                   "definitions for <b>scaled_refln_file</b> "+
                   "in the Xia2run class to ensure that they match "+
                   "the text found in xia2.txt")
      return
    # Write the preamble
    preamble = "xia2 produced the following reflection data files - to "+\
        "download, right-click on the link and select \"Save Link As...\""
    section.addPara(preamble,css_class="preamble")
    # Build a table of reflection files
    refln_tbl = section.addTable()
    refln_tbl.addClass('refln_files')
    last_format = None
    # Each file creates a row in the table
    for refln_file in refln_files:
      filen = refln_file.basename()
      if refln_file.format() != last_format:
        # New format encountered
        #
        # Add a title row for the new format
        refln_tbl.addRow([str(refln_file.format()).upper()+" files",""],
                         css_classes='refln_format')
        last_format = refln_file.format()
        # Add "useful for.."
        try:
          refln_tbl.addRow(["Useful for: "+
                            refln_file.useful_for()],
                           css_classes='useful_for')
        except KeyError:
          pass
        # Add a "header" row for the files below
        if self.__xia2run.multi_crystal():
          header = ['Crystal','Dataset','File name']
        else:
          header = ['Dataset','File name']
        refln_tbl.addRow(header,css_classes='refln_header')
      # Build the row
      if self.__xia2run.multi_crystal():
        # Multicrystal run: prepend crystal name
        reflndata = [refln_file.crystal()]
      else:
        reflndata = []
      reflndata.extend([refln_file.dataset(),
                        Canary.MakeLink(refln_file.filename(),
                                        filen,relative_link=True)])
      # Add the row to the table
      refln_tbl.addRow(reflndata)

  def reportLogFiles(self,section):
    """Add a report of the log files to a section"""
    if not len(self.__xia2run.logfiles()):
      # No log files were found
      # Print warning and diagnostics
      self.addWarning(section,"No program log files found in "+ \
                          Canary.MakeLink(self.__xia2run.log_dir(),
                                          relative_link=True))
      if not os.path.isdir(self.__xia2run.log_dir()):
        self.addInfo(section,
                     "This is because the log file directory wasn't "+
                     "found")
      return
    # Write the preamble
    preamble = "The log files are located in "+ \
        Canary.MakeLink(self.__xia2run.log_dir(),
                        relative_link=True)+ \
                        " and are grouped by"
    if self.__xia2run.multi_crystal():
      preamble += " crystal and"
    preamble += " processing stage:"
    section.addPara(preamble,css_class="preamble")
    # Loop over crystals
    for xtal in self.__xia2run.crystals():
      if not self.__xia2run.multi_crystal():
        this_section = section
      else:
        this_section = section.addSubsection(\
            "Log files for crystal "+xtal.name())
      self.reportLogFilesForXtal(xtal,this_section)
    # Check for and report any log files not assigned to a crystal
    unassigned_logs = []
    for log in self.__xia2run.logfiles():
      if not log.crystal(): unassigned_logs.append(log)
    if len(unassigned_logs):
      unassigned = Canary.List()
      for log in unassigned_logs:
        unassigned.addItem(Canary.MakeLink(
                log.relativeName(),log.basename()))
      self.addWarning(self.__logfiles,
                      "The following files weren't assigned to a "+
                      "crystal:"+unassigned.render())
      self.addInfo(self.__logfiles,
                   "Note to the xia2 developer: check the "+
                   "&quot;addLogFile&quot; definitions in the "+
                   "PipelineInfo class to ensure that information "+
                   "about these files exists and is correct.")

  def reportLogFilesForXtal(self,xtal,section):
    """Report the log files for a specific crystal"""
    # Make a table to report the files
    logs_tbl = section.addTable()
    logs_tbl.addClass('log_files')
    this_stage = None
    this_program = None
    for log in self.__xia2run.logfiles():
      # Check whether if belongs to this crystal
      if log.crystal() != xtal.name(): continue
      # Determine the processing stage
      # Logs are grouped by stage according to the
      # program name
      program = log.program()
      stage = log.processing_stage()
      if not stage:
        # No stage assigned for this program
        # Add a warning to the HTML file and skip
        print "No program stage for program "+str(program)
        self.addWarning(section,"xia2html: failed to classify log "+
                        Canary.MakeLink(
                log.relativeName(),log.basename())+
                        "<br />Please report this problem")
        self.addInfo(section,
                     "Note to the xia2 developer: check that the "+
                     "&quot;addLogFile&quot; definitions in the "+
                     "PipelineInfo class to ensure that information "+
                     "about this file exists and is correct.")
        continue
      if stage != this_stage:
        anchor = self.makeAnchor(xtal.name(),stage)
        logs_tbl.addRow([anchor.embed(stage),''],
                        css_classes='proc_stage')
        this_stage = stage
      # Get the description of the log file
      if program != this_program:
        description = log.description()
        if description:
          logs_tbl.addRow([description],
                          css_classes='proc_description')
          this_program = program
      # Start making the table row for the file
      logdata = [log.basename(),
                 Canary.MakeLink(log.relativeName(),"original")]
      # Link to baubles file
      html_log = log.baublize(target_dir=self.__xia2_html_dir)
      if html_log:
        logdata.append(Canary.MakeLink(html_log,"html"))
      else:
        logdata.append(None)
      # Warnings from smartie analysis
      if len(log.warnings()):
        logdata.append(Canary.MakeLink(html_log+"#warnings",
                                       self.__warning_icon+
                                       " See warnings"))
      else:
        logdata.append('')
      # Add data to the table
      logs_tbl.addRow(logdata)

  def reportJournalFile(self):
    """Add a report of the journal files"""
    # Add a link to the journal file xia2-journal.txt, if found
    if self.__xia2run.journal_file():
      journal = self.__output_files.addSubsection("xia2 Journal file")
      self.addInfo(journal,
                   "More detailed information on what xia2 did can "+
                   "be found in the &quot;journal&quot; file:")
      journal.addList().addItem(Canary.MakeLink(
              self.__xia2run.journal_file(),"xia2-journal.txt",
              relative_link=True))

  def reportIntegrationStatus(self,section):
    """Add a report of the integration status to a section"""
    # Local convenience variables
    multi_crystal = self.__xia2run.multi_crystal()
    int_status_reporter = self.__int_status_reporter
    # Check for problems with the data
    if not len(int_status_reporter.getSymbolList()):
      # No integration status symbols were extracted from the key
      self.addWarning(section,
                      "The integration status symbols were not "+
                      "properly extracted from the xia2.txt file, "+
                      "so the integration status for each sweep "+
                      "cannot be reported")
      self.addInfo(section,
                   "Note to the xia2 developer: this is most likely "+
                   "because the key was not extracted from xia2.txt. "+
                   "Check the 'integration_status_key' pattern in the "+
                   "Xia2run class, and the __makeSymbolLookup method "+
                   "in the IntegrationStatusReporter class.")
      return
    # Write out the preamble
    preamble = "The following sections show the status of "+ \
        "each image from the final integration run "+ \
        "performed on each sweep within each dataset."
    preamble += "The table below summarises the image status for each"
    if self.__xia2run.multi_crystal():
      preamble += " crystal,"
    preamble += " dataset and sweep."
    section.addPara(preamble,css_class="preamble")
    # Initialise the summary table (listing number of images with
    # each status) - it will be populated as we go along
    summary_tbl = section.addTable()
    # Loop over crystals
    last_xtal = None
    for xtal in self.__xia2run.crystals():
      print ">>>> CRYSTAL: "+xtal.name()
      # Make a section for each crystal (if multi-crystal run)
      if multi_crystal:
        xtal_section = section.addSubsection("Crystal %s" %
                                                   xtal.name())
      else:
        xtal_section = section
      # Loop over datasets
      last_dataset = None
      for dataset in xtal.datasets():
        print ">>>> DATASET: "+dataset.datasetName()
        # Make a section for each dataset
        dataset_section = xtal_section. \
            addSubsection("Dataset %s" % dataset.datasetName())
        # Deal with each sweep associated with the dataset
        for sweep in dataset.sweeps():
          print ">>>> SWEEP: "+str(sweep.name())
          last_int_run = sweep.last_integration_run()
          if not last_int_run:
            # No last integration run found
            self.addWarning(dataset_section,
                            "Error aquiring last integration "+
                            "run for sweep "+sweep.name())
            break
          # Output status info for this sweep in its own section
          start_batch = last_int_run.start_batch()
          end_batch = last_int_run.end_batch()
          sweep_section = dataset_section. \
              addSubsection(sweep.name() +
                            ": batches " + start_batch +
                            " to " + end_batch)
          # Get the HTML representation of the status line
          images_html = int_status_reporter. \
              htmliseStatusLine(last_int_run)
          sweep_section.addContent("<p>"+images_html+"</p>")
          # Add a row to the summary table
          row = []
          total = 0
          if multi_crystal:
            if xtal != last_xtal:
              # Only link to each crystal once from the table
              row.append(Canary.MakeLink(
                      xtal_section,xtal.name()))
              last_xtal = xtal
            else:
              row.append('')
          if dataset != last_dataset:
            # Only link to each dataset once from the table
            row.append(Canary.MakeLink(dataset_section,
                                       dataset.datasetName()))
            last_dataset = dataset
          else:
            row.append('')
          # Link to sweep followed by the stats
          row.append(Canary.MakeLink(sweep_section,sweep.name()))
          for symbol in int_status_reporter.getSymbolList():
            row.append(str(last_int_run.countSymbol(symbol)))
            total += last_int_run.countSymbol(symbol)
          row.append(total)
          summary_tbl.addRow(row)
    # Finish off the summary table by adding the header
    header = []
    if multi_crystal:
      header.append('Crystal')
    header.extend(['Dataset','Sweep'])
    for symbol in int_status_reporter.getSymbolList():
      symbol_status = int_status_reporter.lookupStatus(symbol)
      description = int_status_reporter.getDescription(symbol_status)
      symbol_image = int_status_reporter.getIcon(symbol_status)
      header.append(description+"<br />"+symbol_image)
    header.append("Total")
    summary_tbl.setHeader(header)

  def reportSummaryTable(self,table):
    """Populate the initial summary table

    This is the big table at the head of the report, which lists
    the stats for each wavelength and crystal as columns (similar
    to the Acta Cryst D 'table one').

    Note that although this table appears at the start of the final
    document, this method should be called after the sections that
    it references (for example, the full statistics for each
    wavelength) have been written. This is so that we can link
    forward to those sections."""
    # Convenience variables
    has_anomalous = self.__xia2run.has_anomalous()
    # Build up the table content
    #
    # Note that the table is constructed in two sections:
    #
    # * The first section is the top part of the table with
    #   a subset of statistics from Scala, and is constructed
    #   "column-wise".
    #
    # * The second section consists of the crystallographic
    #   parameters and is constructed row-wise
    #
    # Build the first section (stats)
    row_titles = ['Wavelength (&Aring;)',
                  'High resolution limit',
                  'Low resolution limit',
                  'Completeness',
                  'Multiplicity',
                  'CC-half',
                  'I/sigma',
                  'R<sub>merge</sub>']
    if has_anomalous:
      row_titles.extend(['Anomalous completeness',
                         'Anomalous multiplicity'])
    row_titles.extend(['']) # Line linking to full stats
    # Add the initial title column just built
    table.addColumn(row_titles)
    # Loop over crystals and datasets
    for xtal in self.__xia2run.crystals():
      # Add an additional column for each dataset
      for dataset in xtal.datasets():
        # Construct the column of data and add to the table
        # This is for the overall/average values
        column_data = [dataset.wavelength(),
                       dataset['High resolution limit'][1],
                       dataset['Low resolution limit'][1],
                       dataset['Completeness'][1],
                       dataset['Multiplicity'][1],
                       dataset['CC half'][1],
                       dataset['I/sigma'][1],
                       dataset['Rmerge'][1]]
        if has_anomalous:
          try:
            anom_completeness = dataset['Anomalous completeness'][1]
            anom_multiplicity = dataset['Anomalous multiplicity'][1]
          except KeyError:
            anom_completeness = '-'
            anom_multiplicity = '-'
          column_data.extend([anom_completeness,anom_multiplicity])
        # Link forward to full stats for this dataset
        column_data.append(Canary.MakeLink(
                self.__statistics_sections[dataset.datasetName()],
                "See all statistics"))
        # Append the column to the table
        if self.__xia2run.multi_crystal():
          # Add the crystal name
          column_title = xtal.name()+"<br />"
        else:
          column_title = ''
        column_title += dataset.datasetName()
        table.addColumn(column_data,
                        header=column_title)
        # Add a second column with the high and low values
        column_data = [None,
                       "("+dataset['High resolution limit'][2]+\
                       " - "+dataset['High resolution limit'][3]+")",
                       "("+dataset['Low resolution limit'][2]+\
                       " - "+dataset['Low resolution limit'][3]+")",
                       "("+dataset['Completeness'][2]+\
                       " - "+dataset['Completeness'][3]+")",
                       "("+dataset['Multiplicity'][2]+\
                       " - "+dataset['Multiplicity'][3]+")",
                       "("+dataset['CC half'][2]+\
                       " - "+dataset['CC half'][3]+")",
                       "("+dataset['I/sigma'][2]+\
                       " - "+dataset['I/sigma'][3]+")",
                       "("+dataset['Rmerge'][2]+\
                       " - "+dataset['Rmerge'][3]+")"]
        if has_anomalous:
          try:
            anom_completeness = \
                "("+dataset['Anomalous completeness'][2]+\
                " - "+\
                dataset['Anomalous completeness'][3]+")"
            anom_multiplicity = \
                "("+dataset['Anomalous multiplicity'][2]+\
                " - "+\
                dataset['Anomalous multiplicity'][3]+")"
          except KeyError:
            anom_completeness = '-'
            anom_multiplicity = '-'
          column_data.extend([anom_completeness,anom_multiplicity])
        table.addColumn(column_data)
    # Now build the second section of the table (crystal-specific data)
    # This is built up row-wise
    # Store each row as a list in the 'row_data' dictionary
    row_data = { "unit_cell_a": ['Unit cell dimensions: a (&Aring;)'],
                 "unit_cell_b": ['b (&Aring;)'],
                 "unit_cell_c": ['c (&Aring;)'],
                 "unit_cell_alpha": ['&alpha; (&deg;)'],
                 "unit_cell_beta": ['&beta; (&deg;)'],
                 "unit_cell_gamma": ['&gamma; (&deg;)'],
                 "spacegroup": ['Spacegroup'],
                 "twinning": ['Sfcheck twinning score']}
    # Loop over crystals and datasets
    # Add elements to each row in row_data
    last_xtal = None
    for xtal in self.__xia2run.crystals():
      for dataset in xtal.datasets():
        # Crystal-specific data
        if xtal != last_xtal:
          # New crystal - fetch data
          unit_cell = xtal.unit_cell()
          spacegroup = xtal.spacegroup()
          twinning_score = xtal.twinning_score()
          twinning_report = xtal.twinning_report()
          # Store the data for print out at the end
          row_data['unit_cell_a'].append(unit_cell['a'])
          row_data['unit_cell_b'].append(unit_cell['b'])
          row_data['unit_cell_c'].append(unit_cell['c'])
          row_data['unit_cell_alpha'].append(unit_cell['alpha'])
          row_data['unit_cell_beta'].append(unit_cell['beta'])
          row_data['unit_cell_gamma'].append(unit_cell['gamma'])
          row_data['spacegroup'].append(htmlise_sg_name(spacegroup))
          row_data['twinning'].append(twinning_score+"<br />"+
                                      twinning_report)
          # Add an empty element to the end of each row
          # This will correspond to an empty column, so that
          # the columns in this section match up with those
          # in the first section of the table
          for item in row_data.keys():
            row_data[item].append(None)
          # Update last crystal
          last_xtal = xtal
        else:
          # Same crystal as before
          # Add two empty elements to each row
          # These will correspond to two empty columns, so that
          # the columns in this section match up with those
          # in the first section of the table
          for item in row_data.keys():
            row_data[item].extend([None,None])
    # Finished constructing row_data array
    # Add the rows to the table
    table.addRow(['&nbsp;']) # Empty row for padding
    table.addRow(row_data['unit_cell_a'],"unit_cell")
    table.addRow(row_data['unit_cell_b'],"unit_cell")
    table.addRow(row_data['unit_cell_c'],"unit_cell")
    table.addRow(row_data['unit_cell_alpha'],"unit_cell")
    table.addRow(row_data['unit_cell_beta'],"unit_cell")
    table.addRow(row_data['unit_cell_gamma'],"unit_cell")
    table.addRow(['&nbsp;']) # Empty row for padding
    table.addRow(row_data['spacegroup'])
    table.addRow(['&nbsp;']) # Empty row for padding
    table.addRow(row_data['twinning'])
    table.addRow(['',Canary.MakeLink(self.__xtal_parameters,
                                     "All crystallographic parameters..")])
    # Finished - add the CSS class
    table.addClass('table_one')

  def reportStatistics(self,section):
    """Add a detailed report of the statistics for each dataset"""
    # Add information line
    self.addInfo(section,
                 "Detailed statistics for each dataset as "+
                 "reported by Aimless")
    # For multiple crystals and/or multiple datasets, write a table
    # of contents for the statistics
    if len(self.__xia2run.crystals()) > 1 or \
            len(self.__xia2run.crystals()[0].datasets()) > 1:
      section.addTOC()
    # Make a subsection for each dataset
    # and keep a record so we can link to them
    self.__statistics_sections = {}
    for xtal in self.__xia2run.crystals():
      # Create a new subsection for the crystal, if this is a
      # multicrystal run
      xtal_name = xtal.name()
      if self.__xia2run.multi_crystal():
        xtal_section = section.addSubsection("Crystal "+xtal_name)
      else:
        xtal_section = section
      # Loop over datasets
      for dataset in xtal.datasets():
        dataset_name = dataset.datasetName()
        # Make a new subsection
        dataset_stats = xtal_section. \
            addSubsection("Dataset "+dataset_name)
        # Make a table of the statistics
        stats_tbl = Canary.MakeMagicTable(dataset.statistics_table())
        stats_tbl.setHeader(['','Overall','Low','High'])
        dataset_stats.addContent(stats_tbl)
        # Store a reference to the subsection for linking to
        self.__statistics_sections[dataset_name] = dataset_stats

  def reportCredits(self,section):
    """Add report of the software and citations to the section"""
    # Software used
    software = section.addSubsection("Software used").addList()
    for prog in self.__xia2run.programs_used():
      software.addItem(prog)
    # Citations
    citer = Citations()
    citations = section.addSubsection("Citations")
    self.addInfo(citations,
                 "Note that links to external content below may "+
                 "require you to log in before you can view or "+
                 "download the materials")
    citation_list = citations.addList()
    for citation in self.__xia2run.citations():
      # Get citation link
      url = citer.getCitationLink(citation)
      if url:
        citation_list.addItem(Canary.MakeLink(url,citation))
      else:
        citation_list.addItem(citation)
    self.reportXia2Info(section)

  def reportXia2Info(self,section):
    """Add a report of xia2-specific information to the section"""
    # Some other xia2-specific stuff
    xia2_info = section.addSubsection("xia2 Details")
    xia2_info.addPara("Details about this run:",css_class="preamble")
    tbl_xia2_info = xia2_info.addTable()
    tbl_xia2_info.addClass('xia2_info')
    tbl_xia2_info.addRow(['Version',self.__xia2run.version()])
    tbl_xia2_info.addRow(['Run time',self.__xia2run.run_time()])
    tbl_xia2_info.addRow(['Command line',self.__xia2run.cmd_line()])
    tbl_xia2_info.addRow(['Termination status',
                          self.__xia2run.termination_status()])
    xia2txt = os.path.join(self.__xia2run.xia2_dir(),"xia2.txt")
    tbl_xia2_info.addRow(['xia2.txt file',
                          Canary.MakeLink(xia2txt,relative_link=True)])

  def addFooter(self):
    """Add the footer section"""
    self.__xia2doc.addPara("This file was generated for you from xia2 output by Xia2html %s on %s<br />Powered by Magpie %s and Canary %s<br />&copy; Diamond 2009" \
                               % (__version__,
                                  time.asctime(),
                                  Magpie.version(),
                                  Canary.version()),
                           css_class='footer')

  def copyFiles(self):
    """Copy Jloggraph and icon files to the xia2_html directory"""
    # Extras
    # Just jloggraph applet for now
    extras_files = ["JLogGraph.jar"]
    print "Copying files from 'extras' directory..."
    for filen in extras_files:
      print "\t"+str(filen)
      src_file = os.path.join(self.__xia2htmldir,"extras",filen)
      tgt_file = os.path.join(self.__xia2_html,filen)
      if os.path.isfile(src_file):
        shutil.copy(src_file,tgt_file)
      else:
        print "*** %s not found ***" % src_file
        self.addWarning(self.__preamble,
                        " Unable to copy "+str(src_file)+
                        ": file not found<br />"+
                        "Loggraphs in html log files may not work")
    # Icons
    print "Copying icons to %s" % self.__xia2_html
    icons = self.__int_status_reporter.listIconNames()
    icons.append("warning.png")
    icons.append("info.png")
    for icon in icons:
      print "\t"+str(icon)
      shutil.copy(os.path.join(self.__icondir,icon),
                  os.path.join(self.__xia2_html,icon))

  def status(self):
    """Return the status of the Xia2doc object

    Returns True if the run appeared to be successful and False
    if not."""
    return self.__status

# IntegrationStatusReporter
#
# Helps with reporting the status of each image in sweeps
class IntegrationStatusReporter:
  """Class to handle reporting the integration status per image

  The IntegrationStatusReporter class is used by the Xia2doc class
  to assist in reporting information about the status of images
  within a sweep after an integration run on that sweep.

  It acquires information about the meaning of each symbol from
  the symbol key that is printed in the xia2.txt file after each
  report (see the __makeSymbolLookup method) and builds HTML
  versions of the symbol lines taken from IntegrationRun objects
  (see the htmliseStatusLine method).

  It also provides methods for dealing with individual status
  symbols, their descriptions and corresponding icons."""

  def __init__(self,img_dir,key_text):
    """Create a new IntegrationStatusRenderer

    'img_dir' points to the location of the image icons.

    'key_text' is the text extracted from xia2.txt which
    contains the key matching symbols to their descriptions."""
    self.__img_dir = img_dir
    self.__symbol_lookup = {}
    self.__symbol_dict = {}
    self.__symbol_list = []
    self.__makeSymbolLookup(key_text)
    self.__makeSymbolDictionary()
    return

  def __makeSymbolLookup(self,key_text):
    """Internal: build a dictionary with the key to symbols

    The key to symbols from xia2.txt typically looks like:

    'o' => good        '%' => ok        '!' => bad rmsd
    'O' => overloaded  '#' => many bad  '.' => weak
    '@' => abandoned

    This method attempts to parse this text and produce a
    dictionary with the symbols (i.e. o,%,! etc) as keys
    and the corresponding descriptions (good, ok etc) as
    the values."""
    symbol = ''
    description = []
    got_arrow = False
    for token in key_text.split():
      if token == "=>":
        got_arrow = True
        continue
      if got_arrow:
        if not token.startswith('"'):
          description.append(token)
        else:
          # Store the symbol and description
          self.__symbol_list.append(symbol)
          self.__symbol_lookup[symbol] = " ".join(description)
          description = []
          got_arrow = False
      if not got_arrow:
        symbol = token.strip('"')
    if got_arrow:
      # Deal with final symbol, if any
      self.__symbol_list.append(symbol)
      self.__symbol_lookup[symbol] = " ".join(description)

  def __makeSymbolDictionary(self):
    """Internal: build the symbol dictionary from the lookup table"""
    for key in self.__symbol_lookup.keys():
      self.__symbol_dict[self.__symbol_lookup[key]] = key

  def getSymbolList(self):
    """Return the list of symbols"""
    return self.__symbol_list

  def getSymbolDictionary(self):
    """Return the symbol dictionary

    The symbol dictionary is a Python dictionary with keys
    corresponding to the status descriptions with the values
    of the actual symbols."""
    return self.__symbol_dict

  def getReverseSymbolLookup(self):
    """Return a reverse lookup table of the symbol dictionary"""
    return self.__symbol_lookup

  def lookupSymbol(self,status):
    """Return the symbol given the status"""
    try:
      return self.__symbol_dict[status]
    except KeyError:
      # Not found
      return None

  def lookupStatus(self,symbol):
    """Return the status given the symbol"""
    try:
      return self.__symbol_lookup[symbol]
    except KeyError:
      # Not found
      return None

  def listIconNames(self):
    """Return a list of the names of the icons"""
    icon_files = []
    for status in self.__symbol_dict.keys():
      icon_files.append(self.getIconName(status))
    return icon_files

  def getIconName(self,status):
    """Return the name of the icon file associated with 'status'"""
    # Icon is a PNG image called "img_<status>.png"
    name = "img_"+str(status).replace(' ','_').lower()+".png"
    return name

  def getIconFile(self,status):
    """Return the name and path for the icon associated with 'status'"""
    return os.path.join(self.__img_dir,self.getIconName(status))

  def getIcon(self,status,title=None):
    """Return the HTML code for the icon associated with 'status'

    Optionally a 'title' string can also be specified, which
    is added to the HTML."""
    if not title is None:
      title_attr = " title='"+str(title)+"'"
    else:
      title_attr = ""
    return "<img src='%s'%s />" % (self.getIconFile(status),title_attr)

  def getDescription(self,status):
    """Return the description string associated with 'status'"""
    # Description is just a nice version of the status name
    return str(status).replace('_',' ').capitalize()

  def htmliseStatusLine(self,integration_run):
    """Turn an integration status line into HTML for reporting

    'integration_run' is an IntegrationRun object. This method
    takes the status line read from the xia2.txt file,
    for example of the form:

    ooooooooooooo%oooooooooooooo%ooooooooooooooooooooooooooooooo

    and returns the appropriate block of HTML with img tags to
    represent each image."""
    images_html = ""
    batch_num = int(integration_run.start_batch())
    for images_text in integration_run.image_status().split('\n'):
      # Turn the status symbols into icons
      for symbol in list(images_text):
        status = self.lookupStatus(symbol)
        if status:
          description = self.getDescription(status)
          title = "Batch: %d Status: %s" % (batch_num,description)
          images_html += self.getIcon(status,title)
        else:
          images_html += "<span title=\"Unrecognised\">?</span>"
        batch_num += 1
      images_html += "<br />\n"
    return images_html

#######################################################################
# Module Functions
#######################################################################

def htmlise_sg_name(spacegroup):
  """HTMLise a spacegroup name

  Name 'spacegroup' should be supplied as a string with each
  component separated by spaces, e.g. 'P 41 21 1'

  This will be returned as a HTML fragment:
  'P 4<sub>1</sub> 2<sub>1</sub> 1'"""
  html = ''
  # Split on spaces
  for item in spacegroup.split(' '):
    if item.isalpha():
      # Item is a letter - keep it
      html += item
    if item.isdigit():
      # Item is a digit
      if len(item) > 1:
        # More than one digit - subscript the trailing
        # characters
        number = list(item)
        html += str(number[0])+"<sub>"+str(''.join(number[1:]))+"</sub>"
      else:
        # One digit - keep it
        html += str(item)
    # Preserve the spaces
    html += ' '
  # Finished - strip trailing space
  return html.rstrip(' ')

def get_relative_path(filename):
  """Attempt to get the path relative to cwd

  If 'filename' refers to a file or directory below the current
  working directory (cwd) then this function returns the relative
  path to cwd. Otherwise it returns 'filename'."""
  pwd = os.getcwd()
  common_prefix = os.path.commonprefix([pwd,filename])
  if filename == pwd:
    # 'File' is the current working directory
    return '.'
  elif common_prefix == pwd:
    # File is relative to cwd - strip off cwd and return
    return str(filename).replace(common_prefix,'',1).lstrip(os.sep)
  else:
    # File is not relative to cwd - return as is
    return filename

def splitlines(text,maxline):
  """Split text into lines no longer than maxline

  Returns a list of strings, each no longer than 'maxline' characters
  long, from the supplied 'text'."""
  i = 0
  lines = []
  len_text = len(text)
  while i < len_text:
    j = i+maxline
    if j > len_text: j = len_text
    lines.append(text[i:j])
    i = j
  return lines

#######################################################################
# Main program
#######################################################################

if __name__ == "__main__":
  """Xia2html

  Main program: collects command line arguments, processes xia2
  output and writes out report document(s).

  Exits with code 0 on success and 1 if there was an error, or if
  the xia2 output could not be properly processed."""

  # Set usage string
  usage = "python Xia2html.py [<xia2-output-dir>]"

  # Process command line
  # Needs one argument to run (i.e. name of a Xia2 output directory)
  if len(sys.argv) < 2:
    # No Xia2 output directory supplied - assume cwd
    xia2dir = os.getcwd()
  elif len(sys.argv) == 2:
    # Xia2 output directory is the last argument
    xia2dir = os.path.abspath(sys.argv[-1])
  else:
    # Something unexpected
    print "Usage: "+str(usage)
    sys.exit(1)
  print "Xia2html: will run in directory: "+str(xia2dir)

  # Check the target directory exists
  if not os.path.exists(xia2dir):
    print "Xia2html: directory not found: \""+str(xia2dir)+"\",stopping."
    sys.exit(1)

  # Check the xia2.txt file exists
  if not os.path.exists(os.path.join(xia2dir,"xia2.txt")):
    print "Xia2html: xia2.txt not found, stopping."
    sys.exit(1)

  # Process the output
  xia2run = Xia2run(xia2dir)

  # Generate the HTML
  xia2doc = Xia2doc(xia2run)

  # Check the status and exit appropriately
  if xia2doc.status():
    print "Run was successful"
    sys.exit(0)
  else:
    print "Run was unsuccessful, or there was a Xia2html problem"
    sys.exit(1)

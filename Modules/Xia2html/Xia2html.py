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

1. Process the raw data (specifically xia2.txt - processed using classes
   from the Magpie module - and the contents of the LogFiles directory),

2. Populate a data structure (provided by the Xia2run class in this module)
   to organise what was found,

3. Use the data in Xia2run class in conjunction with document generation
   classes and functions in the Canary module to make an output HTML
   document.

This module contains a number of classes to support gathering, organising
and writing out the data:

PipelineInfo and Citations classes hold 'external' data about log files
and citations respectively. The data in these classes may need to be
updated or extended as xia2's output evolves.

Crystal, Dataset, Sweep and Integration run classes are used within
Xia2run to organise the data regarding these data from the run. The
LogFile and ReflectionFile classes organise the data regarding these
two types of file.

IntegrationStatusReporter class is used to help with generating HTML
specific to the sweeps."""

__cvs_id__ = "$Id: Xia2html.py,v 1.81 2010/01/04 10:38:30 pjx Exp $"
__version__ = "0.0.5"

#######################################################################
# Import modules that this module depends on
#######################################################################
import sys
import os
import shutil
import time
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
    the logs will be sorted into on output."""

    def __init__(self):
        """Create pipeline object"""
        self.__pipeline = []
        self.__populate()

    def __populate(self):
        """Setup default pipeline info"""
        # Integration stage
        self.addLogInfo(
            "INTEGRATE",
            "xds",
            "Integration",
            "Integration of this sweep",
            "<PROJECT>_<CRYSTAL>_<DATASET>_<SWEEP>_INTEGRATE.log",
            False)
        self.addLogInfo(
            "CORRECT",
            "xds",
            "Integration",
            "Postrefinement and correction for this sweep",
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
            "_scala",
            "scala",
            "Scaling and merging",
            "Scaling and correction of all measurements on the crystal",
            "<PROJECT>_<CRYSTAL>_scala.log",
            baublize=True)
        # Analysis
        self.addLogInfo(
            "_truncate",
            "truncate",
            "Analysis",
            "Intensity analysis for each wavelength of data",
            "<PROJECT>_<CRYSTAL>_<DATASET>_truncate.log",
            baublize=True)
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

    def setXDSPipeline(self):
        """Update pipeline data for XDS pipeline

        Invoke this to make changes to the pipeline information
        to make it consistent with the 'XDS pipeline'."""
        # Reset description for scala
        self.updateLogInfo(
            "_scala",
            new_description=
            "Merging results for all of the data for the crystal")

    def addLogInfo(self,logname,program,stage,description,template,
                   baublize=False):
        """Add information about a log file

        'logname' is part of the log file name which is used to
        identify it.

        'program' is the source program name.

        'stage' is the name of the processing stage that the file
        belongs to.

        'description' is generic text that describes what the function
        of the log file is.

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
        can be baublized."""
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
                      new_baublize=None):
        """Update the information associated with a log file"""
        data = self.lookupLogInfo(logname)
        if data:
            if new_program:
                data['program'] = new_program
            if new_stage:
                data['stage'] = new_stage
            if new_description:
                data['description'] = new_description
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
        """Get the program associated with a logfile"""
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
        """Get the value of the baublize flag for a logfile"""
        data = self.lookupLogInfo(logfile)
        if data:
            return data['baublize']
        return False

    def listNames(self):
        """Return a list of the log file name fragments in pipeline order"""
        names = []
        for item in self.__pipeline:
            names.append(item['logname'])
        return names

    def compareLogfilesByOrder(self,logfile1,logfile2):
        """Compare logfile names by pipeline position"""
        # List of keywords that might appear in the log file names
        # The list is in the order that we would want the file names
        # to appear in a list of files
        keywords = self.listNames()
        # Locate the keywords in the list for both file names
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

    Provides lookup etc for citations from xia2."""

    def __init__(self):
        """Create citations object"""
        self.__citations = []
        self.__populate()

    def __populate(self):
        """Setup citation info"""
        # CCP4
        self.addCitation(
            'ccp4',
            '(1994) Acta Crystallogr. D 50, 760--763',
            'http://journals.iucr.org/d/issues/1994/05/00/ad0004/ad0004.pdf')
        # Scala, pointless (same paper)
        self.addCitation(
            'scala',
            'Evans, Philip (2006) Acta Crystallographica Section D 62, 72--82',
            'http://journals.iucr.org/d/issues/2006/01/00/ba5084/index.html')
        self.addCitation(
            'pointless',
            'Evans, Philip (2006) Acta Crystallographica Section D 62, 72--82',
            'http://journals.iucr.org/d/issues/2006/01/00/ba5084/index.html')
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
        refers to.
        'citation' is the citation text produced by xia2.
        'link' is the URL link for the citation/paper."""
        self.__citations.append({ "program": program,
                                  "citation": citation,
                                  "link": link })

    def getCitationLink(self,citation_text):
        """Get link for citation text

        Returns the stored link which matches the supplied
        citation text, or None if the text is not found."""
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

    Store the information about a run of xia2 that has been
    gathered from xia2.txt and other sources (like the LogFiles
    directory)."""

    def __init__(self,xia2_magpie,xia2_dir):
        """Create new Xia2run object

        'xia2_magpie' is a Magpie processor object that has
        been run on the output of a xia2 run.

        'xia2_dir' is the directory containing the xia2 output
        (either relative or absolute)."""
        self.__xia2     = xia2_magpie
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
        self.__has_anomalous = False # Anomalous data?
        self.__xds_pipeline  = False # XDS pipeline used?
        self.__multi_crystal = False # Run has multiple crystals?
        self.__pipeline_info = PipelineInfo() # Data about logfiles
        self.__int_status_key = '' # Text with key for integration status
        self.__run_finished = False # Whether run finished or not
        try:
            # Populate the object with data
            self.__populate()
            self.__complete = True
        except:
            # Some problem
            self.__complete = False

    def __populate(self):
        """Internal: populate the data structure"""
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
            for dataset in self.datasets():
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
        # Sweeps and integration runs
        print "POPULATE> SWEEPS"
        # Assign (empty) sweeps to datasets
        for sweep_to_dataset in xia2['sweep_to_dataset']:
            dataset = self.get_dataset(sweep_to_dataset['dataset'])
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
            for dataset in self.datasets():
                for sweep in dataset.sweeps():
                    if sweep.name() == integration_run.name():
                        sweep.addIntegrationRun(integration_run)
                        print "SWEEPS> run assigned to sweep "+sweep.name()
                        break
        # Store the raw text of the key to the symbols 
        print "POPULATE> INTEGRATION STATUS KEY"
        if xia2.count('integration_status_key'):
            self.__int_status_key = str(xia2['integration_status_key'][0])
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
        # Assign multi-crystal flag
        if nxtals > 1: self.__multi_crystal = True
        # Logfiles
        # Look in the xia2 LogFiles directory
        print "POPULATE> LOGFILES"
        self.__log_dir = os.path.abspath(os.path.join(xia2dir,"LogFiles"))
        logdir = get_relative_path(self.__log_dir)
        # Process logfiles
        try:
            self.__xds_pipeline = False
            files = self.__list_logfiles()
            for filen in files:
                print "LOGFILES> "+str(filen)
                log = LogFile(os.path.join(logdir,filen),
                              self.__pipeline_info)
                if log.isLog():
                    # Store the log file
                    self.__logfiles.append(log)
                    # Update found_xds flag
                    if log.program() == "xds":
                        self.__xds_pipeline = True
                else:
                    print "LOGFILES> "+log.basename()+ \
                          " not a log file, ignored"
            if self.__xds_pipeline: self.__pipeline_info.setXDSPipeline()
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
        print "POPULATE> FINISHED"

    def __list_logfiles(self):
        """Internal: get list of xia2 log files in pipeline order"""
        # Get unsorted list of file names
        files = os.listdir(self.__log_dir)
        # Sort list on order of file names within the pipeline
        files.sort(self.__pipeline_info.compareLogfilesByOrder)
        return files

    def version(self):
        """Return the xia2 version"""
        return self.__version

    def run_time(self):
        """Return the processing time"""
        return self.__run_time

    def termination_status(self):
        """Return the termination status"""
        return self.__termination_status

    def cmd_line(self):
        """Return the command line"""
        return self.__cmd_line

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
        """Check whether the run used the 'XDS pipeline'"""
        return self.__xds_pipeline

    def multi_crystal(self):
        """Check whether the run contains multiple crystals"""
        return self.__multi_crystal

    def finished(self):
        """Check whether the run completed or not"""
        return self.__run_finished

    def log_dir(self):
        """Return location of the xia2 LogFiles directory

        This is the absolute path for the xia2 logfile directory."""
        return self.__log_dir

    def project_name(self):
        """Return the project name extracted from the xia2.txt file"""
        return self.__project_name

    def datasets(self):
        """Return Datasets for the run

        This returns a list of the Dataset objects representing
        datasets/wavelengths found in the output."""
        return self.__datasets

    def crystals(self):
        """Return Crystals for the run

        This returns a list of the Crystal objects representing
        crystals found in the output."""
        return self.__crystals

    def logfiles(self):
        """Return LogFiles for the run

        Returns a list of the LogFile objects representing the
        log files found in the xia LogFiles directory."""
        return self.__logfiles

    def refln_files(self):
        """Return ReflectionFiles for the run

        Returns a list of the ReflectionFile objects representing
        the reflection data files reference in the xia2 output."""
        return self.__refln_files

    def journal_file(self):
        """Return name of the journal file for the run

        Returns the full path of the xia2-journal.txt file, if one
        exists - otherwise returns None."""
        return self.__xia2_journal

    def integration_status_key(self):
        """Return the text for the key of integration status icons"""
        return self.__int_status_key

    def get_dataset(self,dataset_name):
        """Fetch the Dataset object corresponding to the supplied name

        'dataset_name' can be either the 'long' version of the name
        (which includes project and crystal qualifiers) or the 'short'
        version (which only has the dataset name)."""
        # Try the long name first i.e. including project and crystal
        for dataset in self.datasets():
            if dataset.name() == dataset_name:
                return dataset
        # Nothing found - try the short name (dataset only)
        for dataset in self.datasets():
            if dataset.datasetName() == dataset_name:
                return dataset
        return None

    def get_crystal(self,xtal_name):
        """Fetch the Crystal object corresponding to the supplied name"""
        for xtal in self.crystals():
            if xtal.name() == xtal_name:
                return xtal
        # Nothing found
        return None

# Crystal
#
# Store information about a crystal
class Crystal:
    """Xia2 crystal information

    Store information associated with each crystal (e.g. unit
    cell, twinning analysis etc)"""

    def __init__(self,name):
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
        self.__datasets = []

    def name(self):
        """Get the crystal name"""
        return self.__name

    def spacegroup(self):
        """Get the assumed spacegroup"""
        return self.__spacegroup

    def alt_spacegroups(self):
        """Get the list of alternative spacegroups"""
        return self.__alt_spacegroups

    def unit_cell(self):
        """Get the unit cell data

        This returns the Magpie.Data object supplied via the
        setUnitCellData call. The individual unit cell
        parameters can be accessed using:

        x = Crystal.unit_cell()['a']
        
        etc."""
        return self.__unit_cell

    def twinning_score(self):
        """Return the twinning score"""
        return self.__twinning_score

    def twinning_report(self):
        """Return the twinning report"""
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
        # Extract and store spacegroup information
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

    Given the tabulated data from Scala that is reproduced for
    each dataset in the xia2.txt file, extract and store the
    information so that it can be accessed later on."""

    def __init__(self,name,summary_table):
        self.__name = str(name)
        self.__wavelength = None
        self.__summary_table = summary_table
        self.__short_name = self.__name.split('/')[-1]
        # List of Sweep objects
        self.__sweeps = []
        # Instantiate the base class and populate the data structure
        Magpie.Tabulator.__init__(self,self.__summary_table)

    def name(self):
        """Return the full name"""
        return self.__name

    def setWavelength(self,wavelength):
        """Set the wavelength for the dataset"""
        self.__wavelength = wavelength

    def wavelength(self):
        """Return the wavelength (lambda)"""
        return self.__wavelength

    def datasetName(self):
        """Return the dataset name

        This is the trailing part of the full name
        (which we expect has the form project/crystal/dataset)"""
        names = self.__name.split('/')
        dataset_name = names[-1]
        return dataset_name

    def crystalName(self):
        """Return the crystal name

        This is the middle part of the full name
        (which we expect has the form project/crystal/dataset)"""
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

        If there are less than 3 components in the full name
        then None is returned."""
        names = self.__name.split('/')
        if len(names) == 3:
            project_name = names[0]
        else:
            project_name = None
        return project_name

    def summary_data(self):
        """Return the tabular summary data"""
        return self.table()

    def addSweep(self,sweep):
        """Add a sweep to the dataset

        'sweep' is a Sweep object.

        Note: the sweeps are automatically sorted into
        alphanumerical order."""
        self.__sweeps.append(sweep)
        self.__sweeps.sort(self.__cmp_sweeps_by_name)

    def sweeps(self):
        """Return the list of sweeps"""
        return self.__sweeps

    def __cmp_sweeps_by_name(self,sweep1,sweep2):
        """Internal: comparision function for sorting sweeps"""
        # Return value indicates order
        if sweep1.name() <  sweep2.name(): return -1
        if sweep1.name() == sweep2.name(): return 0
        if sweep1.name() >  sweep2.name(): return 1
        return

# Sweep
#
# Store information about an individual sweep
class Sweep:
    """Store information about a sweep reported in the xia2
    output.

    Each sweep has a list of integration runs"""

    def __init__(self,name):
        """Create a new Sweep object"""
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
    """Store information about an integration run for a sweep"""
    
    def __init__(self,sweep_data):
        """New IntegrationRun object

        'sweep_data' is a Magpie.Data object for the
        'integration_status_per_image' pattern."""
        self.__name = None
        self.__start_batch = '0'
        self.__end_batch = '0'
        self.__image_status = ''
        self.__symbol_key = {}
        self.__symbol_list = []
        # Extract and store the sweep data
        self.__process(sweep_data)

    def __process(self,sweep_data):
        """Internal: process sweep data to extract information"""
        # Create a new Magpie processor to break up
        # the supplied data
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
        """Return the sweep name for the integration run"""
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
        status of each image in the run."""
        return self.__image_status

    def countSymbol(self,symbol):
        """Return the number of times a symbol appears

        Given a 'symbol', returns the number of times that symbol
        appears in the status line for this integration run"""
        return self.__image_status.count(symbol)

# LogFile
#
# Store information about a log file and provide tools for
# analysis, annotation etc
class LogFile:
    """Xia2 log file information

    Given the name of a log file from xia2, provides various
    methods for analysis and manipulation."""

    def __init__(self,logfile,pipeline_info):
        """Create a new LogFile object.

        'filen' is the name and path of the log file.

        'pipeline_info' is a PipelineInfo object which is
        used to lookup data such as the associated program,
        description etc."""
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
        """Set the project, crystal, dataset and sweep names"""
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
        """Return the relative filename"""
        return os.path.join(self.relativeDirPath(),self.basename())

    def dir(self):
        """Return directory that the log file is in"""
        return os.path.dirname(self.__filen)

    def absoluteDirPath(self):
        """Return the absolute directory for the log file"""
        return os.path.abspath(self.dir())

    def relativeDirPath(self):
        """Return the relative directory for the log file"""
        return get_relative_path(self.absoluteDirPath())

    def isLog(self):
        """Test whether file is a log file

        Checks whether the file name ends with .log extension"""
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
        identifies the dataset that it relates to."""
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

#######################################################################
# Classes for generating the output HTML document
#######################################################################

# IntegrationStatusReporter
#
# Helps with reporting the status of each image in sweeps
class IntegrationStatusReporter:
    """Class to handle reporting the integration status per image"""

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
        'O' => overloaded  '#' => many bad  '.' => blank
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

    #########################################################
    # Deal with command line etc
    #########################################################

    # Set usage string
    usage = "python Xia2html.py [<xia2-output-dir>]"

    # Needs one argument to run (i.e. name of a Xia2 output directory)
    if len(sys.argv) < 2:
        # No Xia2 output directory supplied - assume cwd
        xia2dir = os.getcwd()
        print "Running in current directory: "+str(xia2dir)
    elif len(sys.argv) == 2:
        # Xia2 output directory is the last argument
        xia2dir = os.path.abspath(sys.argv[-1])
    else:
        # Something unexpected
        print "Usage: "+str(usage)
        sys.exit(1)

    # Check the target directory exists
    if not os.path.exists(xia2dir):
        print "Directory not found: \""+str(xia2dir)+"\""
        sys.exit(1)

    # Check the xia2.txt file exists
    if not os.path.exists(os.path.join(xia2dir,"xia2.txt")):
        print "xia2.txt not found"
        sys.exit(1)

    # Collect the XIA2HTML environment variable setting
    xia2htmldir = os.environ['XIA2HTMLDIR']
    print "XIA2HTMLDIR environment variable set to %s" % xia2htmldir

    # Location of the icons
    xia2icondir = os.path.join(xia2htmldir,"icons")

    #########################################################
    # Some decisions are made here
    #########################################################

    # We'll make a subdirectory in the current directory
    # for the generated files, images and helpers
    #
    # Relative path for directory with xia2html output files
    xia2_html_dir = "xia2_html"
    #
    # Absolute path for directory with xia2html output files
    xia2_html = os.path.join(os.getcwd(),xia2_html_dir)
    if not os.path.isdir(xia2_html):
        # Try to make the directory
        print "Making output subdirectory %s" % xia2_html
        os.mkdir(xia2_html)

    #########################################################
    # Construct Magpie processor object for xia2.txt
    #########################################################

    xia2 = Magpie.Magpie(os.path.join(xia2dir,"xia2.txt"))

    # Define patterns
    # Each time a pattern is matched in the source document
    # a data item is created with the name attached to that
    # pattern
    #
    # xia2_version pattern
    #
    # An example of a matching line is:
    #XIA2 0.3.1.0
    xia2.addPattern('xia2_version',
                    "XIA2 ([0-9.]+)$",
                    ['version'])
    # project_name pattern
    #
    # An example of a matching line is:
    #Project: AUTOMATIC
    xia2.addPattern('project_name',"Project: (.*)$",['name'])
    #
    # sequence pattern
    #
    # An example of a matching line is:
    #Sequence: GIVEQCCASVCSLYQLENYCNFVNQHLCGSHLVEALYLVCGERGFFYTPKA
    xia2.addPattern('sequence',"Sequence: ?(.*)$",['sequence'])
    #
    # wavelength pattern
    #
    # An example of a matching set of lines is:
    #Wavelength name: NATIVE
    #Wavelength 0.97900
    xia2.addPattern('wavelength',
                    "Wavelength name: ([^\n]*)\nWavelength (.*)$",
                    ['name','lambda'])
    # xia2_used pattern
    #
    # An example of a matching line is:
    #XIA2 used...  ccp4 mosflm pointless scala xia2
    xia2.addPattern('xia2_used',
                    "XIA2 used... ([^\n]*)",
                    ['software'])
    # processing_time pattern
    #
    # An example of a matching line is:
    #Processing took 00h 14m 24s
    xia2.addPattern('processing_time',
                    "Processing took ([0-9]+h [0-9]+m [0-9]+s)",
                    ['time'])
    # xia2_status
    #
    # An example of a matching line is:
    #Status: normal termination
    xia2.addPattern('xia2_status',
                    "Status: ([^\n]*)",
                    ['status'])
    # twinning pattern
    #
    # An example of a matching set of lines:
    #Overall twinning score: 1.86
    #Ambiguous score (1.6 < score < 1.9)
    xia2.addPattern('twinning',
                    "Overall twinning score: ([^\n]+)\n([^\n]+)",
                    ['score','report'])
    # asu_and_solvent pattern
    #
    # An example of a matching set of lines:
    #Likely number of molecules in ASU: 1
    #Giving solvent fraction:        0.64
    xia2.addPattern('asu_and_solvent',
                    "Likely number of molecules in ASU: ([0-9]+)\nGiving solvent fraction:        ([0-9.]+)",
                    ['molecules_in_asu','solvent_fraction'])
    # unit_cell pattern
    #
    # An example of a matching set of lines:
    #Unit cell:
    #78.013  78.013  78.013
    #90.000  90.000  90.000
    xia2.addPattern('unit_cell',
                    "Unit cell:\n([0-9.]+) +([0-9.]+) +([0-9.]+)\n([0-9.]+) +([0-9.]+) +([0-9.]+)",
                    ['a','b','c','alpha','beta','gamma'])
    # command_line pattern
    #
    # An example of a matching line:
    #Command line: /home/pjb/xia2/Applications/xia2.py -chef -xinfo demo.xinfo
    xia2.addPattern('command_line',
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
    xia2.addPattern('scaled_refln_file',
                    '(mtz|sca|sca_unmerged) format:\nScaled reflections ?\(?([^\):]*)\)?: (.+)$',
                    ['format','dataset','filename'])
    xia2.addPattern('scaled_refln_file',
                    "Scaled reflections ?\(?([^\):]*)\)?: (.+)$",
                    ['dataset','filename','format'])
    # sweep_to_dataset pattern
    #
    # An example of a matching line:
    # SWEEP NATIVE [WAVELENGTH NATIVE]
    xia2.addPattern('sweep_to_dataset',
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
    xia2.defineBlock('dataset_summary',
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
    xia2.defineBlock('assumed_spacegroup',
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
    xia2.defineBlock('citations',
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
    xia2.defineBlock('integration_status_per_image',
                     "--- Integrating","ok",Magpie.EXCLUDE_END)
    # integration_status_key
    #
    # An example of this looks like:
    #
    #"o" => good        "%" => ok        "!" => bad rmsd
    #"O" => overloaded  "#" => many bad  "." => blank
    #"@" => abandoned
    xia2.defineBlock('integration_status_key',"ok","abandoned")
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
    xia2.defineBlock('interwavelength_analysis',
                     "Inter-wavelength B and R-factor analysis",
                     "",Magpie.EXCLUDE)
    # Example of "new style" table:
    #
    #------------------ Local Scaling DEFAULT -------------------
    #WAVE1   0.0 0.00 (ok)
    #WAVE2  -0.3 0.08 (ok)
    #WAVE3  -2.5 0.15 (ok)
    #------------------------------------------------------------
    xia2.defineBlock('interwavelength_analysis',
                     "-- Local Scaling ",
                     "--",Magpie.EXCLUDE)

    # Process the output
    xia2.process()

    # Instantiate a Xia2run object
    xia2run = Xia2run(xia2,xia2dir)
    if not xia2run.complete():
        print "Incomplete processing! Stopped"
        sys.exit(1)

    #########################################################
    # Construct output HTML file
    #########################################################

    # Build up the output HTML using Canary
    xia2doc = Canary.Document("xia2 Processing Report: "+xia2run.project_name())
    xia2doc.addStyle(os.path.join(xia2htmldir,"xia2.css"),Canary.INLINE)
    warning_icon = "<img src='"+os.path.join(xia2_html_dir, "warning.png")+"'>"
    info_icon = "<img src='"+os.path.join(xia2_html_dir,"info.png")+"'>"

    # Test whether xia2 run finished
    if not xia2run.finished():
        # Assume that xia2 is still running
        # For now don't attempt to process incomplete file
        print "*** xia2.txt file is incomplete (xia2 still running?) ***"
        print "Refusing to process incomplete file - stopping"
        sys.exit(1)

    # Build the skeleton of the document here
    # Create the major sections which will be populated later on
    #
    # Preamble
    xia2doc.addPara("XIA2 version %s completed with status '%s'" % \
                    (xia2run.version(), xia2run.termination_status())). \
                    addPara("Read output from %s" % \
                                Canary.MakeLink(xia2dir,
                                                relative_link=True))
    #
    # Initial summary table
    table_one = xia2doc.addTable() # Initial summary table
    #
    # Index section
    index = xia2doc.addSection()
    #
    # Overview section
    xtal_parameters = xia2doc.addSection("Crystallographic parameters")
    #
    # Output files section
    output_files = xia2doc.addSection("Output files")
    output_datafiles = output_files.addSubsection("Reflection data files")
    output_logfiles = output_files.addSubsection("Log files")
    #
    # Integration status section
    int_status_section = xia2doc.addSection("Integration status per image")
    #
    # Detailed statistics
    summary = xia2doc.addSection("Detailed statistics for each dataset")
    #
    # Credits section
    credits = xia2doc.addSection("Credits")
    
    # Crystallographic parameters
    #
    # Unit cell
    unit_cell_params = xtal_parameters.addSubsection("Unit cell")
    for xtal in xia2run.crystals():
        if xia2run.multi_crystal():
            this_section = unit_cell_params.addSubsection("Crystal "+
                                                          xtal.name())
        else:
            this_section = unit_cell_params
        unit_cell = xtal.unit_cell()
        this_section.addTable(['a','b','c',
                               '&alpha;','&beta;','&gamma']). \
                               addRow([unit_cell['a']+'&nbsp;',
                                       unit_cell['b']+'&nbsp;',
                                       unit_cell['c']+'&nbsp;',
                                       unit_cell['alpha']+'&nbsp;',
                                       unit_cell['beta']+'&nbsp;',
                                       unit_cell['gamma']+'&nbsp;'])
    unit_cell_params.addPara(
        info_icon+ \
            " The unit cell parameters are the average for all measurements",
        css_class="info")
    #
    # Spacegroup
    spacegroup = xtal_parameters.addSubsection("Spacegroup")
    for xtal in xia2run.crystals():
        if xia2run.multi_crystal():
            this_section = spacegroup.addSubsection("Crystal "+xtal.name())
        else:
            this_section = spacegroup
        this_section.addPara("Spacegroup: "+htmlise_sg_name(xtal.spacegroup()))
        if xtal.alt_spacegroups():
            this_section.addPara("Other possibilities could be:")
            alt_spg_list = this_section.addList()
            for alt_spg in xtal.alt_spacegroups():
                if alt_spg:
                    alt_spg_list.addItem(htmlise_sg_name(alt_spg))
        else:
            this_section.addPara("No likely alternatives to this spacegroup")
    # Link to logfiles section for pointless log file(s)
    spacegroup.addPara(info_icon+" The spacegroup determination is made using "+
                       "pointless ("+
                       Canary.MakeLink(output_logfiles,
                                       "see the appropriate log file(s)")+")",
                       css_class="info")
    #
    # Twinning
    twinning_analysis = xtal_parameters.addSubsection("Twinning analysis")
    for xtal in xia2run.crystals():
        if xia2run.multi_crystal():
            this_section = twinning_analysis.addSubsection("Crystal "+
                                                           xtal.name())
        else:
            this_section = twinning_analysis
        this_section.addPara("Overall twinning score: "+
                             xtal.twinning_score())
        this_section.addPara(xtal.twinning_report())
    twinning_analysis.addPara(info_icon+
                              " Twinning score is the value of "+
                              "&lt;E<sup>4</sup>&gt;/&lt;I<sup>2</sup>&gt; "+
                              "reported by sfcheck "+
                              Canary.MakeLink("http://www.ccp4.ac.uk/html/sfcheck.html#Twinning%20test",
                                              "(see documentation)"),
                              css_class="info")
    #
    # ASU and solvent content
    asu_contents = xtal_parameters.addSubsection("Asymmetric unit contents")
    for xtal in xia2run.crystals():
        if xia2run.multi_crystal():
            this_section = asu_contents.addSubsection()
        else:
            this_section = asu_contents
        nmols = xtal.molecules_in_asu()
        solvent = xtal.solvent_fraction()
        if not nmols is None and not solvent is None:
            # Create a table
            asu_tbl = this_section.addTable()
            if xia2run.multi_crystal():
                asu_tbl.addRow(["<h4>Crystal "+xtal.name()+"</h4>"],
                               css_classes='xtal_name')
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
            warning_message = warning_icon+" No information on ASU contents"
            if not len(xtal.sequence()):
                warning_message += " due to missing sequence information"
            this_section.addPara(warning_message)

    # Inter-wavelength analysis tables
    #
    # Determine how many tables there are
    got_interwavelength = False
    for xtal in xia2run.crystals():
        if xtal.interwavelength_analysis():
            got_interwavelength = True
            break
    if got_interwavelength:
        # Make a section to print the table(s)
        interwavelength_analysis = xtal_parameters.addSubsection(
            "Inter-wavelength B and R-factor analysis")
        # Examine each crystal
        for xtal in xia2run.crystals():
            if xtal.interwavelength_analysis():
                # This crystal has the data
                interwavelength_table = Canary.MakeMagicTable(
                    xtal.interwavelength_analysis(),' ')
                interwavelength_table.setHeader(['Wavelength',
                                                 'B-factor',
                                                 'R-factor',
                                                 'Status'])
                # Do we need a specific section to display it?
                if xia2run.multi_crystal():
                    # Make a section to display it
                    interwavelength_analysis.addSubsection(
                        "Crystal "+xtal.name()).\
                        addContent(interwavelength_table)
                else:
                    # No specific subsection needed
                    interwavelength_analysis.addContent(interwavelength_table)

    #########################################################
    # External files
    #########################################################

    # External reflection files
    if not xia2.count('scaled_refln_file'):
        output_datafiles.addPara(warning_icon+
                                 " No reflection data files were found",
                                 css_class='warning')
    else:
        # Display table of reflection files
        output_datafiles.addPara("The following reflection data files are available:")
        refln_files = output_datafiles.addTable()
        refln_files.addClass('refln_files')
        last_refln_format = None
        for refln_file in xia2run.refln_files():
            filen = refln_file.basename()
            refln_format = refln_file.format()
            if refln_format != last_refln_format:
                # Add a title row for the new format
                refln_files.addRow([str(refln_format).upper()+" files",""],
                                   css_classes='refln_format')
                last_refln_format = refln_format
                # Add "useful for.."
                try:
                    refln_files.addRow(["Useful for: "+
                                        refln_file.useful_for()],
                                       css_classes='useful_for')
                except KeyError:
                    pass
                # Add a "header" row for the files below
                if xia2run.multi_crystal():
                    header = ['Crystal','Dataset','File name']
                else:
                    header = ['Dataset','File name']
                refln_files.addRow(header,css_classes='refln_header')
            # Build the row data
            if xia2run.multi_crystal():
                reflndata = [refln_file.crystal()]
            else:
                reflndata = []
            reflndata.extend([refln_file.dataset(),
                              Canary.MakeLink(refln_file.filename(),
                                              filen,relative_link=True)])
            refln_files.addRow(reflndata)

    # External log files
    if not len(xia2run.logfiles()):
        output_logfiles.addPara(warning_icon+" No program log files found in"+ \
                                Canary.MakeLink(xia2run.log_dir(),
                                                relative_link=True),
                                css_class="warning")
    else:
        # Display table of log files
        output_logfiles.addPara("The following log files are located in "+ \
                                    Canary.MakeLink(xia2run.log_dir(),
                                                    relative_link=True)+ \
                                    " and are grouped by processing stage:")
        for xtal in xia2run.crystals():
            if not xia2run.multi_crystal():
                this_section = output_logfiles
            else:
                this_section = output_logfiles.addSubsection(\
                    "Log files for crystal "+xtal.name())
            logs = this_section.addTable()
            logs.addClass('log_files')
            this_stage = None
            this_program = None
            for log in xia2run.logfiles():
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
                    output_logfiles.addPara(warning_icon+
                                            " xia2html: failed to classify log "+
                                            Canary.MakeLink(
                            log.relativeName(),log.basename())+
                                            "<br />Please report this problem",
                                            css_class='warning')
                    continue
                if stage != this_stage:
                    logs.addRow([stage,''],css_classes='proc_stage')
                    this_stage = stage
                # Get the description of the log file
                if program != this_program:
                    description = log.description()
                    if description:
                        logs.addRow([description],css_classes='proc_description')
                        this_program = program
                logdata = [log.basename(),
                           Canary.MakeLink(log.relativeName(),"original")]
                # Link to baubles file
                html_log = log.baublize(target_dir=xia2_html_dir)
                if html_log:
                    logdata.append(Canary.MakeLink(html_log,"html"))
                else:
                    logdata.append(None)
                # Warnings from smartie analysis
                if len(log.warnings()):
                    logdata.append(Canary.MakeLink(html_log+"#warnings",
                                                   warning_icon+" See warnings"))
                else:
                    logdata.append('')
                # Add data to the table
                logs.addRow(logdata)
        # Add a warning for any logs that weren't assigned to a crystal
        unassigned_logs = []
        for log in xia2run.logfiles():
            if not log.crystal(): unassigned_logs.append(log)
        if len(unassigned_logs):
            output_logfiles.addPara(warning_icon+ \
                      " The following files weren't assigned to a crystal: ", \
                                      css_class="warning")
            unassigned = output_logfiles.addList()
            for log in unassigned_logs:
                unassigned.addItem(Canary.MakeLink(
                        log.relativeName(),log.basename()))
        # Add a link to the journal file xia2-journal.txt, if found
        if xia2run.journal_file():
            output_logfiles.addPara(info_icon+" More detailed information on what xia2 did can be found in the &quot;journal&quot; file:",css_class="info")
            output_logfiles.addList().addItem(Canary.MakeLink(
                    xia2run.journal_file(),"xia2-journal.txt",
                    relative_link=True))
        # Copy the JLoggraph applet to the xia2_html directory
        # It lives in the "extras" subdir of the Xia2html source
        # directory
        jar_file = "JLogGraph.jar"
        jloggraph_jar = os.path.join(xia2htmldir,"extras",jar_file)
        print "Copying %s to %s" % (jloggraph_jar,xia2_html)
        if os.path.isfile(jloggraph_jar):
            shutil.copy(jloggraph_jar,os.path.join(xia2_html,jar_file))
        else:
            print "*** %s not found ***" % jloggraph_jar
            output_logfiles.addPara(warning_icon+" Unable to copy "+
                                    jloggraph_jar+": file not found<br />"+
                                    "Loggraphs in html log files may not work",
                                    css_class="warning")
                            
    # Detailed statistics for each dataset
    print "Number of datasets: "+str(len(xia2run.datasets()))
    # If there is more than one datatset then write a TOC
    if len(xia2run.datasets()) > 1:
        summary.addPara("Statistics for each of the following datasets:")
        summary.addTOC()
    statistic_sections = {}
    for dataset in xia2run.datasets():
        # Make a subsection for each dataset
        if xia2run.multi_crystal():
            section_title = "Crystal "+dataset.crystalName()+\
                " Dataset "+dataset.datasetName()
        else:
            section_title = "Dataset "+dataset.datasetName()
        stats_subsection = summary.addSubsection(section_title)
        summary_table = Canary.MakeMagicTable(dataset.summary_data())
        summary_table.setHeader(['','Overall','Low','High'])
        stats_subsection.addContent(summary_table)
        # Store a reference to the subsection for linking to later
        statistic_sections[dataset.name()] = stats_subsection

    #########################################################
    # Integration status per image
    #########################################################
    int_status_reporter = IntegrationStatusReporter(xia2_html_dir,
                                            xia2run.integration_status_key())
    # Write out the preamble and key of symbols
    int_status_section.addPara("The following sections show the status of each image from the final integration run performed on each sweep within each dataset.")
    # Add a summary table here - it will be populated as
    # we got along
    int_status_section.addPara("This table summarises the image status for each dataset and sweep.")
    int_table = int_status_section.addTable()
    # Loop over crystals
    this_xtal = None
    for xtal in xia2run.crystals():
        print ">>>> CRYSTAL: "+xtal.name()
        # Make a section for each crystal (if multi-crystal run)
        if xia2run.multi_crystal():
            this_section = int_status_section.addSubsection("Crystal %s" %
                                                            xtal.name())
        else:
            this_section = int_status_section
        # Loop over datasets
        this_dataset = None
        for dataset in xtal.datasets():
            print ">>>> DATASET: "+dataset.datasetName()
            # Make a section for each dataset
            int_status_dataset_section = this_section. \
                addSubsection("Dataset %s" % dataset.datasetName())
            # Deal with each sweep associated with the dataset
            for sweep in dataset.sweeps():
                print ">>>> SWEEP: "+str(sweep.name())
                last_int_run = sweep.last_integration_run()
                if not last_int_run:
                    # No last integration run found
                    int_status_dataset_section.addPara(warning_icon + \
                        " Error aquiring last integration run for sweep "+ \
                        sweep.name(),css_class="warning")
                    break
                # Output status info for this sweep in its own section
                start_batch = last_int_run.start_batch()
                end_batch = last_int_run.end_batch()
                sweep_section = int_status_dataset_section. \
                    addSubsection(sweep.name() + ": batches " + start_batch + \
                                  " to " + end_batch)
                # Get the HTML representation of the status line
                images_html = int_status_reporter. \
                    htmliseStatusLine(last_int_run)
                sweep_section.addContent("<p>"+images_html+"</p>")
                # Add a row to the summary table
                row = []
                total = 0
                if xia2run.multi_crystal():
                    if this_xtal != xtal:
                        # Only link to each crystal once from the table
                        this_xtal = xtal
                        row.append(Canary.MakeLink(this_section,xtal.name()))
                    else:
                        row.append('')
                if this_dataset != dataset:
                    # Only link to each dataset once from the table
                    this_dataset = dataset
                    row.append(Canary.MakeLink(
                            int_status_dataset_section,
                        dataset.datasetName()))
                else:
                    row.append('')
                # Link to sweep followed by the stats
                row.append(Canary.MakeLink(sweep_section,sweep.name()))
                for symbol in int_status_reporter.getSymbolList():
                    row.append(str(last_int_run.countSymbol(symbol)))
                    total += last_int_run.countSymbol(symbol)
                row.append(total)
                int_table.addRow(row)
    # Finish off the summary table by adding the header
    header = []
    if xia2run.multi_crystal():
        header.append('Crystal')
    header.extend(['Dataset','Sweep'])
    for symbol in int_status_reporter.getSymbolList():
        symbol_status = int_status_reporter.lookupStatus(symbol)
        description = int_status_reporter.getDescription(symbol_status)
        symbol_image = int_status_reporter.getIcon(symbol_status)
        header.append(description+"<br />"+symbol_image)
    header.append("Total")
    int_table.setHeader(header)
    # Finally: copy the icons to the xia2_html directory
    print "Copying icons to %s" % xia2_html
    icons = int_status_reporter.listIconNames()
    icons.append("warning.png")
    icons.append("info.png")
    for icon in icons:
        shutil.copy(os.path.join(xia2icondir,icon),
                    os.path.join(xia2_html,icon))
    # Credits section
    #
    # Programs used by XIA2
    programs = credits.addSubsection("Software Used").addList()
    for prog in xia2['xia2_used'][0].value('software').split():
        programs.addItem(prog)
    # Citations
    citer = Citations()
    citations = credits.addSubsection("Citations")
    citations.addPara("Note: links to external content that may require you to login before you can view or download",css_class="info")
    citation_list = citations.addList()
    for line in str(xia2['citations'][0]).split('\n'):
        if line.strip() != "":
            # Get citation link
            url = citer.getCitationLink(line)
            if url:
                citation_list.addItem(Canary.MakeLink(url,line))
            else:
                citation_list.addItem(line)
    # Some other xia2-specific stuff
    sect_xia2_stuff = credits.addSubsection("xia2 Details")
    sect_xia2_stuff.addPara("Additional details about this run:")
    tbl_xia2_stuff = sect_xia2_stuff.addTable()
    tbl_xia2_stuff.addClass('xia2_info')
    tbl_xia2_stuff.addRow(['Version',xia2run.version()])
    tbl_xia2_stuff.addRow(['Run time',xia2run.run_time()])
    tbl_xia2_stuff.addRow(['Command line',xia2run.cmd_line()])
    tbl_xia2_stuff.addRow(['Termination status',xia2run.termination_status()])
    xia2txt = os.path.join(xia2dir,"xia2.txt")
    tbl_xia2_stuff.addRow(['xia2.txt file',
                           Canary.MakeLink(xia2txt,relative_link=True)])
    
    # Put in some forwarding linking from the index
    index.addPara("Contents of the rest of this document:")
    forward_links = index.addList()
    forward_links.addItem(Canary.MakeLink(output_datafiles,
                                     "Reflection data files output from xia2"))
    forward_links.addItem(Canary.MakeLink(summary,
                                     "Full statistics for each wavelength"))
    forward_links.addItem(Canary.MakeLink(output_logfiles,
                                     "Log files from individual stages"))
    forward_links.addItem(Canary.MakeLink(int_status_section,
                       "Integration status for images by wavelength and sweep"))
    forward_links.addItem(Canary.MakeLink(credits,
                                     "Lists of programs and citations"))

    # Footer section
    footer = "This file generated for you from xia2 output by Xia2html %s on %s<br />Powered by Magpie %s and Canary %s<br />&copy; Diamond 2009" \
        % (__version__,
           time.asctime(),
           Magpie.version(),
           Canary.version())
    xia2doc.addContent("<p class='footer'>%s</p>" % footer)

    #########################################################
    # "Table one" (initial summary table)
    #########################################################
    # Note: although this table appears at the start of the output
    # document, we make it last so we can link to later content
    table_one.addClass('table_one')
    row_titles = ['Wavelength (&Aring;)',
                  'High resolution limit',
                  'Low resolution limit',
                  'Completeness',
                  'Multiplicity',
                  'I/sigma',
                  'R<sub>merge</sub>']
    if xia2run.has_anomalous():
        row_titles.extend(['Anomalous completeness',
                           'Anomalous multiplicity'])
    row_titles.extend(['']) # Line linking to full stats
    # Deal with crystal-specific data
    xtal_data = { "unit_cell_a": ['Unit cell dimensions: a (&Aring;)'],
                  "unit_cell_b": ['b (&Aring;)'],
                  "unit_cell_c": ['c (&Aring;)'],
                  "unit_cell_alpha": ['&alpha; (&deg;)'],
                  "unit_cell_beta": ['&beta; (&deg;)'],
                  "unit_cell_gamma": ['&gamma; (&deg;)'],
                  "spacegroup": ['Spacegroup'],
                  "twinning": ['Sfcheck twinning score']}
    last_xtal = None
    # Add initial title column
    table_one.addColumn(row_titles)
    # Add additional columns for each dataset
    for dataset in xia2run.datasets():
        # Crystal-specific data
        xtal = xia2run.get_crystal(dataset.crystalName())
        if xtal.name() != last_xtal:
            # New crystal - fetch data
            unit_cell = xtal.unit_cell()
            spacegroup = xtal.spacegroup()
            twinning_score = xtal.twinning_score()
            twinning_report = xtal.twinning_report()
            # Store the data for print out at the end
            xtal_data['unit_cell_a'].extend([unit_cell['a'],None])
            xtal_data['unit_cell_b'].extend([unit_cell['b'],None])
            xtal_data['unit_cell_c'].extend([unit_cell['c'],None])
            xtal_data['unit_cell_alpha'].extend([unit_cell['alpha'],None])
            xtal_data['unit_cell_beta'].extend([unit_cell['beta'],None])
            xtal_data['unit_cell_gamma'].extend([unit_cell['gamma'],None])
            xtal_data['spacegroup'].extend([htmlise_sg_name(spacegroup),None])
            xtal_data['twinning'].extend([twinning_score+"<br />"+
                                         twinning_report,None])
            # Update last crystal name
            last_xtal = xtal.name()
        else:
            # Same crystal as before
            xtal_data['unit_cell_a'].extend([None,None])
            xtal_data['unit_cell_b'].extend([None,None])
            xtal_data['unit_cell_c'].extend([None,None])
            xtal_data['unit_cell_alpha'].extend([None,None])
            xtal_data['unit_cell_beta'].extend([None,None])
            xtal_data['unit_cell_gamma'].extend([None,None])
            xtal_data['spacegroup'].extend([None,None])
            xtal_data['twinning'].extend([None,None])
        # Construct the column of data and add to the table
        # This is for the overall/average values
        column_data = [dataset.wavelength(),
                       dataset['High resolution limit'][1],
                       dataset['Low resolution limit'][1],
                       dataset['Completeness'][1],
                       dataset['Multiplicity'][1],
                       dataset['I/sigma'][1],
                       dataset['Rmerge'][1]]
        if xia2run.has_anomalous():
            try:
                anom_completeness = dataset['Anomalous completeness'][1]
                anom_multiplicity = dataset['Anomalous multiplicity'][1]
            except KeyError:
                anom_completeness = '-'
                anom_multiplicity = '-'
            column_data.extend([anom_completeness,anom_multiplicity])
        # Link forward to full stats for this dataset
        column_data.append(Canary.MakeLink(
                statistic_sections[dataset.name()],
                "See all statistics"))
        # Append the column to the table
        if len(xia2run.crystals()) > 1:
            # Add the crystal name
            column_title = dataset.crystalName()+"<br />"
        else:
            column_title = ''
        column_title += dataset.datasetName()
        table_one.addColumn(column_data,
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
                       "("+dataset['I/sigma'][2]+\
                       " - "+dataset['I/sigma'][3]+")",
                       "("+dataset['Rmerge'][2]+\
                       " - "+dataset['Rmerge'][3]+")"]
        if xia2run.has_anomalous():
            try:
                anom_completeness = "("+dataset['Anomalous completeness'][2]+\
                                    " - "+\
                                    dataset['Anomalous completeness'][3]+")"
                anom_multiplicity = "("+dataset['Anomalous multiplicity'][2]+\
                                    " - "+\
                                    dataset['Anomalous multiplicity'][3]+")"
            except KeyError:
                anom_completeness = '-'
                anom_multiplicity = '-'
            column_data.extend([anom_completeness,anom_multiplicity])
        table_one.addColumn(column_data)
    # Additional data: unit cell, spacegroup
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(xtal_data['unit_cell_a'],"unit_cell")
    table_one.addRow(xtal_data['unit_cell_b'],"unit_cell")
    table_one.addRow(xtal_data['unit_cell_c'],"unit_cell")
    table_one.addRow(xtal_data['unit_cell_alpha'],"unit_cell")
    table_one.addRow(xtal_data['unit_cell_beta'],"unit_cell")
    table_one.addRow(xtal_data['unit_cell_gamma'],"unit_cell")
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(xtal_data['spacegroup'])
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(xtal_data['twinning'])
    table_one.addRow(['',Canary.MakeLink(xtal_parameters,
                                         "All crystallographic parameters..")])

    # Spit out the HTML
    xia2doc.renderFile('xia2.html')

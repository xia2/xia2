#     Xia2html.py: turn Xia2 output into HTML
#     Copyright (C) Diamond 2009 Peter Briggs
#
########################################################################
#
# Xia2html.py
#
########################################################################
#
# Extract information from XIA2 output and generate an interactive
# HTML document
#
# Run as an application using:
# python /path/to/Xia2Log.py <xia2_output_dir>
#
# where <xia2_output_dir> is the location of xia2.txt and the rest of
# the xia2 output (including LogFiles etc).
#
# Needs the XIA2HTMLDIR environment variable to be set to the directory
# where this file (and supporting modules etc) are held.
#
# Creates a xia2.html file in the current directory, plus a xia2_html
# subdirectory which is used to hold associated files (PNGs, html
# versions of log files etc)
#
__cvs_id__ = "$Id: Xia2html.py,v 1.41 2009/12/16 09:57:20 gwin Exp $"
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
            False)
        self.addLogInfo(
            "CORRECT",
            "xds",
            "Integration",
            "Postrefinement and correction for this sweep")
        self.addLogInfo(
            "_mosflm_integrate",
            "mosflm",
            "Integration",
            "Full logs for the integration of each wavelength")
        self.addLogInfo(
            "_postrefinement",
            "mosflm",
            "Integration",
            "Results of postrefinement",
            baublize=True)
        # Spacegroup determination
        self.addLogInfo(
            "_pointless",
            "pointless",
            "Spacegroup Determination",
            "Decision making for the spacegroup assignment",
            baublize=True)
        # Scaling and merging
        self.addLogInfo(
            "XSCALE",
            "xscale",
            "Scaling and merging",
            "Scaling together all the data for this crystal")
        self.addLogInfo(
            "_scala",
            "scala",
            "Scaling and merging",
            "Scaling and correction of all measurements on the crystal",
            baublize=True)
        # Analysis
        self.addLogInfo(
            "_truncate",
            "truncate",
            "Analysis",
            "Intensity analysis for each wavelength of data",
            baublize=True)
        self.addLogInfo(
            "chef_",
            "chef",
            "Analysis",
            "Cumulative radiation damage analysis",
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

    def addLogInfo(self,logname,program,stage,description,baublize=False):
        """Add information about a log file

        'logname' is part of the log file name which is used to
        identify it.

        'program' is the source program name.

        'stage' is the name of the processing stage that the file
        belongs to.

        'description' is generic text that describes what the function
        of the log file is.

        'baublize' is a logical value indicating whether the log
        can be baublized."""
        self.__pipeline.append({
                'logname': logname,
                'program': program,
                'stage': stage,
                'description': description,
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

    def dataset(self):
        """Return dataset name associated with this log file"""
        print "*** NOT IMPLEMENTED ***"
        return ''

    def sweep(self):
        """Return sweep name associated with this log file"""
        print "*** NOT IMPLEMENTED ***"
        return ''

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

    def __init__(self,filename,format,dataset):
        """Create a ReflectionFile object

        'filename' is the name of the reflection data file,
        'format' is the format (e.g. mtz) and 'dataset' is the
        name of the dataset that it relates to."""
        self.__filename = filename
        self.__format = format
        if not dataset:
            self.__dataset = "All datasets"
        else:
            self.__dataset = dataset
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
        """Return the dataset of the reflection file"""
        return self.__dataset

    def useful_for(self):
        """Return description of the what the file can be used for

        This returns a text description of what the file can be
        used for.

        NB The descriptions are taken from a look-up table that is
        internal to the ReflectionFile class. To modify see the
        __init__ method of this class."""
        return self.__format_useful_for[self.format()]

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
        self.__xia2_journal = None # Journal file
        self.__log_dir   = None # Logfile directory
        self.__datasets    = [] # List of datasets
        self.__crystals    = [] # List of crystals
        self.__sweeps      = [] # List of sweeps
        self.__logfiles    = [] # List of log files
        self.__refln_files = [] # List of reflection data files
        self.__has_anomalous = False # Anomalous data?
        self.__xds_pipeline  = False # XDS pipeline used?
        self.__pipeline_info = PipelineInfo() # Data about logfiles
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
        # Datasets
        print "POPULATE> DATASETS"
        for dataset in xia2['dataset_summary']:
            print "DATASETS> dataset: "+str(dataset.value('dataset'))
            self.__datasets.append(Dataset(dataset.value('dataset'),
                                           dataset.value('table')))
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
        # Anomalous data?
        # Look for the "anomalous_completeness" data item in
        # the dataset summary table
        print "POPULATE> ANOMALOUS DATA"
        for dataset in self.__datasets:
            try:
                x = dataset['anomalous_completeness']
                self.__has_anomalous = True
                break
            except KeyError:
                pass
        # Logfiles
        # Look in the xia2 LogFiles directory
        print "POPULATE> LOGFILES"
        self.__log_dir = os.path.abspath(os.path.join(xia2dir,"LogFiles"))
        logdir = get_relative_path(self.__log_dir)
        # Process logfiles
        try:
            xds_pipeline = False
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
                        xds_pipeline = True
                else:
                    print "LOGFILES> "+log.basename()+ \
                          " not a log file, ignored"
            if xds_pipeline: self.__pipeline_info.setXDSPipeline()
        except OSError:
            # Possibly the LogFiles directory doesn'texist
            if not os.path.isdir(logdir):
                print "LOGFILES> LogFiles directory not found"
            else:
                raise
        # Reflection files
        print "POPULATE> REFLECTION FILES"
        refln_format = None
        for refln_file in xia2['scaled_refln_file']:
            filen = refln_file.value('filename')
            print "REFLN_FILE> file   : "+filen
            if refln_file.value('format'):
                # Format is already defined so collect it
                refln_format = refln_file.value('format')
            print "REFLN_FILE> format : "+refln_format
            refln_dataset = refln_file.value('dataset')
            print "REFLN_FILE> dataset: "+str(refln_dataset)
            # Store the data for this file
            self.__refln_files.append(ReflectionFile(filen,
                                                     refln_format,
                                                     refln_dataset))
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

    def log_dir(self):
        """Return location of the xia2 LogFiles directory

        This is the absolute path for the xia2 logfile directory."""
        return self.__log_dir

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
        self.__twinning   = None

    def name(self):
        """Get the crystal name"""
        return self.__name

    def setUnitCellData(self,unit_cell):
        """Set the unit cell data"""
        self.__unit_cell = unit_cell

    def unitCellData(self):
        """Get the unit cell data"""
        return self.__unit_cell

    def setSpacegroupData(self,spacegroup):
        """Set the spacegroup data"""
        self.__spacegroup = spacegroup

    def spacegroupData(self):
        """Get the spacegroup data"""
        return self.__spacegroup

    def setTwinningData(self,twinning):
        """Set the twinning data"""
        self.__twinning = twinning

    def twinningData(self):
        """Get the twinning data"""
        return self.__twinning

# Dataset
#
# Store information about a dataset
class Dataset:
    """Xia2 dataset information

    Given the tabulated data from Scala that is reproduced for
    each dataset in the xia2.txt file, extract and store the
    information so that it can be accessed later on."""

    def __init__(self,name,tabular_data,auto_separator='\t'):
        self.__name = str(name)
        self.__short_name = self.__name.split('/')[-1]
        # Auto separator is the delimiter separating tabular items
        self.__auto_separator = auto_separator
        # List of keys (stored data items)
        self.__keys = []
        self.__data = {}
        # Extract data and populate the data structure
        self.__extract_tabular_data(tabular_data)

    def __extract_tabular_data(self,tabular_data):
        """Internal: build data structure from tabular data"""
        for row in tabular_data.strip('\n').split('\n'):
            row_data = row.split(self.__auto_separator)
            key = row_data[0].lower().strip(' ').replace(' ','_')
            self.__keys.append(key)
            self.__data[key] = row_data

    def __getitem__(self,name):
        """Implement Dataset[name] for get operations

        Returns the 'row' of data associated with the key 'name'
        i.e. a list of items."""
        return self.__data[name]

    def name(self):
        """Return the full name"""
        return self.__name

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

    def keys(self):
        """Return the list of data item names (keys)"""
        return self.__keys

# IntegrationStatusReporter
#
# Helps with reporting the status of each image in sweeps
class IntegrationStatusReporter:
    """Class to handle reporting the integration status per image"""

    def __init__(self,img_dir,key_text=None):
        """Create a new IntegrationStatusRenderer

        'img_dir' points to the location of the image icons.

        'key_text' is the text from the xia2.txt file which
        links the text symbols to their meanings."""
        self.__img_dir = img_dir
        self.__symbol_dict = self.__makeSymbolDictionary()
        self.__symbol_lookup = self.__makeReverseSymbolLookup()
        self.__symbol_list = self.__listSymbols()
        return

    def __listSymbols(self):
        """Internal: make a list of the symbols"""
        return ['o','%','O','!','#','.','@']

    def __makeSymbolDictionary(self):
        """Internal: build the symbol dictionary from the key text"""
        # FIXME for now just hardcode the dictionary
        return { 'good': 'o',
                 'overloaded': 'O',
                 'ok': '%',
                 'bad_rmsd': '!',
                 'many_bad': '#',
                 'blank': '.',
                 'abandoned': '@' }

    def __makeReverseSymbolLookup(self):
        """Internal: build the reverse lookup table for symbols"""
        symbol_lookup = {}
        for key in self.__symbol_dict.keys():
            symbol_lookup[self.__symbol_dict[key]] = key
        return symbol_lookup

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
        return "img_"+status+".png"

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

    def makeSymbolKey(self,ncolumns=2):
        """Generate the key of symbols to descriptions (alternative)

        Optional argument 'ncolumns' specifies how many columns to
        have in each row of the table."""
        key_tbl = Canary.Table()
        key_tbl.addClass('key')
        key_tbl.addTitle('Explanation of the symbols used below')
        key_tbl.setHeader(['Key to symbols'])
        row_data = []
        for status in self.__symbol_dict.keys():
            img_icon = self.getIcon(status)
            description = self.getDescription(status)
            row_data.append(img_icon)
            row_data.append(description)
            if len(row_data) == ncolumns:
                # Row is full, add to the table
                key_tbl.addRow(row_data)
                row_data = []
        # Make sure that an incomplete final row is also added
        if len(row_data): key_tbl.addRow(row_data)
        return key_tbl.render()

#######################################################################
# Module Functions
#######################################################################

def list_sweeps(int_status_list,dataset=None):
    """Return a list of sweep names

    Given a list of 'integration_status_...' Data objects,
    return a list of the unique sweep names.

    Optionally if a 'dataset' name is given, then the
    list will only have those sweeps associated with that
    dataset name.

    If sweeps are called SWEEP1, SWEEP2 etc then this will
    also sort them into alphanumeric order."""
    sweep_list = []
    auto_assigned = True
    for int_status in int_status_list:
        this_sweep = int_status.value('sweep')
        # Check for matching dataset name
        if dataset:
            if int_status.value('dataset') != dataset: continue
        # Check if name has been encountered before
        if not sweep_list.count(this_sweep):
            sweep_list.append(this_sweep)
            if not this_sweep.startswith("SWEEP"):
                auto_assigned = False
    # If the names were automatically assigned (i.e. all
    # start with SWEEP...) then sort alphanumerically
    if auto_assigned:
        sweep_list.sort()
    return sweep_list

def get_last_int_run(int_status_list,sweep):
    """Return the last integration run for the named sweep

    Given a list of 'integration_status_...' Data objects,
    return the Data object corresponding to the final
    integration run for the named sweep."""
    last_run = None
    for run in int_status_list:
        if run.value('sweep') == sweep: last_run = run
    return last_run

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
    xia2_html_dir = "xia2_html"
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
    xia2.addPattern('xia2_version',
                    "XIA2 ([0-9.]+)$",
                    ['version'])
    xia2.addPattern('project_name',"Project: (.*)$",['name'])
    xia2.addPattern('sequence',"Sequence: (.*)$",['sequence'])
    xia2.addPattern('wavelength',
                    "Wavelength name: ([^\n]*)\nWavelength (.*)$",
                    ['name','lambda'])
    xia2.addPattern('computed_average_unit_cell',
                    "Computed average unit cell \(will use in all files\)\n([^\n]*)",['cell_parameters'])
    xia2.addPattern('xia2_used',
                    "XIA2 used... ([^\n]*)",
                    ['software'])
    xia2.addPattern('processing_time',
                    "Processing took ([0-9]+h [0-9]+m [0-9]+s)",
                    ['time'])
    xia2.addPattern('xia2_status',
                    "Status: ([^\n]*)",
                    ['status'])
    # twinning pattern matches:
    # Overall twinning score: 1.86
    # Ambiguous score (1.6 < score < 1.9)
    xia2.addPattern('twinning',
                    "Overall twinning score: ([^\n]+)\n([^\n]+)",
                    ['score','report'])
    xia2.addPattern('asu_and_solvent',
                    "Likely number of molecules in ASU: ([0-9]+)\nGiving solvent fraction:        ([0-9.]+)",
                    ['molecules_in_asu','solvent_fraction'])
    xia2.addPattern('unit_cell',
                    "Unit cell:\n([0-9.]+) +([0-9.]+) +([0-9.]+)\n([0-9.]+) +([0-9.]+) +([0-9.]+)",
                    ['a','b','c','alpha','beta','gamma'])
    # command_line pattern matches:
    # Command line: /home/pjb/xia2/Applications/xia2.py -chef -xinfo demo.xinfo
    xia2.addPattern('command_line',
                    "Command line: (.*)$",
                    ['cmd_line'])
    # Pair of patterns with the same name but match slightly
    # different instances of the same information (reflection files)
    xia2.addPattern('scaled_refln_file',
                    '(mtz|sca|sca_unmerged) format:\nScaled reflections ?\(?([^\):]*)\)?: (.+)$',
                    ['format','dataset','filename'])
    xia2.addPattern('scaled_refln_file',
                    "Scaled reflections ?\(?([^\):]*)\)?: (.+)$",
                    ['dataset','filename','format'])
    # sweep_to_dataset pattern matches:
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
    # assumed_spacegroup block:
    #Assuming spacegroup: I 2 3
    #Other likely alternatives are:
    #I 21 3
    #Unit cell:
    xia2.defineBlock('assumed_spacegroup',
                     "Assuming spacegroup",
                     "Unit cell:",Magpie.EXCLUDE_END)
    xia2.defineBlock('citations',
                     "Here are the appropriate citations",
                     "Status",Magpie.EXCLUDE)
    xia2.defineBlock('interwavelength_analysis',
                     "Inter-wavelength B and R-factor analysis",
                     "Project:",Magpie.EXCLUDE)
    xia2.defineBlock('integration_status_per_image',
                     "--- Integrating","blank")

    # Process the output
    xia2.process()

    #########################################################
    # Intermediate/additional processing
    #########################################################

    # Post-process the assumed spacegroup block
    #
    # Reprocess the blocks using a text-based Magpie processor
    print "****** Additional processing for assumed spacegroup ******"
    # Set up a new processor specifically for this block
    spg_processor = Magpie.Magpie()
    spg_processor.addPattern('spacegroup',
                            "Assuming spacegroup: (.*)$",['name'])
    spg_processor.addPattern('alternative',
                             "([PCFI/abcdmn0-9\- ]+)$",['name'])
    for assumed_spg in xia2['assumed_spacegroup']:
        print "Processing "+str(assumed_spg)
        # Reprocess the text and update the data
        # FIXME: maybe this could be more generally be done
        # inside of Magpie in future?
        spg_processor.processText(str(assumed_spg))
        assumed_spg.setValue('spacegroup',
                             spg_processor['spacegroup'][0].value('name'))
        alt_spgs = []
        for alt in spg_processor['alternative']:
            alt_spgs.append(alt.value('name'))
        assumed_spg.setValue('alternative',alt_spgs)
        # Reset the processor for the next round
        spg_processor.reset()

    # Post-process the inter-wavelength b/r factor table
    #
    # We need to do this because we may have grabbed too much
    # data if we got the terminating pattern wrong
    print "****** Additional processing for interwavelength analysis ******"
    if xia2.count('interwavelength_analysis') > 0:
        for interwavelength in xia2['interwavelength_analysis']:
            # New copy of table
            tbl = []
            for line in str(interwavelength).split('\n'):
                # Terminate the table at the first blank line
                if line == "":
                    # Reset the stored table
                    interwavelength.setValue('interwavelength_analysis',
                                             "\n".join(tbl))
                    break
                else:
                    # Append line to new copy of table
                    tbl.append(line)
    
    # Post-process integration status per image 
    #
    # Reprocess the blocks found from "integration_status_per_image"
    # using a text-based Magpie processor
    print "****** Additional processing for integration status ******"
    # Set up a new processor specifically for this block
    int_status_reporter = IntegrationStatusReporter(xia2_html_dir)
    status_processor = Magpie.Magpie()
    status_processor.addPattern('sweep',
                                "-+ Integrating ([^ ]*) -+",
                                ['name'])
    status_processor.addPattern('batch',
                                "Processed batches ([0-9]+) to ([0-9]+)",
                                ['start','end'])
    status_processor.addPattern('status_per_image',
                                "([oO%#!@]+)$")
    status_processor.addPattern('key',
                                "\"o\".*\n.*blank")
    for int_status in xia2['integration_status_per_image']:
        print "Processing "+str(int_status)
        # Reprocess the text and update the data
        # FIXME: maybe this could be more generally be done
        # inside of Magpie in future?
        status_processor.processText(str(int_status))
        this_sweep = status_processor['sweep'][0].value('name')
        int_status.setValue('sweep',this_sweep)
        try:
            start_batch = status_processor['batch'][0]. \
                          value('start')
            end_batch = status_processor['batch'][0]. \
                        value('end')
        except IndexError:
            # Fudge the (missing) batch numbers
            start_batch = 0
            end_batch = 0
        int_status.setValue('start_batch',start_batch)
        int_status.setValue('end_batch',end_batch)
        image_status_line = ''
        for line in status_processor['status_per_image']:
            image_status_line += str(line) + "\n"
        image_status_line = image_status_line.strip('\n')
        # Count each type of image
        symbol_count = {}
        for symbol in int_status_reporter.getSymbolList():
            symbol_count[symbol] = image_status_line.count(symbol)
        int_status.setValue('count',symbol_count)
        # Find which dataset this sweep belongs to
        int_status.setValue('dataset',None)
        for sweep in xia2['sweep_to_dataset']:
            if sweep.value('sweep') == this_sweep:
                int_status.setValue('dataset',sweep.value('dataset'))
                print "Sweep %s assigned to dataset %s" % \
                    (this_sweep,sweep.value('dataset'))
                break
        # Store the data
        int_status.setValue('image_status',image_status_line)
        # Reset the processor for the next round
        status_processor.reset()

    # Instantiate a Xia2run object
    xia2run = Xia2run(xia2,xia2dir)
    if not xia2run.complete():
        print "Incomplete processing! Stopped"
        sys.exit(1)

    #########################################################
    # Construct output HTML file
    #########################################################

    # Build up the output HTML using Canary
    xia2doc = Canary.Document("xia2 Processing Report")
    xia2doc.addStyle(os.path.join(xia2htmldir,"xia2.css"),Canary.INLINE)
    # warning_icon = "<img src='"+os.path.join(xia2_html,"warning.png")+"'>"
    warning_icon = "<img src='"+os.path.join("xia2_html", "warning.png")+"'>"
    ##xia2doc.addScript("./baubles.js",Canary.INLINE)

    # XIA2 version and other general info
    try:
        termination_status = xia2['xia2_status'][0].value('status')
    except IndexError:
        # Assume that xia2 is still running
        # For now don't attempt to process incomplete file
        print "*** Missing status, file incomplete (xia2 still running?) ***"
        print "Refusing to process incomplete file - stopping"
        sys.exit(1)

    version = xia2['xia2_version'][0].value('version')
    command_line = xia2['command_line'][0].value('cmd_line')
    run_time = xia2['processing_time'][0].value('time')

    # Build the skeleton of the document here
    # Create the major sections which will be populated later on
    #
    # Preamble
    xia2doc.addPara("XIA2 version %s completed with status '%s'" % \
                    (version, termination_status)). \
                    addPara("Read output from %s" % \
                                Canary.MakeLink(xia2dir,
                                                get_relative_path(xia2dir)))
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

    # Populate the "overview" section
    #
    # Crystallographic parameters section
    unit_cell = xia2['unit_cell'][0]
    twinning_score = str(xia2['twinning'][0].value('score'))
    twinning_report = str(xia2['twinning'][0].value('report'))
    try:
        asu_and_solvent = str(xia2['asu_and_solvent'][0])
    except IndexError:
        # Assume that this was missing
        # Put in a default message
        asu_and_solvent = "No information on ASU contents"
    
    # Crystallographic parameters
    #
    # Unit cell
    unit_cell_params = xtal_parameters.addSubsection("Unit cell")
    unit_cell_params.addTable(['a','b','c',
                               '&alpha;','&beta;','&gamma']). \
                               addRow([unit_cell.value('a')+'&nbsp;',
                                       unit_cell.value('b')+'&nbsp;',
                                       unit_cell.value('c')+'&nbsp;',
                                       unit_cell.value('alpha')+'&nbsp;',
                                       unit_cell.value('beta')+'&nbsp;',
                                       unit_cell.value('gamma')+'&nbsp;'])
    unit_cell_params.addPara(
        "The unit cell parameters are the average for all measurements")
    #
    # Spacegroup
    spacegroup = xtal_parameters.addSubsection("Spacegroup")
    spacegroup.addPara("Spacegroup: "+
                       htmlise_sg_name(xia2['assumed_spacegroup'][0].
                                         value('spacegroup')))
    spacegroup.addPara("The spacegroup determination is made using pointless ("+
                       Canary.Link("see the appropriate log file",
                                   output_logfiles).render()+")")
    alt_spgs = xia2['assumed_spacegroup'][0].value('alternative')
    if alt_spgs:
        spacegroup.addPara("Other possibilities could be:")
        alt_spg_list = spacegroup.addList()
        for alt_spg in alt_spgs:
            if alt_spg:
                alt_spg_list.addItem(htmlise_sg_name(alt_spg))
    else:
        spacegroup.addPara("No likely alternatives to this spacegroup")
    #
    # Twinning
    twinning_analysis = xtal_parameters.addSubsection("Twinning analysis")
    twinning_analysis.addPara("Overall twinning score: "+
                              twinning_score+"<br />"+
                              "This is the value of &lt;E<sup>4</sup>&gt; "+
                              "reported by sfcheck")
    twinning_analysis.addPara(twinning_report)
    #
    # ASU and solvent content
    asu_contents = xtal_parameters.addSubsection("Asymmetric unit contents"). \
        addPara(asu_and_solvent)

    # Inter-wavelength analysis table
    try:
        interwavelength_analysis = \
            str(xia2['interwavelength_analysis'][0])
        interwavelength_table = Canary.MakeMagicTable(
            interwavelength_analysis,' ')
        interwavelength_table.setHeader(['Wavelength',
                                         'B-factor',
                                         'R-factor',
                                         'Status'])
        xtal_parameters.addSubsection(
            "Inter-wavelength B and R-factor analysis"). \
            addContent(interwavelength_table)
    except IndexError:
        # Table not found, ignore
        pass

    #########################################################
    # External files
    #########################################################

    # External reflection files
    if not xia2.count('scaled_refln_file'):
        output_datafiles.addPara("No reflection data files were found",
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
                refln_files.addRow(['Dataset','File name'],
                                   css_classes='refln_header')
            # Build the row data
            reflndata = [refln_file.dataset(),
                         Canary.MakeLink(filen,get_relative_path(
                refln_file.filename()))]
            refln_files.addRow(reflndata)

    # External log files
    if not len(xia2run.logfiles()):
        output_logfiles.addPara("No external log files")
    else:
        # Display table of log files
        output_logfiles.addPara("The following log files are located in "+ \
                                Canary.MakeLink(xia2run.log_dir(),
                                                get_relative_path( \
                                                xia2run.log_dir()))+ \
                                " and are grouped by processing stage:")
        logs = output_logfiles.addTable()
        logs.addClass('log_files')
        this_stage = None
        this_program = None
        for log in xia2run.logfiles():
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
                                        Canary.MakeLink(log.basename(),
                                                        log.relativeName())+
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
                       Canary.MakeLink("original",log.relativeName())]
            # Link to baubles file
            html_log = log.baublize(target_dir=xia2_html_dir)
            if html_log:
                logdata.append(Canary.MakeLink("html",html_log))
            else:
                logdata.append(None)
            # Warnings from smartie analysis
            if len(log.warnings()):
                logdata.append(Canary.MakeLink(warning_icon+" See warnings",
                                               html_log+"#warnings"))
            else:
                logdata.append('')
            # Add data to the table
            logs.addRow(logdata)
        # Add a link to the journal file xia2-journal.txt, if found
        if xia2run.journal_file():
            output_logfiles.addPara("More detailed information on what xia2 did can be found in the &quot;journal&quot; file:")
            output_logfiles.addList().addItem(Canary.MakeLink(
                "xia2-journal.txt",get_relative_path(xia2run.journal_file())))
        # Copy the JLoggraph applet to the xia2_html directory
        # It lives in the "extras" subdir of the Xia2html source
        # directory
        jar_file = "JLogGraph.jar"
        jloggraph_jar = os.path.join(xia2htmldir,"extras",jar_file)
        print "Copying %s status icons to %s" % (jloggraph_jar,xia2_html)
        if os.path.isfile(jloggraph_jar):
            shutil.copy(jloggraph_jar,os.path.join(xia2_html,jar_file))
        else:
            print "*** %s not found ***" % jloggraph_jar

    # Detailed statistics for each dataset
    print "Number of summary tables: "+str(xia2.count('dataset_summary'))
    # If there is more than 1 summary then write a TOC
    if len(xia2['dataset_summary']) > 1:
        summary.addPara("Statistics for each of the following datasets:")
        summary.addTOC()
    statistic_sections = {}
    for dataset in xia2['dataset_summary']:
        # Make a subsection for each dataset
        name = dataset.value('dataset')
        summary_table = Canary.MakeMagicTable(dataset.value('table'))
        summary_table.setHeader(['','Overall','Low','High'])
        stats_subsection = summary.addSubsection(name)
        stats_subsection.addContent(summary_table)
        # Store a reference to the subsection for linking to later
        statistic_sections[name] = stats_subsection

    #########################################################
    # Integration status per image
    #########################################################
    int_status_reporter = IntegrationStatusReporter(xia2_html_dir)
    int_status = xia2['integration_status_per_image']
    # Write out the preamble and key of symbols
    int_status_section.addPara("The following sections show the status of each image from the final integration run performed on each sweep within each dataset.")
    # Add a summary table here - it will be populated as
    # we got along
    int_status_section.addPara("This table summarises the image status for each dataset and sweep.")
    int_table = int_status_section.addTable()
    # Loop over datasets/wavelengths
    this_dataset = None
    for wavelength in xia2['wavelength']:
        # Make a section for each dataset
        dataset = wavelength.value('name')
        int_status_dataset_section = int_status_section. \
            addSubsection("Dataset %s" % dataset)
        print ">>>> DATASET: "+str(dataset)
        sweep_list = list_sweeps(int_status,dataset)
        # Deal with each sweep associated with the dataset
        for sweep in sweep_list:
            print "* Sweep: "+str(sweep)
            last_int_run = get_last_int_run(int_status,sweep)
            if not last_int_run:
                # Failed to find a match
                print ">>> Couldn't locate last run for this sweep"
            else:
                # Output status info for this sweep in its own section
                start_batch = str(last_int_run.value('start_batch'))
                end_batch = str(last_int_run.value('end_batch'))
                sweep_section = int_status_dataset_section. \
                    addSubsection(sweep + ": batches " + start_batch + \
                                      " to " + end_batch)
                # Build the output HTML
                images_html = ''
                # Process each line of the status separately
                batch_num = int(start_batch)
                for images_text in last_int_run.value('image_status'). \
                        split('\n'):
                    # Turn the status symbols into icons
                    for symbol in list(images_text):
                        status = int_status_reporter.lookupStatus(symbol)
                        description = int_status_reporter.getDescription(status)
                        title = "Batch: %d Status: %s" % (batch_num,description)
                        images_html += int_status_reporter.getIcon(status,title)
                        batch_num += 1
                    images_html += "<br />\n"
                # Add the icons to the document
                sweep_section.addContent("<p>"+images_html+"</p>")
                # Add a row to the summary table
                row = []
                total = 0
                if this_dataset != dataset:
                    # Only link to each dataset once from the table
                    this_dataset = dataset
                    row.append(Canary.Link(dataset,int_status_dataset_section).
                               render())
                else:
                    row.append('')
                # Link to sweep followed by the stats
                row.append(Canary.Link(str(sweep),sweep_section).render())
                symbol_count = last_int_run.value('count')
                for symbol in int_status_reporter.getSymbolList():
                    row.append(str(symbol_count[symbol]))
                    total += symbol_count[symbol]
                row.append(total)
                int_table.addRow(row)
    # Finish off the summary table by adding the header
    header = ['Dataset','Sweep']
    for symbol in int_status_reporter.getSymbolList():
        symbol_status = int_status_reporter.lookupStatus(symbol)
        description = int_status_reporter.getDescription(symbol_status)
        symbol_image = int_status_reporter.getIcon(symbol_status)
        header.append(description+"<br />"+symbol_image)
    header.append("Total")
    int_table.setHeader(header)
    # Finally: copy the image icons to the xia2_html directory
    print "Copying image status icons to %s" % xia2_html
    for icon in int_status_reporter.listIconNames():
        shutil.copy(os.path.join(xia2icondir,icon),
                    os.path.join(xia2_html,icon))
    # Also copy the warning icon
    shutil.copy(os.path.join(xia2icondir,"warning.png"),
                os.path.join(xia2_html,"warning.png"))
        
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
                citation_list.addItem(Canary.MakeLink(line,url))
            else:
                citation_list.addItem(line)
    # Some other xia2-specific stuff
    sect_xia2_stuff = credits.addSubsection("xia2 Details")
    sect_xia2_stuff.addPara("Additional details about this run:")
    tbl_xia2_stuff = sect_xia2_stuff.addTable()
    tbl_xia2_stuff.addClass('xia2_info')
    tbl_xia2_stuff.addRow(['Version',version])
    tbl_xia2_stuff.addRow(['Run time',run_time])
    tbl_xia2_stuff.addRow(['Command line',command_line])
    tbl_xia2_stuff.addRow(['Termination status',termination_status])
    xia2txt = os.path.join(xia2dir,"xia2.txt")
    tbl_xia2_stuff.addRow(['xia2.txt file',
                           Canary.MakeLink(xia2txt,get_relative_path(xia2txt))])
    
    # Put in some forwarding linking from the index
    index.addPara("Contents of the rest of this document:")
    forward_links = index.addList()
    forward_links.addItem(Canary.Link("Reflection data files output from xia2",output_datafiles).render())
    forward_links.addItem(Canary.Link("Full statistics for each wavelength", \
                                      summary).render())
    forward_links.addItem(Canary.Link("Log files from individual stages", \
                                      output_logfiles).render())
    forward_links.addItem(Canary.Link("Integration status for images by wavelength and sweep", \
                                      int_status_section).render())
    forward_links.addItem(Canary.Link("Lists of programs and citations",
                                      credits).render())

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
    # Add initial title column
    table_one.addColumn(row_titles)
    # Add additional columns for each dataset
    for dataset in xia2run.datasets():
        # Locate the wavelength
        wave_lambda = '?'
        for wavelength in xia2['wavelength']:
            if dataset.datasetName() == wavelength.value('name'):
                wave_lambda = wavelength.value('lambda')
                break
        # Construct the column of data and add to the table
        # This is for the overall/average values
        column_data = [wave_lambda,
                       dataset['high_resolution_limit'][1],
                       dataset['low_resolution_limit'][1],
                       dataset['completeness'][1],
                       dataset['multiplicity'][1],
                       dataset['i/sigma'][1],
                       dataset['rmerge'][1]]
        if xia2run.has_anomalous():
            try:
                anom_completeness = dataset['anomalous_completeness'][1]
                anom_multiplicity = dataset['anomalous_multiplicity'][1]
            except KeyError:
                anom_completeness = '-'
                anom_multiplicity = '-'
            column_data.extend([anom_completeness,anom_multiplicity])
        # Link forward to full stats for this dataset
        column_data.append(Canary.Link("See all statistics",
                                       statistic_sections[dataset.name()]))
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
                       "("+dataset['high_resolution_limit'][2]+\
                       " - "+dataset['high_resolution_limit'][3]+")",
                       "("+dataset['low_resolution_limit'][2]+\
                       " - "+dataset['low_resolution_limit'][3]+")",
                       "("+dataset['completeness'][2]+\
                       " - "+dataset['completeness'][3]+")",
                       "("+dataset['multiplicity'][2]+\
                       " - "+dataset['multiplicity'][3]+")",
                       "("+dataset['i/sigma'][2]+\
                       " - "+dataset['i/sigma'][3]+")",
                       "("+dataset['rmerge'][2]+\
                       " - "+dataset['rmerge'][3]+")"]
        if xia2run.has_anomalous():
            try:
                anom_completeness = "("+dataset['anomalous_completeness'][2]+\
                                    " - "+\
                                    dataset['anomalous_completeness'][3]+")"
                anom_multiplicity = "("+dataset['anomalous_multiplicity'][2]+\
                                    " - "+\
                                    dataset['anomalous_multiplicity'][3]+")"
            except KeyError:
                anom_completeness = '-'
                anom_multiplicity = '-'
            column_data.extend([anom_completeness,anom_multiplicity])
        table_one.addColumn(column_data)
    # Additional data: unit cell, spacegroup
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(['Unit cell dimensions: a (&Aring;)',
                      unit_cell.value('a')],"unit_cell")
    table_one.addRow(['b (&Aring;)',unit_cell.value('b')],"unit_cell")
    table_one.addRow(['c (&Aring;)',unit_cell.value('c')],"unit_cell")
    table_one.addRow(['&alpha;',unit_cell.value('alpha')],"unit_cell")
    table_one.addRow(['&beta;',unit_cell.value('beta')],"unit_cell")
    table_one.addRow(['&gamma;',unit_cell.value('gamma')],"unit_cell")
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(['Spacegroup',
                      htmlise_sg_name(
                xia2['assumed_spacegroup'][0].value('spacegroup'))])
    table_one.addRow(['&nbsp;']) # Empty row for padding
    table_one.addRow(['Sfcheck twinning score',
                      twinning_score+" ("+twinning_report+")"])
    table_one.addRow(['',Canary.Link("All crystallographic parameters..",
                                     xtal_parameters)])
    

    # Spit out the HTML
    xia2doc.renderFile('xia2.html')

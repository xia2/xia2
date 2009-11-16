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
__cvs_id__ = "$Id: Xia2html.py,v 1.2 2009/11/16 18:01:32 pjx Exp $"
__version__ = "0.0.2"

#######################################################################
# Import modules that this module depends on
#######################################################################
import sys
import os
import shutil
import time
import Magpie
import Canary
import baubles

#######################################################################
# Class definitions
#######################################################################

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

    def shortName(self):
        """Return the short name"""
        return self.__short_name

    def keys(self):
        """Return the list of data item names (keys)"""
        return self.__keys

# Baublizer
#
# Handles running baubles on logfiles
class Baublizer:
    """Class to handle running baubles on logfiles

    Wraps the running of baubles along with some basic filename
    recognition.

    Once a Baublizer is instantiated, use addProgram to specify
    program names that baubles should be run on. When a log file
    is presented to the Baublizer via the baublize method,
    baubles will run if the logfile name matches one of the
    specified program names."""

    def __init__(self):
        # List of file patterns
        self.__baubles_programs = []
        # Set the location of the Jloggraph applet explicitly
        baubles.setJLoggraphCodebase('.')

    def addProgram(self,prog):
        """Add a program name to the list of files to baublize

        If the program name is found at the end the file name
        of a logfile (not including the extension) then the
        baublize method will run baubles on the file."""
        self.__baubles_programs.append(prog)

    def baublize(self,logfile,htmlfile):
        """Run baubles on a log file

        'logfile' is the name and path of the log file to be
        examined. If the log file name contains a program name
        that has been added via the addProgram method then it
        will run baubles to generate 'htmlfile'.

        Returns 'htmlfile', or None if the log file didn't match
        or if baubles failed to run."""
        # Check if this is in the list of files to
        # baublize
        for prog in self.__baubles_programs:
            if os.path.basename(os.path.splitext(logfile)[0]).count(prog):
                # Run baubles
                try:
                    baubles.baubles_html(logfile,htmlfile)
                    return htmlfile
                except:
                    print "Error running baubles on "+str(logfile)
                    return None
                baubles.baubles_html(logfile,htmlfile)
                return htmlfile
        # Didn't find the program in the list
        return None

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
        return

    def __makeSymbolDictionary(self):
        """Internal: build the symbol dictionary from the key text"""
        # FIXME for now just hardcode the dictionary
        return { 'good': 'o',
                 'overloaded': 'O',
                 'ok': '%',
                 'bad_rmsd': '!',
                 'many_bad': '#',
                 'blank': '.' }

    def __makeReverseSymbolLookup(self):
        """Internal: build the reverse lookup table for symbols"""
        symbol_lookup = {}
        for key in self.__symbol_dict.keys():
            symbol_lookup[self.__symbol_dict[key]] = key
        return symbol_lookup

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

def list_logfiles(logdir):
    """Return list of log files in logdir, in data order"""
    # Get unsorted list of names
    files = os.listdir(logdir)
    # Prepend the logdir
    files2 = []
    for filen in files:
        files2.append(os.path.join(logdir,filen))
    # Sort file2 list on modification time
    ##files2.sort(cmp_file_mtime)
    # Sort file2 list on keywords in file names
    files2.sort(cmp_file_by_keyword)
    # Rebuild the list to contain only file names
    files = []
    for filen in files2:
        files.append(os.path.basename(filen))
    return files
        
def cmp_file_mtime(file1,file2):
    """Compare file modification times for sorting"""
    mtime1 = os.stat(file1).st_mtime
    mtime2 = os.stat(file2).st_mtime
    if mtime1 < mtime2:
        return 1
    elif mtime1 == mtime2:
        return 0
    else:
        return -1

def cmp_file_by_keyword(file1,file2):
    """Compare file names with crystallographic components"""
    # List of keywords that might appear in the log file names
    # The list is in the order that we would want the file names
    # to appear in a list of files
    keywords = ['INTEGRATE','integrate','mosflm','chef','pointless',
                'scala','truncate']
    # Locate the keywords in the list for both file names
    for i in range(0,len(keywords)):
        k = os.path.basename(os.path.splitext(file1)[0]).find(keywords[i])
        if k > -1: break
    for j in range(0,len(keywords)):
        k = os.path.basename(os.path.splitext(file2)[0]).find(keywords[j])
        if k > -1: break
    # Return value indicates order
    if i < j: return -1
    if i == j: return 0
    if i > j: return 1

def list_sweeps(int_status_list):
    """Return a list of sweep names

    Given a list of 'integration_status_...' Data objects,
    return a list of the unique sweep names.

    If sweeps are called SWEEP1, SWEEP2 etc then this will
    also sort them into alphanumeric order."""
    sweep_list = []
    auto_assigned = True
    for int_status in int_status_list:
        this_sweep = int_status.value('sweep')
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
    if common_prefix == pwd:
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
    xia2.addPattern('twinning',
                    "Overall twinning score: ([^\n]+)\n(Your data [^\n]+)",
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
                     "-------------------- Integrating","blank")

    # Process the output
    xia2.process()

    #########################################################
    # Intermediate/additional processing
    #########################################################

    # Post-process the information for each wavelength from the
    # dataset_summary data
    #
    print "****** Additional processing for dataset statistics ******"
    datasets = []
    for dataset in xia2['dataset_summary']:
        datasets.append(Dataset(dataset.value('dataset'),
                                dataset.value('table')))
    # Check for anomalous data
    # FIXME surely this could be done in the loop above?
    have_anomalous = False
    for dataset in datasets:
        try:
            x = dataset['anomalous_completeness']
            have_anomalous = True
            break
        except KeyError:
            pass
    # Summarise/report
    for dataset in datasets:
        print "Dataset %s (%s)" % (dataset.name(),dataset.shortName())
        print "Data items:"
        for key in dataset.keys():
            print ">>> "+str(key)+" : "+str(dataset[key])
    # Check for anomalous data

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
    
    # Post-process integration status per image 
    #
    # Reprocess the blocks found from "integration_status_per_image"
    # using a text-based Magpie processor
    print "****** Additional processing for integration status ******"
    # Set up a new processor specifically for this block
    status_processor = Magpie.Magpie()
    status_processor.addPattern('sweep',
                                "-------------------- Integrating ([^ ]*) --------------------",
                                ['name'])
    status_processor.addPattern('batch',
                                "Processed batches ([0-9]+) to ([0-9]+)",
                                ['start','end'])
    status_processor.addPattern('status_per_image',
                                "([oO%#!]+)$")
    status_processor.addPattern('key',
                                "\"o\".*\n.*blank")
    for int_status in xia2['integration_status_per_image']:
        print "Processing "+str(int_status)
        # Reprocess the text and update the data
        # FIXME: maybe this could be more generally be done
        # inside of Magpie in future?
        status_processor.processText(str(int_status))
        int_status.setValue('sweep',status_processor['sweep'][0].value('name'))
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
        int_status.setValue('image_status',image_status_line)
        # Reset the processor for the next round
        status_processor.reset()

    # Deal with any external log files found in LogFiles directory
    # Store the data for each log file as Data objects in the xia2
    # object for reference later
    print "Dealing with LogFiles directory..."
    # Set up Baublizer object to convert log files to html
    baublizer = Baublizer()
    do_baubles = True
    if do_baubles:
        # List of programs to process with baubles
        baublizer.addProgram('scala')
        baublizer.addProgram('truncate')
        baublizer.addProgram('pointless')
        baublizer.addProgram('chef')
    # Sort out relative and absolute paths to log files
    # If the logfiles are in a directory below where the program
    # is running then use relative paths to refer to them,
    # otherwise use absolute paths
    abslogdir = os.path.abspath(os.path.join(xia2dir,"LogFiles"))
    logdir = get_relative_path(abslogdir)
    # Process logiles
    try:
        files = list_logfiles(logdir)
        for filen in files:
            logfile_data = {'name': None,
                            'dir': None,
                            'log': None,
                            'html': None }
            # Test for .log extension
            if os.path.splitext(filen)[1] == ".log":
                print "Found logfile >>> "+filen
                # Store the name without the extension
                logfile_data['name'] = filen
                logfile_data['full_dir'] = abslogdir
                logfile_data['dir'] = logdir
                logfile_data['log'] = os.path.join(logdir,filen)
                # Run baubles on this file
                print "Running baublizer..."
                logfile = logfile_data['log']
                htmlfile = os.path.join(xia2_html_dir,
                                        os.path.splitext(filen)[0]+
                                        ".html")
                logfile_data['html'] = baublizer.baublize(logfile,htmlfile)
                # Store data for this file in the xia2 object
                xia2.addData('logfile',logfile_data)
            else:
                print filen + " : not logfile "
        print "Finished with logfiles"
    except OSError:
        # Possibly the LogFiles directory doesn't
        # exist
        if not os.path.isdir(logdir):
            print "LogFiles directory not found"
        else:
            raise

    # Post-process the reflection file data to set the
    # format for those references that were missing it
    refln_format = '?'
    for refln_file in xia2['scaled_refln_file']:
        if refln_file.value('format'):
            # Format is already defined so collect it
            refln_format = refln_file.value('format')
        else:
            # Format is not defined, reset it to the
            # last defined value we found
            refln_file.setValue('format',refln_format)

    #########################################################
    # Construct output HTML file
    #########################################################

    # Build up the output HTML using Canary
    xia2doc = Canary.Document("xia2 Processing Report")
    xia2doc.addStyle(os.path.join(xia2htmldir,"xia2.css"),Canary.INLINE)
    ##xia2doc.addScript("./baubles.js",Canary.INLINE)

    # XIA2 version and other general info
    try:
        status = xia2['xia2_status'][0].value('status')
    except IndexError:
        # Assume that xia2 is still running
        # For now don't attempt to process incomplete file
        print "*** Missing status, file incomplete (xia2 still running?) ***"
        print "Refusing to process incomplete file - stopping"
        sys.exit(1)

    version = xia2['xia2_version'][0].value('version')
    xia2doc.addPara("XIA2 version %s completed with status '%s'" % \
                    (version, status)). \
                    addPara("Read output from %s" % Canary.MakeLink(xia2dir))
    command_line = xia2['command_line'][0].value('cmd_line')

    # Build summary table ("table 1") at head of file
    table_one = xia2doc.addTable()
    table_one.addClass('table_one')
    row_titles = ['Wavelength (&Aring;)',
                  'High resolution limit',
                  'Low resolution limit',
                  'Completeness',
                  'Multiplicity',
                  'I/sigma',
                  'R<sub>merge</sub>']
    if have_anomalous:
        row_titles.extend(['Anomalous completeness',
                           'Anomalous multiplicity'])
    # Add initial the column
    table_one.addColumn(row_titles)
    # Add additional columns for each dataset
    for dataset in datasets:
        # Locate the wavelength
        wave_lambda = '?'
        for wavelength in xia2['wavelength']:
            if dataset.shortName() == wavelength.value('name'):
                wave_lambda = wavelength.value('lambda')
                break
        # Construct the column of data and add to the table
        column_data = [wave_lambda,
                       dataset['high_resolution_limit'][1],
                       dataset['low_resolution_limit'][1],
                       dataset['completeness'][1],
                       dataset['multiplicity'][1],
                       dataset['i/sigma'][1],
                       dataset['rmerge'][1]]
        if have_anomalous:
            try:
                anom_completeness = dataset['anomalous_completeness'][1]
                anom_multiplicity = dataset['anomalous_multiplicity'][1]
            except KeyError:
                anom_completeness = '-'
                anom_multiplicity = '-'
            column_data.extend([anom_completeness,anom_multiplicity])
        table_one.addColumn(column_data,
                            header=dataset.shortName())
    # Additional data
    unit_cell = xia2['unit_cell'][0]
    table_one.addRow(['Unit cell dimensions: a (&Aring;)',
                      unit_cell.value('a')],"unit_cell")
    table_one.addRow(['b (&Aring;)',unit_cell.value('b')],"unit_cell")
    table_one.addRow(['c (&Aring;)',unit_cell.value('c')],"unit_cell")
    table_one.addRow(['&alpha;',unit_cell.value('alpha')],"unit_cell")
    table_one.addRow(['&beta;',unit_cell.value('beta')],"unit_cell")
    table_one.addRow(['&gamma;',unit_cell.value('gamma')],"unit_cell")
    table_one.addRow(['Spacegroup',
                      htmlise_sg_name(
                xia2['assumed_spacegroup'][0].value('spacegroup'))])

    # Add table of contents
    xia2doc.addTOC()

    # Crystallographic parameters
    twinning = str(xia2['twinning'][0])
    try:
        asu_and_solvent = str(xia2['asu_and_solvent'][0])
    except IndexError:
        # Assume that this was missing
        # Put in a default message
        asu_and_solvent = "No information on ASU contents"

    # Overview section
    overview = xia2doc.addSection("Overview")
    
    # Crystallographic parameters
    xtal_params = overview.addSubsection("Crystallographic parameters")
    xtal_params.addPara("Unit cell parameters:")
    xtal_params.addTable(['a','b','c',
                          '&alpha;','&beta;','&gamma']). \
                          addRow([unit_cell.value('a'),
                                  unit_cell.value('b'),
                                  unit_cell.value('c'),
                                  unit_cell.value('alpha'),
                                  unit_cell.value('beta'),
                                  unit_cell.value('gamma')])
    xtal_params.addPara("Assumed spacegroup: "+
                        htmlise_sg_name(xia2['assumed_spacegroup'][0].
                                         value('spacegroup')))
    alt_spgs = xia2['assumed_spacegroup'][0].value('alternative')
    if alt_spgs:
        xtal_params.addPara("Likely alternatives:")
        alt_spg_list = xtal_params.addList()
        for alt_spg in alt_spgs:
            if alt_spg:
                alt_spg_list.addItem(htmlise_sg_name(alt_spg))
    else:
        xtal_params.addPara("No likely alternatives to this spacegroup")
    xtal_params. \
        addPara(twinning). \
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
        overview.addSubsection("Inter-wavelength B and R-factor analysis"). \
            addContent(interwavelength_table)
    except IndexError:
        # Table not found, ignore
        pass


    #########################################################
    # Integration status per image
    #########################################################
    int_status = xia2['integration_status_per_image']
    int_status_section = xia2doc.addSection("Integration status per image")
    int_status_reporter = IntegrationStatusReporter(xia2_html_dir)
    # Report what was found
    if len(int_status):
        print "*** PROCESSING SWEEPS ***"
        # Write section preamble
        int_status_section.addPara("Status of images from the "+\
                                   "final integration run performed on "+\
                                   "each sweep")
        # Write out the key of symbols
        int_status_section.addContent(
            int_status_reporter.makeSymbolKey(ncolumns=6))
        # Get list of sweeps
        sweep_list = list_sweeps(int_status)
        print "Sweep list:"
        for sweep in sweep_list:
            print ">>> "+sweep
        # For each sweep, find the last integration run
        for sweep in sweep_list:
            print "Processing integration status for sweep: "+sweep
            last_int_run = get_last_int_run(int_status,sweep)
            if not last_int_run:
                # Failed to find a match
                print ">>> Couldn't locate last run for this sweep"
            else:
                # Output status info for this sweep in its own section
                start_batch = str(last_int_run.value('start_batch'))
                end_batch = str(last_int_run.value('end_batch'))
                sweep_section = int_status_section.addSubsection(sweep+\
                                                                 ": batches "+\
                                                                 start_batch+\
                                                                 " to "+\
                                                                 end_batch)
                # Build the output HTML
                images_html = ''
                # Process each line of the status separately
                batch_num = int(start_batch)
                for images_text in last_int_run.value('image_status').split('\n'):
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
        # Finally: copy the image icons to the xia2_html directory
        print "Copying image status icons to %s" % xia2_html
        for icon in int_status_reporter.listIconNames():
            shutil.copy(os.path.join(xia2icondir,icon),
                        os.path.join(xia2_html,icon))
            
    else:
        # Nothing found in the xia2.txt file
        int_status_section.addPara("No data available")

    #########################################################
    # External files
    #########################################################
    
    output_files = xia2doc.addSection("Output files")

    # External log files
    output_logfiles = output_files.addSubsection("Log files")
    if not xia2.count('logfile'):
        output_logfiles.addPara("No external log files")
    else:
        # Display table of log files
        output_logfiles.addPara("Log files found in "+ \
                                    Canary.MakeLink(xia2['logfile'][0]. \
                                                        value('full_dir'), \
                                                        xia2['logfile'][0]. \
                                                        value('dir'))+":")
        logs = output_logfiles.addTable()
        for log in xia2['logfile']:
            logdata = [log.value('name'),
                       Canary.MakeLink("original",log.value('log'))]
            if log.value('html'):
                # Also link to baubles file
                logdata.append(Canary.MakeLink("html",log.value('html')))
            logs.addRow(logdata)
        # Report if baubles was not run
        if not do_baubles:
            output_logfiles.addPara("Baubles wasn't run so there are "+
                                      "no HTML files (set do_baubles to "+
                                      "True in Xia2html.py to change this)")
        else:
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

    # External reflection files
    output_datafiles = output_files.addSubsection("Reflection data files")
    if not xia2.count('scaled_refln_file'):
        output_datafiles.addPara("No external reflection files")
    else:
        # Display table of reflection files
        output_datafiles.addPara("Available reflection files:")
        refln_files = output_datafiles.addTable(('Dataset','Format','File'))
        for refln_file in xia2['scaled_refln_file']:
            # Need to do some processing here to make it look nicer
            # (Note that if possible we link to the files using a
            # relative rather than absolute path)
            filen = os.path.basename(refln_file.value('filename'))
            reflndata = [refln_file.value('dataset'),
                         refln_file.value('format'),
                         Canary.MakeLink(filen,get_relative_path(
                        refln_file.value('filename')))]
            refln_files.addRow(reflndata)

    # Summary from the end of the log
    summary = xia2doc.addSection("Detailed summary")
    print "Number of summary tables: "+str(xia2.count('dataset_summary'))
    for dataset in xia2['dataset_summary']:
        summary_table = Canary.MakeMagicTable(dataset.value('table'))
        summary_table.setHeader(['','Overall','Low','High'])
        summary.addSubsection(dataset.value('dataset')). \
                              addContent(summary_table)

    # Credits section
    credits = xia2doc.addSection("Credits")

    # Programs used by XIA2
    programs = credits.addSubsection("Software Used").addList()
    for prog in xia2['xia2_used'][0].value('software').split():
        programs.addItem(prog)
    
    # Citations
    citations = credits.addSubsection("Citations").addList()
    for line in str(xia2['citations'][0]).split('\n'):
        if line.strip() != "": citations.addItem(line)

    # Some other xia2-specific stuff
    sect_xia2_stuff = credits.addSubsection("xia2 Details")
    sect_xia2_stuff.addPara("Additional details about this run:")
    tbl_xia2_stuff = sect_xia2_stuff.addTable()
    tbl_xia2_stuff.addRow(['Version',version])
    tbl_xia2_stuff.addRow(['Command line',command_line])
    tbl_xia2_stuff.addRow(['Termination status',status])
    tbl_xia2_stuff.addRow(['xia2.txt file',
                           Canary.MakeLink(os.path.join(xia2dir,"xia2.txt"))])

    # Footer section
    footer = "This file generated for you from xia2 output by Xia2html %s on %s<br />Powered by Magpie %s and Canary %s<br />&copy; Diamond 2009" \
        % (__version__,
           time.asctime(),
           Magpie.version(),
           Canary.version())
    xia2doc.addContent("<p class='footer'>%s</p>" % footer)

    # Spit out the HTML
    xia2doc.renderFile('xia2.html')

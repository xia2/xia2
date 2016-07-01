#     Magpie.py: Text file processor
#     Copyright (C) Diamond 2009 Peter Briggs
#
########################################################################
#
# Magpie.py
#
########################################################################
#
# Provide classes and functions for extracting information from
# text files based on pattern matching
#
__cvs_id__ = "$Id$"
__version__ = "0.0.1"

#######################################################################
# Import modules that this module depends on
#######################################################################
import re
import copy
import smartie

#######################################################################
# Module constants
#######################################################################

# Constants for defining Blocks
INCLUDE=0
EXCLUDE=1
EXCLUDE_START=2
EXCLUDE_END=3

#######################################################################
# Class definitions
#######################################################################

# Magpie
#
# Generic text file processing class
class Magpie:
  """Generic text processing class

  Creates a configurable line-by-line text processor object which
  can process input from a file or from text."""

  def __init__(self,txtfile=None,verbose=False):
    """New Magpie object

    Optionally, 'txtfile' is the name and full path of the file
    to be processed.

    """
    # Source text file
    self.__txtfile = txtfile
    # Verbose output
    self.__verbose = verbose
    # List of data items
    self.__data = []
    # List of blocks
    self.__blocks = []
    # Maximum buffer size (number of lines)
    self.__buffersize = 50
    # Patterns to match against
    self.__regex = PatternMatcher()
    return

  def reset(self):
    """Reset the processor

    Erases any results of previous processing but leaves the
    pattern and block definitions intact. This enables an
    application to use the processor multiple times without
    needing to redefine patterns and blocks."""
    self.__data = []
    return

  def defineBlock(self,name,starts_with,ends_with,include_flag=INCLUDE,
                  pattern=None,pattern_keys=None):
    """Define a block of lines to collect"""
    new_block = Block(name,starts_with,ends_with,pattern,pattern_keys,
                      include_flag,verbose=self.__verbose)
    self.__blocks.append(new_block)
    return new_block

  def addData(self,name,data):
    """Add a data element"""
    new_data = Data(name,data)
    self.__data.append(new_data)
    return new_data

  def addPattern(self,name,pattern,keys=None):
    """Define a new regexp pattern"""
    self.__regex.addPattern(name,pattern,keys)
    return

  def getData(self,name=""):
    """Return a list of Data elements

    If a 'name' string is specified then the list will
    be limited to the Data elements that match the name;
    otherwise the list will contain all Data elements."""

    if name == "":
      return copy.copy(self.__data)
    else:
      data = []
      for datum in self.__data:
        if datum.name() == name:
          data.append(datum)
    return data

  def __getitem__(self,name):
    """Implements Magpie[name] for fetching items

    Return a list of Data elements matching 'name'."""
    return self.getData(name)

  def __iter__(self):
    """Return an iterator for this object

    Implements 'for item in Magpie:...'"""
    # Use iter() to turn the list of data items into
    # an iterator
    return iter(self.__data)

  def count(self,name):
    """Return number of occurances of Data elements called 'name'"""
    return len(self.getData(name))

  def process(self):
    """Run the processor on the source text"""
    self.processFile(self.__txtfile)

  def processFile(self,filename):
    """Run the processor on a file"""
    with open(filename,'r') as txt:
      self.__process(txt)

  def processText(self,txt):
    """Run the processor on a block of text"""
    self.__process(str(txt).split('\n'))

  def __process(self,source):
    """Process source text

    'source' must be an iterable object (typically either an
    open file object, or a list of lines of text) which
    acts as the data source.

    This method steps through the data source line-by-line,
    extracting and storing data from fragments that match
    the Pattern and Block definitions."""

    # Smartie buffer object stores chunks of text
    buff = smartie.buffer(self.__buffersize)
    # Move through the file buffering chunks
    # and testing them against our stored patterns
    for line in source:
      buff.append(line)
      # Get a chunk of text to process
      ##bufftext = buff.tail()
      # Get the whole buffer as text
      # Maybe later we can optimise by having different
      # chunk sizes explicitly set for different patterns
      bufftext = buff.all()
      # Test the line for matches
      for pattern in self.__regex.listPatterns():
        test = self.__regex.test(pattern,bufftext)
        if test:
          self.__print("Matched pattern '"+str(pattern)+"'")
          for key in test.keys():
            self.__print(">>> "+str(key)+": "+str(test[key]))
          text = test[pattern]
          self.addData(pattern,test)
          # Clear the buffer and break out the loop
          buff.clear()
          break
      # Deal with blocks
      for block in self.__blocks:
        if not block.isComplete():
          block.add(line)
        if block.isComplete():
          # Create a new Data object to
          # store the block and then reset
          self.addData(block.name(),block.getData())
          block.reset()
    self.__print("Finished")

  def __print(self,text):
    """Internal: print to stdout

    Controlled by the __verbose attribute."""
    if self.__verbose: print text

class Data:
  """Data items from the output"""

  def __init__(self,name,data):
    self.__name = name
    self.__data = data
    return

  def __getitem__(self,key):
    """Implement x = Data[key]

    Wrapper for value() method."""
    return self.value(key)

  def __setitem__(self,key,value):
    """Implement Data[key] = x

    Wrapper for setValue() method."""
    return self.setValue(key,value)

  def __str__(self):
    """Return string representation"""
    try:
      return self.__data[self.__name]
    except KeyError:
      # Assume that the name isn't defined
      # Return a concatentation of all the
      # data items
      text = ""
      for key in self.__data.keys():
        text += str(self.__data[key])+"\n"
      text = text.strip('\n')
      return text

  def keys(self):
    """Return the keys of the data dictionary"""
    return self.__data.keys()

  def name(self):
    """Return the name of the Data object"""
    return self.__name

  def data(self):
    """Return the data dictionary"""
    return self.__data

  def value(self,key):
    """Return the value stored against key"""
    return self.__data[key]

  def setValue(self,key,value):
    """Set the value of a data item

    Sets the value of 'key' to 'value'. Doesn't
    check if 'key' already exists."""
    self.__data[key] = value
    return

class Block:
  """Chunk of output delimited by start/end patterns

  'name' is an identifier, 'starts_with' and 'ends_with'
  are text strings which mark the beginning and end of the
  block of output that is of interest.

  To match blocks ending (or starting) with a blank line
  (i.e. a line containing whitespace only), set the 'ends_with'
  (or 'starts_with') parameter to an empty string i.e. ''.

  include_flag determines whether the delimiters should
  also be added to the block. Values are:
  INCLUDE       : include both start and end delimiters (the default)
  EXCLUDE       : exclude both start and end delimiters
  EXCLUDE_START : include only the end delimiter
  EXCLUDE_END   : include only the start delimiter

  'pattern' defines an optional regular expression pattern.
  If this provided then it will be applied to the matching
  text when the block is complete. If 'pattern_keys' are also
  provided then each key will create a data element with the
  matching regular expression group."""

  def __init__(self,name,starts_with,ends_with,pattern=None,
               pattern_keys=None,include_flag=INCLUDE,
               verbose=False):
    self.__name = name
    self.__text = ""
    self.__start = starts_with
    self.__end = ends_with
    self.__include = include_flag
    self.__verbose = verbose
    if pattern:
      self.__pattern = Pattern(name,pattern,pattern_keys)
    else:
      self.__pattern = None
    self.__active = False
    self.__complete = False

  def __repr__(self):
    return str(self.__name)+":\n"+str(self.__text)

  def name(self):
    """Returns the name of the block"""
    return self.__name

  def text(self):
    """Returns the block text"""
    return self.__text

  def isComplete(self):
    """Check if the block is complete (i.e. end delimiter reached)"""
    return self.__complete

  def isActive(self):
    """Check if the block is active (i.e. start delimiter supplied)"""
    return self.__active

  def getData(self):
    """Return data from the block"""
    data = dict()
    if self.__pattern:
      # Apply the regular expression pattern
      data = self.__pattern.test(self.__text)
    if not data:
      # Associate the name of the block with
      # the stored text
      data = { self.__name : self.__text }
    self.__print("Matched block '"+str(self.__name)+"'")
    for key in data.keys():
      self.__print(">>> "+str(key)+": "+str(data[key]))
    return data

  def add(self,text):
    """Present text to be added to the block

    Text will only be added if the block is active but not
    complete. The block is activated by text which includes the
    start delimiter substring.

    Once the block is active all text that is supplied is stored
    until text is supplied which includes the end delimiter - at
    this point ths block is complete and will not accept any more
    text."""
    if self.__complete:
      # Can't add more
      return
    if not self.__active:
      # Check for start delimiter
      if self.__contains(text,self.__start):
        self.__active = True
        if self.__include == EXCLUDE or \
                self.__include == EXCLUDE_START:
          # Don't store the start delimiter line
          return
        else:
          # Add text
          self.__text += text
          return
      else:
        return
    # Check for end delimiter
    if self.__contains(text,self.__end):
      self.__complete = True
      if self.__include == EXCLUDE or \
              self.__include == EXCLUDE_END:
        # Don't store the end delimiter line
        return
    # Add text
    self.__text += text
    return

  def reset(self):
    """Reset the block to accept data

    This frees a "completed" block by resetting it to the
    initial (empty) state"""
    self.__text = ""
    self.__active = False
    self.__complete = False

  def __contains(self,text,pattern):
    """Internal: test if text contains a pattern

    Used by the 'add' method to determine if supplied
    'text' contains the text in 'pattern'. Returns True
    if a match is found and False otherwise.

    If 'pattern' evaluates as False (e.g. an empty string)
    then 'text' will match if it contains whitespace only."""
    if not pattern:
      return str(text).isspace()
    elif str(text).find(pattern) > -1:
      return True
    return False

  def __print(self,text):
    """Internal: print to stdout

    Controlled by the __verbose attribute."""
    if self.__verbose: print text

class PatternMatcher:
  """Store and invoke regexp pattern matches

  For each regular expression supplied along with a name
  via the addPattern method, a new Pattern object is
  created and stored. Multiple patterns can be associated
  with the same name.

  A list of (unique) pattern names can be retrieved via the
  listPatterns method.

  A text string can be tested against the named expression(s)
  using the test method."""

  def __init__(self):
    # List of the regular expression Pattern objects
    self.__patterns = []
    # List of stored (unique) pattern names
    self.__names = []
    return

  def addPattern(self,name,pattern,keys=None):
    """Add a named pattern to the PatternMatcher

    Adds the regular expression pattern associated with
    'name'.

    Optionally, also associate a list of keys with the
    pattern. Each element of the list should correspond
    to a group defined in the regular expression. Note
    that keys cannot be the same as the pattern name."""
    # Create and store the Pattern object
    self.__patterns.append(Pattern(name,pattern,keys))
    # Store the name
    if not self.__names.count(name):
      self.__names.append(name)
    return

  def test(self,name,text):
    """Test text against named regexp pattern(s)

    Test each stored pattern associated with 'name'. When a
    match is found then a Python dictionary is returned
    with information about the match (see the test
    method of the Pattern object for the details).

    If no match is found (or if there are no patterns
    with the supplied name) then an empty Python dictionary
    instance is returned."""
    for pattern in self.__patterns:
      if pattern.name() == name:
        # Test this pattern
        test = pattern.test(text)
        if test: return test
    # No matches - return an empty dictionary
    return dict()

  def listPatterns(self):
    """Return the list of pattern names"""
    return self.__names

class Pattern:
  """Store and invoke a regular expression.

  Stores a single regular expression associated with
  a name. Arbitrary text can be tested against the stored
  pattern using the test method.

  Optionally, a list of keys can also be associated with
  the pattern. Each element of the list should correspond
  to a group defined in the regular expression. Note
  that none of the keys can be the same as the pattern
  name."""

  def __init__(self,name,pattern,keys=None):
    self.__name = name
    self.__pattern = re.compile(pattern,re.DOTALL)
    self.__keys = keys

  def __repr__(self):
    return str(self.__name)

  def name(self):
    """Return the name of the pattern"""
    return self.__name

  def test(self,text):
    """Test text against the regular expression pattern

    Returns a dictionary object. If the text matches the
    regular expression then the dictionary will be populated
    with data extracted from the text as described.

    The element with key 'name' will always contain the full
    matching text. If a set of keys was also supplied when
    the pattern was defined then the dictionary will also
    contain elements matching these keys, with the value of
    the corresponding regexp group assigned.

    If there is no match then the dictionary will be empty."""
    data = dict()
    match = self.__pattern.search(text)
    if match:
      # Build a dictionary for the match
      data[self.__name] = match.group(0)
      # Check if there are associated keys for
      # this pattern
      #
      # Populate the "data" dictionary with the
      # value of each regexp group assigned to
      # the corresponding keys in order
      #
      # If there are more keys than groups then
      # remaining
      if self.__keys:
        i = 1
        for key in self.__keys:
          try:
            data[key] = match.group(i)
          except IndexError:
            # Insufficient groups for
            # number of keys
            data[key] = None
          i += 1
      ##return match.group(0)
    return data

# Tabulator
#
# Break up a raw text "table"
class Tabulator:
  """Extract data from a raw text 'table'

  The Tabulator will break up a supplied block of text treating
  each line as a table 'row', and split each row into individual
  data items according to a specified delimiter.

  The first data item in each "row" becomes a key to retrieve that
  row (which is stored as a Python list containing all the data
  items in the row).

  For example to access the 'High' row of this 'table':

  High   5.0 9.0
  Medium 3.0 4.5
  Low    1.0 0.0

  use Tabulator['High']. To access the last data item in the 'Medium'
  row, use Tabulator['Medium'][1]."""

  def __init__(self,tabular_data,delimiter='\t'):
    """Create and populate a new Tabulator object

    'tabular_data' is the raw text of the 'table';"""
    self.__tabular_data = tabular_data
    self.__delimiter = delimiter
    # List of keys (stored data items)
    self.__keys = []
    self.__data = {}
    # Extract data and populate the data structure
    self.__extract_tabular_data(tabular_data)

  def __extract_tabular_data(self,tabular_data):
    """Internal: build data structure from tabular data"""
    for row in tabular_data.strip('\n').split('\n'):
      row_data = row.split(self.__delimiter)
      key = row_data[0].strip()
      self.__keys.append(key)
      self.__data[key] = row_data

  def __getitem__(self,key):
    """Implement x = Tabulator[key] for get operations

    Returns the 'row' of data associated with the key 'name'
    i.e. a list of items."""
    return self.__data[key]

  def has_key(self,key):
    """Check if a row called 'key' exists"""
    return key in self.__data

  def keys(self):
    """Return the list of data item names (keys)"""
    return self.__keys

  def table(self):
    """Return the original data that was supplied"""
    return self.__tabular_data

#######################################################################
# Module Functions
#######################################################################

def version():
  """Return the version of the Magpie module"""
  return __version__

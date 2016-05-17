#     smartie.py: CCP4 logfile parsing classes and functions
#     Copyright (C) 2006-2007 Peter Briggs, Wanjuan Yang, CCLRC
#
#     This code is distributed under the terms and conditions of the
#     CCP4 licence agreement as `Part 1' (Annex 2) software.
#     A copy of the CCP4 licence can be obtained by writing to the
#     CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
########################################################################
#
# smartie.py
#
#########################################################################

"""smartie: CCP4 logfile parsing functions

The smartie module provides a set of classes and methods for parsing
logfiles from CCP4i and CCP4 programs. The central class is the 'logfile',
which provides a basic DOM-like description of a logfile and its
contents. Other classes provide descriptions of smaller chunks of logfile
features (programs, tables, keytext data and CCP4i informational messages).

The name 'smartie' reflects the module's origins as the intended driver
for a 'smart logfile browser'.

Some additional documentation material is also available in the file
smartie_overview.html."""

__cvs_id__ = "$Id$"
__version__ = "0.0.15"

#######################################################################
# Import modules that this module depends on
#######################################################################
import sys
import os
import re
import copy
import linecache
import time

#######################################################################
# Class definitions
#######################################################################

# buffer
#
# A class to store sets of lines which can then
# be passed to regular expression matching functions
#
class buffer:
  """Buffer object for parsing log files.

  The buffer object holds lines of text which are added
  a line at a time via the 'append' method."""

  def __init__(self,maxsize=0):
    """Initialise a new buffer object.

    If 'maxsize' is greater than zero then it sets the
    maximum number of lines that the buffer will hold.
    If this number of lines is exceeded by an append
    operation, then the 'oldest' line is dropped from
    the buffer.
    If 'maxsize' is zero or negative then no upper limit
    is placed on the number of lines that the buffer will
    store."""
    self.__contents = []
    self.__maxsize = maxsize

  def __len__(self):
    """Builtin: return the number of lines stored in the buffer."""
    return len(self.__contents)

  def append(self,line):
    """Append a line of text to the buffer.

    The line will have any trailing 'end of line'
    characters removed automatically upon storage."""
    if self.__maxsize > 0 and len(self.__contents) > self.__maxsize:
      self.__contents = self.__contents[1:]
    # Remove trailing newline/end of line characters
    self.__contents.append(line.rstrip("\r\n"))

  def len(self):
    """Return the number of lines currently stored.

    Deprecated: use len(table) instead."""
    return self.__len__()

  def line(self,n):
    """Return the n'th line of text from the buffer.

    The line will be returned without end-of-line characters."""
    return self.__contents[n]

  def tail(self,n=10):
    """Return the 'tail' of the buffer.

    This returns the last n lines of text stored in the
    buffer, concatenated into a single string with end lines
    terminated by a newline character.
    If a number of lines is not specified then it defaults
    to the last 10 lines of text."""
    nend = self.len()
    nstart = nend - n
    if nstart < 0:
      nstart = 0
    return self.contents(nstart,nend)

  def getlines(self,n,m):
    """Return lines 'n' through to 'm' as a list.

    Return a set of lines starting from line index 'n' up to
    but not including line index 'm', as a list."""
    return self.__contents[n:m]

  def contents(self,n,m):
    """Return lines 'n' through to 'm' as a string.

    Return the specified lines from the buffer concatenated
    into a single string with line ends terminated by a newline
    character."""
    str = ""
    subset = self.getlines(n,m)
    for line in subset:
      str = str + line + "\n"
    return str.rstrip("\n")

  def all(self):
    """Return entire buffer contents as a string.

    All lines in the buffer will be concatenated into a single
    string with line ends terminated by a newline character."""
    str = ""
    for line in self.__contents:
      str = str + line + "\n"
    return str.rstrip("\n")

  def clear(self):
    """Clear the buffer of all content.

    Delete all lines currently stored in the buffer."""
    self.__contents[0:self.len()] = []
    return

#
# tablebuffer
#
# Buffer class specialised for handling tables
# Subclasses buffer
class tablebuffer(buffer):
  """Buffer object specialised for dealing with CCP4 tables.

  This class extends the 'buffer' class with additional
  data and methods specialised for CCP4 tables."""

  def __init__(self,maxsize=0):
    """Initialise a new tablebuffer object."""
    self.__hasTABLE = False
    self.__hasGRAPHS = False
    self.__ndoubledollar = 0
    buffer.__init__(self,maxsize)

  def append(self,line):
    """Append a line of text to the tablebuffer.

    This overrides the append method of the parent class
    and performs additional checks on the line being
    added, to also identify specific features (such as
    '$$' symbols) that are part of a CCP4 table."""
    # Check if line has "$TABLE"
    hasTABLE = re.compile(r"\$TABLE *:").search(line)
    if hasTABLE:
      # Check if the buffer already contains a
      # partial or complete table
      if self.__hasTABLE:
        # Dump the existing table
        self.clear()
      self.__hasTABLE = True
    # Check if line has "$(GRAPHS|SCATTER)"
    if self.__hasTABLE:
      buffer.append(self,line)
      hasGRAPHS = re.compile(r"\$(GRAPHS|SCATTER)").search(line)
      if hasGRAPHS:
        self.__hasGRAPHS = True
      # Check if line has "$$"
      if self.__hasGRAPHS:
        ndoubledollar = line.count("$$")
        if ndoubledollar > 0:
          self.__ndoubledollar = self.__ndoubledollar + ndoubledollar

  # Check if we have a complete table yet
  def complete(self):
    """Check if the buffer appears to contain a complete table.

    Returns 'True' if the buffer contains the following
    features, encountered in this order:
    1. '$TABLE' token
    2. '$GRAPH' or '$SCATTER' token
    3. Four '$$' tokens
    In this case it is likely that the buffer contains a
    complete CCP4 table.

    If any of these elements are missing then the method
    returns 'False'."""
    if self.__hasTABLE and self.__hasGRAPHS and self.__ndoubledollar == 4:
      return True
    else:
      return False

  def clear(self):
    """Clear the tablebuffer of all data.

    This overrides the 'clear' method of the parent class
    and also resets the flag data that is specific to the
    tablebuffer class."""
    self.__hasTABLE = False
    self.__hasGRAPHS = False
    self.__ndoubledollar = 0
    buffer.clear(self)

# logfile
#
# Abstract description of a CCP4 logfile
#
class logfile:
  """Object describing a program logfile.

  A logfile object is populated and returned by the
  parselog() function. This takes a file name as a single
  compulsory argument; the optional 'progress' argument
  specifies a number of lines at which to report progress
  when parsing the file.

  A logfile object holds lists of 'programs', 'tables',
  'keytext messages' and 'CCP4i information messages',
  plus a master list of 'fragments' (which can be any of
  the above). There are methods to allow access to each of
  these lists.
  There is also a list of CCP4 'summaries' that have been
  been found in the logfile. These are kept distinct from
  the logfile fragments above."""

  def __init__(self,filename):
    """Initialise the logfile object."""
    # Source file
    if os.path.isabs(filename):
      self.__filename = os.path.normpath(filename)
    else:
      # Construct an absolute path
      self.__filename = os.path.abspath(
          os.path.join(os.getcwd(),filename))
    # CCP4i header and tail
    self.__isccp4i = False
    self.__ccp4i_header = []
    self.__ccp4i_tail = []
    # List of fragments, programs, tables, keytexts
    # and ccp4i_info
    self.__fragments = []
    self.__programs = []
    self.__tables = []
    self.__keytexts = []
    self.__ccp4i_info = []
    self.__summaries = []

  def __nonzero__(self):
    """Implement the nonzero built-in method.

    The logfile will test as True if at least one
    fragment is defined - otherwise it will test as
    False."""
    if self.__fragments:
      return True
    return False

  def append_ccp4i_header(self,line):
    """Append a line of text to the CCP4i header."""
    # FIXME should be internally accessible only?
    self.__ccp4i_header.append(line)
    self.__isccp4i = True

  def ccp4i_header(self):
    """Return the CCP4i header content."""
    return self.__ccp4i_header

  def append_ccp4i_tail(self,line):
    """Append a line of text to the CCP4i tail."""
    # FIXME should be internally accessible only?
    self.__ccp4i_tail.append(line)
    self.__isccp4i = True

  def ccp4i_tail(self):
    """Return the CCP4i tail content."""
    return self.__ccp4i_tail

  def isccp4i(self):
    """Return True if the logfile appears to be from CCP4i."""
    return self.__isccp4i

  def filename(self):
    """Return the filename of the source logfile."""
    return self.__filename

  def newfragment(self):
    """Generate a new fragement and add to the logfile.

    Returns a new fragment object and calls addfragment to
    add it to the list of fragments for this logfile."""
    newfragment = fragment()
    self.addfragment(newfragment)
    return newfragment

  def addfragment(self,fragment):
    """Add an existing fragment-like object to the logfile."""
    self.__fragments.append(fragment)

  def nfragments(self):
    """Return the number of fragments."""
    return len(self.__fragments)

  def fragment(self,i):
    """Return the i'th fragment in the logfile.

    A fragment can be a program, table, CCP4i message or
    keytext object.
    Note that i counts up from zero."""
    try:
      return self.__fragments[i]
    except:
      raise

  def addprogram(self):
    """Add a new program object to the logfile."""
    # FIXME should be internally accessible only?
    newprogram = program()
    self.__programs.append(newprogram)
    self.addfragment(newprogram)
    return newprogram

  def nprograms(self):
    """Return the number of program objects."""
    return len(self.__programs)

  def program(self,i):
    """Return the i'th program object in the logfile.

    Note that i counts up starting from zero."""
    try:
      return self.__programs[i]
    except:
      raise

  def addtable(self,thistable=False,tabletext=""):
    """Add a table object to the list of tables.

    If an existing table object is specified with the
    thistable argument then this is appended to the
    list. Otherwise a new table object is created. In
    that case, if tabletext is supplied then this is
    used to populate the table object; otherwise the
    new table object is empty."""

    # FIXME should be internally accessible only?
    if thistable:
      # Table object supplied
      self.__tables.append(thistable)
      return thistable
    else:
      # Make a new table
      if tabletext:
        new_table = table(tabletext)
      else:
        new_table = table()
      self.__tables.append(new_table)
      return new_table

  def ntables(self):
    """Return the number of tables in the logfile."""
    return len(self.__tables)

  def table(self,i):
    """Return the i'th table object in the logfile.

    This method is deprecated, use 'logfile.tables()[i]'
    instead.

    Note that i counts up starting from zero."""
    try:
      return self.__tables[i]
    except:
      raise

  def findtable(self,title_pattern,index=0):
    """Fetch a table in the logfile by matching the title.

    This method is deprecated; use the 'tables' method
    instead.

    This method looks up a particular table in a list
    of table objects (argument 'table_list'), by finding
    the first table in the list which matches the supplied
    regular expression 'title_pattern'.

    If there is more than one matching table then the 'index'
    argument specifies which of the list of matching tables
    should be returned. If index is out of range (or there are
    no matching tables) then return 'None'.

    It calls the 'find_table_by_title' function."""
    return find_table_by_title(self.__tables,title_pattern,index)

  def tables(self,select_title=""):
    """Return a list of tables in the logfile.

    If no 'select_title' is specifed then this returns
    the list of all the table objects stored in the logfile
    object.

    If 'select_title' is given then this is compiled as
    a regular expression pattern, and the method returns a
    list containing only those table objects for which the
    title matches the pattern.

    In either case if no table objects are found then an
    empty list is returned.

    This method calls the 'find_tables_by_title' function."""
    if select_title == "":
      # Return everything
      return copy.copy(self.__tables)
    return find_tables_by_title(self.__tables,select_title)

  def addkeytext(self,thiskeytext=False,name="",junk_text="",message=""):
    """Add a keytext object to the list of keytexts.

    If an existing keytext object is supplied with the
    thiskeytext argument this is appended to the list.
    Otherwise a new keytext object is created and
    populated with the contents of the name, junk_text
    and message arguments."""

    # FIXME should be internally accessible only?
    if thiskeytext:
      # Table object supplied
      self.__keytexts.append(thiskeytext)
      return thiskeytext
    else:
      # Make a new keytext
      new_keytext = keytext(name,junk_text,message)
      self.__keytexts.append(new_keytext)
      return new_keytext

  def nkeytexts(self):
    """Return the number of keytexts in the logfile."""
    return len(self.__keytexts)

  def keytext(self,i):
    """Return the i'th keytext object in the logfile.

    Note that i counts up starting from zero."""
    try:
      return self.__keytexts[i]
    except:
      raise

  def addccp4i_info(self):
    """Add another ccp4i_info object to the logfile.

    Creates a new ccp4i_info object and added to the
    list of fragments, and to the list of CCP4i information
    messages found in the logfile."""

    # FIXME should be internally accessible only?
    # Make a new ccp4i_info object
    newccp4i_info = ccp4i_info()
    self.__ccp4i_info.append(newccp4i_info)
    self.addfragment(newccp4i_info)
    return newccp4i_info

  def nccp4i_info(self):
    """Return the number of ccp4i_info messages."""
    return len(self.__ccp4i_info)

  def ccp4i_info(self,i):
    """Return the i'th ccp4i_info object in the logfile.

    Note that i counts up starting from zero."""
    try:
      return self.__ccp4i_info[i]
    except:
      raise

  def addsummary(self,start_line=-1):
    """Add another summary object to the logfile.

    A new summary object is created and returned. The
    new object is also added to the list of summaries
    for the logfile."""

    new_summary = summary(self.__filename,start_line)
    self.__summaries.append(new_summary)
    return new_summary

  def nsummaries(self):
    """Return the number of summaries found in the log."""
    return len(self.__summaries)

  def summary(self,i):
    """Return the i'th summary object in the logfile.

    Note that i counts up starting from zero."""
    try:
      return self.__summaries[i]
    except:
      raise

  def set_fragment_start(self,line_no):
    """Set the start line of the most recent fragment.

    The most recent fragment is the last fragment object
    in the list of fragments for this logfile. 'line_no'
    is the current line number in the source file.

    If the fragment has an 'nlines' attribute then this
    is taken to be the offset from the current line back
    to the start of the fragment. If nlines is not
    present then the fragment is taken to start after the
    end of the previous fragment. If there is no previous
    fragment then it is assumed to start from the first
    line of the file"""
    fragment = self.__fragments[-1]
    fragment.set_attribute("source_file",self.__filename)
    if fragment.has_attribute("nlines"):
      # Calculate the start of the fragment from the
      # current position
      offset = fragment.nlines
      fragment.set_startline(line_no-offset)
    else:
      if self.nfragments() > 1:
        # Assume that the fragment starts from here
        fragment.set_startline(line_no)
      else:
        # This is the first fragment
        fragment.set_startline(1)
    # Now deal with the previous fragment,
    # which may not have an end line set
    if self.nfragments() > 1:
      last_fragment = self.__fragments[-2]
      if last_fragment.get_endline() < 0:
        last_fragment.set_endline(fragment.get_startline()-1)

  def set_fragment_end(self,line_no):
    """Set the end line of the most recent fragment.

    The most recent fragment is the last fragment object
    in the list of fragments for this logfile. 'line_no'
    is the current line number in the source file.

    The supplied line number is always taken as the last
    line number of the fragment. This method will also
    check the start line number and will attempt to set
    it to a reasonable value if it is not set: either the
    first line after the end of the previous fragment,
    or the start of the file (if there is no previous
    fragment)."""
    if not self.__fragments:
      # We're in a situation where there was no
      # first fragment
      # Let's make one now
      self.newfragment()
    fragment = self.__fragments[-1]
    if fragment.get_endline() > -1:
      # Don't reset the value if it's already set
      return
    fragment.set_attribute("source_file",self.__filename)
    fragment.set_endline(line_no)
    # Check if the start is also set
    if fragment.get_startline() < 1:
      if self.nfragments() > 1:
        # Assume that the fragment started from the
        # end of the previous fragment
        last_fragment = self.__fragments[-2]
        fragment.set_startline(last_fragment.get_endline()+1)
      else:
        # This is the first fragment
        fragment.set_startline(1)

  def fragment_to_program(self,i):
    """Convert the i'th fragment to a program.

    This method allows a fragment in the logfile to be
    recast as a program, and performs all the necessary
    book keeping operations such as updating the lists
    of fragment and program objects.

    On successful conversion the converted program
    object is returned. If the fragment is already a
    program then no action is taken."""

    if self.fragment(i).isprogram():
      return self.fragment(i)
    prog = copyfragment(self.fragment(i),program())
    # Add the converted program fragment to the
    # list of programs
    # To do this we need to work out where it belongs
    if i == 0:
      # Fragment was the first in the list
      # Add to the start of the program list
      self.__programs.insert(0,prog)
    else:
      # Look for a fragment after this one
      # in the list which is also a program
      nextprog = None
      for j in range(i,self.nfragments()):
        if self.fragment(j).isprogram():
          nextprog = self.fragment(j)
          break
      if not nextprog:
        # No programs found - append
        self.__programs.append(prog)
      else:
        # Locate this in the list of programs
        j = self.__programs.index(nextprog)
        self.__programs.insert(j,prog)
    # Remove the converted fragment
    self.__fragments.remove(self.fragment(i))
    return prog

# fragment
#
# Abstract description of a generic logfile fragment
#
class fragment:
  """Object describing a generic fragment of a logfile.

  The fragment object is intended to represent any
  'top-level' fragment of a logfile, for example a
  program logfile or some output from a script that
  appears inbetween program logs.

  The fragment class is used as the base class for
  the program and ccp4i_info classes."""

  def __init__(self):
    """Initialise a new fragment object."""
    # Initialise a dictionary to store arbitrary
    # attributes taken from the program logfile
    self.__dict = {}
    # List of tables
    self.__tables = []
    # List of keytexts
    self.__keytexts = []
    # For fragment retrieval
    self.set_source_file("")
    self.set_startline(-1)
    self.set_endline(-1)
    # Flags
    self.__nonzero = False

  def __nonzero__(self):
    """Implement the __nonzero__ built-in method.

    The fragment is considered 'nonzero' once an
    attribute, table or keytext has been assigned
    to it."""
    return self.__nonzero

  def __len__(self):
    """Implement the __len__ built-in method.

    The length of a fragment is the number of lines
    of text that it contains."""
    nlines = self.get_endline() - self.get_startline() + 1
    if nlines < 0: nlines = 0
    return nlines

  def isfragment(self):
    """Return True if this represents a basic fragment."""
    return True

  def isprogram(self):
    """Return True if this represents a program logfile."""
    return False

  def isccp4i_info(self):
    """Return True if this is a CCP4i information fragment."""
    return False

  def __setitem__(self,key,value):
    """Implements the functionality for program[key] = value

    Wrapper for the set_attribute method."""
    self.set_attribute(key,value)

  def __getitem__(self,key):
    """Implements the functionality for value = fragment[key]

    Wrapper for the get_attribute method."""
    return self.get_attribute(key)

  def __getattr__(self,key):
    """Implements the functionality for value = fragment.key

    Wrapper for the get_attribute method."""
    return self.get_attribute(key)

  def get_attribute(self,key):
    """Return the value of a fragment attribute.

    The key is a string specifying a particular fragment
    attribute. If the attribute has been read from the file
    then its value is returned, otherwise a KeyError
    exception is raised."""
    try:
      return self.__dict[key]
    except KeyError:
      raise AttributeError, "Unknown attribute '"+str(key)+"'"

  def has_attribute(self,key):
    """Check whether a fragment attribute has been set.

    The key is a string specifying a particular fragment
    attribute. If the attribute has been set then this
    method returns True, otherwise it returns False."""
    return key in self.__dict

  def attributes(self):
    """Return a list of all the fragment attributes.

    The list contains all the attributes that have been
    set for the fragment."""
    return self.__dict.keys()

  def set_attribute(self,key,value):
    """Set the value of a fragment attribute.

    The key is a string specifying a particular fragment
    attribute which will be assigned the given value.
    If the attribute doesn't exist then it will be created,
    if it does then the current value will be overwritten
    by the new one."""
    self.__dict[key] = value
    self.__nonzero = True

  def set_attributes_from_dictionary(self,dict):
    """Set the values of multiple fragment attributes.

    For each key in dictionary 'dict', the value of a
    fragment attribute with the same name as the key will
    be assigned the same value as that of the key."""
    for key in dict:
      self.__dict[key] = dict[key]
    self.__nonzero = True

  def addtable(self,tabletext=""):
    """Add a new table object to the fragment.

    Create a new table object and add it to the list of
    tables associated with the fragment.
    If 'tabletext' is nonblank then the table object will
    be automatically populated from the text, if possible.

    This method returns the new table object."""
    if tabletext:
      newtable = table(tabletext)
    else:
      newtable = table()
    self.__tables.append(newtable)
    self.__nonzero = True
    return newtable

  def ntables(self):
    """Return the number of tables found in the fragment."""
    return len(self.__tables)

  def table(self,i):
    """Return the i'th table object.

    This method is deprecated, use 'fragment.tables()[i]'
    instead.

    fragment.table(i) returns the i'th table object associated
    with the fragment object. The methods of the table class
    can then be used to drill down into the contents of the
    table.

    Use the ntables method to get the total number of table
    objects associated with the fragment."""
    try:
      return self.__tables[i]
    except:
      raise

  def findtable(self,title_pattern,index=0):
    """Fetch a table in the fragment by matching the title.

    This method is deprecated; use the 'tables' method
    instead.

    This method looks up a particular table in a list
    of table objects (argument 'table_list'), by finding
    the first table in the list which matches the supplied
    regular expression 'title_pattern'.

    If there is more than one matching table then the 'index'
    argument specifies which of the list of matching tables
    should be returned. If index is out of range (or there are
    no matching tables) then return 'None'.

    It calls the 'find_table_by_title' function."""
    return find_table_by_title(self.__tables,title_pattern,index)

  def tables(self,select_title=""):
    """Return a list of tables in the fragment.

    If no 'select_title' is specifed then this returns
    the list of all the table objects stored in the fragment
    object.

    If 'select_title' is given then this is compiled as
    a regular expression pattern, and the method returns a
    list containing only those table objects for which the
    title matches the pattern.

    In either case if no table objects are found then an
    empty list is returned.

    This method calls the 'find_tables_by_title' function."""
    if select_title == "":
      # Return everything
      return copy.copy(self.__tables)
    return find_tables_by_title(self.__tables,select_title)

  def addkeytext(self,name="",junk_text="",message=""):
    """Add a new keytext object to the fragment.

    Create a new keytext object and add it to the list of
    keytexts associated with the fragment.
    The values of the parameters 'name', 'junk_text' and
    'message' will be used to initialise the new keytext
    object (one or more of these can be blank).

    This method returns the new keytext object."""
    # FIXME should be internally accessible only?
    newkeytext = keytext(name,junk_text,message)
    self.__keytexts.append(newkeytext)
    self.__nonzero = True
    return newkeytext

  def nkeytexts(self):
    """Return the number of keytexts found in the logfile fragment.

    'Keytexts' are warnings and messages issued by the
    ccperror/CCPERR functions within programs; see the
    loggraph format documentation for more information, e.g.
    http://www.ccp4.ac.uk/dist/html/loggraphformat.html"""
    return len(self.__keytexts)

  def keytext(self,i):
    """Return the i'th keytext object.

    For example: program.keytext(i) returns the i'th keytext
    object associated with the program object. The methods
    of the keytext class can then be used to drill down into
    the contents of the message.

    Use the nkeytexts method to get the total number of
    keytext objects associated with the program/fragment."""
    try:
      return self.__keytexts[i]
    except:
      raise

  def set_startline(self,line_no):
    """Set the start line of the fragment in the source document."""
    self.set_attribute("startline",line_no)

  def get_startline(self):
    """Get the start line of the fragment in the source document."""
    return self.get_attribute("startline")

  def set_endline(self,line_no):
    """Set the end line of the fragment in the source document."""
    self.set_attribute("endline",line_no)

  def get_endline(self):
    """Get the end line of the fragment in the source document."""
    return self.get_attribute("endline")

  def set_source_file(self,source_file):
    """Set the source document for the fragment.

    The source document is specified as the name of the file that
    the fragment is part of."""
    self.set_attribute("source_file",source_file)

  def get_source_file(self):
    """Get the source document for the fragment."""
    return self.get_attribute("source_file")

  def retrieve(self):
    """Retrieve the text associated with the fragment.

    This uses the 'retrieve' method within the module."""
    # Retrieve the information
    filen = self.get_source_file()
    start = self.get_startline()
    end = self.get_endline()
    return retrieve(filen,start,end)

#
# program
#
# Abstract description of the logfile for a single program
#
class program(fragment):
  """Object describing the log for a single program.

  program objects are instantiated and populated by parselog
  as part of the parsing process. The program object is
  intended to describe a fragment of logfile that corresponds
  to the run of a particular program, although in practice
  other types of logfile features (for example, 'interstitial'
  fragments i.e. bits of output inbetween program logs) are
  also assigned to program objects in the current version of
  smartie.

  A program object holds various attributes describing the
  logfile fragment in question, as well as a list of tables
  and keytext messages. A program object may also hold CCP4i
  information messages, however normally it will not hold this
  at the same time as actual program data.

  The attributes associated with the program object can be
  accessed using either of the syntaxes 'program['attribute']'
  or 'program.attribute'.

  For programs using the standard CCP4 banners, the following
  attributes may be defined:

  name: the name of the program from the CCP4 banner, or
  equivalent.

  version: the program version; for CCP4 programs, this is the
  version found in the program banner. For programs that don't
  explicitly give their own version number this will be the same
  as the CCP4 library version.

  date: the date string found in the CCP4 banner; it is
  typically the last date that the source code file was
  committed to CVS. It is not the date that the program was
  run on - for that, see the 'rundate' and 'runtime' attributes.

  ccp4version: the CCP4 library version as it appears in the
  program banner. Typically this includes only the major and
  minor version numbers, but not the patch level.

  user: the user id that appears in the CCP4 banner at runtime.

  runtime: the time of day that the program run started at as
  reported in the program banner.

  rundate: the date that the program run started at as
  reported in the program banner.

  termination_name: the program name as reported in the
  CCP4 termination message at the tail of the program log.

  termination_message: the message text displayed in the
  CCP4 termination message.

  usertime: the value of the 'user time' given at
  termination.

  systemtime: the value of the 'system time' given at
  termination.

  elapsedtime: the value of the 'elapsed time' given at
  termination.

  Note that not all these attributes may be defined, for
  example if the program fragment is an incomplete CCP4 log
  file or if the program is not a CCP4 program. Use the
  'attributes' method to get a list of the defined
  attributes.

  In addition the program object also stores a list of the
  keyword input lines; this list can be retrieved directly
  using the 'keywords' method."""

  def __init__(self):
    """Initialise a new program object."""
    # Initialise the base class
    fragment.__init__(self)
    # Initialise program-specific flags and
    # attributes
    self.__isccp4 = False
    self.__termination = False
    # List of keyword lines
    self.__keywords = []
    # Dictionary of logical name/filename pairs
    self.__logicalnames = {}

  def isprogram(self):
    """Return True if this represents a program logfile.

    Overrides the 'isprogram' method in the base class."""
    return True

  def isfragment(self):
    """Return True if this represents a raw logfile fragment.

    Overrides the 'isfragment' method in the base class."""
    return False

  def set_isccp4(self,isccp4):
    """Set whether the logfile fragment is from a CCP4 program or not.

    This method sets the value of the isccp4 flag to True
    if the logfile fragment is determined to be from a CCP4
    program, and False if not. Use the 'isccp4' method to
    return the value of this flag."""
    # Possibly this should be internally accessible only?
    self.__isccp4 = isccp4

  def isccp4(self):
    """Check if the logfile fragment is from a CCP4 program.

    This returns True if the fragment of logfile appeared to
    be from a CCP4 program, and False otherwise."""
    return self.__isccp4

  def set_termination(self,termination):
    """Set whether the logfile has a termination message.

    This sets the value of the 'termination' flag to be
    True if a termination message was found, and False if
    not. Use the 'termination' method to return the value
    of this flag."""
    # FIXME should be internally accessible only?
    self.__termination = termination

  def termination(self):
    """Check if the logfile fragment ends with a valid termination.

    This returns True if the fragment appeared to finish with a
    recognised termination message, False otherwise.
    Program fragments that do not end with a termination
    message may have terminated prematurely due to an error."""
    return self.__termination

  def addkeyword(self,line):
    """Append a keyword input line to the program logfile.

    This appends a keyword input line (with any leading text
    removed) to the list of keyword lines stored in the
    program object."""
    self.__keywords.append(line)

  def keywords(self):
    """Return the list of keyword lines.

    This method returns a list of the keyword input lines
    that have been stored for the program object. The lines
    are otherwise unprocessed. The lines are stored in the
    order that they were originally stored, and so should
    reflect the order that they appear in the logfile."""
    return self.__keywords

  def addlogicalname(self,logical_name,filename):
    """Add a logical name/filename reference.

    This adds a logical name and the associated filename to
    the dictionary of files that were reported as being opened
    in the logfile.

    If the same logical name is added multiple times then only
    the last associated filename is kept."""

    self.__logicalnames[logical_name] = filename

  def logicalnames(self):
    """Return a list of logical names associated with the program.

    The name of the file associated with a logical name can
    be retrieved using the 'logicalnamefile' method."""
    return self.__logicalnames.keys()

  def logicalnamefile(self,logical_name):
    """Return the filename associated with a logical name.

    Given a logical name, return the associated filename.
    If the logical name isn't found then a KeyError
    exception is raised."""
    try:
      return self.__logicalnames[logical_name]
    except KeyError:
      raise KeyError, "Logical name '"+str(logical_name)+"' not found"

#
# table
#
# Abstract description of a CCP4 formatted logfile table
#
class table:
  """Object describing a CCP4 logfile table

  The table class represents the various components of a table
  as output in CCP4 program logfiles. These tables are formatted
  in a standard way that enables the data that they contain to
  be displayed by the (x|j)loggraph programs.

  For a description of the loggraph format see the loggraph
  format documentation, e.g.
  http://www.ccp4.ac.uk/dist/html/loggraphformat.html

  A table consists of a number of columns of data, and a
  number of graphs which are defined as being a subset of these
  columns. Within smartie the table_column class represents an
  individual column, and the table_graph class represents an
  individual graph.

  A table object can be populated when it is created, by
  supplying it with text containing a CCP4-formatted table
  (typically, a fragment of logfile text). Alternatively an
  'empty' table can be instantiated and then populated using
  the methods of the objects.

  The contents of the table can be output in the correct
  CCP4 format using the 'show' and 'jloggraph' methods."""

  # Initialise the table object
  def __init__(self,tabletext=""):
    """Create a new table object.

    If tabletext contains the text of an existing
    CCP4-formatted table then the table object will
    attempt to parse the table and populate itself using
    the supplied data.

    If 'tabletext' cannot be interpreted as a table
    then the table object will be 'empty' and will contain
    no data. In this case, if 'tabletext' consists of a
    single line with no trailing newline then the table
    object title will be set to 'tabletext'
    automatically."""

    # Table attributes
    self.__title = ""
    self.__type = "GRAPHS" # Default to GRAPHS
    self.__graphs = ""
    self.__columns = ""
    self.__text = ""
    self.__data = ""
    # Derived data
    self.__graph_list = []
    self.__column_list = []
    # Indicate the the object has been populated
    self.__table_parse_error = False
    self.__nonzero = False
    # The "raw" table data from the log file
    self.__rawtable = ""
    # Attempt to populate the table
    if tabletext:
      self.__rawtable = tabletext
      if not self.__buildtable(tabletext):
        # Failed to extract table
        # If it could be a title then use this
        # instead
        if str(tabletext).count("\n") == 0:
          self.settitle(tabletext)
    return

  def __nonzero__(self):
    """Builtin: provides the True/False test.

    A table object is nonzero if data has been loaded
    into it either at instantiation or subsequently
    using any of its methods."""
    return self.__nonzero

  def __str__(self):
    """Builtin: return the table title"""
    if self.__nonzero:
      return self.__title
    return "<Unpopulated table>"

  def __buildtable(self,tabletext):
    """Internal: populates the table object from an existing
    formatted table.

    'tabletext' should be a block of text containing a CCP4
    formatted table. This text can also contain extra leading
    or trailing text which is not part of the table, and this
    will be ignored.

    __buildtable extracts the various components of data from
    the supplied table text and populates the table object
    appropriately."""

    # Set up the table object by parsing the
    # the supplied text
    tabledata = patternmatch().isccp4table(tabletext)
    if not tabledata:
      # No match
      # The regular expression failed to process the table
      self.__table_parse_error = True
      return False
    # Populate the table object
    self.settitle(tabledata["title"])
    self.settype(tabledata["type"])
    self.setgraphs(tabledata["graphs"])
    self.setcolumns(tabledata["columns"])
    self.settext(tabledata["text"])
    self.setdata(tabledata["data"])
    self.__nonzero = True
    return True

  def __populate_columns(self):
    """Internal: populates the table_column objects.

    This method processes the raw data in the body of the
    loggraph text and extracts white-space delimited data
    items, which are then assigned to individual columns.
    Where possible data are stored using an appropriate
    type, either integer, float or string."""

    # Parse the raw data and populate the table_column
    # objects for this table
    i = 0
    for item in self.__data.split():
      self.table_column(i).append(item)
      i += 1
      if i == self.ncolumns():
        i = 0
    # If there are enough items then i should be
    # zero at the end
    if i != 0:
      # This error could be due to two data items
      # no longer being separated by whitespace
      print "Unable to parse table - too many data items (or not enough)?"
      print "Table title: \""+str(self.title())+"\""
      print "Number of columns   : "+str(self.ncolumns())
      print "Number of data items: "+str(len(self.__data.split()))
      self.__table_parse_error = True

  def parse_error(self):
    """Check if the supplied table was parsed correctly.

    If there was a problem parsing the raw table text (for
    example if the table was incomplete or misformatted) then
    parse_error() will return True, otherwise it will be
    False."""

    # Check the table_parse_error flag
    return self.__table_parse_error

  def setrawtable(self,rawtable):
    """Store the 'raw' table text from the original logfile.

    The raw table data is the original text (for example, the
    fragment of log file text) supplied to the object to
    populate itself from."""

    # Store the "raw" table data
    self.__rawtable = rawtable

  def rawtable(self):
    """Return the 'raw' table text taken from the logfile.

    This returns any original 'raw' text of the table that
    was used to populate the table object.

    If the table object wasn't populated from a text fragment
    then this will return an empty string. The 'loggraph' and
    'jloggraph' methods are recommended over the 'rawtable'
    method as a way to return the table data formatted with
    loggraph tags."""
    return self.__rawtable

  def settitle(self,title):
    """Store the table title.

    The table title is an arbitrary string of text that is
    intended to describe briefly the nature of the data
    presented in the table."""
    self.__title = title
    self.__nonzero = True

  def title(self):
    """Return the table title stored in the object."""
    return self.__title

  def settype(self,graphtype):
    """Store the table graph type.

    This is currently one of two possible loggraph keywords,
    either GRAPHS or SCATTER. The keyword is an indication
    to plotting software of how the data should be displayed:

    GRAPHS: line graphs, with data points joined by lines
    SCATTER: scatter plots, with data plotted as points.

    Raises a ValueError if the graphtype is not recognised."""

    if str(graphtype).find("GRAPH") > -1:
      self.__type = "GRAPHS"
    elif str(graphtype).find("SCATTER") > -1:
      self.__type = "SCATTER"
    else:
      # Unknown type of graph - raise an exception
      raise ValueError, "Unknown graph type: "+graphtype+"\n"+\
            "Must be one of 'GRAPHS' or 'SCATTER'"
    self.__nonzero = True

  def type(self):
    """Return the table graph type.

    See the 'settype' method for the possible values and their
    associated meanings for the table graph type."""
    return self.__type

  def nrows(self):
    """Return the number of complete rows in the table.

    Returns the length of the shortest column of data stored
    in the table."""
    if self.ncolumns() == 0:
      return 0
    nrows = self.table_column(0).nrows()
    for i in range(1,self.ncolumns()):
      nrows = min(self.table_column(i).nrows(),nrows)
    return nrows

  def setgraphs(self,graphs):
    """Store the graph definitions in the table in 'raw' format.

    Within a CCP4-formatted table, one or more graphs are
    be defined using simple strings. Generally the descriptions
    take the form:

    :graph1 name:graphtype:column_list:
    :graph2 name:graphtype:column_list: ...

    (The graph definitions can be separated using whitespace,
    not necessarily newlines).

    The 'setgraphs' method takes an arbitrary number of graph
    definition strings of the above form and extracts from each
    the data, namely: the graph name (i.e. title), the type
    (normally either GRAPH or SCATTER) and a list of column
    numbers in the table."""

    self.__graphs = graphs
    # Create table_graph objects
    rgraph = re.compile(r":([^:]+):([^:]+):([^:]+):")
    for graph in rgraph.findall(graphs):
      new_graph = self.addgraph(graph[0])
      new_graph.setscaling(graph[1])
      new_graph.setcolumns(graph[2])
    self.__nonzero = True

  def graphs(self):
    """Return the graph titles and descriptions.

    This method returns the 'raw' string containing the
    graph definitions for the table, which were originally
    supplied via the 'setgraphs' method. Of itself this
    data is probably not very useful."""
    return self.__graphs

  def setcolumns(self,columns):
    """Create new columns in the table from the 'raw' data.

    Within a CCP4-formatted table, titles of columns are
    supplied as a string of white-space delimited 'tokens'
    (the tokens are the titles). For example:

    Resln_Range 1/resol^2 Nref Nz1 Nz2 Nz3 ...

    This string is supplied to the setcolumns method as the
    'columns' argument. setcolumns then extracts the
    individual column titles and for each makes a new
    (empty) table_column object.

    If table values have previously been stored in the
    table object (via the 'setdata' method) then setcolumns
    will also attempt to populate the columns from this
    data."""

    # Store the column titles ("raw" format)
    # This is a list of white-space separated strings
    self.__columns = columns
    # Create table_column objects
    for col in columns.split():
      self.addcolumn(col)
    # Attempt to populate the column objects
    if self.__data:
      self.__populate_columns()
    self.__nonzero = True

  def columns(self):
    """Return the original column titles text string.

    This method returns the 'raw' string that was supplied
    via the 'setcolumns' method, i.e. a single string with
    whitespace delimited column titles. Of itself this
    data is probably not very useful."""
    return self.__columns

  def settext(self,text):
    """Store the arbitrary text from the table.

    Within a CCP4-formatted table there is space for a
    'arbitrary text' (see the table format documentation
    for more details on this). This text is not used when
    plotting graphs but is included when the data in the
    table is written back out in CCP4 $TABLE format."""
    self.__text = text
    self.__nonzero = True

  def text(self):
    """Return the arbitrary text from the table.

    This returns any arbitrary text associated with the
    table header that was previously stored using the
    'settext' method."""
    return self.__text

  def setdata(self,data):
    """Store the raw tabulated data for the table.

    The body of a CCP4-formatted table contains tabulated
    data items corresponding to columns associated with the
    column titles. The table body consists of a sequence
    of white-space separated data items (typically numbers
    but could be other data).

    The table body data is supplied to this method as a
    single text string via the 'data' argument, and is
    stored as is in the table object.
    If table columns have also previously been defined
    then this method will further attempt to populate the
    columns with the data from the table body."""

    # Store the data from the table ("raw" format)
    # This is a list of whitespace separated data items
    self.__data = data
    # Attempt to populate the column objects
    if self.ncolumns() > 0:
      self.__populate_columns()
    self.__nonzero = True

  def data(self):
    """Return the 'raw' data from the table body.

    This method returns the 'raw' table body text as
    supplied originally via the 'setdata' method. Of
    itself this data is probably not very useful."""
    return self.__data

  def ncolumns(self):
    """Return the number of columns in the table.

    This method returns the number of table_column
    objects associated with the table."""
    return len(self.__column_list)

  def addcolumn(self,title=""):
    """Add a new column to the table.

    This method adds a new 'table_column' object to
    the table, to represent a column of data.
    Optionally the name of the column can be supplied
    via the 'title' argument. The table_column is
    otherwise unpopulated.

    The new table_column is returned by this method."""
    new_column = table_column()
    self.__column_list.append(new_column)
    if title:
      new_column.settitle(title)
    return new_column

  def list_columns(self):
    """Return a list of the column names defined in the graph."""
    columns = []
    for icol in range(0,self.ncolumns()):
      columns.append(self.table_column(icol).title())
    return columns

  def add_data(self,rowdata):
    """Add a row of values to the table.

    'rowdata' is a dictionary which specifies column
    names as keys defining the values to be appended. For
    example, if the table has columns called 'X', 'Y' and
    'Z', then rowdata might be defined as:

    rowdata = { 'X': 0.0, 'Y': 0.776, 'Z': 878 }

    'Null' values (i.e. '*' character) will be added to
    columns not named to keep the table data well-formed.
    For example:

    rowdata = { 'X': 0.0, 'Z': 878 }

    will assign the expected data to the 'X' and 'Z'columns,
    while assigning the '*' character to the 'Y' column.
    """
    if not rowdata.keys():
      # No columns were specified
      return
    for colnam in rowdata.keys():
      # Check the the column is actually defined in
      # in the table
      try:
        self.list_columns().index(colnam)
      except ValueError:
        # The column name wasn't found
        raise ValueError, "Column "+str(colnam)+\
              " is not defined in the table"
    for icol in range(0,self.ncolumns()):
      # Look up whether the column has an
      # explicit value assigned
      colnam = self.table_column(icol).title()
      if colnam in rowdata:
        self.table_column(icol).append(rowdata[colnam])
      else:
        # Assign a null value
        self.table_column(icol).append("*")

  def definegraph(self,title,columns,scaling=""):
    """Add a new graph definition to the table.

    This provides an interface to adding new graph
    definitions to an existing table.

    title:   title for the graph.
    columns: a list of column names. The first column
             will the be the X-axis, others will be
             the Y-values.
    scaling: (optional) the scaling definition.

    Possible scaling strings are:

    'A': fully automatic (axes limits are automatically
         determined when the graph is rendered (this is
         the default)
    'N': 'nought', axes limits start at zero
    'XMIN|XMAXxYMIN|YMAX': limits xmin,xmax and ymin,ymax.

    Raises a ValueError if insufficient number of columns
    are specified, or if a specified column name doesn't
    appear in the table.
    """
    # Check that there are at least two columns
    if len(columns) < 2:
      raise ValueError, "Graph definition needs at least two columns"
    # Build the graph description i.e. list of comma-separated
    # column numbers (this is the loggraph format)
    graph_desc = ""
    for colnam in columns:
      found = False
      for icol in range(0,self.ncolumns()):
        if self.table_column(icol).title() == colnam:
          graph_desc = graph_desc+","+str(icol+1)
          found = True
          break
      if not found:
        # The specified column wasn't located
        # Raise an exception
        raise ValueError, "Column "+str(colnam)+" not found in table"
    # Built the list - strip any leading commas
    graph_desc = graph_desc.strip(",")
    # Add a 'blank' table_graph
    new_graph = self.addgraph(title)
    # Scaling type
    new_graph.setscaling('A')
    if scaling != "": new_graph.setscaling(scaling)
    new_graph.setcolumns(graph_desc)
    return new_graph

  def table_column(self,i):
    """Return the i'th column associated with the table.

    This returns the i'th table_column object in the
    table. Note that i counts from zero.

    Generally applications that want to examine the data
    stored in a table are better off using the 'col'
    method of the table class rather than the
    'table_column' method. The 'col' method allows data
    to be retrieved by column name, and returns the
    column of data as a Python list."""
    try:
      return self.__column_list[i]
    except:
      raise

  def col(self,name):
    """Return the data in the column identified by 'name'.

    This method returns the data in the table column
    identified by 'name' (for example, 'Rfree'), as a
    list of values. (This is a copy of the list of values
    in the table_column object representing the column.)

    If the named column isn't found then a LookupError
    exception is raised."""
    # Identify the column corresponding to the
    # supplied name and return a copy of the data
    for i in range(0,self.ncolumns()):
      if self.table_column(i).title() == name:
        return copy.copy(self.table_column(i).data())
    # Column not found
    raise LookupError, "Column called '"+str(name)+"' not found"

  def ngraphs(self):
    """Return the number of graphs defined in the table.

    This method returns the number of 'table_graph'
    objects associated with the table."""
    return len(self.__graph_list)

  def addgraph(self,title=""):
    """Add a new graph object to the table.

    This method adds a new 'table_graph' object to the
    table. Optionally the name of the new graph can be
    supplied using the 'title' argument. All other graph
    attributes are unset by default."""
    new_graph = table_graph()
    self.__graph_list.append(new_graph)
    new_graph.set_parent_table(self)
    if title:
      new_graph.settitle(title)
    return new_graph

  def table_graph(self,i):
    """Return the i'th graph object.

    This method returns the i'th table_graph object
    associated with the table. (Note that i starts from
    zero.)"""
    try:
      return self.__graph_list[i]
    except:
      raise

  def jloggraph(self,codebase="",width=400,height=300):
    """Return a jloggraph-formatted table.

    This method returns the text for CCP4-formatted table
    from this object which includes the HTML tags required
    for the jloggraph Java applet.

    The codebase argument should specify the full path for
    the JLogGraph.class and JLogCanvas.class files required
    to run the applet (typically this is $CCP4/bin/)."""

    # Wraps the show method
    jloggraph = "<applet width=\""+str(width)+ \
                "\" height=\""+str(height)+ \
                "\" code=\"JLogGraph.class\"\n"+ \
                "codebase=\""+str(codebase)+ \
                "\"><param name=\"table\" value=\"\n"
    jloggraph = jloggraph+self.show(loggraph=True)
    jloggraph = jloggraph+"\"><b>For inline graphs use a Java browser</b></applet>"
    return jloggraph

  def loggraph(self,pad_columns=True):
    """Return a loggraph-formatted table.

    The loggraph method generates the text of the table based
    on the data stored in the object, with the correct
    tags defining the columns and graphs and which should
    be viewable in (x)loggraph.

    For information on the 'pad_columns' option, see the 'show'
    method (the setting here is passed directly to 'show').

    To generate jloggraph-formatted tables use the
    jloggraph method."""
    return self.show(loggraph=True,html=True,pad_columns=pad_columns)

  def show(self,loggraph=False,html=False,pad_columns=True):
    """Return the text of a CCP4-formatted table.

    The show method generates the text of the table based
    on the data stored in the object. If the 'loggraph'
    argument is specified as 'True' then the table includes
    the correct tags defining the columns and graphs and
    which should be viewable in (x)loggraph. If the 'html'
    argument is specified then special HTML characters in
    the titles are escaped.

    If 'pad_columns' is True then columns will be padded
    with spaces in order to make them line up nicely. If
    padding is not required then set it to False."""

    tabletext = ""

    # Preamble for loggraph
    if loggraph:
      table_title = self.title()
      if html: table_title = escape_xml_characters(table_title)
      tabletext = tabletext+"$TABLE: "+table_title+":\n$"+self.type()+"\n"
      # Graph descriptions
      for i in range(0,self.ngraphs()):
        graph = self.table_graph(i)
        graph_title = graph.title()
        if html: graph_title = escape_xml_characters(graph_title)
        tabletext = tabletext+" :"+ \
                    graph_title+":"+ \
                    graph.scaling()+":"
        for col in graph.columns():
          tabletext = tabletext+str(col+1)+","
        tabletext = tabletext.rstrip(",")
        tabletext = tabletext+":\n"
      tabletext = tabletext+"$$\n"

    # Columns and rows
    ncolumns = self.ncolumns()
    if ncolumns > 0:
      nrows = len(self.table_column(0))
    else:
      nrows = 0
    # Determine field widths for printing
    field_width = []
    if pad_columns:
      for i in range(0,ncolumns):
        max_width = len(self.table_column(i).title())
        for item in self.table_column(i).data():
          if len(str(item)) > max_width:
            max_width = len(str(item))
        if max_width >= len(self.table_column(i).title()):
          # Put in an extra space again
          max_width = max_width+1
        field_width.append(max_width)
    else:
      for i in range(0,ncolumns):
        field_width.append(0)
    # Column titles
    for i in range(0,ncolumns):
      title = self.table_column(i).title()
      while len(title) < field_width[i]:
        title = " "+title
      tabletext = tabletext+" "+title

    # Arbitrary text in loggraph format
    if loggraph:
      tabletext = tabletext+" $$"
      if self.text():
        tabletext = tabletext+self.text()
      tabletext = tabletext+" $$\n"
    else:
      tabletext = tabletext+"\n\n"

    # The columns of data
    for i in range(0,nrows):
      for j in range(0,ncolumns):
        item = self.table_column(j)[i]
        while len(str(item)) < field_width[j]:
          item = " "+str(item)
        tabletext = tabletext+" "+str(item)
      tabletext = tabletext+"\n"

    # End of table
    if loggraph:
      tabletext = tabletext+"$$"
    return tabletext

  def html(self,border=2):
    """Return the text of a table with HTML formatting.

    This method returns the body of the table (column
    titles and column data) marked up as a HTML table.
    The width of the table can be controlled by setting
    the 'border' argument.
    Any HTML special characters (<, > and &) in the
    column titles or data items are automatically
    converted to the correct form for HTML."""

    tabletext = "<table border=\""+str(border)+"\">\n"

    # Columns and rows
    ncolumns = self.ncolumns()
    if ncolumns > 0:
      nrows = len(self.table_column(0))
    else:
      nrows = 0

    # Column titles
    tabletext = tabletext+"<tr>\n"
    for i in range(0,ncolumns):
      title = self.table_column(i).title()
      tabletext = tabletext+" <th>"+ \
                  str(escape_xml_characters(title))+ \
                  "</th>\n"
    tabletext = tabletext+"</tr>\n"

    # The columns of data
    for i in range(0,nrows):
      tabletext = tabletext+"<tr>\n"
      for j in range(0,ncolumns):
        item = self.table_column(j)[i]
        tabletext = tabletext+" <td>"+ \
                    str(escape_xml_characters(item))+ \
                    "</td>\n"
      tabletext = tabletext+"</tr>\n"

    # End of table
    tabletext = tabletext+"</table>"
    return tabletext

#
# table_graph
#
# Abstract description of a graph in a CCP4 logfile table
#
class table_graph:
  """Object describing a graph in a CCP4 logfile table.

  Tables in logfiles can contain any number of 'graphs',
  which are represented within smartie by table_graph
  objects.

  A graph is defined by a title, a scaling type, and a
  collection of table_columns storing columns of data."""

  # Initialise the table_graph object
  def __init__(self,title="",scaling="",column_list=None):
    """Create a new table_graph object.

    The 'title' argument is a string containing the title
    for the graph.
    'scaling' is a string describing how the graph should
    be displayed within the (x|j)loggraph program.
    'column_list' is a list of integers corresponding to
    the columns in the table that holds the graph. The first
    column in the list will form the 'x' axis of the graph
    when displayed, the others will be displayed on the
    'y' axis."""
    if column_list is None:
      column_list = []

    self.__title = title
    self.__column_list = column_list
    self.__scaling = scaling
    if self.__title:
      self.__nonzero = True
    else:
      self.__nonzero = False
    # Store a reference to the parent table
    self.__parent_table = None

  def __nonzero__(self):
    return self.__nonzero

  def settitle(self,title):
    """Store the title of the graph."""
    self.__title = title

  def title(self):
    """Return the title of the graph."""
    return self.__title

  def set_parent_table(self,table):
    """Store a reference to the parent table object."""
    self.__parent_table = table

  def graphcols(self):
    """Return a list of the column names in the graph."""
    columns = []
    table = self.__parent_table
    for col in self.__column_list:
      columns.append(table.table_column(col).title())
    return columns

  def setscaling(self,scaling):
    """Store the scaling description.

    This is a string which should take one of three possible
    forms, and which is an instruction to the display
    program on how to scale the graph data for display.

    'A' is 'fully automatic' scaling (the display program
    determines the scaling itself for both axes).
    'N' (for 'nought') is automatic y coordinate scaling, where
    the lowest limit on the y axis is 0s.
    'XMIN|XMAXxYMIN|YMAX' (where XMIN, XMAX and YMIN, YMAX are
    numbers) specifies the exact limits of both axes."""

    self.__scaling = scaling

  def scaling(self):
    """Return the scaling description."""
    return self.__scaling

  def setcolumns(self,columns):
    """Set the table_columns associated with the graph.

    The columns are specified as a string of the form
    e.g. '1,2,4,5'. Note that the column numbers are adjusted
    downwards by 1 to map onto Python numbering (which starts
    at zero)."""

    self.__column_list = []
    for i in columns.split(","):
      if str(i).strip().isdigit():
        self.__column_list.append(int(i)-1)

  def columns(self):
    """Return the list of columns associated with the graph.

    This is a list of integers corresponding to the columns
    in the table."""
    return self.__column_list

#
# table_column
#
# Abstract description of a column in a CCP4 logfile table
#
class table_column:
  """Object describing a column in a CCP4i logfile table"""

  def __init__(self,title=""):
    """Initialise the table_column object."""
    self.__title = title
    self.__data = []
    if self.__title:
      self.__nonzero = True
    else:
      self.__nonzero = False

  def __nonzero__(self):
    """Returns True if the column contains data, False otherwise."""
    return self.__nonzero

  def __len__(self):
    """Implements len(table_column)."""
    return len(self.__data)

  def __getitem__(self,key):
    """Implement table_column[i] to return the i'th data value."""
    return self.__data[key]

  def settitle(self,title):
    """Set the title of the column."""
    self.__title = title

  def title(self):
    """Return the title of the column."""
    return self.__title

  def append(self,item):
    """Append a data value to the end of the column.

    The value will be stored as integer, float or string as
    appropriate."""

    try:
      # Is it a float?
      value = float(item)
      # But, could it be an integer?
      # Try a horrible test
      if float(int(item)) == value:
        # It's actually an integer
        value = int(item)
    except ValueError:
      # Not a numerical value - store as a string
      value = item
    # Add the data item as the correct type
    self.__data.append(value)

  def data(self):
    """Return the list of data values in the column."""
    return self.__data

  def nrows(self):
    """Return the number of rows in the column."""
    return len(self.__data)
#
# keytext
#
# Abstract description of a CCP4 formatted keytext message
#
class keytext:
  """Object describing a keytext message in a CCP4 logfile"""
  # Initialise the keytext object
  def __init__(self,name="",junk_text="",message=""):
    self.setname(name)
    self.setjunk_text(junk_text)
    self.setmessage(message)

  def setname(self,name):
    # Set the name attribute
    self.__name = str(name).strip()

  def name(self):
    # Return the name attribute
    return self.__name

  def setjunk_text(self,junk_text):
    # Set the junk_text attribute
    self.__junk_text = str(junk_text).strip()

  def junk_text(self):
    # Return the junk_text attribute
    return self.__junk_text

  def setmessage(self,message):
    # Set the message attribute
    self.__message = str(message).strip()

  def message(self):
    # Return the message attribue
    return self.__message

#
# ccp4i_info
#
# Abstract description of a CCP4i information message
#
class ccp4i_info(fragment):
  """Object describing a CCP4i information message in a CCP4 logfile.

  The ccp4i_info class has the following attributes:

  'message': the text of the CCP4i information message."""
  # Initialise the ccp4i_info object

  def __init__(self):
    # Initialise the base class
    fragment.__init__(self)
    # Initialise program-specific flags and
    # attributes
    self.set_attribute("message","")

  def isccp4i_info(self):
    return True

  def isfragment(self):
    return False
#
# summary
#
# Abstract description of a CCP4 "summary" block
#
class summary:
  """Object describing a summary block in a CCP4 logfile.

  The summary object holds information about the location
  of a block of text in a logfile. Normally this text would
  be a summary block from a CCP4 logfile, which is
  identified as starting with the text '<!--SUMMARY_BEGIN-->'
  and terminating with the text '<!--SUMMARY_END-->'.

  In practice, the summary object has three attributes: the
  name of a source file, and the start and end line numbers
  of the block of text within that file. The actual text is
  not stored. It can be fetched using the 'retrieve' method,
  in which case it is read directly from the file and
  returned."""
  # Initialise the keytext object
  def __init__(self,source_file,start_line=-1):
    self.__source_file = source_file
    if start_line > 0:
      self.__start_line = start_line
    else:
      self.__start_line = -1
    self.__end_line = -1

  def set_start(self,start_line):
    """Set the start line for the summary block."""
    self.__start_line = start_line

  def set_end(self,end_line):
    """Set the end line for the summary block."""
    self.__end_line = end_line

  def start(self):
    """Return the start line for the summary block."""
    return self.__start_line

  def end(self):
    """Return the end line for the summary block."""
    return self.__end_line

  def iscomplete(self):
    """Check whether the summary block is complete.

    Returns True if the start and end line numbers
    are valid and consistent, and False otherwise."""
    if self.__start_line < 0:
      return False
    if self.__end_line < self.__start_line:
      return False
    return True

  def retrieve(self):
    """Return the text within the summary block."""

    if not self.iscomplete(): return ""
    return retrieve(self.__source_file,
                    self.__start_line,
                    self.__end_line)

class patternmatch:
  """Object holding regular expressions for logfile features.

  The patternmatch object provides a set of methods that can
  match various features that might be found in CCP4 logfiles,
  and logfiles from other programs. These are:

  isccp4banner: check for CCP4 program banner
  isccp4termination: check for CCP4 program termination message
  isshelxbanner: check for SHELX program banner
  isshelxtermination: check for SHELX program termination
  isccp4keytext: check for CCP4 keytext messages
  isccp4table: check for CCP4 table
  isccp4iheader: check for CCP4i logfile header line
  isccp4itail: check for CCP4i logfile tail line
  isccp4iinformation: check for CCP4i information block

  It also provides methods to match single lines:

  isdataline: check if line contains CCP4 keyword input
  isfileopen: check if line contains CCP4 file opening information
  issummary_begin: check if line contains the start of a summary
  issummary_end: check if the line contains the end of a summary

  In each case, the method returns False if there is no match,
  and a dictionary of data items if there is a match. The data
  items are dependent on the type of pattern that is matched -
  see the information for the relevant method for descriptions."""

  def __init__(self):
    # Initialise
    # Create a dictionary to hold the regular expressions
    self.__patterns = dict()

  def compile(self,name,pattern):
    """Returns a compiled regular expression from the pattern.

    This method returns a compiled regular expression associated
    with 'name', based on the supplied 'pattern'. If the name
    already has a compiled expression then that is returned,
    otherwise the compile method compiles and stores it before
    returning it."""
    try:
      return self.get_pattern(name)
    except KeyError:
      return self.store_pattern(name,re.compile(pattern))

  def has_pattern(self,name):
    """Returns True if there is a pattern associated 'name'."""
    return name in self.__patterns

  def store_pattern(self,name,cpattern):
    """Store a compiled regular expression associated with 'name'.

    'cpattern' is a compiled regular expression which
    will be associated with 'name'. The expression can be
    retrieved using the 'get_pattern'."""
    # Store the compiled regular expression in "pattern"
    # with the key "name"
    if not self.has_pattern(name):
      self.__patterns[name] = cpattern
      return cpattern
    # Raise an exception if a pattern has already been
    # stored with the same name
    raise KeyError

  def get_pattern(self,name):
    """Fetch a compiled regular expression associated with 'name'."""
    return self.__patterns[name]

  def isccp4banner(self,text):
    """Regular expression match to CCP4 program banner.

    Given a block of text, attempts to match it against
    regular expressions for a CCP4 program banner.
    Returns False if the match fails, otherwise returns
    a dictionary object populated with attributes
    derived from the supplied text.

    See the isccp4banner_standard and isccp4banner_phaser
    functions for descriptions of the attributes that are
    extracted."""
    # Try standard CCP4 banner
    result = self.isccp4banner_standard(text)
    if not result:
      # Try Phaser-style CCP4 banner
      result = self.isccp4banner_phaser(text)
    if not result:
      # Try old-style CCP4 banner
      result = self.isccp4banner_old(text)
    return result

  # Match CCP4 program termination
  def isccp4termination(self,text):
    """Regular expression match to CCP4 program termination.

    Given a block of text, attempts to match it against
    regular expressions for a CCP4 program termination.
    Returns False if the match fails, otherwise returns
    a dictionary object populated with attributes
    derived from the supplied text.

    See the isccp4termination_standard and
    isccp4termination_phaser functions for descriptions of
    the attributes that are extracted."""
    # Try standard CCP4 termination
    result = self.isccp4termination_standard(text)
    if not result:
      # Try Phaser-style CCP4 termination
      result = self.isccp4termination_phaser(text)
    return result

  # Match standard CCP4 program banner
  def isccp4banner_standard(self,text):
    """Test if text matches a standard CCP4 program banner.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    name: the name of the program from the CCP4 banner.

    version: the program version; for CCP4 programs, this is the
    version found in the program banner. For programs that don't
    explicitly give their own version number this will be the same
    as the CCP4 library version.

    date: the date string found in the CCP4 banner; it is
    typically the last date that the source code file was
    committed to CVS. (It is not the date that the program was
    run on - for that, use 'rundate' and 'runtime').

    ccp4version: the CCP4 library version as it appears in the
    program banner. Typically this includes only the major and
    minor version numbers, but not the patch level.

    user: the user id that appears in the CCP4 banner at runtime.

    runtime: the time of day that the program run started at as
    reported in the program banner.

    rundate: the date that the program run started at as
    reported in the program banner."""
    #
    # Current banner looks like:
    #  ###############################################################
    #  ###############################################################
    #  ###############################################################
    #  ### CCP4 5.99: Refmac_5.2.0019    version 5.2.0019  : 04/08/05##
    #  ###############################################################
    #  User: pjx  Run date: 25/10/2005 Run time: 15:19:23
    #
    # There is also an intermediate version between 4.0 and later:
    # 1###############################################################
    #  ###############################################################
    #  ###############################################################
    #  ### CCP4 4.1: OASIS              version 4.1       : 12/02/01##
    #  ###############################################################
    #  User: pjx  Run date: 14/ 5/01  Run time:15:24:36
    #
    if text.find("### CCP") < 0:
      return dict()
    banner = self.compile("isccp4banner_standard",r"(?: |1)#{63,63}\n #{63,63}\n #{63,63}\n ### CCP4 ([0-9.]+[a-z]*): ([A-Za-z0-9_().]+) *version ([0-9.]+[a-z]*) *: ([0-9 /]+)##\n #{63,63}\n User: ([^ ]+) *Run date: ([0-9 /]+) Run time: ?([0-9:]+) ?").search(text)
    #banner = rbanner.search(text)
    result = dict()
    if banner:
      result["banner_text"] = banner.group(0)
      result["ccp4version"] = banner.group(1)
      result["name"] = banner.group(2)
      result["version"] = banner.group(3)
      result["date"] = banner.group(4)
      result["user"] = banner.group(5)
      result["rundate"] = banner.group(6)
      result["runtime"] = banner.group(7)
      result["nlines"] = banner.group(0).count("\n")
    return result

  # Match standard CCP4 program termination
  def isccp4termination_standard(self,text):
    """Test if text matches a standard CCP4 program termination.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    termination_name: the program name as reported in the
    CCP4 termination message at the tail of the program log.

    termination_message: the message text displayed in the
    CCP4 termination message, e.g. 'Normal termination'.

    usertime: the value of the 'user time' given at
    termination.

    systemtime: the value of the 'system time' given at
    termination.

    elapsedtime: the value of the 'elapsed time' given at
    termination."""
    #
    # Termination looks like:
    #  Refmac_5.2.0019:  End of Refmac_5.2.0019
    # Times: User:       6.0s System:    0.4s Elapsed:     0:07
    #
    # (Note that older program logs may have additional or different
    # whitespace arrangements)
    #
    if text.find("Times: User: ") < 0:
      return dict()
    term = self.compile("isccp4termination_standard",r" *([A-Za-z0-9_().]+): *([^\n]+)\n *Times: User: +([0-9.]+)s System: +([0-9.]+)s Elapsed: +([0-9:]+) *").search(text)
    result = dict()
    if term:
      result["termination_text"] = term.group(0)
      result["termination_name"] = term.group(1)
      result["termination_message"] = term.group(2)
      result["usertime"] = term.group(3)
      result["systemtime"] = term.group(4)
      result["elapsedtime"] = term.group(5)
      result["nlines"] = term.group(0).count("\n")
    return result

  # Match "phaser-style" CCP4 banner
  def isccp4banner_phaser(self,text):
    """Test if text matches a 'phaser-style' CCP4 program banner.

    'Phaser-style' banners look similar to CCP4 banners but
    contain some different information. They are also used by
    the 'pointless' program.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    name: the name of the program from the banner.

    version: the reported program version.

    user: the user id that appears in the banner at runtime.

    rundate: the date that the program run started at as
    reported in the program banner.

    runtime: the time of day that the program run started at as
    reported in the program banner.

    os: corresponds to the 'os type' as reported in the banner,
    for example 'linux'.

    date: corresponds to the 'release date' of the program as
    reported in the banner.

    ccp4version: currently set to '?'."""
    # This style of banner looks like:
    # 1234567890123456789012345678901234567890123456789012345678901234567890123456789012345
    # #####################################################################################
    # #####################################################################################
    # #####################################################################################
    # ### CCP4 PROGRAM SUITE: Phaser                                              1.3.2 ###
    # #####################################################################################
    # User:         pjx
    # Run time:     Wed May 17 09:27:42 2006
    # Version:      1.3.2
    # OS type:      linux
    # Release Date: Sun Feb  5 17:29:18 2006
    #
    # Note:
    # 1. The "OS type" line may not always be present
    # 2. Pointless also writes a similar banner, but with "CCP4 SUITE"
    #    substituted for "CCP4 PROGRAM SUITE"
    #
    # The regular expression accommodates both these differences.
    if text.find("### CCP") < 0:
      return dict()
    banner = self.compile("isccp4banner_phaser",r"#+\n#+\n#+\n### CCP4 (PROGRAM )?SUITE: ([A-Za-z0-9_.]+) *([0-9.]+) *###\n#+\nUser: *([^ ]+)\nRun time: *([A-Za-z0-9: /]+)\nVersion: *([0-9.]+)(?:\nOS type: *)?([^\n]*)\nRelease Date: *([A-Za-z0-9: /]+)").search(text)
    result = dict()
    if banner:
      ##print "Identified Phaser-style banner"
      result["banner_text"] = banner.group(0)
      result["name"] = banner.group(2)
      result["version"] = banner.group(3)
      result["user"] = banner.group(4)
      result["rundate"] = banner.group(5)
      result["runtime"] = banner.group(5)
      result["os"] = banner.group(7)
      result["date"] = banner.group(8)
      result["ccp4version"] = "?"
      result["nlines"] = banner.group(0).count("\n")
    return result

  # Match "phaser-style" CCP4 program termination
  def isccp4termination_phaser(self,text):
    """Test if text matches a 'phaser-style' CCP4 program termination.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    termination_name: the program name as reported in the
    CCP4 termination message at the tail of the program log.

    termination_message: the message text displayed in the
    CCP4 termination message, e.g. 'SUCCESS'.

    systemtime: the value of the 'CPU time' given at
    termination.

    Note that this is a subset of the attributes collected
    for standard CCP4 termination messages."""
    # This style of banner looks like:
    # 12345678012345678012
    # --------------------
    # EXIT STATUS: SUCCESS
    # --------------------
    #
    # CPU Time: 0 days 0 hrs 1 mins 34.43 secs (94.43 secs)
    # Finished: Wed May 17 09:29:25 2006
    if text.find("EXIT STATUS:") < 0:
      return dict()
    term = self.compile("isccp4termination_phaser",r"\-*\nEXIT STATUS: *([^\n]+)\n\-*\n\nCPU Time: *([A-Za-z0-9 \.\(\)]*)\nFinished: *([A-Za-z0-9 \.\(\)]*)").search(text)
    result = dict()
    if term:
      result["termination_text"] = term.group(0)
      result["termination_message"] = term.group(1)
      result["systemtime"] = term.group(2)
      result["nlines"] = term.group(0).count("\n")
    return result

  # Match old-style standard CCP4 program banner
  def isccp4banner_old(self,text):
    """Test if text matches an old-style CCP4 program banner.

    'Old-style' banners come from versions of CCP4 predating
    version 4.1 of the suite.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    name: the name of the program from the CCP4 banner.

    version: the program version; for CCP4 programs, this is the
    version found in the program banner. For programs that don't
    explicitly give their own version number this will be the same
    as the CCP4 library version.

    date: the date string found in the CCP4 banner; it is
    typically the last date that the source code file was
    committed to CVS. (It is not the date that the program was
    run on - for that, use 'rundate' and 'runtime').

    ccp4version: the CCP4 library version as it appears in the
    program banner. Typically this includes only the major and
    minor version numbers, but not the patch level.

    user: the user id that appears in the CCP4 banner at runtime.

    runtime: the time of day that the program run started at as
    reported in the program banner.

    rundate: the date that the program run started at as
    reported in the program banner."""
    #
    # Banner looks like:
    #  123456789012345678901234567890123456789012345678901234567890
    # 1##########################################################
    #  ##########################################################
    #  ##########################################################
    #  ### CCP PROGRAM SUITE: dm          VERSION 4.0: 26/11/98##
    #  ##########################################################
    #  User: pjx  Run date:  3/16/00  Run time:14:12:40
    if text.find("### CCP") < 0:
      return dict()
    banner = self.compile("isccp4banner_old",r"1#{58,58}\n #{58,58}\n #{58,58}\n ### CCP PROGRAM SUITE: ([A-Za-z0-9_().]+) *VERSION ([0-9.]+) *: ([0-9 /]+)##\n #{58,58}\n User: ([^ ]+) *Run date: ([0-9 /]+) Run time:([0-9:]+) ?").search(text)
    result = dict()
    if banner:
      result["banner_text"] = banner.group(0)
      result["name"] = banner.group(1)
      result["ccp4version"] = banner.group(2)
      result["version"] = result["ccp4version"]
      result["date"] = banner.group(3)
      result["user"] = banner.group(4)
      result["rundate"] = banner.group(5)
      result["runtime"] = banner.group(6)
      result["nlines"] = banner.group(0).count("\n")
    return result

  # Match CCP4 keytext i.e. $TEXT ...
  def isccp4keytext(self,text):
    """Test if text matches CCP4 keytext message ($TEXT).

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    name: the message 'name' or identifier

    junk_text: 'junk' text provided by the program (normally ignored)

    message: the message text

    nlines: the number of lines of text covered by the entire keytext
    message block."""
    #
    # See e.g. http://www.ccp4.ac.uk/dist/html/loggraphformat.html
    # for format of TEXT information, but essentially it's:
    #
    # $TEXT :text name: $$ junk (ignored) text $$any text characters$$
    #
    keytext = self.compile("isccp4keytext",r"\$TEXT[ \n]*:([^:]*):[ \n]*\$\$([^\$]*)\$\$([^\$]*)\$\$").search(text)
    result = dict()
    if keytext:
      result["name"] = keytext.group(1)
      result["junk_text"] = keytext.group(2)
      result["message"] = keytext.group(3)
      result["nlines"] = keytext.group(0).count("\n")
    return result

  # Match CCP4 TABLE
  def isccp4table(self,text):
    """Test if text matches CCP4 logfile table ($TABLE).

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    rawtable: the exact text of the table as it appeared in the
    logfile

    title: the title of the table.

    type: the table type.

    graphs: the text of the $GRAPHS portion of the table text.

    columns: the text of the column headers in the table.

    text: the 'junk' text after the column headers and before the
    actual table data.

    data: the text of the table data (i.e. columns and rows of
    numbers or other data.

    nlines: the number of lines of text covered by the entire table
    block.

    These data items are themselves relatively unprocessed, so it
    is recommended that the text that matches the table should be
    fed into a 'table' object which provides a much easier to use
    interface to the various bits of data in the table.
    a table"""
    #
    # See e.g. http://www.ccp4.ac.uk/dist/html/loggraphformat.html
    # for format of TABLES
    #
    # Note that this regular expression accommodates slight deviations
    # by making the "closing" ":" of the $TABLE line optional.
    # This is done for consistency with loggraph's behaviour.
    #
    # Set up regular expression for entire table
    # This is the "strict" form of the table
    table = self.compile("isccp4table",r" *\$TABLE ?:([^:]*):?[ \n]+\$(GRAPHS|SCATTER)[^:]*(:[^\$]*)\$\$([^\$]*)\$\$([^\$]*)\$\$([^\$]*)\$\$").search(text)
    result = dict();
    if table:
      result["rawtable"] = table.group(0)
      result["title"] = table.group(1).strip()
      result["type"] = table.group(2).strip()
      result["graphs"] = table.group(3)
      result["columns"] = table.group(4)
      result["text"] = table.group(5)
      result["data"] = table.group(6)
      result["nlines"] = table.group(0).count("\n")
      return result
    # If there wasn't a match then try a simpler match
    # This relaxes some of the rules in the format definintion
    table = self.compile("isccp4simplertable",r" *\$TABLE ?:([^\n]*)\n+\$(GRAPHS|SCATTER)[^:]*(:[^\$]*)\$\$([^\$]*)\$\$([^\$]*)\$\$([^\$]*)\$\$").search(text)
    if table:
      result["rawtable"] = table.group(0)
      result["title"] = table.group(1).strip()
      result["type"] = table.group(2).strip()
      result["graphs"] = table.group(3)
      result["columns"] = table.group(4)
      result["text"] = table.group(5)
      result["data"] = table.group(6)
      result["nlines"] = table.group(0).count("\n")
      return result
    return result

  # Match CCP4i header information
  def isccp4iheader(self,text):
    """Test if text matches a CCP4i header line."""
    #
    # CCP4i header lines look like:
    # #CCP4I VERSION CCP4Interface 1.4.1
    # #CCP4I SCRIPT LOG refmac5
    # #CCP4I DATE 25 Oct 2005  15:19:22
    #
    if self.isccp4itail(text):
      # Reject tail elements
      return ""
    header = self.compile("isccp4iheader",r"#CCP4I (.*)").search(text)
    result = ""
    if header:
      result = header.group(0)
    return result

  # Match CCP4i header information
  def isccp4itail(self,text):
    """Test if text matches a CCP4i tail line."""
    #
    # CCP4i tail lines look like:
    # #CCP4I TERMINATION STATUS 1
    # #CCP4I TERMINATION TIME 25 Oct 2005  15:19:30
    # #CCP4I TERMINATION OUTPUT_FILES  /home/pjx/PROJECTS/myProject/...
    # #CCP4I MESSAGE Task completed successfully
    #
    tail = self.compile("isccp4itail",r"#CCP4I (TERMINATION|MESSAGE) (.*)").search(text)
    result = ""
    if tail:
      result = tail.group(0)
    return result

  # Match CCP4i information text
  def isccp4i_information(self,text):
    """Test if text matches a CCP4i information block."""
    #
    # CCP4i information lines look like:
    # 123456789012345678901234567890123456789012345678901234567890123456789012345
    # ***************************************************************************
    # * Information from CCP4Interface script
    # ***************************************************************************
    # Running SHELXC to prepare data for heavy atom search
    # ***************************************************************************
    #
    info = self.compile("isccp4iinformation",r"\*{75,75}\n\* Information from CCP4Interface script\n\*{75,75}\n(.*)\n\*{75,75}").search(text)
    result = dict()
    if info:
      result["message"] = info.group(1)
      result["nlines"] = info.group(0).count("\n")
    return result

  # Match SHELX banners
  #  123456789012345678901234567890123456789012345678901234567890123456789012
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #  +  SHELXC - Create input files for SHELXD and SHELXE - Version 2006/3  +
  #  +  Copyright (C) George M. Sheldrick 2003-6                            +
  #  +  SHELX_56_shelxc                 Started at 14:30:07 on 21 Apr 2006  +
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #  +  SHELXD-2006/3 - MACROMOLECULAR DIRECT METHODS - FORTRAN-95 VERSION  +
  #  +  Copyright (C)  George M. Sheldrick 2000-2006                        +
  #  +  SHELX_56_shelxd_fa              started at 14:30:11 on 21 Apr 2006  +
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #
  #  12345678901234567890123456789012345678901234567890123456789012345678
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #  +  SHELXE  -  PHASING AND DENSITY MODIFICATION  -  Version 2006/3  +
  #  +  Copyright (C)  George M. Sheldrick 2001-6                       +
  #  +  Started at 14:30:36 on 21 Apr 2006                              +
  #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  #
  def isshelxbanner(self,text):
    """Test if text matches a SHELX program banner.

    This function tries to match the banners from SHELXC,
    SHELXD and SHELXE.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    name: the program name.

    version: the program version.

    runtime: the time of day that the program run started at as
    reported in the program banner.

    rundate: the date that the program run started at as
    reported in the program banner."""

    # Set up regular expression for partial SHELX banner
    if text.find("SHELX") < 0:
      return dict()
    banner = self.compile("isshelxbanner",r"\+{68,72}\n  \+  (SHELXC|SHELXD|SHELXE)([^\+]*)\+\n  \+  Copyright \(C\) *George M. Sheldrick[^\n]*\n  \+  ([^\+]*)\+\n  \+{68,72}").search(text)
    result = dict()
    if banner:
      result["banner_text"] = banner.group(0)
      result["name"] = banner.group(1)
      result["nlines"] = banner.group(0).count("\n")
      # Try and untangle the versions
      name = banner.group(1)
      version = False
      if name == "SHELXC" or name == "SHELXE":
        version = re.compile(r"Version ([^ \+]*)").search(banner.group(2))
      elif name == "SHELXD":
        version = re.compile(r"\-([^ \-]*)").search(banner.group(2))
      if version:
        result["version"] = version.group(1)
      else:
        result["version"] = "?"
      # Try and untangle the start times
      date = re.compile(r"(S|s)tarted at ([0-9:]+) on ([0-9A-Za-z ]+)").search( \
             banner.group(3))
      if date:
        result["runtime"] = str(date.group(2))
        result["rundate"] = str(date.group(3))
      else:
        result["runtime"] = "?"
        result["rundate"] = "?"
    return result

  # Match SHELX program termination
  def isshelxtermination(self,text):
    """Test if text matches a SHELX program termination.

    This function tries to match the messages from SHELXC,
    SHELXD and SHELXE.

    If the match fails then return False; if it succeeds then
    return a dictionary with the following keys:

    termination_name: the program name as reported in the
    SHELX termination message at the tail of the program log.

    termination_message: the message text displayed in the
    termination message. The content of this text varies
    between SHELXC and SHELXD/E so no further processing is
    currently attempted."""
    #
    # Termination looks like:
    #  123456789012345678901234567890123456789012345678901234567890123456789012
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #  +  SHELXC for SHELX_56_shelxc finished at 14:30:11 on 21 Apr 2006      +
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #  +  SHELXD finished at 14:30:36      Total time:        23.43 secs  +
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #  +  SHELXE finished at 14:34:01      Total time:       198.15 secs  +
    #  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #
    # Set up regular expression for partial SHELX termination
    if text.find("SHELX") < 0:
      return dict()
    term = self.compile("isshelxtermination",r"\+{68,72}\n  \+  (SHELXC|SHELXD|SHELXE)([^\+]*)\+\n  \+{68,72}").search(text)
    result = dict()
    if term:
      result["termination_text"] = term.group(0)
      result["termination_name"] = term.group(1)
      result["termination_message"] = term.group(2)
      result["nlines"] = term.group(0).count("\n")
    return result

  # Match program keyword input line ("Data line")
  def isdataline(self,line):
    """Test if line matches a CCP4 keyword input line.

    This function tries to match the keyword input lines.

    If the match fails then return False; if it succeeds then
    returns a dictionary with the following keys:

    data_line: the keyword data"""
    #
    # Keyworded lines look like:
    #
    # Data line--- make check NONE
    #
    # Set up regular expression for keyword input lines
    data = self.compile("isdataline",r"^ Data line--- ([^\n]*)\n").search(line)
    result = dict()
    if data:
      result["data_line_text"] = data.group(0)
      result["data_line"] = data.group(1)
      result["nlines"] = data.group(0).count("\n")
    return result

  # Match CCP4 file opening line (logical name/filename)
  def isfileopen(self,line):
    """Test if line matches a CCP4 file opening report.

    This function tries to match the reports of a file opening
    event from the CCP4 libraries, which report the logical name
    and associated filename.

    If the match fails then return False; if it succeeds then
    returns a dictionary with the following keys:

    logical_name: the logical name
    filename:     the associated filename"""
    #
    # File opening report lines look like:
    #
    # Logical Name: /home/pjx/PROJECTS/myProject/aucn.mtz   Filename: /home/pjx/PROJECTS/myProject/aucn.mtz
    #
    # Set up regular expression for file opening report lines
    fileopen = self.compile("isfileopen",r"^ Logical Name: ([^\n]*) Filename: ([^\n]*)\n").search(line)
    result = dict()
    if fileopen:
      result["fileopen_text"] = fileopen.group(0)
      result["logical_name"] = fileopen.group(1).strip()
      result["filename"] = fileopen.group(2).strip()
    return result

  # Match CCP4 SUMMARY_BEGIN line (summary start)
  def issummary_begin(self,line):
    """Test if line matches a CCP4 SUMMARY_BEGIN line.

    This function tries to match lines that indicate the start
    of a CCP4 summary block i.e. lines containing the text
    '<!--SUMMARY_BEGIN-->'.

    If the match fails then return False; if it succeeds then
    return True."""
    #
    # Summary start lines look like:
    # <B><FONT COLOR="#FF0000"><!--SUMMARY_BEGIN-->
    #
    # Set up regular expression for SUMMARY_BEGIN lines
    summary = self.compile("issummary_begin",r"<\!--SUMMARY_BEGIN-->").search(line)
    if summary:
      return True
    return False

  # Match CCP4 SUMMARY_END line (summary end)
  def issummary_end(self,line):
    """Test if line matches a CCP4 SUMMARY_END line.

    This function tries to match lines that indicate the end
    of a CCP4 summary block i.e. lines containing the text
    '<!--SUMMARY_END-->'.

    If the match fails then return False; if it succeeds then
    return True."""
    #
    # Summary start lines look like:
    # <!--SUMMARY_END--></FONT></B>
    #
    # Set up regular expression for SUMMARY_BEGIN lines
    summary = self.compile("issummary_end",r"<\!--SUMMARY_END-->").search(line)
    if summary:
      return True
    return False

#######################################################################
# External Functions
#######################################################################

# parselog
#
# Given the name of a logfile, populates and returns a
# logfile object

def parselog(filen,progress=0):
  """Process a file and return a populated logfile object.

  parselog takes a file name as input; optionally if the
  progress argument is set to a positive integer then the
  function also reports its progress when it reaches a
  multiple of that number of lines.

  parselog works by reading the source file one line at a
  time from beginning to end. Each line is added to two
  buffers: a 'small' buffer, which stores the last 10 lines
  read, and a 'large' tablebuffer, which can store the last
  1000 lines.

  After a line has been added, the small buffer is checked
  against a series of regular expressions designed to match
  the various features (banners, terminations and so on).
  If a match is found then parselog updates the logfile object
  that it is constructing and then clears the buffer.
  The tablebuffer is also checked at each line, to see if it
  contains a whole CCP4 logfile table. (The tablebuffer is a
  specialised form of buffer which is intended to optimise
  dealing with tables).

  The buffer sizes for the small and large buffers affect the
  speed of operation of parselog - if they are large then the
  parsing is slower because larger chunks of text are being
  tested multiple times.
  However if the buffers are too small to accommodate some
  of the logfile features then parselog is unable to detect
  those features. As some logfiles can contain extremely large
  tables, the tablebuffer must also be large. However other
  features are generally quite small.

  The other factor that can affect the speed of parsing is the
  make-up of the logfile. Counterintuitively, long files that
  contain few recognisable features can take longer because the
  buffers are only infrequently flushed."""

  # Process a file and return a populated logfile object
  #
  # Maximum size of text buffer to use
  bufsize = 50
  # Initial size of chunks to process
  chunksize = 50
  # Regular expression object
  regex = patternmatch()
  # Buffer objects
  buff = buffer(bufsize)
  tablebuff = tablebuffer()
  linecount = 0
  # New (empty) logfile object
  log = logfile(filen)
  prog = False
  summary = None
  # Open the file for reading
  f = open(filen,"r")
  # Read line-by-line
  for line in f:
    linecount += 1
    # Progress indicator (if requested)
    # Report reaching "progress" number of lines
    if progress:
      if not linecount % progress:
        print "Processed "+str(linecount)+" lines"
    # Append line to buffers
    buff.append(line)
    tablebuff.append(line)
    # Get a chunk of text to process
    bufftext = buff.tail(chunksize)
    # Test the line for matches
    #
    # Data line i.e. CCP4 program keywords
    result = regex.isdataline(line)
    if result:
      if not prog or not prog.isprogram():
        # Found a data line outside the context
        # of a program
        # Assume that we are now inside a program
        prog = log.addprogram()
        # Set the start line to be immediately
        # after the previous fragment
        try:
          previous_fragment = log.fragment(log.nfragments()-2)
          start = previous_fragment.get_endline() + 1
        except IndexError:
          # Failed to get end line of previous
          # fragment
          start = 0
        log.set_fragment_start(start)
      # Remove any html tags and store
      data_line = strip_logfile_html(result["data_line"])
      prog.addkeyword(data_line)
    # File opening report line i.e. logical name/filename pairs
    result = regex.isfileopen(line)
    if result:
      if not prog or not prog.isprogram():
        # Found a file opening report outside the context
        # of a program
        # Assume that we are now inside a program
        prog = log.addprogram()
        # Set the start line to be immediately
        # after the previous fragment
        try:
          previous_fragment = log.fragment(log.nfragments()-2)
          start = previous_fragment.get_endline() + 1
        except IndexError:
          # Failed to get end line of previous
          # fragment
          start = 0
        log.set_fragment_start(start)
      # Store the logical name/filename pair
      prog.addlogicalname(result["logical_name"],result["filename"])
    # Start of a summary block i.e. <!--SUMMARY_BEGIN-->
    result = regex.issummary_begin(line)
    if result:
      summary = log.addsummary(linecount)
    # End of a summary block i.e. <!--SUMMARY_END-->
    result = regex.issummary_end(line)
    if result:
      if not summary:
        # Make a new summary with no start
        summary = log.addsummary()
      # Close out the current summary
      summary.set_end(linecount)
    # Test the buffer for matches
    #
    # CCP4 program banner
    result = regex.isccp4banner(bufftext)
    if result:
      ##print "Found CCP4 program banner"
      ##print "Result = "+str(result)
      prog = log.addprogram()
      prog.set_isccp4(True)
      prog.set_attributes_from_dictionary(result)
      log.set_fragment_start(linecount)
      buff.clear()
      tablebuff.clear()
      continue
    # SHELX program banner
    result = regex.isshelxbanner(bufftext)
    if result:
      ##print "Found SHELX program banner"
      ##print "Result = "+str(result)
      prog = log.addprogram()
      prog.set_attributes_from_dictionary(result)
      log.set_fragment_start(linecount)
      buff.clear()
      tablebuff.clear()
      continue
    # CCP4 program termination
    result = regex.isccp4termination(bufftext)
    if result:
      ##print "Found CCP4 program termination"
      ##print "Result = "+str(result)
      if not prog:
        # Outside the context of any fragment, and
        # found the end of a program before its start
        log.set_fragment_end(offsetline(linecount,result))
        prog = log.addprogram()
      elif not prog.isprogram():
        # Within the context of a fragment which
        # is not a program and found the end of a
        # program before its start
        log.set_fragment_end(offsetline(linecount,result))
        prog = log.addprogram()
      prog.set_attributes_from_dictionary(result)
      log.set_fragment_end(linecount)
      prog.set_termination(True)
      # Clear the current pointer
      prog = False
      buff.clear()
      tablebuff.clear()
      continue
    # SHELX program termination
    result = regex.isshelxtermination(bufftext)
    if result:
      ##print "Found SHELX program termination"
      ##print "Result = "+str(result)
      if not prog:
        # Found the end of a program before its start
        prog = log.addprogram()
      prog.set_attributes_from_dictionary(result)
      log.set_fragment_end(linecount)
      prog.set_termination(True)
      # Clear the current pointer
      prog = False
      buff.clear()
      tablebuff.clear()
      continue
    # CCP4 table
    if tablebuff.complete():
      if not prog:
        # Found a table outside the context of a program
        ##print "Adding table as a fragment"
        prog = log.newfragment()
        log.set_fragment_start(linecount)
      table_error = False
      table = prog.addtable(tablebuff.all())
      if not table:
        print "*** Failed to extract table data ***"
        table_error = True
      elif table.parse_error():
        print "*** Failed to parse table data ***"
        table_error = True
      if table_error:
        print "\tLogfile: "+str(log.filename())
        print "\tTable start: L"+str(linecount - len(tablebuff) + 1)
        print "\tTable end  : L"+str(linecount)
      # Add the table to the log, regardless of status
      log.addtable(table)
      # clear the buffers
      buff.clear()
      tablebuff.clear()
      continue
    # CCP4 keytext message
    result = regex.isccp4keytext(bufftext)
    if result:
      ##print "Found CCP4 keytext"
      ##print "Result = "+str(result)
      if not prog:
        # Found a message outside the context of a program
        ##print "Adding keytext as a fragment"
        prog = log.newfragment()
        log.set_fragment_start(linecount)
      keytext = prog.addkeytext(result["name"], \
                                result["junk_text"], \
                                result["message"])
      log.addkeytext(keytext)
      buff.clear()
      tablebuff.clear()
      continue
    # CCP4i header
    result = regex.isccp4iheader(bufftext)
    if result:
      ##print "Found CCP4i header"
      ##print "Result = "+str(result)
      log.append_ccp4i_header(result)
      buff.clear()
      continue
    # CCP4i tail
    result = regex.isccp4itail(bufftext)
    if result:
      ##print "Found CCP4i tail"
      ##print "Result = "+str(result)
      log.append_ccp4i_tail(result)
      buff.clear()
      tablebuff.clear()
      continue
    # CCP4i information
    result = regex.isccp4i_information(bufftext)
    if result:
      ##print "Found CCP4i information"
      ##print "Result = "+str(result)
      # Make a new fragment - these messages shouldn't
      # appear inside the context of another program
      prog = log.addccp4i_info()
      prog.set_attributes_from_dictionary(result)
      log.set_fragment_start(linecount)
      log.set_fragment_end(linecount)
      # Clear the current context
      prog = False
      buff.clear()
      tablebuff.clear()
      continue
  # Ensure that the endline of the last fragment
  # is assigned
  log.set_fragment_end(linecount)
  # Close the file
  f.close()
  return log

#
# summarise
#
# Produce a summary of the data in a logfile object
#
def summarise(thislog):
  """Summarise the content of a logfile object.

  This function takes a logfile object as input and writes a
  a summary of the contents (fragments, programs, tables, messages
  and so on) to stdout."""

  # Logfile name
  print "Summary for "+thislog.filename()+"\n"
  # Was it from CCP4i?
  if thislog.isccp4i():
    print "This is a CCP4i logfile\n"
  # Number of programs or pseudo-programs
  print str(thislog.nfragments())+" logfile fragments\n"
  print "Fragments:"
  for i in range(0,thislog.nfragments()):
    fragment = thislog.fragment(i)
    if fragment.isprogram():
      if fragment.has_attribute("name"):
        print "\tProgram: "+str(fragment.name)
      else:
        print "\tProgram: <no name>"
    else:
      if fragment.isccp4i_info():
        print "\tCCP4i info"
      elif fragment.isfragment():
        print "\tFragment"
      if fragment.ntables():
        print "\t\t"+str(fragment.ntables())+" tables"
      if fragment.nkeytexts():
        print "\t\t"+str(fragment.nkeytexts())+" keytexts"

  print ""
  # Summarise program logfile fragments
  if thislog.nprograms() > 0:
    print str(thislog.nprograms())+" program logfiles\n"
    print "Programs:"
    for i in range(0,thislog.nprograms()):
      prog = thislog.program(i)
      # Is it a CCP4 program?
      if prog.isccp4():
        # Print name, version (and CCP4 version)
        print "\t"+prog.name+ \
              "\tv"+prog.version+ \
              "\t(CCP4 "+prog.ccp4version+")"
      else:
        # Print name and version
        if prog.has_attribute("name") and prog.has_attribute("version"):
          print "\t"+prog.name+"\t"+prog.version
        else:
          print "\t<No name and/or version>"
      if prog.termination():
        print "\tTerminated with: "+prog.termination_message
      else:
        print "\tNo termination message found"
      # Keytexts
      if prog.nkeytexts():
        print "\n\t\tKeytext messages:"
        for j in range(0,prog.nkeytexts()):
          print "\t\t"+str(prog.keytext(j).name())+ \
                ": \""+str(prog.keytext(j).message())+"\""
      # Tables
      if prog.ntables():
        print "\n\t\tTables:"
        for table in prog.tables():
          print "\t\tTable: \""+table.title()+"\""
      print ""
  else:
    print "No program logfiles found"
  print ""
  # Total set of CCP4i information messages in the file
  print "CCP4i messages in file:"
  if thislog.nccp4i_info():
    for i in range(0,thislog.nccp4i_info()):
      print "\tCCP4i info: \""+thislog.ccp4i_info(i).message+"\""
  else:
    print "\tNo messages found"
  print ""
  # Total set of tables in the file
  print "Tables in file:"
  if thislog.ntables():
    for table in thislog.tables():
      print "\tTable: \""+table.title()+"\" ("+str(table.nrows())+" rows)"
  else:
    print "\tNo tables found"
  print ""
  # Total set of keytexts in the file
  print "Keytext messages in file:"
  if thislog.nkeytexts():
    for i in range(0,thislog.nkeytexts()):
      print "\t"+str(thislog.keytext(i).name())+ \
            ": \""+thislog.keytext(i).message()+"\""
  else:
    print "\tNo keytext messages found"
  print ""

#######################################################################
# Utility Functions
#######################################################################

def copyfragment(fragment0,newobj):
  """Copy the data in a fragment to another object.

  The data in the source fragment 'fragment0' is copied to the
  target object 'newobj', and 'newobj' is returned. 'newobj'
  should be a fragment object or some subclass of fragment (such
  as a 'program' object).

  copyfragment can be used to 'mutate' a fragment into (for
  example) a program object."""

  # Copy attribute data
  for item in fragment0.attributes():
    newobj[item] = fragment0.get_attribute(item)
  # Copy tables
  for tbl in fragment0.tables():
    newobj.addtable(tbl)
  # Copy keytexts
  for i in range(0,fragment0.nkeytexts()):
    keytext = fragment0.keytext(i)
    newobj.addkeytext(keytext.name(),
                      keytext.junk_text(),
                      keytext.message())
  # Try to copy other attributes that fragment subclasses
  # have (such as keywords)
  try:
    for line in fragment0.keywords():
      newobj.addkeyword(line)
  except AttributeError:
    # Either the source or target doesn't support
    # keyword storage
    pass
  # Return the populated object
  return newobj

def offsetline(linen,pattern_result):
  """Return the line number offset by the size of a matched pattern.

  This is an internal utility function.

  Given 'linen' (the current line number) and 'pattern_result'
  (a dictionary containing data items returned from one of the
  regular expression functions), this function returns a line
  number which is offset to the start of the regular expression.
  It does this by locating a dictionary key 'nlines', which
  gives the size of the regular expression match."""

  if "nlines" in pattern_result:
    nlines = pattern_result["nlines"]
  else:
    nlines = 0
  new_linen = linen - nlines - 1
  if new_linen < 0:
    return 0
  else:
    return new_linen

def find_table_by_title(table_list,title_pattern,index=0):
  """Fetch a table object from a list by matching the title.

  This method is deprecated; use find_tables_by_title instead.

  This method looks up a particular table in a list
  of table objects (argument 'table_list'), by finding
  the first table in the list which matches the supplied
  regular expression 'title_pattern'.

  If there is more than one matching table then the 'index'
  argument specifies which of the list of matching tables
  should be returned. If index is out of range (or there are
  no matching tables) then return 'None'."""

  rtable_list = find_tables_by_title(table_list,title_pattern)
  try:
    return rtable_list[index]
  except:
    return None

def find_tables_by_title(table_list,title_pattern):
  """Return a list of tables by matching the title.

  This method returns a list of table objects containing
  all the tables in the supplied list 'table_list' for
  which the regular expression 'title_pattern' matches
  the table title.

  If no pattern is given then a list with all the table
  objects will be returned.

  A list is always returned, so in cases where there
  are no matches an empty list is returned, and if there
  is just one match then a list with a single item is
  returned."""

  rtitle = re.compile(title_pattern)
  rtable_list=[]
  for table in table_list:
    if rtitle.match(table.title()): rtable_list.append(table)
  return rtable_list

def escape_xml_characters(data):
  """Return copy of string with XML special characters escaped.

  This replaces the characters <, > and & with the XML escape
  sequences &lt;, &gt; and &amp;. It also replaces double
  quotes with &quot;.

  This could be replaced in future by the
  'xml.sax.saxutils.escape' function."""
  return str(data).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def strip_logfile_html(text):
  """Strip out HTML tags from logfile text.

  Return copy of input 'text' with HTML tags removed
  and any HTML special characters escaped.

  Note that this is specialised for CCP4 logfiles,
  in particular CCP4-formatted logfiles will be
  extracted from <param name='table' ...> tags."""
  out_text = ""
  buff = ""
  start_tag = ""
  end_tag = ""
  context = "none"
  for i in range(len(text)):
    c = text[i]
    #print "c = "+str(c)+" context = "+str(context)
    if c == "<":
      if context == "none":
        # Possible start of a tag, depending on
        # next character
        context = "putative_tag"
        buff = c
      else:
        # Everything up to this needs to
        # be dumped directly to output
        out_text = out_text + escape_xml_characters(buff)
    elif context == "putative_tag":
      buff = buff + c
      if c.isalpha():
        context = "start_tag"
      elif c == "/":
        context = "end_tag"
      elif c == "!":
        context = "comment_tag"
      else:
        # Not a tag so dump it
        context = "none"
        out_text = out_text + escape_xml_characters(buff)
    elif context == "start_tag" \
             or context == "end_tag" \
             or context == "comment_tag":
      buff = buff + c
      if c == ">":
        if context == "start_tag":
          # End of a start tag
          # Process it and see if we can
          # salvage something
          salvage_text = salvage_tag_data(buff)
          if salvage_text != "":
            out_text = out_text + escape_xml_characters(salvage_text)
          # Reset the buffer
          context = "none"
          buff = ""
        elif context == "end_tag":
          # End of an end tag
          # Throw this away (for now)
          context = "none"
          buff = ""
        elif context == "comment_tag":
          # End of a comment
          # Throw this away (for now)
          context = "none"
          buff = ""
    else:
      # Nothing special about this
      # Add to the output
      out_text = out_text + escape_xml_characters(c)
  # Finished - append the remaining buffer
  out_text = out_text + escape_xml_characters(buff)
  return remove_blank_lines(out_text)

def remove_blank_lines(text):
  """Remove duplicated blank lines from text.

  This function tries to remove extra blank lines from
  the supplied text, so that multiple blank lines are
  collapsed to just a single line."""
  out_text = ""
  blank = True
  for line in text.splitlines(True):
    if line.isspace():
      if not blank:
        blank = True
        out_text = out_text + line
    else:
      blank = False
      out_text = out_text + line
  return out_text

def process_start_tag(tag_text):
  """Process an arbitrary HTML start tag.

  Given the text of an arbitrary tag, this function returns
  a tuple consisting of two elements. The first element is
  the tag name, the second is a dictionary with keys
  corresponding to attributes found in the tag and the values
  of those keys corresponding to the attribute values."""
  tokens = tokenise(tag_text.strip("<>"))
  tag = tokens[0]
  attributes = {}
  if len(tokens) > 1:
    for token in tokens[1:]:
      try:
        i = token.index("=")
        key = token[0:i]
        value = token[i+1:].strip(" \"")
      except ValueError:
        key = token
        value = ""
      attributes[key] = value
  return (tag,attributes)

def salvage_tag_data(tag_text):
  """Extract data from a HTML tag.

  This function deals with extracting the useful data from
  certain HTML tags found in CCP4 logfiles.
  Currently it is set up to extract CCP4 table data from the
  'param' tags of JLogGraph applets.

  If no data could be salvaged then an empty string is
  returned."""
  data = process_start_tag(tag_text)
  tag = data[0]
  attributes = data[1]
  # Jloggraph applet data
  if tag == "param" and "name" in attributes:
    if attributes["name"] == "table" and "value" in attributes:
      return attributes["value"]
  # Spacegroup
  if tag_is_spacegroup(tag_text):
    return tag_text

  # Return an empty string by default
  return ""

def tag_is_spacegroup(text):
  """Check if a HTML tag looks like a spacegroup name.

  This does a very crude test to see whether the supplied
  string looks like a spacegroup name (rather than a random
  HTML tag)."""

  spacegroup = re.compile(r"<?[PABCIFHRpabcifhr] *[1-9][1-9]? *[1-9]?[1-9]? *[1-9]?[1-9]?>$")
  result = spacegroup.search(text)
  if result:
    return True
  else:
    return False

def retrieve(filen,start,end):
  """Retrieve a block of text from a file.

  Given the name of a file 'filen' and a pair of start and
  end line numbers, extract and return the text from the
  file.

  This uses the linecache module - beware of problems with
  consuming too much memory if the cache isn't cleared."""

  text = ""
  # Check for consistency and validity of lines
  if start < 0 and end < 0 or end < start:
    return ""
  # Fetch from a file if possible
  if os.path.isfile(filen):
    try:
      for i in range(start,end+1):
        text = text+str(linecache.getline(filen,i))
      return text
    except:
      print "Exception raised in retrieve method:"
      print "\tSource file  = \""+str(filen)+"\""
      print "\tStart line   = "+str(start)
      print "\tEnd line     = "+str(end)
      print "\tCurrent line = "+str(i)
      raise
  # Otherwise return nothing
  return ""

def tokenise(line):
  """Tokenise a string and return a list.

  Split a line of text into tokens separated by whitespace, but
  ignoring whitespace that appears within quotes.

  This attempts to do a similar to job the CCP4 'parser' (which is
  itself actually a tokeniser) in the core CCP4 libraries. The
  hard part is dealing with quoted strings which form a single
  token, and which can themselves also contain quotes."""

  sline = str(line)
  tokens = []
  token = False
  quote = False
  tquote = ""
  start = 0
  for i in range(len(sline)):
    c = sline[i]
    if token and not quote:
      if c == " " or c == "\t" or c == "\n":
        # end of current token
        tokens.append(sline[start:i])
        token = False
        quote = False
    if token and ( c == '"' or c == "'" ):
      # Detected a quote - flip the quote flag
      if quote:
        if c == tquote: quote = False
      else:
        quote = True
        tquote = c
    if not token:
      if c != " " and c != "\t" and c != "\n":
        # Start of a new token
        token = True
        start = i
        if c == '"' or c == "'":
          # Also it's quoted
          quote = True
          tquote = c

  # End of the loop
  if token:
    # End of the last token
    tokens.append(sline[start:len(sline)])
  return tokens

##############################################################
# Diagnostic methods used for testing and as examples
##############################################################

# List the TABLE tags in a file
def table_tags(filen):
  """Report occurances of '$TABLE' tags in a log file.

  This function is principally a diagnostic tool and is
  independent of the other classes and methods in this
  module. It takes the name of a log file as input,
  scans the file for occurances of the $TABLE tag, and
  reports this to stdout."""

  print "Scanning file "+str(filen)
  rtable = re.compile(r"\$TABLE *:")
  f = open(filen,"r")
  linecount = 0
  tablecount = 0
  tablelist = []
  for line in f:
    linecount = linecount + 1
    table = rtable.search(line)
    if table:
      tablecount = tablecount + 1
      print str(linecount)+": "+str(line.rstrip("\n"))
      tablelist.append(line.rstrip("\n"))
  f.close()
  print str(linecount)+" lines and "+str(tablecount)+" tables"
  return tablelist

# An example of making a new table from scratch
def table_example():
  """Demonstration function that creates and populates a table object.

  This function is for demonstration purposes only; it shows
  the basics of how to make and output a table. It creates
  a new table object, names it, populates some columns of data
  and then adds some graph definitions before outputting the
  formatted table to stdout."""

  print "\nExample making a new table from scratch:\n"
  # Make a new (empty) table object
  tbl = table("A table with random data")
  # Add three columns called "x", "x^2" and "1/x"
  tbl.addcolumn("x")
  tbl.addcolumn("x^2")
  tbl.addcolumn("1/x")
  # Add some rows of data
  for i in range(0,10):
    row = dict()
    row["x"] = i
    row["x^2"] = i*i
    if i != 0:
      row["1/x"] = 1.0/float(i)
    else:
      row["1/x"] = "?"
    tbl.add_data(row)
  # Define some graphs
  tbl.definegraph("Y = X(squared)",("x","x^2"))
  tbl.definegraph("Y = 1/X",("x","1/x"))
  tbl.definegraph("All data",("x","x^2","1/x"))
  # Print out the data as a simple "table" and in loggraph markup
  print tbl.show()
  print tbl.loggraph()

if __name__ == "__main__":
  """Usage example and demonstration for smartie.

  Run the main program using:

  python smartie.py file1 [file2 [...] ]

  For each file this example will generate a logfile object
  and then use the logfile 'summarise' method to print out
  a summary of the file's contents."""

  print "Running test on logparser code"
  # Get the command line args
  print "command line: "+str(sys.argv)
  if len(sys.argv) == 1:
    print "Usage: smartie.py file1 [file2 [...] ]"
    sys.exit(0)
  # Cycle over files and process
  for filen in sys.argv[1:]:
    print "**** Parsing file \""+filen+"\""
    start_time = time.clock()
    log = parselog(filen)
    end_time = time.clock()
    # Use the summarise function
    summarise(log)
    print "\nTime: "+str(end_time-start_time)+"\n"

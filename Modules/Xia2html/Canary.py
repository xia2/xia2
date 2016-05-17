#     Canary.py: HTML document generation
#     Copyright (C) Diamond 2009 Peter Briggs
#
########################################################################
#
# Canary.py
#
########################################################################

"""Canary: classes and functions for building HTML documents.

Canary provides classes and functions that can be used build HTML
documents programmatically.

Documents can be created by instantiating Document objects, and content
such as sections, lists and paragraphs etc are added using the
appropriate methods to fetch back objects that represent each of these
types of content (Section, List etc).

Similarly Section objects can also have Sections, Lists and so on added
to them in a similar fashion."""

__cvs_id__ = "$Id$"
__version__ = "0.0.3"

#######################################################################
# Import modules that this module depends on
#######################################################################
import os
import smartie

#######################################################################
# Module constants
#######################################################################

# Constants for automagic formatting
NO_FORMATTING=0
PRESERVE_NEWLINES=1

# Constants for inlining or linking to external files e.g. CSS
LINK=0
INLINE=1

#######################################################################
# Class definitions
#######################################################################

class DocElement:
  """Generic document element

  The DocElement is a generic part of a document, and is not really
  intended to be used directly but instead should be subclassed
  to create more elements (for example Sections).

  Note: subclasses of DocElement should provide a 'renderContent'
  method to generate their specific HTML code by the DocElement
  'render' method, and should avoid overriding the 'render'
  method."""

  def __init__(self,parent_doc=None):
    """Instantiate new DocElement

    'parent_doc' should be a Document object, however it could
    in principle be any object which implements the getUniqueId
    method."""
    # Basic class properties
    # Parent document
    self.__parent = parent_doc
    self.__classes = ''
    if self.__parent:
      self.__doc_id = self.__parent.getUniqueId()
    else:
      self.__doc_id = ''

  def getDocId(self):
    """Return the unique id for the DocElement

    This is a unique id string obtained from the parent document.
    Typically this method is only called when overriding the
    id method in a subclass."""
    return self.__doc_id

  def id(self):
    """Return the DocElement's name for itself

    This is a placeholder method which returns the unique
    id given to the DocElement by the parent Document (which
    is typically just an integer).

    Subclasses of the DocElement class can override this
    method to embelish the document id and make it more
    meaningful - for example by prepending it with a string
    indicating the type of element that the subclass
    represents.

    The id returned by this method is written to the 'id'
    attribute of the DocElement's <div> wrapper."""
    return self.getDocId()

  def parent(self):
    """Return the DocElement's parent document"""
    return self.__parent

  def addCSSClass(self,css_class):
    """Add a CSS class to the DocElement

    This defines a CSS class string to be added to the
    'class' attribute of the DocElement's <div> wrapper when it
    is rendered into HTML.

    Multiple CSS classes can be placed in the 'css_class'
    string by separating them with spaces."""
    if self.__classes: self.__classes += " "
    self.__classes += css_class

  def renderContent(self):
    """Placeholder method

    The renderContent method should be overridden by subclasses
    of the DocElement to return the actual HTML which represents
    the subclass's content."""
    return ''

  def render(self):
    """Return the HTML code for the DocElement

    The render method gets the actual content from the renderContent
    method, which should be implemented by any subclass to produce
    the appropriate HTML code.

    render will then wrap this content in a <div ...> </div> tag
    pair and return it to the calling subprogram."""
    # Get the specific content for the element
    content = self.renderContent()
    # Build the div wrapper
    open_div = "<div"
    if self.id(): open_div += " id='"+str(self.id())+"'"
    if self.__classes: open_div += " class='"+str(self.__classes)+"'"
    open_div += ">"
    close_div = "</div>\n"
    # Return the rendered element
    return open_div + content + close_div

class Section(DocElement):
  """Section object

  A Section is part of a Document, and can contain other
  Sections, Lists, Tables and paragraphs. These are added to
  the Section using the appropriate methods (addList, addTable,
  addSubsection, addPara). Arbitrary content can also be added
  via the addContent method.

  Sections may be created with or without a title string. Sections
  created with an empty title are referred to as 'anonymous'
  Sections.

  When the Section is rendered to HTML the content is generated
  in the order that it was added to the Section.

  A 'table of contents' can be added to the Section using the
  addTOC method. This will automatically create a list of links
  to the subsquent subsections in the Section.

  When rendered into HTML, the section will take the form

  <div id='...' class='...'>
  <hX>Title</hX>
  ...content...
  </div>

  The div id will be a unique name built from the title (if
  supplied) plus an id number acquired from the parent document.

  The div class will be 'section_<X>', where <X> is the level of
  the section (also used in the <h..> tags around the title, if
  a title was supplied).

  If no title was supplied then none will be written and the section
  will also be assigned a class of 'anonymous'.

  Typically Sections are created either via a call to the addSection
  method of the Document class, or a call to the addSubsection of
  another Section."""

  def __init__(self,title,level,parent_doc):
    """Initialise a new section.

    'title' is the title text for the section.
    'level' is the heading level corresponding to
    h1, h2 etc.
    'parent' is the parent Document object to
    which the Section belongs.

    See the renderContent() method for information on
    the HTML that is generated (including CSS classes
    etc)."""
    # Specific class properties
    self.__title = None
    if title is not None: self.__title = str(title)
    self.__subsections = []
    self.__content = []
    self.__level = level
    # Call the base class initialiser
    DocElement.__init__(self,parent_doc=parent_doc)
    # Set the classes
    self.addCSSClass('section_'+str(self.__level))
    if not self.__title: self.addCSSClass('anonymous')
    return

  def id(self):
    """Return the id for this section

    Overrides the base class 'id' method and returns the
    unique id that will be written to the id attribute of
    the section container.

    This id can be used to make HTML links to the section
    from elsewhere, and as a CSS selector."""
    # Base part of the id is a unique id from the parent
    id = "sect_"+str(self.getDocId())
    # Add some title text to make it more human-friendly
    if self.__title is not None:
      id += "-"+replace_special_characters(self.__title)
    return id

  def title(self):
    """Return the title for the section

    This the title string supplied on initialisation."""
    return self.__title

  def sections(self):
    """Return list of (sub)section objects

    This returns a list of the Section objects that are
    contained as subsections within the Section."""
    return self.__subsections

  def addList(self):
    """Add a new list to the section

    Creates and returns a new List object which is also
    added to the Section. See the List class for more
    information on how to add data to the List."""
    return self.addContent(List())

  def addTable(self,header=None):
    """Add a new table to the section

    Creates and returns a new Table object which is also
    added to the Section.

    'header' is an optional argument which should be a
    Python list or tuple, the elements of which will be
    assigned as column titles for the new table.

    See the Table class for more information on how to
    add data to the Table."""
    return self.addContent(Table(header=header))

  def addSubsection(self,title=None):
    """Add a subsection to the section

    Creates and returns a new Section object which is also
    added to the parent Section as a subsection."""
    new_section = Section(title,self.__level+1,self.parent())
    self.__subsections.append(new_section)
    return self.addContent(new_section)

  def addPara(self,text,css_class=None):
    """Add a paragraph to the section

    Create a new Para(graph) object populated with 'text',
    and add this to the Section. Optionally also associate a
    CSS class string with the Para(graph) - see the Para
    class for more information.

    Note that this method returns a reference to the parent
    Section and *not* to the Para object (which is different
    from other methods e.g. addList). This is to allow the
    idiom:

    sect.addPara('1st').addPara('2nd').addPara('3rd').addPara..

    whereby multiple paragraphs can be added in a single
    line of Python."""
    new_para = Para(str(text),css_class=css_class)
    self.__content.append(new_para)
    return self

  def addTOC(self):
    """Add an automatic table of contents

    Inserts an automatic table of contents (TOC) into the
    Section at the point where it is invoked.

    When rendered the table of contents will create a list
    linking to all subsections that occur after it in the
    Section."""
    new_toc = TOC(self)
    self.__content.append(new_toc)
    return self

  def addContent(self,content):
    """Add arbitrary content to the section

    'content' can be any object or string. If the object has a
    'render' method then that will be invoked to generate a
    representation of the content when the Section itself is
    rendered to HTML. Otherwise a string conversion will be
    attempted to get a string representation of the object."""
    self.__content.append(content)
    return content

  def renderTOC(self):
    """Generate table of contents entry

    This creates the HTML that should be added to a table of
    contents list - this will include a table of contents
    list for subsections in this section."""
    toc_html = "<a href='#"+self.id()+"'>"+self.title()+"</a>"
    if self.__subsections:
      subtoc = List()
      for sect in self.__subsections:
        subtoc.addItem(sect.renderTOC())
      toc_html += subtoc.render()
    return toc_html

  def renderContent(self):
    """Generate a HTML version of the section"""
    # Deal with the title
    if self.__title:
      open_tag = "<h"+str(self.__level)+">"
      close_tag = "</h"+str(self.__level)+">"
      contents = open_tag + self.__title + close_tag + "\n"
    else:
      contents = ''
    # Deal with the contents
    for content in self.__content:
      try:
        contents = contents + content.render()
      except AttributeError:
        # Assume no render method
        contents = contents + str(content)
    return contents

# Document
#
# A class that stores structured content which can then be rendered
# as HTML
#
class Document(Section):
  """Document object

  The Document object is an abstract representation of a document.

  It is a subclass of the Section class and so has all the same
  methods for adding content (such as Sections, Tables, Lists, tables
  of contents and Para(graph)s).

  An 'addSection' method is also provided as an alias for the
  'addSubsection' method inherited from the Section base class.

  In addition CSS stylesheets and script files can be associated
  with the Document via 'addStyle' and 'addScript' methods. A 'master
  table of contents' can be added to the document by invoking the
  'toc' method.

  HTML can be rendered from the Document object at any time by using
  one of the rendering methods. 'render' returns the document HTML,
  'renderFile' writes the HTML to a file. Rendering doesn't change
  or erase the Document content so it can further modified and
  rendered as required."""

  def __init__(self,title):
    """Initialise a new document object.

    'title' is the document title. Set to an empty string
    to create an untitled document."""
    # Class properties
    self.__styles = []
    self.__scripts = []
    self.__last_id = 0 # Automatically assigned numeric id
    self.__level = 1 # Internally stores the heading level
    self.__toc = False # Table of contents flag
    Section.__init__(self,title,1,self)
    return

  def addStyle(self,stylefile,inline=INLINE):
    """Add a stylesheet link to the document

    By default the stylesheet will be copied into an inline
    'style' declaration. Set the optional 'inline' parameter
    to LINK to make a link instead."""
    self.__styles.append(Stylesheet(stylefile,inline))
    return

  def addScript(self,scriptfile,inline=INLINE):
    """Add a script link to the document

    By default the script will be copied into an inline
    'script' declaration. Set the optional 'inline' parameter
    to LINK to make a link instead"""
    self.__scripts.append(Script(scriptfile,inline))
    return

  def toc(self,toc):
    """Set whether to display automatic table of contents

    By default a master table of contents is not displayed.
    Set 'toc' to True to turn on the table of contents, or
    to False to turn it off."""
    self.__toc = toc

  def addSection(self,title=None):
    """Add a section to the Document

    Creates and returns a new Section object which is also
    added to the Document.

    This is basically a wrapper to addSubsection from the
    base class."""
    return self.addSubsection(title)

  def getUniqueId(self):
    """Fetch a new unique id number

    This returns an integer which is unique within the
    Document, and thus can be used in element names to
    make them unique across the Document."""
    # Increment id number, store and return
    self.__last_id += 1
    return self.__last_id

  def render(self):
    """Generate a HTML version of the document

    Returns the HTML code representing the Document and its
    content."""
    HTML = HTML_components()
    contents = HTML.start(self.title(),self.__styles,self.__scripts)
    contents += Section.render(self)
    contents = contents + HTML.end()
    return contents

  def renderFile(self,filename):
    """Generate HTML file

    This writes the HTML for the document to a file called
    'filename'.

    If this file already exists then it will be overwritten."""
    html = open(filename,'w')
    html.write(self.render())
    html.close()
    return

class Para:
  """Paragraph object

  A paragraph is an arbitrary string of text. When the paragraph
  is rendered into HTML this text will be wrapped in <p>...</p>
  tags."""

  def __init__(self,content='',formatting=PRESERVE_NEWLINES,css_class=None):
    """Make a new paragraph

    'content' is any string of text.

    The optional 'formatting' flag can be used to specify how to
    treat newlines when generating the HTML with render:

    PRESERVE_NEWLINES : newlines are replaced by <br /> tags
    NO_FORMATTING     : no changes are made to newlines

    The optional 'css_class' flag can be used to specify CSS classes
    to associate with the paragraph."""
    self.__content = content
    self.__formatting = formatting
    self.__css_class = css_class
    return

  def render(self):
    """Generate a HTML version of the paragraph

    This converts HTML special characters in the string to their
    HTML entity codes (for example, & is turned into &amp;) and
    replaces newlines with <br /> (unless NO_FORMATTING was set).

    It then wraps it in <p>...</p> tags, with the class attribute
    set to any CSS classes that were specified on instantiation."""
    # Convert special characters
    content = smartie.escape_xml_characters(self.__content)
    content = self.__content
    # Deal with newlines
    if self.__formatting == PRESERVE_NEWLINES:
      content = content.rstrip("\n").replace("\n","<br />")
    if self.__css_class:
      return "<p class=\""+self.__css_class+"\">"+content+"</p>\n"
    else:
      return "<p>"+content+"</p>\n"

class List:
  """List object

  A List is one or more strings of text (don't confuse with
  Python lists) which form the items of an unordered HTML list
  when rendered.

  A new List may be created within a Document or Section using
  the addList method of the parent object, or it can be created
  on its own and then attached to the parent via the parent's
  addContent method.

  Once a List object has been created, items are added using the
  addItem method, e.g.:

  myList = List()
  myList.addItem('First item')

  It is also possible to add several items in a single call using
  the idiom:

  myList.addItem('Second').addItem('Third').addItem(...

  When rendered as HTML the items are written in the order that
  were added to the list."""

  def __init__(self):
    """Make a new List"""
    self.__items = []
    return

  def addItem(self,item):
    """Append an item to the list

    'item' is typically a string of text although it can be
    anything which can be converted to a string."""
    self.__items.append(item)
    return self

  def render(self):
    """Generate a HTML version of the list

    Returns an unordered HTML list with each of the items
    added via addItem converted to a string representation
    and wrapped in <li>...</li> tags."""
    contents = "<ul>\n"
    for item in self.__items:
      contents = contents + "<li>" + str(item) + "</li>\n"
    contents = contents + "</ul>\n"
    return contents

class Table(DocElement):
  """Table object

  A Table consists of one or more rows with columns of items.
  Items can be text, or any object that has a render method that
  can be used to generate a string representation when the
  table as a whole is rendered.

  Data can be added to a Table row-wise, column-wise, or via
  a combination of the two - though this last method needs some
  care in order to manage correctly.

  A new Table can be created as part of a Document or Section
  using the addTable method of the parent object, or it can be
  created on its own and then attached to the parent via the
  parent's addContent method.

  (The MakeMagicTable function also returns a Table that can be
  manipulated using Table methods.)

  Two simple examples:

  1. Create and populate a table row-wise:

  tbl = Table([None,'Column 1','Column 2'])
  tbl.addRow(['Row 1',1,2])
  tbl.addRow(['Row 2',3,4])
  tbl.render()

  This will render to:

  <div>
  <table>
  <tr><th>&nbsp;</th><th>Column 1</th><th>Column 2</th></tr>
  <tr><td>Row 1</td><td>1</td><td>2</td></tr>
  <tr><td>Row 2</td><td>3</td><td>4</td></tr>
  </table>
  </div>

  2. Create and populate the same table column-wise:

  tbl = Table()
  tbl.addColumn(['Row 1','Row 2'])
  tbl.addColumn([1,3],header='Column 1')
  tbl.addColumn([2,4],header='Column 2')
  tbl.render()

  Note that each time a row or column is added the Table object
  will perform automatic management of the table internals to
  keep the table rectangular: if a supplied row or column doesn't
  have enough items then it pads them with 'empty' items to make
  it wide/long enough; if the row or column has 'too many' items
  then the table is expanded and padded with 'empty' items to fit.

  Empty items are items containing None. At render time empty
  cells are merged into non-empty cells to their left.

  CSS classes can be added to the Table as a whole using the
  addClass method. Classes can also be added to individual rows
  in the table, but only when they are initially added. There is
  no way to add classes to columns.

  Note that CSS classes can be added to the <div> wrapper using the
  appropriate methods inherited from the DocElement base class."""

  def __init__(self,header=None):
    """Make a new table

    'header' is a list or other iterable object, the items
    of which will form the table column headers."""
    self.__header = []
    self.__classes = []
    self.__title = None
    self.__rows = []
    self.__row_classes = []
    # Populate the header row, if data was supplied
    if header:
      for item in header:
        self.__header.append(item)
    # Initialise base class
    DocElement.__init__(self)

  def __normalise(self):
    """Internal: normalise the table

    This method checks that all rows and columns are the
    same length i.e. that they contain the same number of
    items as the longest row/column in the table.

    If necessary items (set to None) are added, to 'pad' the
    table out."""
    # Check and if necessary extend each row
    ncolumns = self.nColumns()
    for row in self.__rows:
      while len(row) < ncolumns:
        # Pad the row
        row.append(None)
    # Check the header
    while len(self.__header) < ncolumns:
      # Pad the header
      self.__header.append(None)

  def hasEmptyHeader(self):
    """Check if the header of the table is empty"""
    for item in self.__header:
      # A single non-None (!) item indicates that
      # the header isn't empty
      if not item is None: return False
    # All items were None, so header is empty
    return True

  def nRows(self):
    """Get number of rows in the table"""
    return len(self.__rows)

  def nColumns(self):
    """Get the number of columns in the table

    Returns the length of the longest row in
    the table."""
    ncolumns = 0
    for row in self.__rows:
      if len(row) > ncolumns: ncolumns = len(row)
    return ncolumns

  def addTitle(self,title):
    """Set the title for the table

    The supplied string 'title' will be written to the
    table's 'title' attribute when the table is rendered."""
    self.__title = title

  def addClass(self,css_class):
    """Add a CSS class name to the table"""
    self.__classes.append(css_class)
    # Also add the class to the wrapper div
    self.addCSSClass(css_class)

  def addRow(self,data,css_classes=None):
    """Add a row to the table

    'data' is a list or other iterable object, the items
    of which will form the values of columns in the row.

    One or more CSS classes can be associated with the row
    via the optional 'css_classes' parameter. This should
    be a string, with multiple classes separated by spaces.
    The classes will be attached to the rendered HTML table
    row."""
    new_row = []
    for item in data:
      new_row.append(item)
    self.__rows.append(new_row)
    # CSS class associated with the row
    self.__row_classes.append(css_classes)
    # Normalise the table
    self.__normalise()

  def addColumn(self,data,header=None):
    """Add a column of data to the table

    'data' is a list or other iterable object, the items
    of which will form the values of rows in the column.

    Optionally 'header' defines the title of the column,
    which will be added to the header."""
    # Normalise the table before starting
    self.__normalise()
    # Add data items to each row - if we run out of
    # rows then make new ones
    for i in range(0,max(len(self.__rows),len(data))):
      try:
        self.__rows[i].append(data[i])
      except IndexError:
        if len(data) > len(self.__rows):
          # No row at this position - make new one
          # This will automatically be the same 'width'
          # as all previous rows, but populated with
          # 'None' items
          self.addRow([])
          if self.nRows() == 1:
            # Special case: this is the first
            # row in an empty table
            self.__rows[0].append(data[i])
          else:
            # Put the new data at the last position
            self.__rows[i][-1] = data[i]
        else:
          # Not enough data in the column
          self.__rows[i].append(None)
    self.__normalise()
    # Deal with the header
    self.__header[-1] = header

  def setHeader(self,header):
    """(Re)set the header for the table

    'header' is a list of the header items."""
    i = 0
    for item in header:
      if i < len(self.__header):
        self.__header[i] = item
      else:
        self.__header.append(item)
      i += 1
    self.__normalise()
    return

  def fetchHeader(self):
    """Fetch the header data"""
    return self.__header

  def fetchRow(self,key):
    """Fetch the data in a row

    Return a row as a list of items from the table,
    where the string 'key' matches the value in the
    first column.

    If there are multiple possible matches then only the
    first match will be returned.

    Raises a KeyError exception if no match is found."""
    for row in self.__rows:
      if str(row[0]).find(key):
        return row
    # Not found - raise an exception
    raise KeyError

  def fetchColumn(self,key):
    """Fetch the data in a column

    Return a column as a list of items. The column
    to be returned is identified by the 'key'
    matching the header for that column.

    If there are multiple possible matches then only the
    first match will be returned.

    Raises a KeyError exception if no match is found."""
    i = 0
    for item in self.__header:
      if not str(item).find(key):
        i += 1
      else:
        # Found the matching header
        column = []
        for row in self.__rows:
          column.append(row[i])
        return column
    # Didn't match the header
    raise KeyError

  def __renderRow(self,row,tag,classes=None):
    """Internal: render a single row of the table.

    Calling method must supply 'row' (list of data
    items forming the row) and 'tag' (HTML tag to
    enclose row elements with - typically either
    'td' or 'th').

    Optional argument 'classes' is a string of
    class names to attach to the row.

    This method will do automatic cell merging on
    the generated row, with empty cells merged into
    the first non-empty cell to the left

    Returns the HTML code for the row."""
    # Build a template for cell merging
    template = []
    last_nonempty_cell = 0
    for i in range(0,len(row)):
      if not row[i] is None:
        last_nonempty_cell = i
      template.append(last_nonempty_cell)
    # Deal with supplid CSS classes
    if classes:
      row_classes = " class='"+str(classes)+"'"
    else:
      row_classes = ''
    # Start building the row
    row_html = "<tr"+row_classes+">"
    for i in range(0,len(row)):
      # Colspan (number of columns this cell spans)
      colspan = template.count(i)
      if colspan > 0:
        item = row[i]
        if colspan > 1:
          colspan_attr = " colspan='"+str(colspan)+"' "
        else:
          colspan_attr = ''
        # Cell contents
        try:
          item_str = item.render()
        except AttributeError:
          # Assume item has no render method
          if item is None:
            item_str = ''
          else:
            item_str = str(item)
        row_html += "<"+tag+colspan_attr+">"+item_str+"</"+tag+">"
    # Close the row
    row_html += "</tr>\n"
    return row_html

  def renderContent(self):
    """Generate a HTML version of the table"""
    # Deal with CSS classes
    if self.__classes:
      class_attribute = " class='"+" ".join(self.__classes)+"' "
    else:
      class_attribute = ''
    # Deal with table title
    if self.__title:
      title_attribute = " title='"+str(self.__title)+"' "
    else:
      title_attribute = ''
    # Construct table tag
    contents = "<table"+class_attribute+title_attribute+">\n"
    # Build the table header
    if len(self.__header) and not self.hasEmptyHeader():
      contents += self.__renderRow(self.__header,'th')
    # Table contents
    i = 0 # Row counter
    for row in self.__rows:
      # Deal with CSS classes assigned to this row
      if self.__row_classes[i]:
        row_classes = " class='"+str(self.__row_classes[i])+"'"
      else:
        row_classes = ''
      contents += self.__renderRow(row,'td',self.__row_classes[i])
      i += 1
    contents += "</table>\n"
    return contents

class Anchor:
  """Create an 'anchor' to arbitrary content within a Document.

  The Anchor class provides a mechanism to create links to
  arbitrary content within a Document.

  To use when generating a Document, do e.g.
  doc = Document()
  ...
  # Create anchor
  a = Anchor(doc)
  ...
  # Associate anchor with some document content
  # Adds <a name='1' id='1'>Hello</a> to a paragraph
  doc.addPara(a.embed('Hello'))
  ...
  # Link to that content from elsewhere
  # Adds <a href='1'>See the greeting</a> to a paragraph
  doc.addPara(a.link('See the greeting'))
  ...

  Notes:

  1. Anchors don't need to be used when linking to document
  Sections; these have their own built-in anchoring mechanism.

  2. The 'embed' method should only be invoked once; otherwise
  the document will contain multiple anchors with the same
  name. Multiple links can be made from the same anchor."""

  def __init__(self,document,text=''):
    """Create a new Anchor object

    'document' is the parent Document object, 'text' is an
    (optional) string that will be combined with the id for
    the anchor."""
    # Fetch a unique id from parent document
    id = str(document.getUniqueId())
    # Append modified string, if supplied
    if text:
      id = replace_special_characters(text)+"-"+id
    self.__id = id

  def id(self):
    """Return the Anchor id"""
    return self.__id

  def embed(self,text=''):
    """Return the HTML code to embed the anchor in the document

    Returns the HTML code i.e. <a name=...>...</a> to embed
    the Anchor in a document.

    Optional argument 'text' specifies the text that will be
    inserted between the opening and closing tags."""
    return "<a name='"+self.id()+"' id='"+self.id()+"'>"+str(text)+"</a>"

  def link(self,text):
    """Return the HTML code to link to the anchor

    Wrapper for the MakeLink method: returns the HTML code
    to link to the Anchor code generated by 'embed', i.e.
    <a href=...>...</a>.

    'text' is text that will be inserted between the opening and
    closing tags."""
    return MakeLink(self,text)

class TOC:
  """Table of contents object

  Generates a list of links to each Section within the
  parent Section or Document.

  TOC objects are typically created and managed internally by the
  Document or Section objects that they belong to and so aren't
  created by an application."""

  def __init__(self,parent):
    """Create a new TOC object

    'parent' is the parent object (Section or Document)."""
    self.__parent = parent
    return

  def render(self):
    """Generate HTML for table of contents"""
    toc = List()
    for sect in self.__parent.sections():
      toc.addItem(sect.renderTOC())
    return toc.render()

class HTML_components:
  """HTML components object

  This class groups a set of utility functions for generating
  basic components for a HTML document, specifically the document
  head (returned by the 'start' method) and the document end
  (returned by the 'end' method).

  HTML_components is used by the Document class at render time
  to top and tail the HTML that is written out."""

  def start(self,title,styles=None,scripts=None):
    """Return the HTML document head

    The head is opening html tag, plus the full head
    declaration and the opening body tag.

    'title' is the document title (written into the <title> tags)

    'styles' is an optional list of Stylesheet objects which
    reference stylesheet files that will either be inlined or
    referenced from the document head.

    'scripts' is an optional list of Script objects which reference
    script files that will either be inlined or referenced from the
    document head."""
    if styles is None:
      styles = []
    if scripts is None:
      scripts = []
    header = "<html>\n<head>\n<title>" + str(title) + "</title>\n"
    for style in styles:
      header += style.render()
    for script in scripts:
      header += script.render()
    header += "</head>\n<body>"
    return header

  def end(self):
    """Return the HTML footer.

    Return the tags to close the HTML document started by the
    'start' method."""
    return "</body>\n</html>"

class ExternalFile:
  """External file reference

  Use this as a base class for referencing external files
  that can be linked or inlined within the document."""

  def __init__(self,filename,inline):
    """Initialise the ExternalFile object

    Subclasses should invoke this and then override the
    'inline_start' and 'inline_end' attributes (text that is
    printed before and after inline content) and the
    'link_format' attribute (a format string which should
    contain a %s placeholder into which the filename will
    be substituted when the link is rendered."""
    # These attributes are private
    self.__filename = filename
    self.__inline = inline
    # These can be altered by the subclass
    self.inline_start = '<!--' # Tag to print at start of inlining
    self.inline_end = '-->' # Tag to print at the end of inlining
    self.link_format = "<!-- %s -->" # Format string for links

  def render(self):
    """Generate inline or referencing text"""
    if self.__inline == LINK:
      # Write a link to the file
      return (self.link_format % self.__filename) + "\n"
    else:
      # Copy the file contents to an inline
      # stylesheet
      try:
        text = "<!-- Inline content from "+self.__filename+" -->\n"
        f = open(self.__filename,'r')
        text += self.inline_start+"\n"
        for line in f:
          text += line
        f.close()
        text += self.inline_end
      except:
        # Failed to get the stylesheet
        text = "<!-- Failed to inline external file "+ \
            self.__filename+"-->\n"
      return text

class Stylesheet(ExternalFile):
  """Stylesheet reference

  Subclasses the ExternalFile class to reference a CSS stylesheet
  file.

  Normally created and managed automatically by the Document class
  when a stylesheet is added via the Document.addStyle method."""

  def __init__(self,stylesheet,inline):
    """Create a new Stylesheet object

    'stylesheet' is the name of the stylesheet file.

    'inline' is a flag indicating where the file contents
    should be inlined at render time (inline=INLINE), or if a
    link should be written to the file instead (inline=LINK)."""
    ExternalFile.__init__(self,stylesheet,inline)
    # Modify base class attributes to set appropriate
    # tags for inline and referenced stylesheets
    self.inline_start = \
        '<style type="text/css">' + \
        '<!-- /* Hide the stylesheet from older browsers *"'
    self.inline_end = "-->\n</style>"
    self.link_format = \
        '<link rel="stylesheet" type="text/css" href="%s" />'

class Script(ExternalFile):
  """Script reference

  Subclasses the ExternalFile class to reference a script file.

  Normally created and managed automatically by the Document class
  when a stylesheet is added via the Document.addScript method."""

  def __init__(self,script,inline):
    """Create a new Script object

    'script' is the name of the script file.

    'inline' is a flag indicating where the file contents
    should be inlined at render time (inline=INLINE), or if a
    link should be written to the file instead (inline=LINK)."""
    # Modify base class attributes to set appropriate
    # tags for inline and referenced scripts
    ExternalFile.__init__(self,script,inline)
    self.inline_start = '<script>'
    self.inline_end = '</script>'
    self.link_format = '<script src="%s"></script>'

#######################################################################
# Module Functions
#######################################################################

def version():
  """Return the version of the Canary module"""
  return __version__

def replace_special_characters(text):
  """Replace special characters in a string

  Makes a copy of string 'text' with special characters (i.e.
  non-alphanumeric) replaced by underscores, and spaces replaced
  by hyphens.

  This is useful for generating strings to use in HTML documents."""
  ele = []
  for c in list(str(text).lower()):
    if c.isspace():
      ch = '-'
    elif not c.isalnum():
      ch = '_'
    else:
      ch = c
    ele.append(ch)
  return "".join(ele)

def MakeMagicTable(text,magic_separator='\t',ignore_empty=True):
  """Convert tabular plain text into a Table

  Optionally supply the 'magic_separator' (defaults to a tab)
  which separates the values on each row of the plain text
  table supplied to the class.

  By default if two or more delimiters are found side by side
  then they will be treated as a single delimiter - essentially
  this behaviour ignores the 'empty' data items that would
  otherwise be generated for each pair of contigious delimiters.
  To explicitly keep the empty data items, set the 'ignore_empty'
  flag to False.

  Returns a populated Table object."""
  # Split into lines, discarding any trailing newline
  # and build a Table object
  magic_table = Table()
  table = text.rstrip("\n").split("\n")
  for row in table:
    # Split into datum items, separated by the
    # magic delimiter
    data = []
    for datum in row.split(magic_separator):
      if ignore_empty:
        if datum == '': continue
      # Strip surrounding whitespace from item
      data.append(datum.strip(' '))
    # Add to the table
    magic_table.addRow(data)
  # Finished
  return magic_table

def MakeLink(resource,text=None,relative_link=False):
  """Build a <a href='...'>...</a> tag to link to a resource

  'resource' can be a URL or a string, or a Canary document
  element (typically a Section) which supplies an 'id()'
  method.

  'text' specifies the text for the link. If no text is supplied
  then the text defaults to the resource name or URL.

  Optional parameter 'link_type' specifies whether links should
  be left as they are or else where possible converted to
  relative links (relative to the current working directory).

  Basic usage examples:

  MakeLink('http://www.yoyodyne.com/')
  => <a href='http://www.yoyodyne.com/'>http://www.yoyodyne.com/</a>

  MakeLink('http://www.yoyodyne.com/','Yoyodyne homepage')
  => <a href='http://www.yoyodyne.com/'>Yoyodyne homepage</a>

  yoyodyne = doc.addSection("About Yoyodyne")
  MakeLink(yoyodyne,'Read more about Yoyodyne here')
  => <a href='#sect_1-about-yoyodyne'>Read more about Yoyodyne here</a>"""

  # Obtain the resource URL
  try:
    # Try to get the resource id
    url = '#'+str(resource.id())
  except AttributeError:
    # Doesn't have an id method
    url = str(resource)
  # Deal with relative links
  if relative_link:
    # Determine if URL is in or below the current directory
    # and convert if necessary
    pwd = os.getcwd()
    common_prefix = os.path.commonprefix([pwd,url])
    if url == pwd:
      # URL is the current working directory
      url = '.'
    elif common_prefix == pwd:
      # URL is relative to cwd - strip off cwd and return
      url = str(url).replace(common_prefix,'',1).lstrip(os.sep)
  # Obtain the link text
  link_text = None
  if not text:
    try:
      link_text = str(resource)
    except AttributError:
      # No str method support
      link_text = url
  else:
    link_text = str(text)
  # Build and return the link
  return "<a href='"+str(url)+"'>"+str(link_text)+"</a>"

def MakeImg(src,alt=None,title=None):
  """Build a <img... /> tag to link to an image

  'src' is the path to the image file.

  Optional parameters 'alt' and 'title' are used to populate
  alt and title attributes of the img tag, if provided."""
  img = "<img src='"+str(src)+"'"
  if alt:
    img += " alt='"+str(alt)+"'"
  if title:
    img += " title='"+str(title)+"'"
  img += " />"
  return img

#######################################################################
# Main program
#######################################################################

# Test script
# Now somewhat out of date
if __name__ == "__main__":
  """Test script"""
  d = Document("Test document")
  d.toc(True)

  intro = d.addSection("Introduction")
  intro.addPara("This is the intro")

  startup = d.addSection("Getting started")
  startup.addPara("Lots of info for getting started")
  prelim = startup.addSubsection("Preliminaries")
  prelim.addPara("What you need before you begin")
  config = startup.addSubsection("Configuration")
  config.addPara("How to make it do what you want")

  versions = d.addSection("Versions")
  versiontab = versions.addTable(("Version number","Notes"))
  versiontab.addRow(('0.3.0.5','First version I tried'))
  versiontab.addRow(('0.3.0.6','Second version made available'))

  bugs = d.addSection("Known bugs")
  bugs.addPara("We know that this will probably fail")
  buglist = bugs.addList()
  buglist.addItem("Memory leak").addItem("Floating divide by zero")

  print d.render()

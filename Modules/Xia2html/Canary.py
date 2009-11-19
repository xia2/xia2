#     Canary.py: HTML document generation
#     Copyright (C) Diamond 2009 Peter Briggs
#
########################################################################
#
# Canary.py
#
########################################################################
#
# Provide classes and functions for generating interactive HTML
# documents
#
__cvs_id__ = "$Id: Canary.py,v 1.2 2009/11/19 18:54:51 pjx Exp $"
__version__ = "0.0.2"

#######################################################################
# Import modules that this module depends on
#######################################################################
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

class Section:
    """Section object

    A section is part of a document. Sections can be contained
    within sections."""

    def __init__(self,title,level,parent):
        """Initialise a new section.

        'title' is the title text for the section.
        'level' is the heading level corresponding to
        h1, h2 etc.
        'parent' is the parent Document object to
        which the Section belongs."""
        # Class properties
        self.__title = str(title)
        self.__subsections = []
        self.__content = []
        self.__level = level
        # Parent document
        self.__parent = parent
        # Generate the unique HTML id
        self.__make_id()
        return

    def __make_id(self):
        """Internal: generate the id for this section"""
        # Base part of the id is a unique id from the parent
        ele = ["sect_",str(self.__parent.getUniqueId()),"-"]
        # Add some title text to make it more human-friendly
        # Substitute special characters with "-" and "_"
        text = ''
        for c in list(self.__title.lower()):
            if c.isspace():
                text += '-'
            elif not c.isalnum():
                text += '_'
            else:
                text += c
        # Make the id
        ele.append(text)
        self.__id = "".join(ele)

    def id(self):
        """Return the id for this section"""
        return self.__id

    def title(self):
        """Return the title for the section"""
        return self.__title

    def sections(self):
        """Return list of (sub)section objects"""
        return self.__subsections

    def addList(self):
        """Add a new list to the section"""
        return self.addContent(List())

    def addTable(self,header=None):
        """Add a new table to the section"""
        return self.addContent(Table(header=header))

    def addSubsection(self,title):
        """Add a subsection to the section."""
        new_section = Section(title,self.__level+1,self.__parent)
        self.__subsections.append(new_section)
        return self.addContent(new_section)

    def addPara(self,text):
        """Add a paragraph to the section"""
        new_para = Para(str(text))
        self.__content.append(new_para)
        return self

    def addTOC(self):
        """Add an automatic table of contents"""
        new_toc = TOC(self)
        self.__content.append(new_toc)
        return self

    def addContent(self,content):
        """Add content to the section

        'content' can be any object which has a render method that
        returns a string representation of that object."""
        self.__content.append(content)
        return content

    def renderTOC(self):
        """Generate table of contents entry

        This creates the HTML that should be added to a table of
        contents list - this will include a table of contents
        list for subsections in this section."""
        toc_html = "<a href='#"+self.id()+"'>"+self.title()+"</a>"
        if len(self.__subsections):
            subtoc = List()
            for sect in self.__subsections:
                subtoc.addItem(sect.renderTOC())
            toc_html += subtoc.render()
        return toc_html

    def render(self):
        """Generate a HTML version of the section"""
        open_tag = "<h"+str(self.__level)+"><a id='"+self.__id+"'></a>"
        close_tag = "</h"+str(self.__level)+">"
        contents = open_tag + self.__title + close_tag + "\n"
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

    It is a subclass of the Section class and is a specialised type
    of section.
    
    It is populated with content via its input methods, and an actual
    document can be generated using its rendering methods."""

    def __init__(self,title):
        """Initialise a new document object."""
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
        """Set whether to display automatic table of contents"""
        self.__toc = toc

    def addSection(self,title):
        """Add a section to the SDocument"""
        # Wrapper for addSubsection
        return self.addSubsection(title)

    def getUniqueId(self):
        """Fetch a new unique id number"""
        # Increment id number, store and return
        self.__last_id += 1
        return self.__last_id

    def render(self):
        """Generate a HTML version of the document"""
        HTML = HTML_components()
        contents = HTML.start(self.title(),self.__styles,self.__scripts)
        contents += Section.render(self)
        contents = contents + HTML.end()
        return contents

    def renderFile(self,filename):
        """Generate HTML file"""
        html = open(filename,'w')
        html.write(self.render())
        html.close()
        return
    
class Para:
    """Paragraph object

    A paragraph is an arbitrary string of text.

    The optional 'formatting' flag can be used to specify how to
    treat newlines when generating the HTML with render:

    PRESERVE_NEWLINES : newlines are replaced by <br /> tags
    NO_FORMATTING     : no changes are made to newlines"""

    def __init__(self,content='',formatting=PRESERVE_NEWLINES):
        """Make a new paragraph"""
        self.__content = content
        self.__formatting = formatting
        return

    def render(self):
        """Generate a HTML version of the paragraph"""
        # Convert special characters
        content = smartie.escape_xml_characters(self.__content)
        content = self.__content
        # Deal with newlines
        if self.__formatting == PRESERVE_NEWLINES:
            content = content.rstrip("\n").replace("\n","<br />")
        return "<p>"+content+"</p>\n"

class List:
    """List object

    A list is one or more strings of text. Don't confuse with
    Python lists."""

    def __init__(self):
        """Make a new list"""
        self.__items = []
        return

    def addItem(self,item):
        """Append an item to the list"""
        self.__items.append(item)
        return self

    def render(self):
        """Generate a HTML version of the list"""
        contents = "<ul>\n"
        for item in self.__items:
            contents = contents + "<li>" + str(item) + "</li>\n"
        contents = contents + "</ul>\n"
        return contents

class Table:
    """Table object

    A table is one or more rows with columns of items. Items
    can be text, or any object that has a render method that
    can be used to generate a string representation when the
    table as a whole is rendered.

    The Table object will perform automatic management of the
    table internals (for example padding rows or columns to
    keep the table rectangular, and merging empty header
    cells)."""

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
        first column."""
        for row in self.__rows:
            if str(row[0]).find(key):
                return row
        # Not found - raise an exception
        raise KeyError

    def fetchColumn(self,key):
        """Fetch the data in a column

        Return a column as a list of items. The column
        to be returned is identified by the 'key'
        matching the header for that column."""
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
                    if item == None:
                        item_str = ''
                    else:
                        item_str = str(item)
                row_html += "<"+tag+colspan_attr+">"+item_str+"</"+tag+">"
        # Close the row
        row_html += "</tr>\n"
        return row_html

    def render(self):
        """Generate a HTML version of the table"""
        # Deal with CSS classes
        if len(self.__classes):
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

class Link:
    """Link to another section in the document"""

    def __init__(self,text,section):
        """Build a HTML link to another section of the document
        
        'text' is the text that will appear as the wording for the
        link; 'section' is the section object that represents the
        section that the link should go to."""
        self.__text = text
        self.__resource = section

    def render(self):
        """Generate HTML code for the link"""
        # Get the name of the resource
        url = "#"+str(self.__resource.id())
        return "<a href='"+str(url)+"'>"+str(self.__text)+"</a>"

class TOC:
    """Table of contents object"""
    def __init__(self,parent):
        # Parent is the parent object
        self.__parent = parent
        return

    def render(self):
        """Generate HTML for table of contents"""
        toc = List()
        for sect in self.__parent.sections():
            toc.addItem(sect.renderTOC())
        return toc.render()

class HTML_components:
    """HTML components

    Page headers, footers etc"""
    def start(self,title,styles=[],scripts=[]):
        """Return a HTML header

        The header is opening html tag, plus the full head
        declaration and the opening body tag.

        'title' is the document title (written into the <title>)
        'styles' is a list of stylesheets and 'scripts' a list
        of script files (optional)."""
        header = "<html>\n<head>\n<title>" + str(title) + "</title>\n"
        for style in styles:
            header += style.render()
        for script in scripts:
            header += script.render()
        header += "</head>\n<body>"
        return header

    def end(self):
        """Return the HTML footer."""
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
    """Stylesheet reference"""
    
    def __init__(self,stylesheet,inline):
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
    """Script reference"""
    
    def __init__(self,script,inline):
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

    Returns a populated Table object"""
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
    
def MakeLink(text,url=None):
    """Build a <a href='...'>...</a> tag

    If 'url' is not supplied then the text and the url are
    assumed to be the same."""
    if url is None: url = text
    return "<a href='"+str(url)+"'>"+str(text)+"</a>"

#######################################################################
# Main program
#######################################################################

# Test script
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

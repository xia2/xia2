#     baubles.py: a smarter CCP4 logfile browser
#     Copyright (C) STFC 2007 Peter Briggs, Kevin Cowtan
#
#     This code is distributed under the terms and conditions of the
#     CCP4 licence agreement as `Part 1' (Annex 2) software.
#     A copy of the CCP4 licence can be obtained by writing to the
#     CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
#     NB: Modified from Baubles 0.0.8 by Peter Briggs Nov 2009
#
#     Changes:
#
#     1. Introduced global JAVALOGGRAPH_CODEBASE which overrides the
#        automatic codebase determination in javaloggraph.__init__()
#        Applications can set and get JAVALOGGRAPH_CODEBASE using the
#        setJLoggraphCodebase() and getJLoggraphCodebase() functions.
#
#     2. New function "baubles()" now generates the HTML output directly
#        from a populated smartie.logfile object.
#        The "baubles_html()" function wraps "baubles()" and should
#        behave as before i.e. accepting the name of an input logfile
#        and optionally an output html file.
#
#     3. Added the id "warnings" to the containing HTML div for
#        warning messages extracted from the log file, so that they
#        can be linked to using e.g. <a href="baubles.html#warnings">...
#
########################################################################
#
# baubles.py
#
##########################################################################
#
# Backend for a smarter logfile browser
# using smartie
#
import smartie
import sys
import os
import re
import time

__cvs_id__ = "$Id$"
__version__ = "0.0.8"
__diamond_version__ = "0.0.1"

############################################################
# Module globals
############################################################

JAVALOGGRAPH_CODEBASE = None # Default for Jloggraph codebase

############################################################
# HTML and Javascript generation functions
############################################################

def writeInlineStyle(html):
  """Write an inline stylesheet."""

  html.write("""<!-- Inline stylesheet -->
<style type="text/css"><!-- /* Hide the stylesheet from older browsers */
body { font-family: Verdana, Arial, sans-serif;
       font-size: 17px;
       background-color: white; }
h1 { background-color: gray; }
h2 { background-color: lightgray; }
.logfile { background-color: #fffddc; }
.ccp4i   { font-weight: bold; }
.banner  { background-color: lightgray;
           border-top-style: solid;
           border-bottom-style: solid;
           border-color: gray;
           border-width: 2px; }
.summary  { font-weight: bold;
            color: red;
            font-size: 90%;
            white-space: pre;
            background-color: #ffffc6;
            border-style: solid;
            border-width: 1px;
            border-color: orange; }
.non_summary { font-size: 80%; }
.result   { margin-left:5%; margin-right:5%; }
.references { font-size: 70%; }
.progname { font-size: 150%; font-weight: bold; }
.proginfo { font-size: 90%; font-style: italic; }
.progvers { font-size: 90%; font-style: italic; font-weight: bold; }
.progterm { font-size: 90%; font-style: italic; font-weight: bold; }
.doclink { font-size: 90%; position: absolute; right: 5%;}
.applet  { border-bottom: 1px solid gray; }
table,td,th { border-style: solid;
              border-width: 2px;
              border-spacing: 0;
              border-color: gray;
              padding: 1px;
              font-size: 90%; }
td,th { padding-left: 8px; padding-right: 8px; }
.loggraph_tables      { border-style: none;
                        background-color: #cfcdff; }
table.loggraph_tables { padding: 8px;
                        background-color: white; }
.inner_control > a { font-size: 70%;
                     background-color: white;
                     position: relative; bottom: 0px; left: 80%; }
-->
</style>
""")
  return

def writeJavascriptLibrary(html):
  """Write a block of Javascript code."""

  html.write("""<!-- Javascript functions to hide/display folder content -->
<script type="text/javascript">
<!--  to hide script contents from old browsers

// Pick loggraph
// Hides all loggraphs and then shows just the one of
// interest
function pick_loggraph(name,i,nloggraphs)
{
  hide_all_loggraphs(name,nloggraphs);
  show_loggraph(name,i);
}

// Function to display a loggraph associated with a log
function show_loggraph(name,i)
{
  var loggraph_name = name + "_loggraph_" + i;
  var loggraph_title = name + "_loggraph_title_" + i;
  showElement(loggraph_name);
  // Also make the title link bold
  var obj = document.getElementById(loggraph_title);
  obj.style.fontWeight = "bold";
}

// Function to hide a loggraph associated with a log
function hide_loggraph(name,i)
{
  var loggraph_name = name + "_loggraph_" + i;
  var loggraph_title = name + "_loggraph_title_" + i;
  hideElement(loggraph_name);
  // Also make the title link normal
  var obj = document.getElementById(loggraph_title);
  obj.style.fontWeight = "normal";
}

// Function to hide all loggraphs associated with a log
function hide_all_loggraphs(name,n)
{
  // Loop over all graphs up to n and hide each one
  for (var i=0; i<n; i++){
    hide_loggraph(name,i);
  }
}

// Function to open the complete log file from the
// hidden state
function open_full_logfile(name) {

  // Show the entire logfile
  var classname = name + "_logfile";
  setDisplayByClass(classname,"block");

  // Show the controls for toggling between
  // summary and complete views
  classname = name + "_logfile_open_controls";
  setDisplayByClass(classname,"block");

  // Hide the controls for accessing the logfile
  // when it's hidden
  classname = name + "_logfile_closed_controls";
  setDisplayByClass(classname,"none");

  // Show the full view
  show_full_logfile(name);
}

// Function to open the log file summary from the
// hidden state
function open_summary_logfile(name) {

  // Show the entire logfile
  var classname = name + "_logfile";
  setDisplayByClass(classname,"block");

  // Show the controls for toggling between
  // summary and complete views
  classname = name + "_logfile_open_controls";
  setDisplayByClass(classname,"block");

  // Hide the controls for accessing the logfile
  // when it's hidden
  classname = name + "_logfile_closed_controls";
  setDisplayByClass(classname,"none");

  // Show the summary view
  show_only_summary(name);
}

// Function to hide the complete log file
function close_logfile(name)
{
  // Hide the entire logfile
  var classname = name + "_logfile";
  setDisplayByClass(classname,"none");

  // Hide the controls for toggling between
  // summary and complete views
  classname = name + "_logfile_open_controls";
  setDisplayByClass(classname,"none");

  // Show the controls for accessing the logfile
  // when it's hidden
  classname = name + "_logfile_closed_controls";
  setDisplayByClass(classname,"block");
}

// Function to show only summary for a program log
function show_only_summary(name)
{
  // Hide everything that isn't a summary
  // i.e. all the elements that have belong to
  // classes ending with "_non_summary"
  var classname = name + "_non_summary";
  setDisplayByClass(classname,"none");

  // Now deal with control elements

  // Hide all controls that offer the option of
  // showing the summary only
  classname = name + "_show_summary_control";
  setDisplayByClass(classname,"none");

  // Show all controls that offer the option if
  // showing the full log file
  classname = name + "_show_full_logfile_control";
  setDisplayByClass(classname,"block");
}

// Function to show full version of a program log
function show_full_logfile(name)
{
  // Show all the associated elements that
  // have class ending with "_non_summary"
  var classname = name + "_non_summary";
  setDisplayByClass(classname,"block");

  // Now deal with control elements

  // Show all controls that offer the option of
  // showing the summary only
  classname = name + "_show_summary_control";
  setDisplayByClass(classname,"block");

  // Hide all controls that offer the option if
  // showing the full log file
  classname = name + "_show_full_logfile_control";
  setDisplayByClass(classname,"none");
}

// Open the view of a logfile fragment
function open_fragment(n)
{
 var closed_classname = "fragment_closed_" + n;
 setDisplayByClass(closed_classname,"none");
 var open_classname = "fragment_open_" + n;
 setDisplayByClass(open_classname,"block");
}

// Close the view of a logfile fragment
function close_fragment(n)
{
 var closed_classname = "fragment_open_" + n;
 setDisplayByClass(closed_classname,"none");
 var open_classname = "fragment_closed_" + n;
 setDisplayByClass(open_classname,"block");
}

// General function to reveal a specific element
// Specify the id of an element and its display
// style will be changed to "block"
function showElement(name)
{
  // This changes the display style to be "block"
  var obj = document.getElementById(name);
  obj.style.display = "block";
}

// General function to hide a specific element
// Specify the id of an element and its display
// style will be changed to "none"
function hideElement(name)
{
  // This changes the display style to be "none"
  var obj = document.getElementById(name);
  obj.style.display = "none";
}

// General function to set the display property for all elements
// with a specific class
// This is able to deal with elements that belong to multiple
// classes
function setDisplayByClass(classname,value)
{
  // Get all elements in the document
  var elements = document.getElementsByTagName("*");

  // For each element look for the "class" attribute
  for (var i = 0; i < elements.length; i++) {
      var node = elements.item(i);
      // First try to get the class attribute using 'class'
      // This seems to work on Firefox 2.* and 1.5
      var classes = node.getAttribute('class');
      if (classes == null) {
          // If the attribute is null then try using the
          // 'className' attribute instead
          // This works for IE7 and IE6
          classes = node.getAttribute('className');
      }
      if (classes != null) {
          classes = classes.split(" ");
          for (var k in classes) {
              if (classes[k] == classname) {
                  node.style.display = value;
              }
          }
      }
  }
}

// end hiding contents from old browsers  -->
</script>
""")
  return

def writeLoggraphFolder(html,program,n):
  """Write HTML and Javascript for a 'loggraph folder'."""

  ntables = program.ntables()
  if ntables == 0:
    # Nothing to do
    return
  name = identifyProgram(program).upper()+"_"+str(n)
  # Write out the start of the containing division and table
  html.write("<div id=\""+str(name)+"_loggraph_folder\" class=\"loggraphs\">\n\n")
  html.write("<table class=\"loggraph_tables\">\n<tr>\n")
  # Write the list of links for each loggraph
  html.write("<td class=\"loggraph_tables\">\n<div class=\"loggraph_tables\">\n")
  html.write("<p>The following tables were found in the logfile:</p>\n")
  fontWeight = "bold"
  for i in range(0,ntables):
    tbl = program.table(i)
    title = smartie.escape_xml_characters(tbl.title())
    html.write("<p id=\""+str(name)+"_loggraph_title_"+str(i)+"\" " \
               "style=\"font-weight:"+str(fontWeight)+"\">")
    html.write("<a href=\"javascript://\" onclick=\"pick_loggraph('" + \
               str(name)+"',"+str(i)+","+str(ntables)+")\">" + \
               str(title)+"</a></p>\n")
    fontWeight = "normal"
  html.write("</div>\n")
  html.write("</td>\n\n")
  # Write each of the jloggraph applets
  html.write("<td>\n<div class=\"loggraph_applets\">\n")
  style = "block"
  for i in range(0,ntables):
    tbl = program.table(i)
    title = smartie.escape_xml_characters(tbl.title())
    if not tbl.parse_error():
      if tbl.ngraphs() > 0:
        # Graphs are defined so display using some java viewer
        html.write("<div id=\""+str(name)+"_loggraph_"+str(i) + \
                   "\" style=\"display:"+str(style)+"\">\n")
        jloggraph = javaloggraph()
        html.write("<div class=applet><applet archive=\""+
                   jloggraph.archive()+
                   "\"\n")
        html.write("        code=\""+jloggraph.code()+"\"\n")
        html.write("        codebase=\""+jloggraph.codebase()+"\"\n")
        html.write("        width=\"500\"\n")
        html.write("        height=\"400\">\n")
        html.write("<param name=\"table\" value=\"\n")
        html.write(tbl.loggraph(pad_columns=False))
        html.write("\n\"><param name=\"list\" value=\"4\">\n")
        html.write("</applet></div>\n")
        html.write("<p><b>"+str(title)+"</b></p>\n")
        html.write("</div>\n")
      else:
        # No graphs - show the tabulated data
        html.write("<div id=\""+str(name)+"_loggraph_"+str(i) + \
                   "\" style=\"display:"+str(style)+"\">\n")
        html.write("<p><b>"+str(title)+"</b></p>\n")
        html.write(tbl.html())
        html.write("</div>\n")
    else:
      # There was a problem parsing this table
      # Write a little summary
      html.write("<div id=\""+str(name)+"_loggraph_"+str(i) + \
                 "\" style=\"display:"+str(style)+"\">\n")
      html.write("<p><b>Sorry, the graphs in this table cannot be ")
      html.write("displayed:</b></p>")
      html.write("<p>&quot;"+str(title)+"&quot;</p>")
      html.write("<p>baubles was unable to process the data in the table ")
      html.write("(possibly due to a formatting error in the columns)</p>")
      html.write("</div>\n")
    # Reset display style after first graph
    style = "none"
  # Close off the table element
  html.write("</div>\n")
  html.write("</td>\n\n")
  # Close off the containing table and division
  html.write("</tr>\n</table>\n")
  html.write("</div>\n")

def writeFragmentFolder(html,logfile,fragment,n):
  """Write HTML and Javascript for an arbitrary 'fragment folder'."""

  # Create the "visibility controls" at the start of the fragment
  # display
  html.write("\n<!-- Top-level visibility controls for fragment -->\n\n")
  html.write("<div class=\"fragment_closed_"+str(n)+"\">\n")
  html.write("   <!-- What is seen when fragment is completely hidden -->\n")
  html.write("   <p>\n")
  html.write("   <a href=\"javascript://\"\n")
  html.write("      onclick=\"open_fragment('"+str(n)+\
             "')\">[View fragment]</a>\n")
  html.write("   </p>\n")
  html.write("</div>\n\n")
  html.write("<div class=\"fragment_open_"+str(n)+"\" style=\"display: none\">\n")
  html.write("   <!-- What is seen when the fragment is visible -->\n")
  html.write("   <p>\n")
  html.write("      <a href=\"javascript://\"\n")
  html.write("         onclick=\"close_fragment('"+str(n)+\
             "')\">[Hide fragment]</a>\n")
  html.write("   </p>\n")

  # The fragment goes in here
  html.write("<div class=\"logfile\">\n\n")
  print "len(fragment)="+str(len(fragment))
  html.write("<p>Fragment with "+str(len(fragment))+" lines</p>\n")
  writeLogfileSummary(html,fragment.retrieve())
  html.write("</div>\n")

  # End the open fragment section
  html.write("</div>\n\n")

def writeAdvancedLogfileFolder(html,logfile,program,n):
  """Write HTML and Javascript for an advanced program 'logfile folder'."""

  # Start up
  name = identifyProgram(program).upper()+"_"+str(n)

  # Find start and end of the program log
  prog_beg = program.get_startline()
  prog_end = program.get_endline()
  logfilen = logfile.filename()
  curr_line = -1

  # Create the "visibility controls" at the start of the logfile
  # display
  html.write("\n<!-- Top-level visibility controls for "+str(name)+" -->\n\n")
  writeLogfileControls(html,name)

  # Start writing the folder
  html.write("<!-- Start of the "+str(name)+" logfile -->\n")
  html.write("<div class=\""+str(name)+"_logfile\" style=\"display: none\">\n\n")
  html.write("<div class=\"logfile\">\n\n")

  # Write the log file content as summaries interleaved with
  # non-summary blocks
  found_summary = False
  for i in range(0,logfile.nsummaries()):

    if found_summary:
      # Check whether the next summary block starts
      # inside the current program
      if logfile.summary(i).start() > prog_end:
        # Write the final non-summary chunk
        writeLogfileNonSummary( \
        html,name,smartie.retrieve(\
        logfilen,curr_line,prog_end))
        # This is the end of the log - exit the loop
        break

      # Fetch the block before the summary
      writeLogfileNonSummary( \
          html,name,smartie.retrieve(\
          logfilen,curr_line,logfile.summary(i).start()-1))
      # Fetch the summary itself
      writeLogfileSummary(html,logfile.summary(i).retrieve())
      # Update the current line
      curr_line = logfile.summary(i).end()+1

      # Test for stop condition in loop so we don't look
      # at every single summary
      if logfile.summary(i).start() <= prog_end and \
         logfile.summary(i).end() >= prog_end:
        # This was the last summary - exit the loop
        break

    if not found_summary and logfile.summary(i).start() > prog_end:
      # We have passed the end of the program
      # logfile without finding any summaries
      # Exit the loop
      break

    if not found_summary and logfile.summary(i).end() >= prog_beg:
      # This is the first summary that is part of
      # the log file fragment of interest
      found_summary = True
      # Was there any non-summary before the summary?
      if prog_beg < logfile.summary(i).start():
        # Write this section first
        writeLogfileNonSummary( \
        html,name,smartie.retrieve(\
        logfilen,prog_beg,logfile.summary(i).start()-1))
      # Fetch the summary itself
      writeLogfileSummary(html,logfile.summary(i).retrieve())
      # Initialise the current line
      curr_line = logfile.summary(i).end()+1

  # Check if there is some more (non-summary) logfile to write after the
  # last summary in the program log
  if found_summary and logfile.summary(i).end() < prog_end:
    writeLogfileNonSummary( \
            html,name,smartie.retrieve(\
            logfilen,logfile.summary(i).end()+1,prog_end))

  # If there were no summaries then just dump the log with no processing
  # Mark it as summary
  if not found_summary: writeLogfileSummary(html,program.retrieve())

  # Close off the folder
  html.write("\n</div>\n")

  # Generate another set of controls
  html.write("\n<!-- Tail-end visibility controls for "+str(name)+" -->\n\n")
  writeLogfileControls(html,name)

  # Close off completely
  html.write("</div>\n<!-- End of "+str(name)+" logfile -->\n\n")

def writeLogfileControls(html,name):
  """Generate a set of 'visibility controls' for a logfile folder."""

  html.write("<div class=\""+str(name)+"_logfile_closed_controls\">\n")
  html.write("   <!-- Controls available when logfile is completely hidden -->\n")
  html.write("   <p>\n")
  html.write("   <a href=\"javascript://\"\n")
  html.write("      onclick=\"open_summary_logfile('"+str(name)+\
             "')\">[Show logfile summary]</a>\n")
  html.write("   <a href=\"javascript://\"\n")
  html.write("      onclick=\"open_full_logfile('"+str(name)+\
             "')\">[Show full logfile]</a>\n")
  html.write("   </p>\n")
  html.write("</div>\n\n")
  html.write("    <div class=\""+str(name)+\
             "_logfile_open_controls\" style=\"display: none\">\n")
  html.write("   <!-- Controls available if some or all the logfile is visible -->\n")
  html.write("   <div class=\""+str(name)+\
             "_show_full_logfile_control\" style=\"display: none\">\n")
  html.write("      <p>Current view: summary only\n")
  html.write("      <a href=\"javascript://\"\n")
  html.write("         onclick=\"show_full_logfile('"+str(name)+\
             "')\">[Show full logfile]</a>\n")
  html.write("      <a href=\"javascript://\"\n")
  html.write("         onclick=\"close_logfile('"+str(name)+\
             "')\">[Hide logfile]</a>\n")
  html.write("     </p>\n")
  html.write("   </div>\n")
  html.write("   <div class=\""+str(name)+"_show_summary_control\">\n")
  html.write("      <p>Current view: full logfile\n")
  html.write("      <a href=\"javascript://\"\n")
  html.write("         onclick=\"show_only_summary('"+str(name)+\
             "')\">[Show logfile summary]</a>\n")
  html.write("      <a href=\"javascript://\"\n")
  html.write("         onclick=\"close_logfile('"+str(name)+\
             "')\">[Hide logfile]</a>\n")
  html.write("      </p>\n")
  html.write("   </div>\n")
  html.write("</div>\n\n")

def writeLogfileSummary(html,text):
  """Write a block of summary logfile text."""
  html.write("<div class=\"summary\"><pre>")
  html.write(smartie.strip_logfile_html(text))
  html.write("</pre></div>\n\n")
  #html.write("<div class=\"summary\">\n")
  #html.write(plainTextMarkup(text))
  #html.write("</div>\n\n")

def writeLogfileNonSummary(html,name,text):
  """Write a block of non-summary logfile text."""
  html.write("<div class=\""+str(name)+"_non_summary non_summary\"><pre>")
  html.write(smartie.strip_logfile_html(text))
  html.write("</pre>\n")
  html.write("  <!-- Add a control in the non-summary to flip back\n")
  html.write("     to the summary only -->\n")
  html.write("  <div class=\""+str(name)+\
             "_inner_control inner_control\">\n")
  html.write("     <a href=\"javascript://\" onclick=\"show_only_summary('"+
             str(name)+"')\">[Show summary only]</a>\n")
  html.write("  </div>\n")
  html.write("</div>\n\n")

def writeBanner(html,name,program,anchor):
  """Write a generic HTML banner for the program"""

  html.write("<div class=\"banner\">\n")
  if anchor != "":
    html.write("<a name=\""+str(anchor)+"\">\n")
  # Program name
  try:
    html.write("<span class=\"progname\">"+str(name)+"</span>\n")
  except AttributeError:
    pass
  # Version
  try:
    html.write("<span class=\"progvers\">Version "+str(program.version)+"</span>\n")
  except AttributeError:
    pass
  # Run time/date
  try:
    html.write("<span class=\"proginfo\">"+ \
               "Run at "+str(program.runtime)+" on "+str(program.rundate)+ \
               "</span>\n")
  except AttributeError:
    pass
  # Termination message
  try:
    html.write("<span class=\"progterm\">Finished with: "+ \
               str(program.termination_message)+ \
               "</span>\n")
  except AttributeError:
    pass
  if anchor != "":
    html.write("</a>\n")
  html.write("</div>\n")
  return

def writeDocumentationLink(html,program):
  """Write a link to the program documentation."""

  if "CHTML" in os.environ:
    name = identifyProgram(program).lower()+".html"
    docfile = os.path.join(os.environ["CHTML"],name)
    if os.path.isfile(docfile):
      html.write("<div class=\"doclink\"><p><a href=\""+ \
                 str(docfile)+ \
                 "\">[Documentation]</a></p></div>\n")
      return True
  return False

############################################################
# Secondary processing functions and classes
############################################################

# Java applet for loggraph viewing
class javaloggraph:
  """Encapsulate the acquisition of java loggraph."""

  def __init__(self):
    """Determine applet parameters.

    On instantiation, the javaloggraph object determines which
    java applet is available and sets applet parameters
    appropriately.

    These parameters can then be recovered using the 'code',
    'codebase' and 'archive' methods."""
    self.__codebase = getJLoggraphCodebase()
    self.__code = ""
    self.__archive = "JLogGraph.jar"

    # Determine what archive is available
    if self.__codebase is None:
      if "CBIN" in os.environ:
        # Local version of java
        self.__codebase = "file:"+os.sep*2+os.environ["CBIN"]
        if os.path.exists(os.path.join(os.environ["CBIN"],"JLogView.jar")):
          self.__archive = "JLogView.jar"
        elif os.path.exists(os.path.join(os.environ["CBIN"],"JLogGraph.jar")):
          self.__archive = "JLogGraph.jar"
      else:
        # No local version - use the web version instead
        self.__codebase = "http://www.ccp4.ac.uk/peter/java"

    # Set the 'code' parameter according to the archive name
    if self.__archive == "JLogGraph.jar":
      self.__code="JLogGraph.class"
    elif self.__archive == "JLogView.jar":
      self.__code="JLogView_.LGApplet.class"

  def setCodebase(self,codebase):
    """Explicitly set the codebase for the applet"""
    self.__codebase = codebase;

  def codebase(self):
    """Return the value of the codebase for the applet."""
    return self.__codebase

  def code(self):
    """Return the value of the code parameter for the applet."""
    return self.__code

  def archive(self):
    """Return the value of the archive parameter for the applet."""
    return self.__archive

# Extended pattern recognition
class extendedpatternmatch(smartie.patternmatch):
  """Extend the patternmatch class for secondary processing.

  This class extends the patternmatch class from smartie
  and adds new patterns to match with program-specific
  features. The idea is that these patterns can be used in
  a 'secondary processing step', in which additional data
  can be extracted for specific programs.

  This class adds new patterns:

  issfcheckbanner: check for SFCHECK program banner
  matthews_table:  extract tabulated data from Matthews_coef"""

  def __init__(self):
    smartie.patternmatch.__init__(self)

  def isrecognisedbanner(self,text):
    """Check text against a set of possible program banners."""

    # Try SFCHECK banner
    result = self.issfcheckbanner(text)
    if result:
      return result
    # Try LIBCHECK banner
    result = self.islibcheckbanner(text)
    if result:
      return result
    return result

  def issfcheckbanner(self,text):
    """Regular expression match to SFCHECK program banner.

    If the match fails then return False, otherwise return
    a dictionary with the following keys:

    name: will be 'SFCHECK'
    version: the program version."""
    #
    # SFCHECK banner looks like:
    #  Sol_
    #  Sol_ --- SFCHECK --- /Vers 7.1.01; 30.11.2005/
    #  Sol_   Memory:   10 Mb     N_atom_max:  40000
    #  Sol_
    #
    banner = self.compile("issfcheckbanner",r" Sol_\n Sol_ --- SFCHECK --- /Vers ([0-9.]+); ([0-9.]+)/\n").search(text)
    result = dict()
    if banner:
      result["banner_text"] = banner.group(0)
      result["name"] = "SFCHECK"
      result["version"] = banner.group(1)
    return result

  def islibcheckbanner(self,text):
    """Regular expression match to LIBCHECK program banner.

    If the match fails then return False, otherwise return
    a dictionary with the following keys:

    name: will be 'LIBCHECK'
    version: the program version."""
    #
    # LIBCHECK "banner" looks like:
    #   --- LIBCHECK --- /Vers 4.2.3   ; 28.07.2006/
    #
    banner = self.compile("islibcheckbanner",r"  --- LIBCHECK --- /Vers ([0-9.]+); ([0-9.]+)/\n").search(text)
    result = dict()
    if banner:
      result["banner_text"] = banner.group(0)
      result["name"] = "LIBCHECK"
      result["version"] = banner.group(1)
    return result

  def matthews_table(self,text):
    """Regular expression match to Matthews_coeff data.

    Attempts to match the tabulated values from the
    output of the Matthews_coeff program. If the match
    fails then returns False, otherwise returns a
    dictionary with the following keys:

    mol_weight: the estimated molecular weight
    table_head: a list of the column titles
    table_data: the raw tabulated data from the body of the
                table"""
    #
    # One form of the Matthews table looks like:
    #
    # For estimated molecular weight   12938.
    # Nmol/asym  Matthews Coeff  %solvent       P(tot)
    # ________________________________________________
    #   1         1.28             3.75         1.00
    # ________________________________________________
    # 123456789012345678901234567890123456789012345678
    #
    # The other form looks like:
    #
    # For estimated molecular weight    6600.
    # Nmol/asym  Matthews Coeff  %solvent       P(4.00)     P(tot)
    # _____________________________________________________________
    #   1         2.50            50.89         1.00         1.00
    #   2         1.25             1.79         0.00         0.00
    # _____________________________________________________________
    # 1234567890123456789012345678901234567890123456789012345678901
    #
    table = self.compile("matthews_table",r"For estimated molecular weight *([0-9.]+)\n(Nmol/asym) *(Matthews Coeff) *(%solvent) *(P\([0-9.]*\))? *(P\(tot\))\n_{48,61}\n([ 0-9.\n]*)\n_{48,61}").search(text)
    result = dict()
    if table:
      result["table_text"] = table.group(0)
      result["mol_weight"] = table.group(1)
      result["table_head"] = []
      for i in range(2,7):
        if table.group(i):
          result["table_head"].append(table.group(i))
      result["table_data"] = table.group(7)
    return result

  def phaser_module(self,text):
    """Regular expression match to identify 'Phaser module' data.

    Attempts to identify the 'Phaser module' and the associated
    version number from the Phaser log file. If the match
    fails then returns False, otherwise returns a
    dictionary with the following keys:

    phaser_module:         the name of the Phaser module
    phaser_module_version: the associated version number"""
    #
    # 1234567890123456789012345678901234567890123456789012345678901234567890123456789012345
    # *************************************************************************************
    # *** Phaser Module: PERMUTATIONS AND SPACEGROUPS                             1.3.2 ***
    # *************************************************************************************
    module = self.compile("phaser_module",r"\*{85,85}\n\*\*\* Phaser Module: ([^\*]*) \*\*\*\n\*{85,85}").search(text)
    result = dict()
    if module:
      result["module_text"] = module.group(0)
      # Break up the text into module name and version number
      result["phaser_module"] = " ".join(module.group(1).split()[0:-1])
      result["phaser_module_version"] = module.group(1).split()[-1]
    return result

def processUnknownProgram(program):
  """Perform additonal processing on an unknown program."""

  # Reacquire the text
  logtext = program.retrieve()
  # Set up objects for parsing
  bufsize = 10
  buff = smartie.buffer(bufsize)
  regex = extendedpatternmatch()
  # Loop over lines and look for other features
  for line in logtext.split("\n"):
    buff.append(line)
    bufftext = buff.tail(bufsize)
    result = regex.isrecognisedbanner(bufftext)
    if result:
      # Recognised the program
      # Set the newly discovered attributes and return
      program.set_attributes_from_dictionary(result)
      buff.clear()
      return

def processMatthews_Coef(program):
  """Perform additional processing on Matthews_Coef output.

  This extracts additional data items from the output of
  Matthews_coef, and sets up a table object with the
  tabulated data."""

  # Reacquire the text
  logtext = program.retrieve()
  # Set up objects for parsing
  bufsize = 20
  buff = smartie.buffer(bufsize)
  regex = extendedpatternmatch()
  # Loop over lines and look for specific features
  for line in logtext.split("\n"):
    buff.append(line)
    bufftext = buff.tail(bufsize)
    result = regex.matthews_table(bufftext)
    if result:
      # Collected the tabular data
      program.set_attributes_from_dictionary(result)
      # Turn this into a smartie table within the
      # program object
      table = program.addtable()
      table.settitle("Matthews_Coeff mol weight "+\
                     str(program.mol_weight))
      for name in program.table_head:
        table.addcolumn(name)
      # Once the columns are defined just send
      # the remaining table body directly to the
      # table object to populate it
      table.setdata(program.table_data)
      buff.clear()
      return

def processRefmac(program):
  """Perform additional processing on Refmac output."""

  try:
    # Summary of initial and final Rfactors
    tbl = program.tables("Rfactor analysis, stats vs cycle")[0]
    program.set_attribute("Ncycles",int(tbl.col("Ncyc")[-1]))
    program.set_attribute("Rfact_init",tbl.col("Rfact")[0])
    program.set_attribute("Rfact_final",tbl.col("Rfact")[-1])
    program.set_attribute("Rfree_init",tbl.col("Rfree")[0])
    program.set_attribute("Rfree_final",tbl.col("Rfree")[-1])
    program.set_attribute("rmsBOND_init",tbl.col("rmsBOND")[0])
    program.set_attribute("rmsBOND_final",tbl.col("rmsBOND")[-1])
    program.set_attribute("rmsCHIRAL_init",tbl.col("rmsCHIRAL")[0])
    program.set_attribute("rmsCHIRAL_final",tbl.col("rmsCHIRAL")[-1])
    # Looks like there was a change in the spelling of ANGL(E)
    # between versions once
    try:
      program.set_attribute("rmsANGLE_init",tbl.col("rmsANGLE")[0])
      program.set_attribute("rmsANGLE_final",tbl.col("rmsANGLE")[-1])
    except LookupError:
      program.set_attribute("rmsANGLE_init",tbl.col("rmsANGL")[0])
      program.set_attribute("rmsANGLE_final",tbl.col("rmsANGL")[-1])
    program.set_attribute("Result",True)
  except IndexError:
    # Probably couldn't find the table
    program.set_attribute("Result",False)
  return

def processPhaser(program):
  """Perform additional processing on Phaser output.

  This tries to acquire the 'Phaser module' name which describes
  the function that the run is performing e.g. 'Molecular
  Replacment Packing' or 'Permutations And Spacegroups'."""
  # Reacquire the text
  logtext = program.retrieve()
  # Set up objects for parsing
  bufsize = 3
  buff = smartie.buffer(bufsize)
  regex = extendedpatternmatch()
  # Loop over lines and look for specific features
  for line in logtext.split("\n"):
    buff.append(line)
    bufftext = buff.tail(bufsize)
    result = regex.phaser_module(bufftext)
    if result:
      # Identified the phaser_module
      program.set_attributes_from_dictionary(result)
      buff.clear()
      return

def identifyProgram(program):
  """Return a standard (generic) program name."""
  try:
    name = program.name
  except AttributeError:
    # No name was set for this program
    # Try to acquire the name from the termination
    # message
    try:
      name = program.termination_name
    except AttributeError:
      # No name found anywhere
      name = "unknown"
  if re.compile(r"^Refmac").match(name):
    name = "refmac5"
  if re.compile(r"^FFT(BIG)?").match(name):
    name = "fft"
  # Return name as a title
  return str(name).title()

def collectReferences(program):
  """Collect program references for citation"""
  result = []
  for i in range(0,program.nkeytexts()):
    keytext = program.keytext(i)
    if keytext.name().find("Reference") >= 0:
      result.append(str(keytext.message()))
  return result

def plainTextMarkup(text):
  """Turn plain text into HTML markup using expert recognition

  This function tries to recognise 'paragraphs' in plain text
  (a paragraph is a set of one or more lines of text which is
  separated from other paragraphs by one or more lines of
  whitespace).

  Paragraphs are then rendered in one of three ways dependent
  on the rules encoded in the plainTextMarkup function. These
  are:

  Paragraph: the text is wrapped in <p>...</p> tags to be
  displayed as a HTML paragraph.

  List: if a group of consecutive paragraphs start with a
  hyphen then those paragraphs will be gathered together into
  a bulleted list, with each paragraph being an item in the
  list.

  Table: 'magic' tables are generated from plain text based on
  the following rules:

  1) A data-field is a field, defined by a separator of at least
  two whitespaces, which contains either a numeric value, or
  '-' or '*'.

  2) A header-field is a field, defined by a separator of at
  least two whitespaces, which is not a data field.

  3) A data line is a line containing at least one trailing
  data-field. The data-count of a line is equal to the number of
  trailing data-fields.

  4) A header line is a line consisting of at least one data or
  header field, where at least the last field on the line is a
  header field.

  5) A table is a paragraph with more than one line, consisting
  of at most one header line followed by at least one data line,
  and where every data-line has the same data-count, and the
  total number of data fields is at least 2.

  6) Multiple consecutive tables with the same data-count are
  merged into a single table with a thin-separator between the
  paragraphs.
  """
  lines = smartie.escape_xml_characters(text).split("\n");
  # split into paragraphs
  paras = []
  para = []
  for line in lines:
    if line.strip() != "":
      para.append(line)
    else:
      if para:
        paras.append(para)
        para = []
  if para:
    paras.append(para)
  # identify paragraphs as tables and lists
  tablesep = re.compile( r'\s\s+' )
  istable = [False]*len(paras)
  islist = [False]*len(paras)
  plines = [0]*len(paras)
  fields = [0]*len(paras)
  for p in range(len(paras)):
    lines = paras[p]
    plines[p] = len(lines)
    nnum = 0
    nwrd = 0
    if len(lines) > 0:  # identify list elements
      words = lines[0].split()
      nwrd = len(words)
      if len(words) > 1:
        if words[0] == "-":
          islist[p] = True
    if len(lines) > 1:  # identify table elements
      nnums = []
      for line in lines:
        words = tablesep.split( line.strip() )
        nnum = 0
        for word in words:
          nnum += 1  # count trailing numbers or placeholders
          if word != "-" and word != "*":
            try:
              f = float(word)
            except:
              nnum = 0
        nnums.append(nnum)
      if nnum > 0:
        nrow = 0
        for n in nnums:
          if n == nnum:
            nrow += 1
        if nrow == len(lines):                      # unheaded table
          istable[p] = True
        if nrow == len(lines)-1 and nnums[0] == 0:  # headed table
          if nnum > 1 or nrow > 1:
            istable[p] = True
    if istable[p]:
      fields[p] = nnum
    else:
      fields[p] = nwrd

  # now print with markup
  result = ""
  intable = False
  inlist  = False
  for p in range(len(paras)):
    # close tags
    if   intable:
      if ( not istable[p] ) or ( fields[p] != fields[p-1] ):
        intable = False
        result += "</table>\n"
    if   inlist:
      if ( not islist[p] ):
        inlist = False
        result += "</ul>\n"
    # markup
    if   istable[p]:
      if not intable:
        result += "<table>\n"
      else:
        result += "<tr><td></td></tr>\n"
      intable = True
      for line in paras[p]:
        words = tablesep.split( line.strip() )
        heads = max( len(words)-fields[p], 0 )
        row = "<tr><th>"
        for w in range(0,heads):
          row += words[w] + " "
        row += "</th>"
        for w in range(heads,len(words)):
          try:
            f = float(words[w])
            row += "<td>"+words[w]+"</td>"
          except:
            row += "<th>"+words[w]+"</th>"
        row += "</tr>\n"
        result += row
    elif islist[p]:
      if not inlist:
        result += "<ul>\n"
      inlist = True
      result += "<li>"
      result += paras[p][0].strip()[1:] + "\n"
      for line in paras[p][1:]:
        result += line + "\n"
      result += "</li>\n"
    else:
      result += "<p>\n"
      for line in paras[p]:
        result += line + "<br />\n"
      result += "</p>\n"
  # close tags
  if intable: result += "</table>\n"
  if inlist:  result += "</ul>\n"
  return result

############################################################
# Summarising functions
############################################################

def summariseGeneric(html,program):
  """Generate a summary for a program object"""

  # collect warning a results messages for summary
  warnings = []
  result = None
  for i in range(0,program.nkeytexts()):
    keytext = program.keytext(i)
    if   keytext.name() == "Warning":
      warnings.append( str(keytext.message() ) )
    elif keytext.name() == "Result":
      result = str(keytext.message())
  if result is not None:
    html.write("<div class=\"keytext\">\n")
    html.write("<p><b>Result:</b><div class=result>\n")
    html.write(plainTextMarkup(result))
    html.write("</div></p>\n")
    html.write("</div>\n")
  if warnings:
    html.write("<div id=\"warnings\" class=\"keytext\">\n")
    html.write("<p>The following warnings were issued:</p>\n")
    html.write("<ul>\n")
    for warning in warnings:
      html.write("<li><span class=\"Warning\">"+
                 str(warning)+"</span></li>\n")
    html.write("</ul>")
    html.write("</div>\n")

def summariseMatthews_Coef(html,program):
  """Generate a summary for a Matthews_Coef program object"""

  if program.has_attribute("mol_weight"):
    html.write("<p>Molecular weight "+\
               str(program.mol_weight)+"</p>")

def summariseRefmac(html,program):
  """Generate a summary for a Refmac program object"""

  # Write a small table with initial and final Rfactors
  if ( program.Result ):
    html.write("<p><b>Summary:</b><div class=result>\n")
    html.write("<p><table border=2>\n")
    html.write("<tr><th>&nbsp;</th><th>Initial</th>")
    html.write("<th>After "+str(program.Ncycles)+" cycles</th></tr>\n")
    html.write("<tr><td><b>R factor</b></td>")
    html.write("<td>"+str(program.Rfact_init)+"</td>")
    html.write("<td>"+str(program.Rfact_final)+"</td></tr>\n")
    html.write("<tr><td><b>R<sub>free</sub></b></td>")
    html.write("<td>"+str(program.Rfree_init)+"</td>")
    html.write("<td>"+str(program.Rfree_final)+"</td></tr>\n")
    html.write("<tr><td><b>RMSD Bond Length</b></td>")
    html.write("<td>"+str(program.rmsBOND_init)+"</td>")
    html.write("<td>"+str(program.rmsBOND_final)+"</td></tr>\n")
    html.write("<tr><td><b>RMSD Bond Angle</b></td>")
    html.write("<td>"+str(program.rmsANGLE_init)+"</td>")
    html.write("<td>"+str(program.rmsANGLE_final)+"</td></tr>\n")
    html.write("<tr><td><b>RMSD Chiral Centre</b></td>")
    html.write("<td>"+str(program.rmsCHIRAL_init)+"</td>")
    html.write("<td>"+str(program.rmsCHIRAL_final)+"</td></tr>\n")
    html.write("</table></div></p>\n")
  # Write a list of warnings
  summariseGeneric(html,program)

def summarisePhaser(html,program):
  """Generate a summary for a Phaser program object"""

  # Write out the phaser module
  if program.has_attribute("phaser_module"):
    html.write("<p><b>Phaser module</b>: "+\
               str(program.phaser_module).title()+"</p>")
  # Write a list of warnings
  summariseGeneric(html,program)

############################################################
# Experimental conversion functions
############################################################

def polarrfn_plot(pltfile,imgbase=""):
  """Convert .plt output from Polarrfn to multiple gif images.

  Note that this function is still under development.

  Given a .plt output file from the Polarrfn program, this
  function attempts to generate a set of gif images from each
  frame of the plot.

  The operation of this function depends on the presence of
  the CCP4 'pltdev' program and the 'convert' program from
  the ImageMagick package.

  By default the gif images are created in the CCP4_SCR
  directory and have names that are derived from the plt file
  name with the number of the image appended and the
  extension '.gif' instead of '.plt'."""
  # Check for the pltdev program
  try:
    pltdev = os.path.join(os.environ["CBIN"],"pltdev")
  except KeyError:
    # Unable to get CBIN from the environment
    print "Unable to make path name for pltdev"
    return
  # Make a temporary ps file
  if not os.path.exists(pltfile):
    print str(pltfile)+": file not found"
    return
  try:
    psfile = os.path.join(os.environ["CCP4_SCR"], \
                          os.path.splitext(os.path.basename(pltfile))[0]+".ps")
    os.popen("pltdev -xp 0.7 -yp 0.7 -dev ps -o "+ \
             str(psfile)+" "+str(pltfile))
  except:
    # Unable to generate the name or run the program
    raise
  if not os.path.exists(psfile):
    print "Failed to make postscript file"
    return
  # Count the number of pages in the file
  npages = 0
  ps = open(psfile,"r")
  for line in ps:
    if line.count("%%Page:") > 0:
      npages = npages + 1
  ps.close()
  print "Number of pages (=frames): "+str(npages)
  # Loop over pages and use convert to turn them
  # into gifs
  for i in range(0,npages):
    frame = os.path.splitext(psfile)[0]+"_"+str(i)+".gif"
    cmd = "convert "+str(psfile)+"'["+str(i)+"]' "+str(frame)
    print "Processing frame "+str(i)+"... ("+str(frame)+")"
    os.popen(cmd)
  return

############################################################
# Core baubles functions
############################################################

def baubles_html(logfile,htmlfile=None):
  """Create an HTML summary of the logfile.

  logfile specifies the log file to process; htmlfile
  specifies the name of the file to write the HTML output
  to. If htmlfile is None then the HTML is written to
  stdout."""

  # Process the logfile
  log = smartie.parselog(logfile)
  # Generate the HTML
  baubles(log,htmlfile)
  return

def baubles(log,htmlfile=None):
  """Given a smartie logfile object, generate HTML summary

  'log' specifies a populated smartie logfile object; htmlfile
  specifies the name of the file to write the HTML output
  to. If htmlfile is None then the HTML is written to
  stdout."""

  # Open the file
  if htmlfile:
    html = open(htmlfile,"w")
  else:
    import sys
    html = sys.stdout

  # Write a header
  html.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
  "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>\n""")
  jloggraph = javaloggraph()
  html.write("<!-- Baubles info\n")
  html.write("     Version "+str(__version__)+"\n")
  html.write("     Java loggraph:\n")
  html.write("          archive  = "+jloggraph.archive()+"\n")
  html.write("          codebase = "+jloggraph.codebase()+"\n")
  html.write("          code     = "+jloggraph.code()+"\n")
  html.write("-->\n")
  writeInlineStyle(html)
  writeJavascriptLibrary(html)
  logfilename = os.path.basename(log.filename())
  html.write("<title>baubles: "+str(logfilename)+"</title>\n")
  html.write("""</head>
<body>
<!-- Start of logfile -->\n""")
  html.write("<!-- baubles "+str(__cvs_id__)+" -->\n")
  html.write("<h1>"+str(logfilename)+"</h1>\n")

  # Write contents list, if there was more than one program
  if log.nprograms() > 1:
    html.write("<!-- Index linking to individual programs -->\n")
    html.write("<p>The logfile is composed of output "+
               "from the following programs:</p>\n")
    html.write("<ul>\n")
    for i in range(0,log.nfragments()):
      fragment = log.fragment(i)
      if fragment.isprogram():
        program = fragment
        name = identifyProgram(program)
        if name == "Unknown":
          processUnknownProgram(program)
          name = identifyProgram(program)
        if program.has_attribute("termination_message"):
          termination = "Finished with: "+ \
                        str(program.termination_message)
        else:
          termination = ""
        anchor = str(name)+"_"+str(i)
        html.write("<li><a href=\"#"+str(anchor)+"\">"+ \
                   str(name)+"</a> "+ \
                   "<span class=\"termination_message\">"+ \
                   str(termination)+"</span></li>\n")
    html.write("</ul>\n")

  # List of references
  refs = {}
  for i in range(0,log.nfragments()):
    fragment = log.fragment(i)
    if fragment.isprogram():
      program = fragment
      name = identifyProgram(program)
      progrefs = collectReferences(program)
      if progrefs:
        refs[name] = progrefs
  if refs:
    html.write("<!-- List of references for programs -->\n")
    html.write("<div class=\"references\">")
    html.write("Please consider citing the following papers:\n<ul>\n")
    for key,val in refs.iteritems():
      html.write("<li> "+key+"\n")
      html.write("<ul>\n")
      for ref in val:
        html.write("<li> "+ref+" </li>\n")
      html.write("</ul>\n")
    html.write("</ul>\n")
    html.write("</div>\n")

  # Contents of the logfile
  if log.nfragments() > 0:
    for i in range(0,log.nfragments()):
      fragment = log.fragment(i)
      if fragment.isprogram():
        program = fragment
        name = identifyProgram(program)
        anchor = str(name)+"_"+str(i)
        # Write a general banner
        writeBanner(html,name,program,anchor)
        # Output for specific programs
        if name == "Matthews_Coef":
          processMatthews_Coef(program)
          summariseMatthews_Coef(html,program)
        elif name == "Refmac5":
          processRefmac(program)
          summariseRefmac(html,program)
        elif name == "Phaser":
          processPhaser(program)
          summarisePhaser(html,program)
        else:
          summariseGeneric(html,program)
        # Write the loggraphs
        writeLoggraphFolder(html,program,i)
        # Link to program documentation
        writeDocumentationLink(html,program)
        # Generate the folder for the raw logfile
        writeAdvancedLogfileFolder(html,log,program,i)
      elif fragment.isccp4i_info():
        ccp4i_info = fragment
        html.write("<p><span class=\"ccp4i\">CCP4i:</span> <em>"+\
                   str(ccp4i_info.message)+\
                   "</em></p>\n")
      elif fragment.ntables() > 0:
        # An arbitrary fragment with tables
        # Write the loggraphs
        writeLoggraphFolder(html,fragment,i)
      else:
        # An arbitrary fragment with no tables
        writeFragmentFolder(html,log,fragment,i)

  # Write a footer
  date = time.asctime()
  html.write("<hr />\n")
  html.write("<p><em>Generated for you by baubles "+str(__version__)+\
             " on "+str(date)+"</em></p>\n")
  html.write("</body>\n")
  html.write("</html>\n")

  # Close the file
  if html: html.close()
  return

# Configuration
def setJLoggraphCodebase(codebase):
  """Set the default value for the Java loggraph codebase

  This allows an application to override the value of the
  'codebase' parameter that is written to the output HTML
  for the Java loggraphs.

  The codebase tells the browser where to find the java
  applet or archive containing the JLoggraph code. If this
  is not set to an explicit value then it is determined
  automatically on initialisation of a 'javaloggraph' object.

  Set 'codebase' to None to return to the automatic
  defaults."""
  global JAVALOGGRAPH_CODEBASE
  JAVALOGGRAPH_CODEBASE = codebase
  return

def getJLoggraphCodebase():
  """Fetch the default value for the Java loggraph codebase

  Returns the setting of the default value of the 'codebase'
  parameter that is written to the output HTML for the Java
  loggraphs."""
  global JAVALOGGRAPH_CODEBASE
  return JAVALOGGRAPH_CODEBASE

############################################################
# Top level (baubles program)
############################################################

if __name__ == "__main__":

  # Set usage string
  usage = "baubles [options] <file>\n"+ \
          "Options:\n"+ \
          "-o <file>:      write HTML output to <file>\n" \
          "-summary:       print summaries from logfile\n"+ \
          "-polarrfn_plot: generate gifs from Polarrfn .plt file"

  # Needs at least one argument to run (i.e. name of a log file)
  if len(sys.argv) < 2:
    print "Usage: "+str(usage)
    sys.exit(0)
  # Assume that the logfile is the last argument
  logfile = sys.argv[-1]

  # Check the target file exists
  if not os.path.exists(logfile):
    print "File not found: \""+str(logfile)+"\""
    sys.exit(1)

  # Initialise
  htmlfile = None

  # Process the command line options
  i = 1
  nargs = len(sys.argv)-1
  while i < nargs:
    arg = str(sys.argv[i])
    if arg == "-o":
      # Output file name
      i=i+1
      htmlfile = str(sys.argv[i])
      print "Output file: "+str(htmlfile)
    elif arg == "-summary":
      # Write out a summary
      log = smartie.parselog(logfile)
      for i in range(0,log.nsummaries()):
        print str(smartie.strip_logfile_html(log.summary(i).retrieve()))
      sys.exit(0)
    elif arg == "-polarrfn_plot":
      # Assume that the input file is a
      # polarrfn plt file
      polarrfn_plot(logfile)
      sys.exit(0)
    else:
      # Unrecognised option
      print "Unrecognised option: "+str(arg)
      print "Usage: "+str(usage)
      sys.exit(1)
    # Next argument
    i=i+1

  # Don't knowingly overwrite the input file
  if htmlfile:
    if htmlfile == logfile:
      print "Input and output files are the same!"
      sys.exit(1)

  # Run baubles
  baubles_html(logfile,htmlfile)

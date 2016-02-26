# LIBTBX_SET_DISPATCHER_NAME dev.xia2.gui
from __future__ import division

#from rstbx.viewer import results_base, indexing, integration
from rstbx.viewer.frame import XrayFrame
from wxtbx import process_control, icons
import wxtbx.app
from wxtbx.phil_controls import path
from wxtbx.utils import LogViewer
import wx.lib.agw.flatnotebook
import wx
import wx.html
import wx.html2
import os
import sys

class ProcessingFrame (wx.Frame) :
  def __init__ (self, *args, **kwds) :
    wx.Frame.__init__(self, *args, **kwds)
    self.viewer = None
    self.toolbar = self.CreateToolBar(style=wx.TB_3DBUTTONS|wx.TB_TEXT)
    btn = self.toolbar.AddLabelTool(id=-1,
      label="Image viewer",
      bitmap=icons.hkl_file.GetBitmap(),
      shortHelp="Image viewer",
      kind=wx.ITEM_NORMAL)
    self.Bind(wx.EVT_MENU, self.OnLaunchViewer, btn)
    self.toolbar.Realize()
    self.statusbar = self.CreateStatusBar()
    self.sizer = wx.BoxSizer(wx.VERTICAL)
    self.SetSizer(self.sizer)
    self.nb = wx.lib.agw.flatnotebook.FlatNotebook(self)
    self.sizer.Add(self.nb, 1, wx.EXPAND)
    self.nb.SetMinSize((800,40))
    self.start_panel = StartPanel(self.nb)
    self.nb.AddPage(self.start_panel, "Setup")
    self.output_panel = LogViewer(self.nb)
    self.nb.AddPage(self.output_panel, "Output")
    try:
      self.html_panel = wx.html2.WebView.New(self.nb)
    except NotImplementedError:
      self.html_panel = wx.html.HtmlWindow(self.nb)
    self.nb.AddPage(self.html_panel, "Report")
    #self.indexing_panel = indexing.IndexingPanel(self.nb)
    #self.nb.AddPage(self.indexing_panel, "Indexing")
    #self.integration_panel = integration.IntegrationPanel(self.nb)
    #self.nb.AddPage(self.integration_panel, "Integration")
    self.SetSize((800,600))

    self.event_dispatcher = process_control.event_agent(
      window=self,
      project_id=0,
      job_id=0)

    self.was_aborted = False

  #def LoadResults (self, dir_name) :
    #self.result = results_base.result(dir_name)
    #self.indexing_panel.SetIndexingResults(self.result.get_indexing())
    #self.integration_panel.SetResults(self.result)
    #self.nb.SetSelection(1)

  def OnRunXia2 (self, evt) :

    #thread = WorkerThread(0, self)
    #thread.start()
    #return

    output_dir = self.start_panel.GetOutputDir()
    result = self.run_xia2(
      imagesets=self.start_panel.GetImagesets(),
      output_dir=output_dir)

  def run_xia2 (self, **kwds) :
    output_dir = kwds['output_dir']
    imagesets = kwds['imagesets']
    args = []
    for imageset in imagesets:
      scan = imageset.get_scan()
      first, last = scan.get_image_range()
      args.append('image=%s:%i:%i' %(imageset.paths()[0], first, last))
    kwds = {}

    self.nb.AdvanceSelection(forward=True)
    thread = xia2Thread(self, output_dir, args)
    thread.start()
    return

  def launch_viewer_frame (self) :
    if (self.viewer is None) :
      self.viewer = XrayFrame(
        parent=self,
        title="Image viewer")
      self.viewer.Show()
      self.Bind(wx.EVT_CLOSE, self.OnCloseViewer, self.viewer)

  def get_viewer_frame (self) :
    self.launch_viewer_frame()
    return self.viewer

  def set_viewer_frame (self, frame) :
    assert (self.viewer is None)
    self.viewer = frame

  def OnCloseViewer (self, evt) :
    self.viewer.Destroy()
    self.viewer = None

  def OnLaunchViewer (self, evt) :
    self.launch_viewer_frame()



  def callback_start (self, data) :
    self.event_dispatcher.callback_start(data)

  def callback_stdout (self, data) :
    self.output_panel.AppendText(data)
    self.event_dispatcher.callback_stdout(data)

  def callback_other (self, data) :
    print 'other'
    self.event_dispatcher.callback_other(data)

  def callback_abort (self) :
    self.event_dispatcher.callback_abort()
    self.close()

  def callback_final (self, result) :
    if self.was_aborted : # XXX hack for jobs killed with 'qdel'
      self.callback_abort()
      return
    import glob
    html_files = glob.glob(os.path.join(
      result.output_dir, 'LogFiles/*_report.html'))
    print html_files
    if len(html_files):
      html_file = html_files[0]
      try:
        # wx.html.HtmlWindow
        self.html_panel.LoadFile(html_file)
      except AttributeError:
        # wx.html2.WebView
        self.html_panel.LoadURL(html_file)
      self.nb.AdvanceSelection()
    self.event_dispatcher.callback_final(result)
    self.close()

  def callback_error (self, error, traceback_info) :
    self.event_dispatcher.callback_error(error, traceback_info)
    self.close()

  def callback_pause (self) :
    self.event_dispatcher.callback_pause()

  def callback_resume (self) :
    self.event_dispatcher.callback_resume()

  def close(self):
    pass

  def OnLogEvent(self, event):
    print event


from xia2.GUI import dataset
class StartPanel (wx.Panel, dataset.SelectDatasetPanelMixin) :
  def __init__ (self, *args, **kwds) :
    wx.Panel.__init__(self, *args, **kwds)
    szr = wx.BoxSizer(wx.VERTICAL)
    self.SetSizer(szr)
    box = wx.StaticBox(self, -1, "Indexing setup")
    bszr = wx.StaticBoxSizer(box, wx.VERTICAL)
    szr.Add(bszr, 1, wx.ALL|wx.EXPAND, 5)
    self.draw_dataset_controls(bszr, pick_frames=False)
    btn = wx.Button(self, -1, "Run...")
    szr.Add(btn, 0, wx.ALL, 10)
    frame = self.GetTopLevelParent()
    frame.Bind(wx.EVT_BUTTON, frame.OnRunXia2, btn)

  def add_controls_to_grid (self, sizer) :
    txt = wx.StaticText(self, -1, "Output directory:")
    self.output_ctrl = path.PathCtrl(
      parent=self,
      style=path.WXTBX_PHIL_PATH_DIRECTORY)
    self.output_ctrl.SetValue(os.getcwd())
    sizer.Add(txt, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    sizer.Add(self.output_ctrl, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

  def GetOutputDir (self) :
    return self.output_ctrl.GetPhilValue()


import threading
import random
class WorkerThread(threading.Thread):
  """
  This just simulates some long-running task that periodically sends
  a message to the GUI thread.
  """
  def __init__(self, threadNum, window):
    threading.Thread.__init__(self)
    self.threadNum = threadNum
    self.window = window
    self.timeToQuit = threading.Event()
    self.timeToQuit.clear()
    self.messageCount = random.randint(10,20)
    self.messageDelay = 0.1 + 2.0 * random.random()

  def stop(self):
    self.timeToQuit.set()

  def run(self):
    msg = "Thread %d iterating %d times with a delay of %1.4f\n" \
      % (self.threadNum, self.messageCount, self.messageDelay)
    wx.CallAfter(self.window.callback_stdout, msg)

    for i in range(1, self.messageCount+1):
      self.timeToQuit.wait(self.messageDelay)
      if self.timeToQuit.isSet():
        break
      msg = "Message %d from thread %d\n" % (i, self.threadNum)
      wx.CallAfter(self.window.callback_stdout, msg)
    else:
      wx.CallAfter(self.window.callback_final, self)

class RedirectText(object):
  def __init__(self,aWxTextCtrl):
    self.out=aWxTextCtrl

  def write(self,string):
    wx.CallAfter(self.out.WriteText, string)

  def flush(self):
    pass


class xia2Thread(threading.Thread):

  def __init__(self, window, output_dir, args):
    threading.Thread.__init__(self)
    self.window = window
    self.output_dir = output_dir
    self.args = args
    self.timeToQuit = threading.Event()
    self.timeToQuit.clear()

  def stop(self):
    self.timeToQuit.set()

  def run(self):

    redir = RedirectText(self.window.output_panel)
    sys.stdout = redir

    old_sys_argv = sys.argv
    sys.argv = ['xia2'] + self.args
    from xia2.command_line import xia2_main
    self.xinfo = xia2_main.run()
    sys.argv = old_sys_argv

    wx.CallAfter(self.window.callback_final, self)
    return


if (__name__ == "__main__") :
  app = wxtbx.app.CCTBXApp(0)
  frame = ProcessingFrame(None, -1, "xia2")
  frame.Show()
  if (len(sys.argv) > 1) and (os.path.isdir(sys.argv[1])) :
    frame.LoadResults(sys.argv[1])
  app.MainLoop()

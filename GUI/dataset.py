from __future__ import absolute_import, division

import wx
from libtbx.utils import Sorry
from wxtbx import app, icons, phil_controls
from wxtbx.phil_controls import ints, path

RSTBX_SELECT_IMAGE_IDS = 0

class SelectDatasetPanelMixin (object) :
  def draw_dataset_controls (self, sizer=None, pick_frames=True) :
    if (sizer is None) :
      sizer = self.GetSizer()
    szr2 = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(szr2, 0, wx.ALL, 5)
    szr3 = wx.BoxSizer(wx.HORIZONTAL)
    szr2.Add(szr3)
    bmp = wx.StaticBitmap(self, -1, icons.img_file.GetBitmap())
    szr3.Add(bmp, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    caption = "Please select a directory of images to process."
    if (pick_frames) :
      caption += "  If you wish you may specify which frames you want to "+ \
        "use; otherwise the program will attempt to pick sensible defaults."
    caption_txt = wx.StaticText(self, -1, caption)
    caption_txt.Wrap(500)
    szr3.Add(caption_txt, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    grid = wx.FlexGridSizer(cols=2)
    sizer.Add(grid, 0, wx.ALL)
    txt1 = wx.StaticText(self, -1, "Directory:")
    grid.Add(txt1, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    self.dir_ctrl = path.PathCtrl(
      parent=self,
      style=path.WXTBX_PHIL_PATH_DIRECTORY)
    grid.Add(self.dir_ctrl, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    self.Bind(phil_controls.EVT_PHIL_CONTROL, self.OnChooseDirectory,
      self.dir_ctrl)
    txt2 = wx.StaticText(self, -1, "Image set:")
    grid.Add(txt2, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    self.stack_ctrl = wx.ListBox(
      parent=self,
      size=(400,-1),
      style=wx.LB_MULTIPLE|wx.LB_HSCROLL)
    grid.Add(self.stack_ctrl, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    self.Bind(wx.EVT_LISTBOX, self.OnChooseDataset, self.stack_ctrl)
    if (pick_frames) :
      txt3 = wx.StaticText(self, -1, "Use frames:")
      grid.Add(txt3, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
      self.frame_ctrl = ints.IntsCtrl(
        parent=self,
        size=(400,-1))
      self.frame_ctrl.SetMin(1)
      grid.Add(self.frame_ctrl, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    else :
      self.frame_ctrl = None
    self.add_controls_to_grid(grid)

  def add_controls_to_grid (self, sizer) :
    """
    For subclasses which need to add aligned controls.
    """
    pass

  def GetImageset(self):
    if self._imagesets:
      i = self.stack_ctrl.GetSelections()
      frames = None
      if self.frame_ctrl is not None:
        frames = self.frame_ctrl.GetPhilValue()
      return self._imagesets[i], frames
    else:
      raise Sorry("No imageset selected!")

  def GetImagesets(self):
    return [self._imagesets[i] for i in self.stack_ctrl.GetSelections()]

  def OnChooseDirectory (self, event) :
    dir_name = self.dir_ctrl.GetPhilValue()
    if (dir_name is not None) :
      from dxtbx.datablock import DataBlockFactory
      datablocks = DataBlockFactory.from_filenames([dir_name])
      imagesets = datablocks[0].extract_imagesets()

      self._imagesets = imagesets

      #from iotbx.detectors import identify_dataset
      #self._datasets = identify_dataset(dir_name)
      #choices = [ d.format() for d in self._datasets ]
      choices = [imgset.get_template() for imgset in self._imagesets]
      self.stack_ctrl.SetItems(choices)
      for i in range(len(choices)):
        self.stack_ctrl.SetSelection(i)

  def OnChooseDataset (self, event) :
    print self.stack_ctrl.GetSelections()

class SelectDatasetDialog (wx.Dialog, SelectDatasetPanelMixin) :
  def __init__ (self, *args, **kwds) :
    self._datasets = []
    style = wx.CAPTION
    dlg_style = kwds.get("style", 0)
    kwds['style'] = style
    wx.Dialog.__init__(self, *args, **kwds)
    szr = wx.BoxSizer(wx.VERTICAL)
    self.SetSizer(szr)
    self.draw_dataset_controls(pick_frames=(dlg_style & RSTBX_SELECT_IMAGE_IDS))
    btn_sizer = wx.StdDialogButtonSizer()
    szr.Add(btn_sizer, 0, wx.ALL|wx.ALIGN_RIGHT, 10)
    cancel_btn = wx.Button(self, wx.ID_CANCEL)
    ok_btn = wx.Button(self, wx.ID_OK)
    btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 5)
    btn_sizer.Add(ok_btn)
    szr.Fit(self)

  def OnOkay (self, event) :
    pass

def select_imageset (parent=None,
                    title="Select a dataset",
                    pick_frames=False) :
  style = 0
  if (pick_frames) :
    style |= RSTBX_SELECT_IMAGE_IDS
  dlg = SelectDatasetDialog(
    parent=parent,
    title=title,
    style=style)
  if (dlg.ShowModal() == wx.ID_OK) :
    imagesets = dlg.GetImagesets()
  wx.CallAfter(dlg.Destroy)
  return imagesets

# regression testing
if (__name__ == "__main__") :
  app = app.CCTBXApp(0)
  imagesets = select_imageset(pick_frames=True)
  for imageset in imagesets:
    print imageset

# LIBTBX_PRE_DISPATCHER_INCLUDE_SH export PHENIX_GUI_ENVIRONMENT=1
# LIBTBX_PRE_DISPATCHER_INCLUDE_SH export BOOST_ADAPTBX_FPE_DEFAULT=1

from __future__ import division

import libtbx.load_env
from cctbx.miller.display import render_2d, scene
from scitbx.array_family import flex

class MultiplicityViewPng(render_2d):

  def __init__(self, scene, settings=None):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot
    render_2d.__init__(self, scene, settings)

    self._open_circle_points = flex.vec2_double()
    self._open_circle_radii = []
    self._open_circle_colors = []
    self._filled_circle_points = flex.vec2_double()
    self._filled_circle_radii = []
    self._filled_circle_colors = []

    self.fig, self.ax = pyplot.subplots(figsize=self.settings.size_inches)
    self.render(self.ax)

  def GetSize (self) :
    return self.fig.get_size_inches() * self.fig.dpi # size in pixels

  def draw_line (self, ax, x1, y1, x2, y2) :
    ax.plot([x1, x2], [y1, y2], c=self._foreground)

  def draw_text (self, ax, text, x, y) :
    ax.text(x, y, text, color=self._foreground, size=self.settings.font_size)

  def draw_open_circle (self, ax, x, y, radius, color=None) :
    self._open_circle_points.append((x, y))
    self._open_circle_radii.append(2 * radius)
    if color is None:
      color = self._foreground
    self._open_circle_colors.append(color)

  def draw_filled_circle (self, ax, x, y, radius, color) :
    self._filled_circle_points.append((x, y))
    self._filled_circle_radii.append(2 * radius)
    self._filled_circle_colors.append(color)

  def render(self, ax):
    from matplotlib import pyplot
    from matplotlib import colors
    render_2d.render(self, ax)
    if self._open_circle_points.size():
      x, y = self._open_circle_points.parts()
      ax.scatter(
        x.as_numpy_array(), y.as_numpy_array(), s=self._open_circle_radii,
        marker='o', edgecolors=self._open_circle_colors, facecolors=None)
    if self._filled_circle_points.size():
      x, y = self._filled_circle_points.parts()
      # use pyplot colormaps then we can more easily get a colorbar
      data = self.scene.multiplicities.data()
      cmap_d = {
        'heatmap': 'hot',
        'redblue': colors.LinearSegmentedColormap.from_list("RedBlud",["b","r"]),
        'grayscale': 'Greys_r' if self.settings.black_background else 'Greys',
        'mono': (colors.LinearSegmentedColormap.from_list("mono",["w","w"])
                 if self.settings.black_background
                 else colors.LinearSegmentedColormap.from_list("mono",["black","black"])),
      }
      cm = cmap_d.get(
        self.settings.color_scheme, self.settings.color_scheme)
      if isinstance(cm, basestring):
        cm = pyplot.cm.get_cmap(cm)
      im = ax.scatter(
        x.as_numpy_array(), y.as_numpy_array(), s=self._filled_circle_radii,
        marker='o',
        c=data.select(self.scene.slice_selection).as_numpy_array(),
        edgecolors='none',
        vmin=0, vmax=flex.max(data),
        cmap=cm)
      # colorbar
      cb = self.fig.colorbar(im, ax=ax)
      [t.set_color(self._foreground) for t in cb.ax.get_yticklabels()]
      [t.set_fontsize(self.settings.font_size) for t in cb.ax.get_yticklabels()]
    self.ax.set_aspect('equal')
    self.ax.set_axis_bgcolor(self._background)
    xmax, ymax = self.GetSize()
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.invert_yaxis()
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    self.fig.tight_layout()
    self.fig.savefig(
      self.settings.filename, bbox_inches='tight', facecolor=self._background)


import iotbx.phil
master_phil = iotbx.phil.parse("""
include scope cctbx.miller.display.master_phil
unit_cell = None
  .type = unit_cell
space_group = None
  .type = space_group
filename = multiplicities.png
  .type = path
size_inches = 20,20
  .type = floats(size=2, value_min=0)
font_size = 20
  .type = int(value_min=1)
""", process_includes=True)

def run(args):
  from libtbx.utils import Sorry
  pcl = iotbx.phil.process_command_line_with_files(
    args=args,
    master_phil=master_phil,
    reflection_file_def="data",
    pdb_file_def="symmetry_file",
    usage_string="%s scaled_unmerged.mtz [options]" %libtbx.env.dispatcher_name)
  settings = pcl.work.extract()
  file_name = settings.data

  data_only = True
  from iotbx.reflection_file_reader import any_reflection_file
  from iotbx.gui_tools.reflections import get_array_description
  try :
    hkl_file = any_reflection_file(file_name)
  except Exception, e :
    raise Sorry(str(e))
  arrays = hkl_file.as_miller_arrays(merge_equivalents=False)
  valid_arrays = []
  array_info = []
  for array in arrays :
    if array.is_hendrickson_lattman_array() :
      continue
    elif (data_only) :
      if (not array.is_real_array()) and (not array.is_complex_array()) :
        continue
    labels = array.info().label_string()
    desc = get_array_description(array)
    array_info.append("%s (%s)" % (labels, desc))
    valid_arrays.append(array)
  if (len(valid_arrays) == 0) :
    msg = "No arrays of the supported types in this file."
    raise Sorry(msg)
  miller_array = valid_arrays[0]

  settings.scale_colors_multiplicity = True
  settings.scale_radii_multiplicity = True
  settings.expand_to_p1 = True
  settings.expand_anomalous = True
  settings.slice_mode = True

  view = MultiplicityViewPng(
    scene(miller_array, settings, merge=True), settings=settings)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])

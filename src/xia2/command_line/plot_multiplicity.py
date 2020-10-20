# LIBTBX_PRE_DISPATCHER_INCLUDE_SH export PHENIX_GUI_ENVIRONMENT=1


import json
import sys

import iotbx.phil
from cctbx.miller.display import render_2d, scene
from dials.util import Sorry
from iotbx.gui_tools.reflections import get_array_description
from iotbx.reflection_file_reader import any_reflection_file
from scitbx.array_family import flex


class MultiplicityViewPng(render_2d):
    def __init__(self, scene, settings=None):
        import matplotlib

        matplotlib.use("Agg")
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
        pyplot.close()

    def GetSize(self):
        return self.fig.get_size_inches() * self.fig.dpi  # size in pixels

    def draw_line(self, ax, x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], c=self._foreground)

    def draw_text(self, ax, text, x, y):
        ax.text(x, y, text, color=self._foreground, size=self.settings.font_size)

    def draw_open_circle(self, ax, x, y, radius, color=None):
        self._open_circle_points.append((x, y))
        self._open_circle_radii.append(2 * radius)
        if color is None:
            color = self._foreground
        self._open_circle_colors.append(color)

    def draw_filled_circle(self, ax, x, y, radius, color):
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
                x.as_numpy_array(),
                y.as_numpy_array(),
                s=self._open_circle_radii,
                marker="o",
                edgecolors=self._open_circle_colors,
                facecolors=None,
            )
        if self._filled_circle_points.size():
            x, y = self._filled_circle_points.parts()
            # use pyplot colormaps then we can more easily get a colorbar
            data = self.scene.multiplicities.data()
            cmap_d = {
                "heatmap": "hot",
                "redblue": colors.LinearSegmentedColormap.from_list(
                    "RedBlue", ["b", "r"]
                ),
                "grayscale": "Greys_r" if self.settings.black_background else "Greys",
                "mono": (
                    colors.LinearSegmentedColormap.from_list("mono", ["w", "w"])
                    if self.settings.black_background
                    else colors.LinearSegmentedColormap.from_list(
                        "mono", ["black", "black"]
                    )
                ),
            }
            cm = cmap_d.get(self.settings.color_scheme, self.settings.color_scheme)
            if isinstance(cm, str):
                cm = pyplot.cm.get_cmap(cm)
            im = ax.scatter(
                x.as_numpy_array(),
                y.as_numpy_array(),
                s=self._filled_circle_radii,
                marker="o",
                c=data.select(self.scene.slice_selection).as_numpy_array(),
                edgecolors="none",
                vmin=0,
                vmax=flex.max(data),
                cmap=cm,
            )
            # colorbar
            cb = self.fig.colorbar(im, ax=ax)
            [t.set_color(self._foreground) for t in cb.ax.get_yticklabels()]
            [t.set_fontsize(self.settings.font_size) for t in cb.ax.get_yticklabels()]
        self.ax.set_aspect("equal")
        self.ax.set_facecolor(self._background)
        xmax, ymax = self.GetSize()
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, ymax)
        ax.invert_yaxis()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)

        self.fig.tight_layout()
        self.fig.savefig(
            self.settings.plot.filename, bbox_inches="tight", facecolor=self._background
        )


class MultiplicityViewJson(render_2d):
    def __init__(self, scene, settings=None):
        render_2d.__init__(self, scene, settings)

        self._open_circle_points = flex.vec2_double()
        self._open_circle_radii = []
        self._open_circle_colors = []
        self._filled_circle_points = flex.vec2_double()
        self._filled_circle_radii = []
        self._filled_circle_colors = []
        self._text = {"x": [], "y": [], "text": []}
        self._lines = []
        json_d = self.render(None)

        if self.settings.json.compact:
            indent = None
        else:
            indent = 2
        with open(self.settings.json.filename, "w") as fh:
            json.dump(json_d, fh, indent=indent)

    def GetSize(self):
        return 1600, 1600  # size in pixels

    def draw_line(self, ax, x1, y1, x2, y2):
        self._lines.append((x1, y1, x2, y2))

    def draw_text(self, ax, text, x, y):
        self._text["x"].append(x)
        self._text["y"].append(y)
        self._text["text"].append(text)

    def draw_open_circle(self, ax, x, y, radius, color=None):
        self._open_circle_points.append((x, y))
        self._open_circle_radii.append(2 * radius)
        if color is None:
            color = self._foreground
        self._open_circle_colors.append(color)

    def draw_filled_circle(self, ax, x, y, radius, color):
        self._filled_circle_points.append((x, y))
        self._filled_circle_radii.append(2 * radius)
        self._filled_circle_colors.append(color)

    def render(self, ax):
        render_2d.render(self, ax)
        data = []
        if self._open_circle_points.size():
            x, y = self._open_circle_points.parts()
            z = self._open_circle_colors
            data.append(
                {
                    "x": list(x.round(1)),
                    "y": list(y.round(1)),
                    #'z': list(z),
                    "type": "scatter",
                    "mode": "markers",
                    "name": "missing reflections",
                    "showlegend": False,
                    "marker": {
                        #'color': list(z),
                        "color": (
                            "white" if self.settings.black_background else "black"
                        ),
                        "line": {
                            #'color': 'black',
                            "width": 0
                        },
                        "symbol": "circle",
                        "size": 5,
                    },
                }
            )
        if self._filled_circle_points.size():
            x, y = self._filled_circle_points.parts()
            z = self.scene.multiplicities.data().select(self.scene.slice_selection)

            # why doesn't this work?
            # colorscale = []
            # assert len(z) == len(self._filled_circle_colors)
            # for zi in range(flex.max(z)+1):
            #  i = flex.first_index(z, zi)
            #  if i is None: continue
            #  print i, self._filled_circle_colors[i], 'rgb(%i,%i,%i)' %tuple(rgb * 264 for rgb in self._filled_circle_colors[i])
            #  colorscale.append([zi, 'rgb(%i,%i,%i)' %self._filled_circle_colors[i]])

            cmap_d = {
                "rainbow": "Jet",
                "heatmap": "Hot",
                "redblue": "RdbU",
                "grayscale": "Greys",
                "mono": None,
            }

            color = list(z)
            colorscale = cmap_d.get(
                self.settings.color_scheme, self.settings.color_scheme
            )

            if self.settings.color_scheme == "mono":
                color = "black"
                colorscale = None

            data.append(
                {
                    "x": list(x.round(1)),
                    "y": list(y.round(1)),
                    #'z': list(z),
                    "type": "scatter",
                    "mode": "markers",
                    "name": "multiplicity",
                    "showlegend": False,
                    "marker": {
                        "color": color,
                        "colorscale": colorscale,
                        "cmin": 0,
                        "cmax": flex.max(self.scene.multiplicities.data()),
                        "showscale": True,
                        "colorbar": {"title": "Multiplicity", "titleside": "right"},
                        "line": {
                            #'color': 'white',
                            "width": 0
                        },
                        "symbol": "circle",
                        "size": 5,
                    },
                }
            )

        text = {"mode": "text", "showlegend": False, "textposition": "top right"}
        text.update(self._text)
        data.append(text)

        shapes = []
        for x0, y0, x1, y1 in self._lines:
            # color = 'rgb(%i,%i,%i)' %tuple(rgb * 264 for rgb in self._foreground)
            color = "black"
            shapes.append(
                {
                    "type": "line",
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "layer": "below",
                    "line": {"color": color, "width": 2},
                }
            )

        d = {
            "data": data,
            "layout": {
                "plot_bgcolor": "rgb(%i,%i,%i)"
                % tuple(rgb * 264 for rgb in self._background),
                "title": "Multiplicity plot (%s=%s)"
                % (self.settings.slice_axis, self.settings.slice_index),
                "shapes": shapes,
                "hovermode": False,
                "xaxis": {
                    "showgrid": False,
                    "zeroline": False,
                    "showline": False,
                    "ticks": "",
                    "showticklabels": False,
                },
                "yaxis": {
                    "autorange": "reversed",
                    "showgrid": False,
                    "zeroline": False,
                    "showline": False,
                    "ticks": "",
                    "showticklabels": False,
                },
            },
        }
        return d


master_phil = iotbx.phil.parse(
    """
include scope cctbx.miller.display.master_phil
unit_cell = None
  .type = unit_cell
space_group = None
  .type = space_group
plot {
  filename = multiplicities.png
    .type = path
}
json {
  filename = None
    .type = path
  compact = True
    .type = bool
}
size_inches = 20,20
  .type = floats(size=2, value_min=0)
font_size = 20
  .type = int(value_min=1)
""",
    process_includes=True,
)


def run(args):
    pcl = iotbx.phil.process_command_line_with_files(
        args=args,
        master_phil=master_phil,
        reflection_file_def="data",
        pdb_file_def="symmetry_file",
        usage_string="xia2.plot_multiplicity scaled_unmerged.mtz [options]",
    )
    settings = pcl.work.extract()
    file_name = settings.data

    try:
        hkl_file = any_reflection_file(file_name)
    except Exception as e:
        raise Sorry(str(e))
    arrays = hkl_file.as_miller_arrays(merge_equivalents=False)
    valid_arrays = []
    array_info = []
    for array in arrays:
        if array.is_hendrickson_lattman_array():
            continue
        if (not array.is_real_array()) and (not array.is_complex_array()):
            continue
        labels = array.info().label_string()
        desc = get_array_description(array)
        array_info.append(f"{labels} ({desc})")
        valid_arrays.append(array)
    if len(valid_arrays) == 0:
        msg = "No arrays of the supported types in this file."
        raise Sorry(msg)
    miller_array = valid_arrays[0]
    plot_multiplicity(miller_array, settings)


def plot_multiplicity(miller_array, settings):
    settings.scale_colors_multiplicity = True
    settings.scale_radii_multiplicity = True
    settings.expand_to_p1 = True
    settings.expand_anomalous = True
    settings.slice_mode = True

    if settings.plot.filename is not None:
        MultiplicityViewPng(
            scene(miller_array, settings, merge=True), settings=settings
        )

    if settings.json.filename is not None:
        MultiplicityViewJson(
            scene(miller_array, settings, merge=True), settings=settings
        )


if __name__ == "__main__":
    run(sys.argv[1:])

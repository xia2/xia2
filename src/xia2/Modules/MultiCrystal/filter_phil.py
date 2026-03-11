from __future__ import annotations

import iotbx.phil

filtering_scope = iotbx.phil.parse(
    """
filtering
  .short_caption = "Filtering"
{

  method = None deltacchalf
    .type = choice
    .help = "Choice of whether to do any filtering cycles, default None."

  deltacchalf
    .short_caption = "ΔCC½"
  {
    max_cycles = None
      .type = int(value_min=1)
      .short_caption = "Maximum number of cycles"
    max_percent_removed = None
      .type = float
      .short_caption = "Maximum percentage removed"
    min_completeness = None
      .type = float(value_min=0, value_max=100)
      .help = "Desired minimum completeness, as a percentage (0 - 100)."
      .short_caption = "Minimum completeness"
    mode = dataset image_group
      .type = choice
      .help = "Perform analysis on whole datasets or batch groups"
    group_size = None
      .type = int(value_min=1)
      .help = "The number of images to group together when calculating delta"
              "cchalf in image_group mode"
      .short_caption = "Group size"
    stdcutoff = None
      .type = float
      .help = "Datasets with a ΔCC½ below (mean - stdcutoff*std) are removed"
      .short_caption = "Standard deviation cutoff"
  }
}
""",
    process_includes=True,
)

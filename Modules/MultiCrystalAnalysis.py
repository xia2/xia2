from __future__ import absolute_import, division, print_function

import logging
import sys
from collections import OrderedDict


logger = logging.getLogger(__name__)


batch_phil_scope = """\
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
"""


class separate_unmerged(object):
    def __init__(self, unmerged_intensities, batches_all, id_to_batches=None):

        intensities = OrderedDict()
        batches = OrderedDict()

        if id_to_batches is None:
            run_id_to_batch_id = None
            run_id = 0
            unique_batches = sorted(set(batches_all.data()))
            last_batch = None
            run_start = unique_batches[0]
            for i, batch in enumerate(unique_batches):
                if (
                    last_batch is not None
                    and batch > (last_batch + 1)
                    or (i + 1) == len(unique_batches)
                ):
                    if (i + 1) == len(unique_batches):
                        last_batch += 1
                    batch_sel = (batches_all.data() >= run_start) & (
                        batches_all.data() <= last_batch
                    )
                    batches[run_id] = batches_all.select(batch_sel)
                    intensities[run_id] = unmerged_intensities.select(batch_sel)
                    run_id += 1
                    run_start = batch
                last_batch = batch

        else:
            run_id_to_batch_id = OrderedDict()
            run_id = 0
            for batch_id, batch_range in id_to_batches.iteritems():
                run_id_to_batch_id[run_id] = batch_id
                run_start, last_batch = batch_range
                batch_sel = (batches_all.data() >= run_start) & (
                    batches_all.data() <= last_batch
                )
                batches[run_id] = batches_all.select(batch_sel)
                intensities[run_id] = unmerged_intensities.select(batch_sel)
                run_id += 1

        self.run_id_to_batch_id = run_id_to_batch_id
        self.intensities = intensities
        self.batches = batches


if __name__ == "__main__":
    import sys

    run(sys.argv[1:])

from __future__ import annotations

import json
import sys
import timeit
from collections import Counter

import iotbx.phil
from dials.util.options import ArgumentParser, flatten_experiments
from libtbx import easy_mp
from scitbx.array_family import flex

help_message = """

Examples::

  xia2.overload (data_master.h5|integrated.expt) [nproc=8]

"""

phil_scope = iotbx.phil.parse(
    """
nproc = 1
  .type = int(value_min=1)
    .help = "The number of processes to use."

output {
    filename = overload.json
        .type = path
        .help = "Histogram output file name"
}
"""
)


def run(args=None):
    usage = "xia2.overload (data_master.h5|integrated.expt) [nproc=8]"

    parser = ArgumentParser(
        usage=usage,
        phil=phil_scope,
        read_experiments=True,
        read_experiments_from_images=True,
        epilog=help_message,
    )

    params, _ = parser.parse_args(args=args, show_diff_phil=True)

    experiments = flatten_experiments(params.input.experiments)
    if len(experiments) != 1:
        parser.print_help()
        sys.exit("Please pass an experiment list\n")
        return

    build_hist(experiments, params)


def build_hist(experiment_list, params):
    """Iterate through the images in experiment_list and generate a pixel
    histogram, which is written to params.output.filename."""

    nproc = params.nproc

    for experiment in experiment_list:
        imageset = experiment.imageset
        limit = experiment.detector[0].get_trusted_range()[1]
        n0, n1 = experiment.scan.get_image_range()
        image_count = n1 - n0 + 1

        binfactor = 5  # register up to 500% counts
        histmax = (limit * binfactor) + 0.0
        histbins = int(limit * binfactor) + 1
        use_python_counter = histbins > 90000000  # empirically determined

        print(
            "Processing %d images in %d processes using %s\n"
            % (
                image_count,
                nproc,
                "python Counter" if use_python_counter else "flex arrays",
            )
        )

        def process_image(process):
            last_update = start = timeit.default_timer()

            i = process
            if use_python_counter:
                local_hist = Counter()
            else:
                local_hist = flex.histogram(
                    flex.double(), data_min=0.0, data_max=histmax, n_slots=histbins
                )

            max_images = image_count // nproc
            if process >= image_count % nproc:
                max_images += 1
            while i < image_count:
                data = imageset.get_raw_data(i)[0]
                if not use_python_counter:
                    data = flex.histogram(
                        data.as_double().as_1d(),
                        data_min=0.0,
                        data_max=histmax,
                        n_slots=histbins,
                    )
                local_hist.update(data)
                i = i + nproc
            if process == 0:
                if timeit.default_timer() > (last_update + 3):
                    last_update = timeit.default_timer()
                    if sys.stdout.isatty():
                        sys.stdout.write("\033[A")
                    print(
                        "Processed %d%% (%d seconds remain)    "
                        % (
                            100 * i // image_count,
                            round((image_count - i) * (last_update - start) / (i + 1)),
                        )
                    )
            return local_hist

        results = easy_mp.parallel_map(
            func=process_image,
            iterable=range(nproc),
            processes=nproc,
            preserve_exception_message=True,
        )

        print("Merging results")
        result_hist = None
        for hist in results:
            if result_hist is None:
                result_hist = hist
            else:
                result_hist.update(hist)

        if not use_python_counter:
            # reformat histogram into dictionary
            result = list(result_hist.slots())
            result_hist = {b: count for b, count in enumerate(result) if count > 0}

        results = {
            "scale_factor": 1 / limit,
            "overload_limit": limit,
            "counts": result_hist,
        }

        print("Writing results to overload.json")
        with open("overload.json", "w") as fh:
            json.dump(results, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    run()

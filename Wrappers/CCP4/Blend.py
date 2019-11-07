from __future__ import absolute_import, division, print_function

import os

import numpy

from xia2.Driver.DriverFactory import DriverFactory


def Blend(DriverType=None):
    """A factory for BlendWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class BlendWrapper(DriverInstance.__class__):
        """A wrapper for Blend."""

        def __init__(self):
            # generic things
            super(BlendWrapper, self).__init__()

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "blend"))

            self._hklin_files = []
            self._labels = []

            # Blend/R crashes with cctbx dispatcher mangling of LD_LIBRARY_PATH
            self.set_working_environment("LD_LIBRARY_PATH", "")

        def add_hklin(self, hklin, label=None):
            """Add a reflection file to the list to be sorted together."""
            self._hklin_files.append(hklin)
            if label is not None:
                self._labels.append(label)

        def analysis(self):
            """Run blend in analysis mode."""

            assert (
                len(self._hklin_files) > 1
            ), "BLEND requires more than one reflection file"

            input_files_dat = os.path.join(
                self.get_working_directory(), "input_files.dat"
            )
            with open(input_files_dat, "w") as f:
                for hklin in self._hklin_files:
                    print(hklin, file=f)

            self.add_command_line("-a")
            self.add_command_line(input_files_dat)

            self.start()

            # switch off radiation damage analysis since this can be quite slow
            # and we don't actually need it anyway
            self.input("RADFRAC 0.00")

            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()

            self._clusters_file = os.path.join(
                self.get_working_directory(), "CLUSTERS.txt"
            )
            assert os.path.isfile(self._clusters_file)

            self._summary_file = os.path.join(
                self.get_working_directory(), "BLEND_SUMMARY.txt"
            )
            assert os.path.isfile(self._summary_file)

            self._analysis_file = os.path.join(
                self.get_working_directory(), "FINAL_list_of_files.dat"
            )
            assert os.path.isfile(self._analysis_file)

            self._summary = parse_summary_file(self._summary_file)
            self._clusters = parse_clusters_file(self._clusters_file)
            self._analysis = parse_final_list_of_files_dat(self._analysis_file)
            self._linkage_matrix = clusters_as_scipy_linkage_matrix(self._clusters)

            self._dendrogram_file = os.path.join(
                self.get_working_directory(), "tree.png"
            )

        def get_clusters_file(self):
            return self._clusters_file

        def get_summary_file(self):
            return self._summary_file

        def get_analysis_file(self):
            return self._analysis_file

        def get_dendrogram_file(self):
            return self._dendrogram_file

        def get_summary(self):
            return self._summary

        def get_clusters(self):
            return self._clusters

        def get_linkage_matrix(self):
            return self._linkage_matrix

        def get_analysis(self):
            return self._analysis

        def get_label(self, dataset_id):
            if self._labels:
                assert dataset_id <= len(self._labels)
                return self._labels[dataset_id - 1]
            return None

        def plot_dendrogram(self, filename="blend_dendrogram.png", no_plot=False):
            from scipy.cluster import hierarchy

            linkage_matrix = self.get_linkage_matrix()

            labels = self._labels
            if labels:
                assert len(labels) == len(self._hklin_files)
            else:
                labels = ["%i" % (i + 1) for i in range(len(self._hklin_files))]

            if not no_plot:
                try:
                    import matplotlib

                    # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
                    matplotlib.use("Agg")  # use a non-interactive backend
                    from matplotlib import pyplot
                except ImportError:
                    raise Sorry("matplotlib must be installed to generate a plot.")

                fig = pyplot.figure(dpi=1200, figsize=(16, 12))

            d = hierarchy.dendrogram(
                linkage_matrix,
                # truncate_mode='lastp',
                color_threshold=0.05,
                labels=labels,
                # leaf_rotation=90,
                show_leaf_counts=False,
                no_plot=no_plot,
            )

            if not no_plot:
                locs, labels = pyplot.xticks()
                pyplot.setp(labels, rotation=70)
                pyplot.ylabel("Ward distance")
                fig.savefig(filename)

            return d

    return BlendWrapper()


def parse_summary_file(summary_file):
    with open(summary_file, "r") as f:
        lines = f.readlines()

    summary = {}
    for line in lines:
        row = line.strip().strip("|").split("|")
        row = [s.strip() for s in row]
        if len(row) != 7:
            continue

        try:
            crystal_id = int(row[0])
        except ValueError:
            continue

        cell = tuple(float(s) for s in row[1].split())
        assert len(cell) == 6
        volume = float(row[2].strip())
        mosaicity = float(row[3].strip())
        d_max, d_min = (float(s) for s in row[4].split())
        distance = float(row[5].strip())
        wavelength = float(row[6].strip())

        summary[crystal_id] = {
            "cell": cell,
            "volume": volume,
            "mosaicity": mosaicity,
            "d_max": d_max,
            "d_min": d_min,
            "distance": distance,
            "wavelength": wavelength,
        }

    return summary


def parse_clusters_file(clusters_file):
    with open(clusters_file, "r") as f:
        lines = f.readlines()

    contains_furthest_datasets = False

    clusters = {}
    for line in lines:
        if "Furthest" in line:
            contains_furthest_datasets = True
        row = line.split()
        if len(row) < 6:
            continue

        try:
            cluster_id = int(row[0])
        except ValueError:
            continue

        n_datasets = int(row[1])
        height = float(row[2])
        lcv = float(row[3])
        alcv = float(row[4])
        if contains_furthest_datasets:
            dataset_ids = [int(s) for s in row[7:]]
            furthest_datasets = [int(s) for s in row[5:7]]
        else:
            dataset_ids = [int(s) for s in row[5:]]
            furthest_datasets = None

        clusters[cluster_id] = {
            "n_datasets": n_datasets,
            "height": height,
            "lcv": lcv,
            "alcv": alcv,
            "dataset_ids": dataset_ids,
            "furthest_datasets": furthest_datasets,
        }

    return clusters


def parse_final_list_of_files_dat(filename):
    # The "FINAL_list_of_files.dat" file has 6 columns. The first
    # is the path to the input files, the second is the serial number assigned
    # from BLEND (and used in cluster analysis), the fourth and fifth are
    # initial and final input image numbers, the third is the image number after
    # which data are discarded because weakened by radiation damage, the sixth
    # is resolution cutoff.

    with open(filename, "r") as f:
        lines = f.readlines()

    result = {}
    for line in lines:
        row = line.split()
        if len(row) != 6:
            continue

        input_file = row[0]
        serial_no = int(row[1])
        rad_dam_cutoff = int(row[2])
        start_image = int(row[3])
        final_image = int(row[4])
        d_min = float(row[5])

        result[serial_no] = {
            "input_file": input_file,
            "radiation_damage_cutoff": rad_dam_cutoff,
            "start_image": start_image,
            "final_image": final_image,
            "d_min": d_min,
        }

    return result


def clusters_as_scipy_linkage_matrix(clusters):
    n = len(clusters) + 1
    linkage_matrix = numpy.ndarray(shape=(n - 1, 4))
    cluster_id_to_datasets = {}
    datasets_to_cluster_id = {}

    for i in range(n - 1):
        c = clusters[i + 1]
        dataset_ids = tuple(sorted(c["dataset_ids"]))
        cluster_id = n + i
        if len(dataset_ids) == 2:
            linkage_matrix[i] = [
                dataset_ids[0] - 1,
                dataset_ids[1] - 1,
                c["height"],
                len(dataset_ids),
            ]
        else:
            new = None
            for cid, dids in cluster_id_to_datasets.items():
                diff = tuple(sorted(set(dataset_ids) - set(dids)))
                if len(diff) == 1:
                    new = diff[0] - 1
                    break
                elif len(diff) < len(dataset_ids):
                    if diff in datasets_to_cluster_id:
                        new = datasets_to_cluster_id[diff]
                        break
            assert new is not None
            linkage_matrix[i] = [cid, new, c["height"], len(dataset_ids)]
        cluster_id_to_datasets[cluster_id] = dataset_ids
        datasets_to_cluster_id[dataset_ids] = cluster_id

    return linkage_matrix

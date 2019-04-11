#!/usr/bin/env python
# xia2setup.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# xia2setup.py - an application to generate the .xinfo file for data
# reduction from a directory full of images, optionally with scan and
# sequence files which will be used to add matadata.
#
# 18th December 2006

from __future__ import absolute_import, division, print_function

import collections
import os
import sys
import traceback

from xia2.Experts.FindImages import image2template_directory
from xia2.Handlers.CommandLine import CommandLine
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Debug, streams_off
from xia2.Modules.LabelitBeamCentre import compute_beam_centre

image_extensions = [
    "img",
    "mccd",
    "mar2300",
    "mar1200",
    "mar1600",
    "mar3450",
    "osc",
    "cbf",
    "mar2000",
    "sfrm",
    "",
]

compression = ["", ".bz2", ".gz"]

known_image_extensions = []

for c in compression:
    for ie in image_extensions:
        ext = "%s%s" % (ie, c)
        if ext:
            known_image_extensions.append(ext)

xds_file_names = [
    "ABS",
    "ABSORP",
    "BKGINIT",
    "BKGPIX",
    "BLANK",
    "DECAY",
    "X-CORRECTIONS",
    "Y-CORRECTIONS",
    "MODPIX",
    "FRAME",
    "GX-CORRECTIONS",
    "GY-CORRECTIONS",
    "DX-CORRECTIONS",
    "DY-CORRECTIONS",
    "GAIN",
]

known_sweeps = {}

known_sequence_extensions = ["seq"]

known_hdf5_extensions = [".h5", ".nxs"]

latest_sequence = None

target_template = None


def is_sequence_name(file):
    global known_sequence_extensions

    if os.path.isfile(file):
        if file.split(".")[-1] in known_sequence_extensions:
            return True

    return False


def is_image_name(filename):

    global known_image_extensions
    from xia2.Wrappers.XDS.XDSFiles import XDSFiles

    if os.path.isfile(filename):

        if os.path.split(filename)[-1] in XDSFiles:
            return False

        for xds_file in "ABSORP", "DECAY", "MODPIX":
            if os.path.join("scale", xds_file) in filename:
                return False

        for exten in known_image_extensions:
            if filename.endswith(exten):
                return True

        end = filename.split(".")[-1]
        try:
            if not ".log." in filename and len(end) > 1:
                return True
        except Exception:
            pass

        if is_hd5f_name(filename):
            return True

    return False


def is_hd5f_name(filename):

    if os.path.isfile(filename):
        if os.path.splitext(filename)[-1] in known_hdf5_extensions:
            return True

    return False


def is_xds_file(f):
    filename = os.path.split(f)[1]

    xds_files = [
        "ABS",
        "ABSORP",
        "BKGINIT",
        "BKGPIX",
        "BLANK",
        "DECAY",
        "DX-CORRECTIONS",
        "DY-CORRECTIONS",
        "FRAME",
        "GAIN",
        "GX-CORRECTIONS",
        "GY-CORRECTIONS",
        "MODPIX",
        "X-CORRECTIONS",
        "Y-CORRECTIONS",
    ]

    return filename.split(".")[0].split("_") in xds_files


def get_template(f):

    global target_template

    if not is_image_name(f):
        return

    if is_xds_file(f):
        return

    # in here, check the permissions on the file...

    template = None
    directory = None

    if not os.access(f, os.R_OK):
        Debug.write("No read permission for %s" % f)

    try:
        template, directory = image2template_directory(f)
        template = os.path.join(directory, template)

        if target_template:
            if template not in target_template:
                return

    except Exception as e:
        Debug.write("Exception A: %s (%s)" % (str(e), f))
        Debug.write(traceback.format_exc())

    if template is None or directory is None:
        raise RuntimeError("template not recognised for %s" % f)

    return template


def save_experiments(filename):
    from xia2.Schema import imageset_cache
    from dxtbx.model.experiment_list import ExperimentList
    from dxtbx.model.experiment_list import ExperimentListFactory
    from dxtbx.serialize import dump

    experiments = ExperimentList([])
    for imagesets in imageset_cache.values():
        for imageset in imagesets.values():
            experiments.extend(
                ExperimentListFactory.from_imageset_and_crystal(imageset, None)
            )

    dump.experiment_list(experiments, filename, compact=True)


def parse_sequence(sequence_file):
    sequence = ""

    for record in open(sequence_file).readlines():
        if record[0].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ ":
            sequence += record.strip().upper()

    global latest_sequence
    latest_sequence = sequence


def visit(root, directory, files):
    files.sort()

    templates = set()

    for f in files:

        full_path = os.path.join(directory, f)

        if is_hd5f_name(full_path):
            from dxtbx.format.Registry import Registry

            format_class = Registry.find(full_path)
            if format_class is None:
                Debug.write(
                    "Ignoring %s (Registry can not find format class)" % full_path
                )
                continue
            elif format_class.ignore():
                continue
            templates.add(full_path)

        elif is_image_name(full_path):
            try:
                template = get_template(full_path)
            except Exception as e:
                Debug.write("Exception B: %s" % str(e))
                Debug.write(traceback.format_exc())
                continue
            if template is not None:
                templates.add(template)

        elif is_sequence_name(full_path):
            parse_sequence(full_path)

    return templates


def print_sweeps(out=sys.stdout):

    global known_sweeps, latest_sequence

    sweeplists = known_sweeps.keys()
    assert len(sweeplists) > 0, "no sweeps found"
    sweeplists.sort()

    # sort sweeplist based on epoch of first image of each sweep
    import operator

    epochs = [
        known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
        for sweep in sweeplists
    ]

    if len(epochs) != len(set(epochs)):
        Debug.write("Duplicate epochs found. Trying to correct epoch information.")
        cumulativedelta = 0.0
        for sweep in sweeplists:
            known_sweeps[sweep][0].get_imageset().get_scan().set_epochs(
                known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()
                + cumulativedelta
            )
            # could change the image epoch information individually, but only
            # the information from the first image is used at this time.
            cumulativedelta += sum(
                known_sweeps[sweep][0].get_imageset().get_scan().get_exposure_times()
            )
        epochs = [
            known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
            for sweep in sweeplists
        ]

        if len(epochs) != len(set(epochs)):
            Debug.write("Duplicate epoch information remains.")
        # This should only happen with incorrect exposure time information.

    sweeplists, epochs = zip(
        *sorted(zip(sweeplists, epochs), key=operator.itemgetter(1))
    )

    # analysis pass

    wavelengths = []

    settings = PhilIndex.get_python_object().xia2.settings
    wavelength_tolerance = settings.wavelength_tolerance
    min_images = settings.input.min_images
    min_oscillation_range = settings.input.min_oscillation_range

    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]

        # sort on exposure epoch
        epochs = [s.get_imageset().get_scan().get_epochs()[0] for s in sweeps]
        sweeps, epochs = zip(*sorted(zip(sweeps, epochs), key=operator.itemgetter(1)))
        for s in sweeps:

            if len(s.get_images()) < min_images:
                Debug.write("Rejecting sweep %s:" % s.get_template())
                Debug.write(
                    "  Not enough images (found %i, require at least %i)"
                    % (len(s.get_images()), min_images)
                )
                continue

            oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
            width = oscillation_range[1] - oscillation_range[0]
            if width < min_oscillation_range:
                Debug.write("Rejecting sweep %s:" % s.get_template())
                Debug.write(
                    "  Too narrow oscillation range (found %i, require at least %i)"
                    % (width, min_oscillation_range)
                )
                continue

            wavelength = s.get_wavelength()

            if not wavelength in wavelengths:
                have_wavelength = False
                for w in wavelengths:
                    if abs(w - wavelength) < wavelength_tolerance:
                        have_wavelength = True
                        s.set_wavelength(w)
                if not have_wavelength:
                    wavelengths.append(wavelength)

    assert len(wavelengths), "No sweeps found matching criteria"

    wavelength_map = {}

    project = settings.project
    crystal = settings.crystal

    out.write("BEGIN PROJECT %s\n" % project)
    out.write("BEGIN CRYSTAL %s\n" % crystal)

    out.write("\n")

    # check to see if a user spacegroup has been assigned - if it has,
    # copy it in...

    if settings.space_group is not None:
        out.write("USER_SPACEGROUP %s\n" % settings.space_group.type().lookup_symbol())
        out.write("\n")

    if settings.unit_cell is not None:
        out.write(
            "USER_CELL %.2f %.2f %.2f %.2f %.2f %.2f\n"
            % settings.unit_cell.parameters()
        )
        out.write("\n")

    freer_file = PhilIndex.params.xia2.settings.scale.freer_file
    if freer_file is not None:
        out.write("FREER_FILE %s\n" % PhilIndex.params.xia2.settings.scale.freer_file)
        out.write("\n")

    if latest_sequence:
        out.write("BEGIN AA_SEQUENCE\n")
        out.write("\n")
        for sequence_chunk in [
            latest_sequence[i : i + 60] for i in range(0, len(latest_sequence), 60)
        ]:
            out.write("%s\n" % sequence_chunk)
        out.write("\n")
        out.write("END AA_SEQUENCE\n")
        out.write("\n")

    if settings.input.atom:
        out.write("BEGIN HA_INFO\n")
        out.write("ATOM %s\n" % settings.input.atom.lower())
        out.write("END HA_INFO\n")
        out.write("\n")
    elif settings.input.anomalous:
        out.write("BEGIN HA_INFO\n")
        out.write("ATOM X\n")
        out.write("END HA_INFO\n")
        out.write("\n")

    for j in range(len(wavelengths)):
        anomalous = settings.input.anomalous
        if settings.input.atom is not None:
            anomalous = True
        if len(wavelengths) == 1 and anomalous:
            name = "SAD"
        elif len(wavelengths) == 1:
            name = "NATIVE"
        else:
            name = "WAVE%d" % (j + 1)

        wavelength_map[wavelengths[j]] = name

        out.write("BEGIN WAVELENGTH %s\n" % name)

        dmin = PhilIndex.params.xia2.settings.resolution.d_min
        dmax = PhilIndex.params.xia2.settings.resolution.d_max

        if dmin and dmax:
            out.write("RESOLUTION %f %f\n" % (dmin, dmax))
        elif dmin:
            out.write("RESOLUTION %f\n" % dmin)

        out.write("WAVELENGTH %f\n" % wavelengths[j])

        out.write("END WAVELENGTH %s\n" % name)
        out.write("\n")

    j = 0
    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]
        # sort on exposure epoch
        epochs = [s.get_imageset().get_scan().get_epochs()[0] for s in sweeps]
        sweeps, epochs = zip(*sorted(zip(sweeps, epochs), key=operator.itemgetter(1)))
        for s in sweeps:

            # require at least n images to represent a sweep...
            if len(s.get_images()) < min_images:
                Debug.write("Rejecting sweep %s:" % s.get_template())
                Debug.write(
                    "  Not enough images (found %i, require at least %i)"
                    % (len(s.get_images()), min_images)
                )
                continue

            oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
            width = oscillation_range[1] - oscillation_range[0]
            if width < min_oscillation_range:
                Debug.write("Rejecting sweep %s:" % s.get_template())
                Debug.write(
                    "  Too narrow oscillation range (found %i, require at least %i)"
                    % (width, min_oscillation_range)
                )
                continue

            key = os.path.join(s.get_directory(), s.get_template())
            if CommandLine.get_start_ends(key):
                start_ends = CommandLine.get_start_ends(key)
                start_good = (
                    min(s.get_images()) <= start_ends[0][0] <= max(s.get_images())
                )
                end_good = (
                    min(s.get_images()) <= start_ends[0][1] <= max(s.get_images())
                )
                if not all((start_good, end_good)):
                    Debug.write("Rejecting sweep %s:" % s.get_template())
                    if not start_good:
                        Debug.write(
                            "  Your specified start-point image lies outside the bounds of this sweep."
                        )
                    if not end_good:
                        Debug.write(
                            "  Your specified end-point image lies outside the bounds of this sweep."
                        )
                    Debug.write(
                        "  Your specified start and end points were %d & %d,"
                        % start_ends[0]
                    )
                    Debug.write(
                        "  this sweep consists of images from %d to %d."
                        % (min(s.get_images()), max(s.get_images()))
                    )
                    Debug.write(
                        """  If there are missing images in your sweep, but you have selected valid
  start and end points within a contiguous range of images, you will see this
  message, even though all is well with your selection, because xia2 treats
  each contiguous image range as a separate sweep."""
                    )
                    continue
            else:
                start_ends = [(min(s.get_images()), max(s.get_images()))]

            for start_end in start_ends:
                j += 1
                name = "SWEEP%d" % j

                out.write("BEGIN SWEEP %s\n" % name)

                if PhilIndex.params.xia2.settings.input.reverse_phi:
                    out.write("REVERSEPHI\n")

                out.write("WAVELENGTH %s\n" % wavelength_map[s.get_wavelength()])

                out.write("DIRECTORY %s\n" % s.get_directory())
                imgset = s.get_imageset()
                out.write("IMAGE %s\n" % os.path.split(imgset.get_path(0))[-1])
                out.write("START_END %d %d\n" % start_end)

                # really don't need to store the epoch in the xinfo file
                # out.write('EPOCH %d\n' % int(s.get_collect()[0]))
                if not settings.trust_beam_centre:
                    interactive = False
                    if PhilIndex.params.xia2.settings.interactive == True:
                        interactive = True
                        PhilIndex.params.xia2.settings.interactive = False
                        PhilIndex.get_python_object()
                    beam_centre = compute_beam_centre(s)
                    if beam_centre:
                        out.write("BEAM %6.2f %6.2f\n" % tuple(beam_centre))
                    PhilIndex.params.xia2.settings.interactive = interactive
                    PhilIndex.get_python_object()

                if settings.detector_distance is not None:
                    out.write("DISTANCE %.2f\n" % settings.detector_distance)

                out.write("END SWEEP %s\n" % name)

                out.write("\n")

    out.write("END CRYSTAL %s\n" % crystal)
    out.write("END PROJECT %s\n" % project)


def get_sweeps(templates):
    global known_sweeps

    from libtbx import easy_mp
    from xia2.Applications.xia2setup_helpers import get_sweep

    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    nproc = mp_params.nproc

    if params.xia2.settings.read_all_image_headers and nproc > 1:
        method = "multiprocessing"

        # If xia2 was a proper cctbx module, then we wouldn't have to do this
        # FIXME xia2 is now a proper cctbx module ;o)

        python_path = 'PYTHONPATH="%s"' % ":".join(sys.path)
        qsub_command = "qsub -v %s -V" % python_path

        args = [(template,) for template in templates]
        results_list = easy_mp.parallel_map(
            get_sweep,
            args,
            processes=nproc,
            method=method,
            qsub_command=qsub_command,
            asynchronous=True,
            preserve_order=True,
            preserve_exception_message=True,
        )

    else:
        results_list = [get_sweep((template,)) for template in templates]

    from xia2.Schema import imageset_cache

    for template, sweeplist in zip(templates, results_list):
        if sweeplist is not None:
            known_sweeps[template] = sweeplist
            for sweep in sweeplist:
                imageset = sweep.get_imageset()
                if template not in imageset_cache:
                    imageset_cache[template] = collections.OrderedDict()
                imageset_cache[template][
                    imageset.get_scan().get_image_range()[0]
                ] = imageset


def rummage(directories):
    """Walk through the directories looking for sweeps."""
    templates = set()
    visited = set()
    for path in directories:
        for root, dirs, files in os.walk(path, followlinks=True):
            realpath = os.path.realpath(root)
            if realpath in visited:
                # safety-check to avoid recursively symbolic links
                continue
            visited.add(realpath)
            templates.update(visit(os.getcwd(), root, files))

    get_sweeps(templates)


def write_xinfo(filename, directories, template=None, hdf5_master_files=None):
    global target_template

    target_template = template

    settings = PhilIndex.get_python_object().xia2.settings
    crystal = settings.crystal

    if not os.path.isabs(filename):
        filename = os.path.abspath(filename)

    directory = os.path.join(os.getcwd(), crystal, "setup")

    try:
        os.makedirs(directory)
    except OSError as e:
        if not "File exists" in str(e):
            raise

    # FIXME should I have some exception handling in here...?

    start = os.getcwd()
    os.chdir(directory)

    # if we have given a template and directory on the command line, just
    # look there (i.e. not in the subdirectories)

    if CommandLine.get_template() and CommandLine.get_directory():
        templates = set()
        for directory in CommandLine.get_directory():
            templates.update(visit(None, directory, os.listdir(directory)))
        get_sweeps(templates)
    elif hdf5_master_files is not None:
        get_sweeps(hdf5_master_files)
    else:
        rummage(directories)

    with open(filename, "w") as fout:
        print_sweeps(fout)

    # change back directory c/f bug # 2693 - important for error files...
    os.chdir(start)


def run():
    streams_off()

    # test to see if sys.argv[-2] + path is a valid path - to work around
    # spaced command lines

    argv = CommandLine.get_argv()

    if not CommandLine.get_directory():

        directories = []

        for arg in argv:
            if os.path.isdir(arg):
                directories.append(os.path.abspath(arg))

        if not directories:
            raise RuntimeError("directory not found in arguments")

    else:
        directories = [CommandLine.get_directory()]

    directories = [os.path.abspath(d) for d in directories]

    # perhaps move to a new directory...
    settings = PhilIndex.get_python_object().xia2.settings
    crystal = settings.crystal

    with open(os.path.join(os.getcwd(), "automatic.xinfo"), "w") as fout:
        directory = os.path.join(os.getcwd(), crystal, "setup")
        try:
            os.makedirs(directory)
        except OSError as e:
            if not "File exists" in str(e):
                raise e
        os.chdir(directory)

        rummage(directories)
        print_sweeps(fout)


if __name__ == "__main__":
    run()

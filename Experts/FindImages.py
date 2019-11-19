#!/usr/bin/env python
# FindImages.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 9th June 2006
#
# A set of routines for finding images and the like based on file names.
# This includes all of the appropriate handling for templates, directories
# and the like.
#
# 15/JUN/06
#
# Also routines for grouping sets of images together into sweeps based on
# the file names and the information in image headers.
#
# FIXME 24/AUG/06 this needs to renamed to something a little more obvious
#                 than FindImages - perhaps ImageExpert?
# FIXME 04/OCT/06 when the image name is all numbers like 999_1_001 need to
#                 assume that the extension is the number, BEFORE testing any
#                 of the other possibilities...
# FIXME 04/OCT/10 when we have images 200-299 (say) don't merge th2 2 with
#                 the template - you end up with batch 0.
#

from __future__ import absolute_import, division, print_function

import copy
import math
import os
import re
import string

from xia2.Handlers.Streams import Debug

# N.B. these are reversed patterns...

patterns = [
    r"([0-9]{2,12})\.(.*)",
    r"(.*)\.([0-9]{2,12})_(.*)",
    r"(.*)\.([0-9]{2,12})(.*)",
]

joiners = [".", "_", ""]

compiled_patterns = [re.compile(pattern) for pattern in patterns]


def template_regex(filename):
    """Try a bunch of templates to work out the most sensible. N.B. assumes
    that the image index will be the last digits found in the file name."""

    rfilename = filename[::-1]

    global patterns, compiled_patterns

    template = None
    digits = None

    for j, cp in enumerate(compiled_patterns):
        match = cp.match(rfilename)
        if not match:
            continue
        groups = match.groups()

        if len(groups) == 3:
            exten = "." + groups[0][::-1]
            digits = groups[1][::-1]
            prefix = groups[2][::-1] + joiners[j]
        else:
            exten = ""
            digits = groups[0][::-1]
            prefix = groups[1][::-1] + joiners[j]

        template = prefix + ("#" * len(digits)) + exten
        break

    if not template:
        raise RuntimeError("template not recognised for %s" % filename)

    return template, int(digits)


def work_template_regex():
    questions_answers = {
        "foo_bar_001.img": "foo_bar_###.img",
        "foo_bar001.img": "foo_bar###.img",
        "foo_bar_1.8A_001.img": "foo_bar_1.8A_###.img",
        "foo_bar.001": "foo_bar.###",
        "foo_bar_001.img1000": "foo_bar_###.img1000",
        "foo_bar_00001.img": "foo_bar_#####.img",
    }

    for filename in questions_answers:
        answer = template_regex(filename)
        assert answer[0] == questions_answers[filename]


def image2template(filename):
    return template_regex(filename)[0]


def image2image(filename):
    return template_regex(filename)[1]


def image2template_directory(filename):
    """Separate out the template and directory from an image name."""

    directory = os.path.dirname(filename)

    if not directory:

        # then it should be the current working directory
        directory = os.getcwd()

    image = os.path.split(filename)[-1]

    from xia2.Applications.xia2setup import is_hd5f_name

    if is_hd5f_name(filename):
        return image, directory

    template = image2template(image)

    return template, directory


def find_matching_images(template, directory):
    """Find images which match the input template in the directory
    provided."""

    files = os.listdir(directory)

    # to turn the template to a regular expression want to replace
    # however many #'s with EXACTLY the same number of [0-9] tokens,
    # e.g. ### -> ([0-9]{3})

    # change 30/may/2008 - now escape the template in this search to cope with
    # file templates with special characters in them, such as "+" -
    # fix to a problem reported by Joel B.

    length = template.count("#")
    regexp_text = re.escape(template).replace("\\#" * length, "([0-9]{%d})" % length)
    regexp = re.compile(regexp_text)

    # FIXME there are faster ways of determining this - by generating the lists
    # of possible images. That said, the code for this is now in dxtbx...

    images = []

    for f in files:
        match = regexp.match(f)

        if match:
            images.append(int(match.group(1)))

    images.sort()

    return images


def template_directory_number2image(template, directory, number):
    """Construct the full path to an image from the template, directory
    and image number."""

    # FIXME why does this duplicate code shown below??

    length = template.count("#")

    # check that the number will fit in the template

    if (math.pow(10, length) - 1) < number:
        raise RuntimeError("number too big for template")

    # construct a format statement to give the number part of the
    # template
    format = "%%0%dd" % length

    # construct the full image name
    image = os.path.join(directory, template.replace("#" * length, format % number))

    return image


def headers2sweeps(header_dict):
    """Parse a dictionary of headers to produce a list of summaries."""

    # SCI-545 - remove still images from sweeps

    zap = []

    for i in header_dict:
        header = header_dict[i]
        delta_phi = math.fabs(header["phi_end"] - header["phi_start"])
        if delta_phi == 0:
            zap.append(i)

    Debug.write("Removing %d apparently still images" % len(zap))

    for z in zap:
        del header_dict[z]

    images = sorted(header_dict)

    if not images:
        return []

    sweeps = []

    current_sweep = copy.deepcopy(header_dict[images[0]])

    current_sweep["images"] = [images[0]]

    # observation: in RIGAKU SATURN data sets the epoch is the same for
    # all images => add the IMAGE NUMBER to this as a workaround if
    # that format. See also RIGAKU_SATURN below.

    if "rigaku saturn" in current_sweep["detector_class"]:
        current_sweep["epoch"] += images[0]

    current_sweep["collect_start"] = current_sweep["epoch"]
    current_sweep["collect_end"] = current_sweep["epoch"]

    for i in images[1:]:
        header = header_dict[i]

        # RIGAKU_SATURN see above

        if "rigaku saturn" in header["detector_class"]:
            header["epoch"] += i

        # if wavelength the same and distance the same and this image
        # follows in phi from the previous chappie then this is the
        # next frame in the sweep. otherwise it is the first frame in
        # a new sweep.

        delta_lambda = math.fabs(header["wavelength"] - current_sweep["wavelength"])
        delta_distance = math.fabs(header["distance"] - current_sweep["distance"])
        delta_phi = math.fabs(header["phi_start"] - current_sweep["phi_end"]) % 360.0

        # Debug.write('Image %d %f %f %f' % \
        # (i, delta_lambda, delta_distance,
        # min(delta_phi, 360.0 - delta_phi)))

        if (
            delta_lambda < 0.0001
            and delta_distance < 0.01
            and min(delta_phi, 360.0 - delta_phi) < 0.01
            and i == current_sweep["images"][-1] + 1
        ):
            # this is another image in the sweep
            # Debug.write('Image %d belongs to the sweep' % i)
            current_sweep["images"].append(i)
            current_sweep["phi_end"] = header["phi_end"]
            current_sweep["collect_end"] = header["epoch"]
        else:
            Debug.write("Image %d starts a new sweep" % i)
            sweeps.append(current_sweep)
            current_sweep = header_dict[i]
            current_sweep["images"] = [i]
            current_sweep["collect_start"] = current_sweep["epoch"]
            current_sweep["collect_end"] = current_sweep["epoch"]

    sweeps.append(current_sweep)

    return sweeps


def common_prefix(strings):
    """Find a common prefix among the list of strings. May return an empty
    string. This is O(n^2)."""

    common = strings[0]
    finished = False

    while not finished:

        finished = True
        for s in strings:
            if not common == s[: len(common)]:
                common = common[:-1]
                finished = False
                continue

    return common


def ensure_no_batches_numbered_zero(template, images, offset):
    """Working in collaboration with digest_template, ensure that none of
    the images end up being numbered 0, and if they do try to add last digit of
    template section. Finally, if this extra character is not a digit raise
    an exception."""

    if min(images) > 0:
        return template, images, offset

    prefix = template.split("#")[0]
    suffix = template.split("#")[-1]
    hashes = template.count("#")

    while min(images) == 0:
        if not prefix[-1] in string.digits:
            raise RuntimeError("image 0 found matching %s" % template)

        add = int(prefix[-1]) * int(math.pow(10, hashes))
        offset -= add
        hashes += 1
        prefix = prefix[:-1]
        images = [add + i for i in images]

    template = "%s%s%s" % (prefix, "#" * hashes, suffix)

    return template, images, offset


def digest_template(template, images):
    """Digest the template and image numbers to copy as much of the
    common characters in the numbers as possible to the template to
    give smaller image numbers."""

    length = template.count("#")

    format = "%%0%dd" % length

    strings = [format % i for i in images]

    offset = 0
    if len(strings) > 1:
        prefix = common_prefix(strings)
        if prefix:
            offset = int(prefix + "0" * (length - len(prefix)))
            template = template.replace(len(prefix) * "#", prefix, 1)
            images = [int(s.replace(prefix, "", 1)) for s in strings]

    try:
        template, images, offset = ensure_no_batches_numbered_zero(
            template, images, offset
        )
    except RuntimeError:
        Debug.write("Throwing away image 0 from template %s" % template)
        template, images, offset = ensure_no_batches_numbered_zero(
            template, images[1:], offset
        )

    return template, images, offset


if __name__ == "__main__":

    work_template_regex()

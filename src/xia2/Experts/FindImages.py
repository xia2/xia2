# A set of routines for finding images and the like based on file names.
# This includes all of the appropriate handling for templates, directories
# and the like.
#
# Also routines for grouping sets of images together into sweeps based on
# the file names and the information in image headers.


import logging
import math
import os
import re
import string

logger = logging.getLogger("xia2.Experts.FindImages")

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

    directory, image = os.path.split(os.path.abspath(filename))

    from xia2.Applications.xia2setup import is_hdf5_name

    if is_hdf5_name(filename):
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
        logger.debug("Throwing away image 0 from template %s", template)
        template, images, offset = ensure_no_batches_numbered_zero(
            template, images[1:], offset
        )

    return template, images, offset


if __name__ == "__main__":
    work_template_regex()

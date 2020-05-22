import os
import re
import sys


def image_path_obtainer(summary_file):
    """Read a xia2-summary.dat file and return a function capable of
    translating image numbers to file paths"""

    with open(summary_file) as f:
        summary = f.read()

    file_patterns = []
    image_counts = []
    first_image_numbers = []

    for line in summary.split("\n"):
        pattern = re.search("^Files (.*)", line)
        if pattern:
            filename_pattern = pattern.groups()[0]
            hashstring = re.search("(#+)", filename_pattern).groups()[0]
            file_patterns.append(
                filename_pattern.replace(hashstring, "%%0%dd" % len(hashstring))
            )
        images = re.search("^Images: ([0-9]+) to ([0-9]+)", line)
        if images:
            first, last = images.groups()
            first_image_numbers.append(int(first))
            image_counts.append(int(last) - int(first) + 1)

    def number_to_name(number):
        for (fp, ic, fi) in zip(file_patterns, image_counts, first_image_numbers):
            if number > ic:
                number -= ic
                continue
            return fp % (number + fi - 1)
        return None

    #  print file_patterns
    #  print image_counts
    #  print first_image_numbers
    return number_to_name


if __name__ == "__main__":
    if len(sys.argv) > 1:
        summary_file = "xia2-summary.dat"
        if os.path.isfile(summary_file):
            obtainer = image_path_obtainer(summary_file)
            for parameter in sys.argv[1:]:
                if "-" in parameter:
                    img_range = parameter.split("-")
                    images = list(range(int(img_range[0]), int(img_range[1]) + 1))
                else:
                    images = [int(parameter)]
                if 0 in images:
                    sys.exit(
                        "The first image number is 1. Image number 0 is disallowed"
                    )
                for i in images:
                    print(obtainer(i))
        else:
            print(
                "required file %s not found. Are you in a xia2 run directory?"
                % summary_file
            )
    else:
        print("Usage: xia2.get_image_number [n[-m] ...]")
        print()
        print("Can be run after xia2 completed processing to obtain the file")
        print("names of images and image ranges")

from __future__ import absolute_import, division, print_function

import os
import platform
import re
import six
import warnings

import xia2.Test.regression

default_data_files = [
    "AUTOMATIC_DEFAULT_free.mtz",
    "AUTOMATIC_DEFAULT_scaled.sca",
    "AUTOMATIC_DEFAULT_scaled_unmerged.mtz",
    "AUTOMATIC_DEFAULT_scaled_unmerged.sca",
]


class Xia2RegressionToleranceWarning(UserWarning):
    pass


def check_result(
    test_name, result, tmpdir, ccp4, xds=None, expected_data_files=default_data_files
):
    ccp4 = ccp4["version"]
    xds = xds["version"] if xds else 0

    error_file = tmpdir / "xia2-error.txt"
    if error_file.check():
        print(error_file.read())
        return False, "xia2-error.txt present after execution"

    if result["stderr"]:
        return False, "xia2 terminated with output to STDERR:\n" + result["stderr"]
    if result["exitcode"]:
        return (
            False,
            "xia2 terminated with non-zero exit code (%d)" % result["exitcode"],
        )

    summary_file = tmpdir / "xia2-summary.dat"
    if not summary_file.check():
        return False, "xia2-summary.dat not present after execution"

    summary_text_lines = summary_file.readlines(cr=False)
    template_name = "result.%s.%d.%d.%d.%d" % (
        test_name,
        ccp4[0],
        ccp4[1],
        ccp4[2],
        xds,
    )

    system = platform.system()
    if system != "Linux":
        template_name += "." + system

    output_result_dir = os.path.join(
        os.path.dirname(xia2.Test.regression.__file__), "output"
    )
    if not os.path.exists(output_result_dir):
        os.mkdir(output_result_dir)
    with open(os.path.join(output_result_dir, template_name), "w") as fh:
        fh.write(generate_tolerant_template(summary_text_lines))

    expected_result_dir = os.path.join(
        os.path.dirname(xia2.Test.regression.__file__), "expected"
    )
    if not os.path.exists(expected_result_dir):
        return False, "Reference result directory (%s) not found" % expected_result_dir

    expected_result_file, expected_result_file_version = None, None
    cv_search = re.compile(r"\.([0-9]+)\.([0-9]+)\.([0-9]+)(\.([0-9]+)(\.([^.]+))?)?$")
    for f in os.listdir(expected_result_dir):
        if f.startswith("result.%s." % test_name) and os.path.isfile(
            os.path.join(expected_result_dir, f)
        ):
            candidate_version = cv_search.search(f)
            if candidate_version:
                candidate_version = [
                    int(v) if v else 0 for v in candidate_version.group(1, 2, 3, 5)
                ] + [candidate_version.group(7)]
                major, minor, revision, xdsrev, candidate_platform = candidate_version
                cmaj, cmin, crev = ccp4
                xdsv = xds
                # ensure file is not made for a newer CCP4 version
                if cmaj < major:
                    continue
                if cmaj == major and cmin < minor:
                    continue
                if cmaj == major and cmin == minor and crev < revision:
                    continue
                # ensure file is not made for a newer XDS version
                if xdsv and (xdsv < xdsrev):
                    continue
                # ensure file is not made for a more specific platform
                if (
                    candidate_platform
                    and candidate_platform != "Linux"
                    and candidate_platform != system
                ):
                    continue
                if (
                    expected_result_file is not None
                    and expected_result_file_version is not None
                ):
                    cmaj, cmin, crev, xdsv, plat = expected_result_file_version
                    # ensure file is for a more recent version than any already found file
                    if cmaj > major:
                        continue
                    if cmaj == major and cmin > minor:
                        continue
                    if cmaj == major and cmin == minor and crev > revision:
                        continue
                    if xds and xdsv > xdsrev:
                        continue
                    if plat == system and candidate_platform != system:
                        continue
                expected_result_file = f
                expected_result_file_version = candidate_version
            elif expected_result_file is None:
                expected_result_file = f
    assert (
        expected_result_file is not None
    ), "Could not find expected results file to compare actual results to"
    with open(os.path.join(expected_result_dir, expected_result_file), "r") as fh:
        expected_summary_lines = fh.readlines()

    print()
    print("CCP4 version is %d.%d.%d" % (ccp4[0], ccp4[1], ccp4[2]))
    if xds:
        print("XDS revision is %d" % xds)
    print("Platform is %s" % system)
    print("Comparing against %s" % expected_result_file)
    print("-" * 80)

    number = re.compile(r"(-?\d*\.\d+|-?\d+\.?)")
    number_with_tolerance = re.compile(
        r"(-?\d*\.\d+|-?\d+\.?)\((ignore|\*\*|\d*\.\d+%?|\d+\.?%?)\)"
    )
    output_identical = True
    for actual, expected in zip(summary_text_lines, expected_summary_lines):
        if actual == expected:
            print(" " + actual)
            continue

        actual_s = re.split(r"(\s+)", actual)
        expected_s = re.split(r"(\s+)", expected)

        valid = []
        equal = []

        for e, a in zip(expected_s, actual_s):
            if e == "***" or e.strip() == a.strip():
                equal.append(True)
                valid.append(True)
            elif e == "(ignore)":
                equal.append(False)
                valid.append(True)
            elif number_with_tolerance.match(e) and number.match(a):
                expected_value, tolerance = number_with_tolerance.match(e).groups()
                expected_value = float(expected_value)
                if number.match(e).groups()[0] == a:
                    # identical value, but missing brackets
                    equal.append(True)
                    valid.append(True)
                    continue
                if tolerance == "**":
                    equal.append(True)
                    valid.append(True)
                    continue
                if tolerance == "ignore":
                    equal.append(False)
                    valid.append(True)
                    continue
                if (
                    isinstance(tolerance, six.string_types) and "%" in tolerance
                ):  # percentage
                    tolerance = expected_value * float(tolerance[:-1]) / 100
                else:
                    tolerance = float(tolerance)
                equal.append(False)
                valid.append(abs(expected_value - float(a)) <= tolerance)
            else:
                equal.append(False)
                valid.append(False)

        if all(equal):
            print(" " + actual)
            continue

        expected_line = ""
        actual_line = ""
        for expected, actual, vld, eq in zip(expected_s, actual_s, valid, equal):
            template = "%%-%ds" % max(len(expected), len(actual))
            if eq:
                expected_line += template % expected
                actual_line += template % ""
            elif vld:
                expected_line += template % expected
                actual_line += template % actual
            else:
                expected_line += " " + template % expected + " "
                actual_line += "*" + template % actual + "*"
                output_identical = False
        print("-" + expected_line)
        if not all(valid):
            print(">" + actual_line)
        else:
            print("+" + actual_line)
    print("-" * 80)

    for data_file in expected_data_files:
        if not (tmpdir / "DataFiles" / data_file).check():
            return False, "expected file %s is missing" % data_file

    html_file = "xia2.html"
    if not (tmpdir / html_file).check():
        return False, "xia2.html not present after execution"

    if not output_identical:
        print("xia2 output failing tolerance checks")
        warnings.warn(
            "xia2 output failing tolerance checks", Xia2RegressionToleranceWarning
        )
    return True, "All OK"


def generate_tolerant_template(lines):
    tolerances = {
        "Distance": ["", "0.1"],
        "High resolution limit": ["5%", "10%", "**", "0.02"],
        "Low resolution limit": ["5%", "**", "**", "0.03"],
        "Completeness": ["5%", "5%", "10", "5%"],
        "Multiplicity": ["0.2", "0.2", "0.2", "0.2"],
        "I/sigma": ["15%", "**", "0.3", "0.3"],
        "Rmerge(I+/-)": ["10%", "10%", "15%", "10%"],
        "CC half": ["2%", "0.2", "0.2", "0.2"],
        "Anomalous completeness": ["2%", "5%", "10", "2%"],
        "Anomalous multiplicity": ["0.5", "0.5", "0.5", "0.5"],
        "Cell:": [
            "0.5%",
            "0.5%",
            "0.5%",
            lambda x: "0.5%" if x != "90.000" and x != "120.000" else "",
            lambda x: "0.5%" if x != "90.000" and x != "120.000" else "",
            lambda x: "0.5%" if x != "90.000" and x != "120.000" else "",
        ],
    }
    number = re.compile(r"(\d*\.\d+|\d+\.?)")
    f = []
    for l in lines:
        if l.startswith("Files "):
            l = "Files ***"
        items = re.split(r"(\s+)", l)
        number_positions = [pos for pos, item in enumerate(items) if number.match(item)]
        if number_positions and number_positions[0] > 0:
            prefix = "".join(items[0 : number_positions[0]]).strip()
            if prefix in tolerances:
                for num, pos in enumerate(number_positions):
                    tolerance = tolerances[prefix][num]
                    if callable(tolerance):
                        tolerance = tolerance(items[pos])
                    if tolerance != "":
                        tolerance = "(%s)" % tolerance
                    items[pos] += tolerance
                l = "".join(items)
        f.append(l)
    return "\n".join(f)

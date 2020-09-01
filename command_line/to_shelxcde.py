import argparse
import sys
from pprint import pformat

from iotbx.reflection_file_reader import any_reflection_file
from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf
from cctbx.xray import observation_types


def read_input_data(lb, params, update_params=True):
    print("Reading data from %s" % params[lb])
    reader = any_reflection_file(params[lb])
    file_content = reader.file_content()
    is_merged = False if file_content.n_batches() > 0 else True
    data = [
        m
        for m in reader.as_miller_arrays(merge_equivalents=is_merged)
        if type(m.observation_type()) is observation_types.intensity
        and (m.anomalous_flag() if is_merged else True)
    ]
    if not data:
        raise ValueError("Intensity data not found in %s" % params[lb])
    try:
        indices = file_content.extract_original_index_miller_indices()
        intensities = [
            dt.customized_copy(indices=indices, info=dt.info()) for dt in data
        ]
    except Exception:
        intensities = data
    if update_params:
        uc = intensities[0].unit_cell().parameters()
        sg = intensities[0].space_group().type().lookup_symbol().replace(" ", "")
        maxm = (2 * intensities[0].data().size() // 1000000) + 1
        params.update({"unit_cell": uc, "spacegroup": sg, "maxm": maxm})
    return intensities


def export_native_hkl(params):
    data = read_input_data("nat", params, False)
    if len(data) > 1:
        raise ValueError(
            "Multiple datasets found in the input native data file %s" % params["nat"]
        )
    hkl_filename = "%s_nat.hkl" % params["prefix"]
    print(
        "Exporting data from columns %s to %s"
        % (pformat(data[0].info().labels), hkl_filename)
    )
    with open(hkl_filename, "w") as fp:
        miller_array_export_as_shelx_hklf(data[0], fp)
    return {"nat": hkl_filename}


def export_sad_hkl(params):
    data = read_input_data("sad", params)
    if len(data) > 1:
        try:
            sel_data = next(
                dt for dt in data if params["label"] in "".join(dt.info().labels)
            )
        except KeyError:
            raise ValueError(
                "Please specify column label to select a single dataset using --label parameter"
            )
        except StopIteration:
            raise ValueError(
                "Dataset matching column label %s not found" % params["label"]
            )
    else:
        sel_data = data[0]
        if "label" in params:
            sel_data_labels = "".join(sel_data.info().labels)
            if params["label"] not in sel_data_labels:
                raise ValueError(
                    "Selected dataset colum label doesn't match --label %s"
                    % params["label"]
                )
    hkl_filename = "%s.hkl" % params["prefix"]
    print(
        "Exporting data from columns %s to %s"
        % (pformat(sel_data.info().labels), hkl_filename)
    )
    with open(hkl_filename, "w") as fp:
        miller_array_export_as_shelx_hklf(sel_data, fp)
    return {"sad": hkl_filename}


def export_mad_hkl(params):
    res = {}
    for lb in ("peak", "infl", "hrem", "lrem"):
        if lb in params:
            data = read_input_data(lb, params)
            if len(data) > 1:
                raise ValueError("Multiple datasets found in %s" % params[lb])
            hkl_filename = "%s_%s.hkl" % (params["prefix"], lb)
            with open(hkl_filename, "w") as fp:
                miller_array_export_as_shelx_hklf(data[0], fp)
            res[lb] = hkl_filename
    return res


def export_single_mad_hkl(params):
    data = sorted(read_input_data("mad", params), key=lambda d: d.info().wavelength)
    dt_labels = {
        v: k for (k, v) in params.items() if k in ("peak", "infl", "hrem", "lrem")
    }
    if not dt_labels:
        dt_labels = dict(
            zip(
                ("".join(dt.info().labels) for dt in data),
                ("hrem", "peak", "infl", "lrem"),
            )
        )
    res = {}
    for dt in data:
        for dt_name in dt_labels:
            if dt_name in "".join(dt.info().labels):
                dt_label = dt_labels[dt_name]
                hkl_filename = "%s_%s.hkl" % (params["prefix"], dt_label)
                print(
                    "Exporting data from columns %s to %s"
                    % (pformat(dt.info().labels), hkl_filename)
                )
                with open(hkl_filename, "w") as fp:
                    miller_array_export_as_shelx_hklf(dt, fp)
                res[dt_label] = hkl_filename
    return res


def write_shelxc_script(hkl_files, params):
    datasets = ["%s %s" % vals for vals in hkl_files.items()]

    # spacegroup name disputes
    sg = params["spacegroup"]
    if sg.startswith("R3:"):
        sg = "H3"
    elif sg.startswith("R32:"):
        sg = "H32"

    if "sites" in params:
        datasets += ["find %d" % params["sites"]]
    script_file = "%s.sh" % params["prefix"]
    print("Writing %s script for running SHELXC" % script_file)
    with open(script_file, "w") as fh:
        fh.write(
            "\n".join(
                [
                    "shelxc %s << eof" % params["prefix"],
                    "cell %f %f %f %f %f %f" % params["unit_cell"],
                    "spag %s" % sg,
                ]
                + datasets
                + [
                    "maxm %d" % params["maxm"],
                    "eof",
                    "",
                ]
            )
        )


def run(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="xia2.to_shelxcde - Generate script"
        " to run SHELXC on the input SAD/MAD datasets",
        epilog="Following combinations of the input parameters are valid:"
        "\n  sad, label - for SAD dataset. label parameter is optional if only one dataset is available."
        "\n  peak, infl, hrem, lrem - for MAD datasets that are read from different files."
        "\n  mad, peak, infl, hrem, lrem - for MAD datasets read from a single multi-wavelength file."
        "\n                                If labels are not provided datasets will be labeled according to wavelength."
        "\n  nat - native dataset can be provided with any of the previous parameter combinations.",
    )
    parser.add_argument("--peak", help="Peak MAD dataset file/column label")
    parser.add_argument("--infl", help="Inflection MAD dataset file/column label")
    parser.add_argument("--hrem", help="High-remote MAD dataset file/column label")
    parser.add_argument("--lrem", help="Low-remote MAD dataset file/column label")
    parser.add_argument("--label", help="Column label for selecting SAD dataset")
    parser.add_argument("--sad", help="SAD dataset file")
    parser.add_argument("--mad", help="MAD dataset file")
    parser.add_argument("--nat", help="Native dataset file")
    parser.add_argument("-s", "--sites", type=int, help="Number of atoms to search")
    parser.add_argument("prefix", help="Output file name prefix")

    vals = parser.parse_args(args)
    params = {k: v for (k, v) in vars(vals).items() if v}
    param_names = set(params.keys())

    allowed_groups = (
        {"peak", "infl", "hrem", "lrem", "nat", "prefix", "sites"},
        {"sad", "label", "nat", "prefix", "sites"},
        {"mad", "peak", "infl", "hrem", "lrem", "nat", "prefix", "sites"},
    )
    if not any(param_names.issubset(grp) for grp in allowed_groups):
        parser.error("Invalid combination of the input parameters")

    if "sad" in params:
        shelx_files = export_sad_hkl(params)
    elif "mad" in params:
        shelx_files = export_single_mad_hkl(params)
    elif any(p in params for p in ("peak", "infl", "hrem", "lrem")):
        shelx_files = export_mad_hkl(params)
    else:
        parser.error("Input dataset file not specified")

    if "nat" in params:
        shelx_files.update(export_native_hkl(params))

    write_shelxc_script(shelx_files, params)


if __name__ == "__main__":
    run(sys.argv[1:])

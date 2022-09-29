from __future__ import annotations

import functools
import itertools
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, TypedDict

import h5py
import numpy as np
import yaml
from yaml.loader import SafeLoader

from dials.array_family import flex
from dxtbx import flumpy
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Modules.SSX.data_reduction_programs import FilePair

xia2_logger = logging.getLogger(__name__)


class MetadataInFile(object):
    def __init__(self, file, item):
        self.file = file
        self.item = item

    def __eq__(self, other):
        return self.file == other.file and self.item == other.item


class ConstantMetadataForFile(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value


class ParsedGrouping(object):
    def __init__(self, images):
        self.name = "test"  # name
        self._images_to_metadata = {i: {} for i in images}
        self.tolerances: dict = {}
        self._metadata_names = set()

    @property
    def n_images(self):
        return len(self._images_to_metadata)

    @property
    def metadata_names(self):
        return self._metadata_names

    def add_metadata_for_image(self, image: str, metadata: dict):
        if image not in self._images_to_metadata:
            raise ValueError(f"{image} not in initialised images")
        self._images_to_metadata[image].update(metadata)
        self._metadata_names.add(list(metadata.keys())[0])

    def add_tolerances(self, tolerances: dict):
        self.tolerances = tolerances

    def check_consistent(self):
        # check we have all same keys for all images.
        if not all(self._images_to_metadata.values()):
            raise AssertionError("Metadata location only specified for some images")
        for img, v in self._images_to_metadata.items():
            if set(v.keys()) != self.metadata_names:
                raise AssertionError(
                    "Metadata names not consistent across all images:\n"
                    + f"full set of metadata names across images: {self.metadata_names}\n"
                    + f"Image {img} : metadata names: {set(v.keys())}"
                )
        if set(self.tolerances.keys()) != self.metadata_names:
            raise AssertionError(
                f"Tolerance names != metadata names: {set(self.tolerances.keys())}, {self.metadata_names}"
            )

    def __str__(self):
        tolerances = "\n".join(f"    {n} : {t}" for n, t in self.tolerances.items())
        header = f"""
Summary of data in ParsedGrouping class
  Grouping name: {self.name}
  Metadata names: {','.join(n for n in self.metadata_names)}
  Tolerances:
{tolerances}
"""
        for i, v in self._images_to_metadata.items():
            header += f"  Image: {i}\n    metadata: {v}\n"
        return header

    def join(self, new):
        assert self.name == new.name
        assert self.metadata_names == new.metadata_names
        assert self.tolerances == new.tolerances
        for image, meta in new._images_to_metadata.items():
            if image in self._images_to_metadata:
                assert self._images_to_metadata[image] == meta
            else:
                self._images_to_metadata[image] = meta
        return self

    def extract_data(self) -> dict:
        relevant_metadata: dict[str, dict] = defaultdict(dict)
        for img, metadata_dict in self._images_to_metadata.items():
            for k, v in metadata_dict.items():
                if isinstance(v, MetadataInFile):
                    file = v.file
                    item = v.item
                    with h5py.File(file, mode="r") as filedata:
                        try:
                            item = item.split("/")[1:]
                            while item:
                                next = item.pop(0)
                                filedata = filedata[next]
                            this_values = filedata[()]
                        except Exception:
                            raise ValueError(f"Unable to extract {item} from {file}")
                        else:
                            relevant_metadata[img][k] = this_values
                elif isinstance(v, ConstantMetadataForFile):
                    relevant_metadata[img][k] = v.value
                else:
                    raise TypeError()
        return relevant_metadata


class ParsedYAML(object):
    def __init__(self, images, metadata, structure):
        self._images = images
        self.metadata_items = {}
        self._groupings: dict[str, ParsedGrouping] = {}
        self._parse_metadata(metadata)
        self._parse_structure(structure)

    @property
    def groupings(self) -> dict[str, ParsedGrouping]:
        return self._groupings

    def _parse_metadata(self, metadata):
        for name, metadict in metadata.items():
            self.metadata_items[name] = {}
            for image, meta in metadict.items():
                if image not in self._images:
                    raise ValueError(f"Image {image} not specified in 'Images:'")
                if type(meta) is float or type(meta) is int:
                    self.metadata_items[name][image] = ConstantMetadataForFile(meta)
                elif type(meta) is str:
                    pieces = meta.split(":")
                    if len(pieces) != 2:
                        raise ValueError(
                            f"Unable to understand value: {meta}, expected format file:item e.g. /data/file.h5:/entry/data/timepoint"
                        )
                    metafile, loc = pieces
                    self.metadata_items[name][image] = MetadataInFile(metafile, loc)
                else:
                    raise TypeError(
                        "Only float, int and string metadata items understood"
                    )
        for name, items in self.metadata_items.items():
            if len(items) != len(self._images):
                raise ValueError(f"Not all images do have {name} values specified")

    def _parse_structure(self, structure):
        for groupby, data in structure.items():
            self._groupings[groupby] = ParsedGrouping(self._images)
            if "values" not in data:
                raise ValueError(f"Grouping {groupby} does not have 'values' specified")
            if "tolerances" not in data:
                raise ValueError(
                    f"Grouping {groupby} does not have 'tolerances' specified"
                )
            if type(data["values"]) is not list:
                raise ValueError(
                    f"Grouping {groupby}: values must be a list of metadata names"
                )
            values = data["values"]
            if type(data["tolerances"]) is not list:
                raise ValueError(f"Grouping {groupby}: tolerances must be a list")
            tolerances = data["tolerances"]
            if len(tolerances) != len(values):
                raise ValueError(
                    f"The tolerances and values lists are unequal in {groupby} grouping"
                )
            for name in values:
                if name not in self.metadata_items:
                    raise ValueError(
                        f"Location of {name} values not specified in metadata category"
                    )
                for image in self._images:
                    self._groupings[groupby].add_metadata_for_image(
                        image, {name: self.metadata_items[name][image]}
                    )
            self._groupings[groupby].add_tolerances(
                {n: t for n, t in zip(values, tolerances)}
            )
            self._groupings[groupby].check_consistent()

    def join(self, new):
        self._images = list(set(self._images + new._images))
        # first combine the metadata
        assert set(self.metadata_items.keys()) == set(new.metadata_items.keys())
        for name, metadict in new.metadata_items.items():
            self.metadata_items[name].update(metadict)
        for name, items in self.metadata_items.items():
            if len(items) != len(self._images):
                raise ValueError(f"Not all images do have {name} values specified")
        # now join the groupings
        for name, group in new.groupings.items():
            # FIXME should we assert same name groupings?
            if name in self.groupings.keys():
                self.groupings[name].join(group)
            else:
                self.groupings[name] = group
        return self


def full_parse(yml):
    data = list(yaml.load_all(yml, Loader=SafeLoader))[0]

    if "images" not in data:
        raise AssertionError("No images defined in yml file")
    images = data["images"]
    if "metadata" not in data:
        raise AssertionError("No metadata defined in yml file")
    metadata = data["metadata"]
    if "structure" not in data:
        raise AssertionError("No structure defined in yml file")
    structure = data["structure"]

    return ParsedYAML(images, metadata, structure)


def determine_groups(
    metadata: dict, metadata_names: List[str], tolerances: dict
) -> List[MetaDataGroup]:
    # based on the metadata, determine what are the unique groupings.

    # a bit of reshaping is needed to handle the fact that the metadata is
    # allowed to be an array of values (of length the number of images in the h5)
    # file, or a single value that corresponds to all images.
    #
    groups: List[MetaDataGroup] = []  # list of dicts
    uniques = []  # list of arrays

    n_images_per_file: dict[str, int] = {file: 1 for file in metadata.keys()}

    # First determine the unique values for each metadata name
    # also do a little bookkeeping as to how many images are in each file
    # in the case that we have a metadata array for that h5 file.
    for name in metadata_names:
        values = np.array([])
        for file, md in metadata.items():
            if isinstance(md[name], float) or isinstance(md[name], int):
                values = np.concatenate([values, np.array([md[name]])])
            else:
                values = np.concatenate([values, md[name]])
                n_images_per_file[file] = md[name].size
        set_of_values = np.array(sorted(set(np.around(values, decimals=9))))
        if len(set_of_values) == 1:
            uniques.append(set_of_values)
        else:
            diffs = np.abs(set_of_values[1:] - set_of_values[:-1])
            if np.min(diffs) > tolerances[name]:
                unique_vals = set_of_values
            else:
                unique_vals = [set_of_values[0]]
                for tp in set_of_values[1:]:
                    if tp - unique_vals[-1] > tolerances[name]:
                        unique_vals.append(tp)
                unique_vals = np.array(unique_vals)
            uniques.append(unique_vals)

    # NB this is not necessarily the number of actual images, in the case
    # that the metadata for a file is only single values rather than arrays.
    n_images = sum(n_images_per_file.values())
    # Create a single array of values for the effective number of images, needed
    # for doing repeated selections below when determining group membership.
    full_values_per_metadata = {}
    for name in metadata_names:
        values = np.array([])
        for file, md in metadata.items():
            val = md[name]
            if isinstance(val, float) or isinstance(val, int):
                n_images_this = n_images_per_file[file]
                new_values = np.repeat([val], n_images_this)
                values = np.concatenate([values, new_values])
            else:
                values = np.concatenate([values, val])
        full_values_per_metadata[name] = values

    # Now work out the all combinations of the metadata groups, and check which
    # of these are actually populated. Record the valid ranges for each group.
    combs = list(itertools.product(*uniques))
    for vals in combs:
        sel1 = flex.bool(n_images, True)
        for name, val in zip(
            metadata_names, vals
        ):  # val is the lower bound for that group
            full_vals = full_values_per_metadata[name]
            sel = (full_vals >= val) & (full_vals < val + tolerances[name] + 1e-9)
            sel1 = sel1 & flumpy.from_numpy(sel)
        if any(sel1):
            groups.append(
                MetaDataGroup(
                    {
                        n: {"min": v, "max": v + tolerances[n]}
                        for n, v in zip(metadata_names, vals)
                    }
                )
            )
    return groups


class MetaDataGroup(object):
    def __init__(self, data_dict):
        self._data_dict = data_dict

    def min_max_for_metadata(self, name):
        return (self._data_dict[name]["min"], self._data_dict[name]["max"])

    def __str__(self):
        return "\n".join(
            f"  {k} : {v['min']} - {v['max']}" for k, v in self._data_dict.items()
        )


class ImgIdxToGroupId(object):
    def __init__(self, single_return_val=None):
        self.single_return_val = single_return_val
        self.group_ids = None

    def add_selection(self, int_array):
        self.group_ids = int_array

    def set_selected(self, sel, i):
        self.group_ids.set_selected(sel, i)

    def __getitem__(self, key):
        if self.single_return_val is not None:
            return self.single_return_val
        return self.group_ids[key]


class GroupInfo(TypedDict):
    groups: List[int]
    img_idx_to_group_id: ImgIdxToGroupId


def files_to_groups(
    metadata: dict, groups: List[MetaDataGroup]
) -> dict[str, GroupInfo]:

    file_to_groups: dict[str, GroupInfo] = {
        n: {"groups": [], "img_idx_to_group_id": ImgIdxToGroupId()}
        for n in metadata.keys()
    }
    for f in file_to_groups:
        metaforfile = metadata[f]
        for i, group in enumerate(groups):
            in_group = np.array([])
            for n, data in metaforfile.items():
                if isinstance(data, float) or isinstance(data, int):
                    data = np.array([data])
                minv, maxv = group.min_max_for_metadata(n)
                s1 = data >= minv
                s2 = data < maxv
                if in_group.size == 0:
                    in_group = s1 & s2
                else:
                    in_group = in_group & s1 & s2
            if any(in_group):
                file_to_groups[f]["groups"].append(i)

                if in_group.size == 1:
                    file_to_groups[f]["img_idx_to_group_id"].single_return_val = i
                else:
                    if file_to_groups[f]["img_idx_to_group_id"].group_ids:
                        file_to_groups[f]["img_idx_to_group_id"].set_selected(
                            flumpy.from_numpy(in_group), i
                        )
                    else:
                        file_to_groups[f]["img_idx_to_group_id"].add_selection(
                            flex.int(in_group.size, 0)
                        )
                        file_to_groups[f]["img_idx_to_group_id"].set_selected(
                            flumpy.from_numpy(in_group), i
                        )
    return file_to_groups


class GroupsIdentifiersForExpt(object):
    def __init__(self):
        self.single_group = None
        self.groups_array = None
        self.keep_all_original = True
        self.identifiers = []
        self.unique_group_numbers = None


def get_expt_file_to_groupsdata(
    integrated_files: List[FilePair], img_file_to_groups: dict
) -> dict:
    expt_file_to_groupsdata = {}

    for fp in integrated_files:
        expts = load.experiment_list(fp.expt, check_format=False)
        images = list({expt.imageset.paths()[0] for expt in expts})
        groupdata = GroupsIdentifiersForExpt()
        if len(images) == 1:  # the experiment list only refers to one image file.
            groups_for_img = img_file_to_groups[images[0]]
            if len(groups_for_img["groups"]) == 1:
                groupdata.single_group = groups_for_img["groups"][
                    0
                ]  # all data from this expt goes to a single group
                groupdata.unique_group_numbers = set(groups_for_img["groups"])
            else:
                # the image goes to several groups, we just need to know the groups
                # relevant for this subset of the image
                groups_for_this = []
                group_indices = img_file_to_groups[images[0]]["img_idx_to_group_id"]
                for expt in expts:
                    index = expt.imageset.indices()[0]
                    idx = group_indices[index]
                    groups_for_this.append(idx)
                groupdata.groups_array = np.array(groups_for_this)
                groupdata.unique_group_numbers = set(groupdata.groups_array)
        else:
            # the expt list contains data from more than one h5 image
            groups_for_this = []
            for expt in expts:
                img, index = expt.imageset.paths()[0], expt.imageset.indices()[0]
                idx = img_file_to_groups[img]["img_idx_to_group_id"][index]
                groups_for_this.append(idx)
            groupdata.groups_array = np.array(groups_for_this)
            groupdata.unique_group_numbers = set(groupdata.groups_array)

        expt_file_to_groupsdata[fp.expt] = groupdata
    return expt_file_to_groupsdata


def split_files_to_groups(
    working_directory, groups, expt_file_to_groupsdata, integrated_files, grouping
) -> dict[str, List[FilePair]]:

    template = "{name}group_{index:0{maxindexlength:d}d}"
    name_template = functools.partial(
        template.format,
        name=f"{grouping.split('_by')[0]}",
        maxindexlength=len(str(len(groups))),
    )

    names: List[str] = [name_template(index=i + 1) for i, _ in enumerate(groups)]
    filesdict: dict[str, List[FilePair]] = {name: [] for name in names}
    output_group_idx = 0
    for g, name in enumerate(names):
        expts_0 = ExperimentList([])
        refls_0: List[flex.reflection_table] = []
        for fp in integrated_files:
            groupdata = expt_file_to_groupsdata[fp.expt]
            if groupdata.single_group == g:
                filesdict[name].append(fp)
            elif g in groupdata.unique_group_numbers:
                expts = load.experiment_list(fp.expt, check_format=False)
                refls = flex.reflection_table.from_file(fp.refl)
                identifiers = expts.identifiers()
                sel = groupdata.groups_array == g
                sel_identifiers = list(identifiers.select(flumpy.from_numpy(sel)))
                expts.select_on_experiment_identifiers(sel_identifiers)
                refls_0.append(refls.select_on_experiment_identifiers(sel_identifiers))
                expts_0.extend(expts)
        if refls_0:
            exptout = working_directory / f"group_{output_group_idx}.expt"
            reflout = working_directory / f"group_{output_group_idx}.refl"
            expts_0.as_file(exptout)
            joint_refls = flex.reflection_table.concat(refls_0)
            joint_refls.as_file(reflout)
            output_group_idx += 1
            filesdict[name].append(FilePair(exptout, reflout))
    return filesdict


def yml_to_filesdict(
    working_directory: Path,
    parsed: ParsedYAML,
    integrated_files: List[FilePair],
    grouping: str = "scale_by",
) -> Tuple[dict[str, List[FilePair]], List[MetaDataGroup]]:
    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    parsed_group = parsed._groupings[grouping]
    metadata = parsed_group.extract_data()

    groups = determine_groups(
        metadata, parsed_group.metadata_names, parsed_group.tolerances
    )
    img_file_to_groups = files_to_groups(metadata, groups)

    expt_file_to_groupsdata = get_expt_file_to_groupsdata(
        integrated_files, img_file_to_groups
    )

    fd = split_files_to_groups(
        working_directory, groups, expt_file_to_groupsdata, integrated_files, grouping
    )
    return fd, groups

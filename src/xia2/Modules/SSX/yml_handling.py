from tkinter import E
from dxtbx.serialize import load
import h5py
from importlib_metadata import metadata
import numpy as np
from dxtbx.model import ExperimentList
from pathlib import Path
from collections import defaultdict

from xia2.Modules.SSX.data_reduction_programs import FilePair, ReductionParams

from collections import defaultdict
import yaml
from yaml.loader import SafeLoader
import h5py

class MetadataInFile(object):

    def __init__(self, file, item):
        self.file = file
        self.item = item

    def __eq__(self, other):
        return (self.file == other.file and self.item == other.item)

class ConstantMetadataForFile(object):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

class ParsedGrouping(object):
    def __init__(self, images):
        self.name = 'test'#name
        self._images_to_metadata = {i:{} for i in images}
        self.tolerances:dict = {}
        self._metadata_names = set()

    @property
    def n_images(self):
        return len(self._images_to_metadata)

    @property
    def metadata_names(self):
        return self._metadata_names

    def add_metadata_for_image(self, image:str, metadata:dict):
        if not image in self._images_to_metadata:
            raise ValueError(f"{image} not in initialised images")
        self._images_to_metadata[image].update(metadata)
        self._metadata_names.add(list(metadata.keys())[0])

    def add_tolerances(self, tolerances:dict):
        self.tolerances = tolerances

    def check_consistent(self):
        # check we have all same keys for all images.
        if not all(self._images_to_metadata.values()):
            raise AssertionError("Metadata location only specified for some images")
        for img, v in self._images_to_metadata.items():
            if set(v.keys()) != self.metadata_names:
                raise AssertionError("Metadata names not consistent across all images:\n" +
                  f"full set of metadata names across images: {self.metadata_names}\n" +
                  f"Image {img} : metadata names: {set(v.keys())}"
                )
        if set(self.tolerances.keys()) != self.metadata_names:
          raise AssertionError(f"Tolerance names != metadata names: {set(self.tolerances.keys())}, {self.metadata_names}")

    def __str__(self):
        tolerances = '\n'.join(f'    {n} : {t}' for n,t in self.tolerances.items())
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


    def extract_data(self):
        relevant_metadata = defaultdict(dict)
        for img, metadata_dict in self._images_to_metadata.items():
            for k,v in metadata_dict.items():
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
        self._groupings = {}
        self._parse_metadata(metadata)
        self._parse_structure(structure)

    @property
    def groupings(self):
        return self._groupings

    def _parse_metadata(self, metadata):
        for name, metadict in metadata.items():
            self.metadata_items[name] = {}
            for image, meta in metadict.items():
                if not image in self._images:
                    raise ValueError(f"Image {image} not specified in 'Images:'")
                if type(meta) is float:
                    self.metadata_items[name][image] = ConstantMetadataForFile(meta)
                elif type(meta) is str:
                    pieces = meta.split(":")
                    if len(pieces) != 2:
                        raise ValueError(f"Unable to understand value: {meta}, expected format file:item e.g. /data/file.h5:/entry/data/timepoint")
                    metafile, loc = pieces
                    self.metadata_items[name][image] = MetadataInFile(metafile, loc)
                else:
                    raise TypeError("Only float and string metadata items understood")
        for name, items in self.metadata_items.items():
            if len(items) != len(self._images):
                raise ValueError(f"Not all images do have {name} values specified")

    def _parse_structure(self, structure):
        for groupby, data in structure.items():
            self._groupings[groupby] = ParsedGrouping(self._images)
            if "values" not in data:
               raise ValueError(f"Grouping {groupby} does not have 'values' specified")
            if "tolerances" not in data:
                raise ValueError(f"Grouping {groupby} does not have 'tolerances' specified")
            if type(data["values"]) is not list:
                raise ValueError(f"Grouping {groupby}: values must be a list of metadata names")
            values = data["values"]
            if type(data["tolerances"]) is not list:
                raise ValueError(f"Grouping {groupby}: tolerances must be a list")
            tolerances = data["tolerances"]
            if len(tolerances) != len(values):
                raise ValueError(f"The tolerances and values lists are unequal in {groupby} grouping")
            for name in values:
                if not name in self.metadata_items:
                    raise ValueError(f"Location of {name} values not specified in metadata category")
                for image in self._images:
                    self._groupings[groupby].add_metadata_for_image(image, {name: self.metadata_items[name][image]})
            self._groupings[groupby].add_tolerances({n:t for n, t in zip(values, tolerances)})
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

    if not "images" in data:
        raise AssertionError("No images defined in yml file")
    images = data["images"]
    if not "metadata" in data:
        raise AssertionError("No metadata defined in yml file")
    metadata = data["metadata"]
    if not "structure" in data:
        raise AssertionError("No structure defined in yml file")
    structure = data["structure"]

    return ParsedYAML(images, metadata, structure)

from collections import defaultdict



from typing import List

def assign_(metadata_values_list: List[np.array], tolerance=0.001):
    # FIXME just assume 1d vector for now
    combined_metadata_values = np.concatenate(metadata_values_list)
    combined_image_indices = [np.arange(start=0,stop=m.size) for m in metadata_values_list]
    images_to_groups = [np.zeros(m.shape, dtype=int) for m in metadata_values_list]
    #print(groups_for_images)
    #minimum, maximum = np.min(groups_for_images), np.max(groups_for_images)

    # want to determine group centre and half tolerance

    group_idx_to_image_idx = defaultdict(list)
    set_of_values = np.array(sorted(set(np.around(combined_metadata_values, decimals=9))))
    # special case of all the same for this
    #print(set_of_values)
    diffs = np.abs(set_of_values[1:] - set_of_values[:-1])
    if np.min(diffs) > tolerance:
        unique_vals = set_of_values
    else:
        unique_vals = [set_of_values[0]]
        for tp in set_of_values[1:]:
            if tp - unique_vals[-1] > tolerance:
                unique_vals.append(tp)
    groups = {}
    for i, u in enumerate(unique_vals):
        maxval = None
        for j, (image_indices, metadata_values) in enumerate(zip(combined_image_indices, metadata_values_list)):
            sel = np.abs(metadata_values - (u + (tolerance * 0.5))) <= (tolerance * 0.5) + 1e-9
            sel_values = metadata_values[sel]
            images_to_groups[j][sel] = i
            group_idx_to_image_idx[i].append(image_indices[sel])
            if not maxval:
                maxval = np.max(sel_values)
            else:
                maxval = max(maxval, np.max(sel_values))
        groups[i] = (u, np.max(sel_values))
    #print(images_to_groups)
    return group_idx_to_image_idx, groups, images_to_groups

import logging
xia2_logger = logging.getLogger(__name__)

def yml_to_filesdict(working_directory, parsed, integrated_files, good_crystals_data=None, grouping="scale_by"):
    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    parsed_group = parsed._groupings[grouping]
    metadata = parsed_group.extract_data()
    joint_metadata = {n : [] for n in parsed_group.metadata_names}
    for _, metadata_item in metadata.items():# iterate over images
        for name,values in metadata_item.items(): # iterate over different metadata categories
            joint_metadata[name].append(values)
    tolerances = [parsed_group.tolerances[k] for k in joint_metadata.keys()]

    groups_for_images = list(joint_metadata.values())[0] # FIXME just works for one metadata name atm
    metadata_name = list(joint_metadata.keys())[0]
    tolerance = tolerances[0]
    import random
    #groups_for_images = np.array([g + random.uniform(-0.01, 0.01) for g in groups_for_images])

    group_idx_to_image_idx, groups, images_to_groups = assign_(groups_for_images, tolerance)
    images_to_order = {img:i for i,img in enumerate(parsed_group._images_to_metadata.keys())}
    file_to_groups = {}
    file_to_identifiers = {} # map of integrated_expt file to good identifiers

    for i, fp in enumerate(integrated_files):
        expts = load.experiment_list(fp.expt, check_format=False)
        if good_crystals_data:
            good_crystals_this = good_crystals_data[str(fp.expt)]
            good_identifiers = good_crystals_this.identifiers
            if not good_crystals_this.keep_all_original:
                expts.select_on_experiment_identifiers(good_identifiers)
        if not expts:
            file_to_groups[i] = np.array([])
            file_to_identifiers[i] = np.array([])
        else:
            groups_for_this = []
            for expt in expts:
                img, index = expt.imageset.paths()[0], expt.imageset.indices()[0]
                group = images_to_groups[images_to_order[img]][index]
                groups_for_this.append(group)
            file_to_groups[i] = np.array(groups_for_this)
            file_to_identifiers[i] = np.array(expts.identifiers())
    xia2_logger.info(f"Grouping into {len(groups)} {grouping.split('_by')[0]} groups based on {metadata_name} values with tolerance {tolerance}")
    # ok, so now have mapping from each expt file to groups

    from dials.array_family import flex

    filesdict = {} # dict of lists
    import functools
    template = "{name}group_{index:0{maxindexlength:d}d}"
    name_template = functools.partial(
        template.format,
        name=f"{grouping.split('_by')[0]}",
        maxindexlength=len(str(len(group_idx_to_image_idx.keys()))),
    )

    names = [name_template(index=i+1) for i in groups.keys()]

    for g, name in zip(groups.keys(), names):
        expts_0 = ExperimentList([])
        refls_0 = []
        for i, fp in enumerate(integrated_files):

            expts = load.experiment_list(fp.expt, check_format=False)
            refls = flex.reflection_table.from_file(fp.refl)
            group_numbers = file_to_groups[i]
            sel = (group_numbers == g)
            identifiers = file_to_identifiers[i][sel]
            identifiers = identifiers.tolist()
            expts.select_on_experiment_identifiers(identifiers)
            refls_0.append(refls.select_on_experiment_identifiers(identifiers))
            expts_0.extend(expts)
        exptout = working_directory / f"group_{g}.expt"
        reflout = working_directory / f"group_{g}.refl"
        expts_0.as_file(exptout)
        refls_0 = flex.reflection_table.concat(refls_0)
        refls_0.as_file(reflout)
        filesdict[name] = [FilePair(exptout, reflout)]
    return filesdict

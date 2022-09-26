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

def parse_grouping(data, groupname="group_by"):
    #data = list(yaml.load_all(yml, Loader=SafeLoader))[0]

    # first check we have everything expected in our yml definition - images, structure with values and tolerances
    if not "images" in data:
        raise AssertionError("No images defined in yml file")
    images = data["images"]
    if not "structure" in data:
        raise AssertionError("No structure defiend in yml file")
    structure = data["structure"]
    if not groupname in structure:
        raise AssertionError(f"{groupname} not found as a key in the yml structure section")
    if not "values" in data["structure"][groupname]:
        raise AssertionError(f"values key not found in structure:{groupname} in the yml definition")
    values =  data["structure"][groupname]["values"]
    if not "tolerances" in data["structure"][groupname]:
        raise AssertionError(f"Tolerances must be specified")
    tolerances = data["structure"][groupname]["tolerances"]

    # in python, want to form a dict of image file to
    from collections import defaultdict
    metadata_dict = defaultdict(dict)
    """image_i: {value_name_j : {file: , item: }}"""
    parsed = ParsedGrouping(groupname, images)

    if "metadata" not in data:
        # expected format is file:data, so split on ':'
        for value in values:
            pieces = value.split(":")
            if len(pieces) != 2:
                raise AssertionError(f"Unable to understand value: {value}, expected format file:item e.g. /data/file.h5:/entry/data/timepoint")
            image, metadata = pieces
            _, valuename = metadata.rsplit('/', 1)#FIXME use Path
            if image not in images:
                raise AssertionError("File part of values does not match any input datafiles listed in images")
            #metadata_dict[image][valuename] = {"file" : image, "item": metadata}
            parsed.add_metadata_for_image(image, {valuename : {"file" : image, "item": metadata}})
    else:
        images_to_metadata = data["metadata"]
        if set(images_to_metadata.keys()) != set(images):
            raise AssertionError("Not all images have a corresponding metadata file")
        for value in values:
            pieces = value.split(":")
            if len(pieces) != 2:
                raise AssertionError(f"Unable to understand value: {value}, expected format file:item e.g. /data/file.h5:/entry/data/timepoint")
            metafile, metadata = pieces
            _, valuename = metadata.rsplit('/', 1)#FIXME use Path
            image = None
            for k,v in images_to_metadata.items():
                if v == metafile:
                    image = k
                    break
            if not image:
                raise AssertionError(f"Unable to find image matching metadata file {metafile}")
            #metadata_dict[image][valuename] = {"file" : metafile, "item": metadata}
            parsed.add_metadata_for_image(image, {valuename : {"file" : metafile, "item": metadata}})

    parsed.add_tolerances(tolerances)
    parsed.check_consistent()
    #print(parsed)
    return parsed

def full_parse(yml):
    data = list(yaml.load_all(yml, Loader=SafeLoader))[0]
    if not "structure" in data:
        raise AssertionError("No structure defiend in yml file")
    structure = data["structure"]
    parsed_groups = {}
    groups = structure.keys()
    for g in groups:
        parsed_groups[g] = parse_grouping(data, g)
    #print(parsed_groups)

    return parsed_groups

class ParsedGrouping(object):
    def __init__(self, name, images):
        self.name = name
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
        self._images_to_metadata[image] = metadata
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

    def extract_data(self):
        relevant_metadata = defaultdict(dict)
        for img, metadata_dict in self._images_to_metadata.items():
            for k,v in metadata_dict.items():
                file = v["file"]
                item = v["item"]
                with h5py.File(file, mode="r") as filedata:
                    item = item.split("/")[1:]
                    while item:
                        next = item.pop(0)
                        filedata = filedata[next]
                    this_values = filedata[()]
                relevant_metadata[img][k] = this_values
        #print(relevant_metadata)
        return relevant_metadata

def extract_metadata_from_parsed(parsed, grouping="scale_by"):
    relevant_metadata = defaultdict(dict)
    #print(parsed)
    for img, metadata_dict in parsed[grouping].items():
        for k,v in metadata_dict.items():
            #print(k,v)
            if k == "tolerances":
                continue
            file = v["file"]
            item = v["item"]
            #print(file, item)
            with h5py.File(file, mode="r") as filedata:
                item = item.split("/")[1:]
                while item:
                    next = item.pop(0)
                    filedata = filedata[next]
                this_values = filedata[()]
            relevant_metadata[img][k] = this_values
    #print(relevant_metadata)
    return relevant_metadata


    file = parsed[grouping]["/Users/whi10850/Documents/vmxi_grouping/image_58769.h5"]["timepoint"]["file"]
    with h5py.File(file, mode="r") as filedata:
        metadata = parsed["scale_by"]["/Users/whi10850/Documents/vmxi_grouping/image_58769.h5"]["timepoint"]["item"]
        metadata = metadata.split("/")[1:]
        while metadata:
            next = metadata.pop(0)
            filedata = filedata[next]
        groups_for_images = filedata[()]
    #{image: {name1:values, name2:values}} etc
    return groups_for_images
from collections import defaultdict

def join_groups(g1, g2, tolerance=0.1):
    #while g2.items():
    g2_to_g1_map = {}
    for n1,v1 in g1.items():
        letftover_g2 = {}
        for n2,v2 in g2.items():
            min_overall = min(v1[0], v2[0])
            max_overall = max(v1[1], v2[1])
            if abs(max_overall - min_overall) < tolerance:
                # join groups
                print(f"join {n1}, {n2}")
                g1[n1] = (min_overall, max_overall)
                v1 = (min_overall, max_overall)
                g2_to_g1_map[n2] = n1
            elif (abs(v1[1] - v2[0]) > tolerance) and (abs(v1[0] - v2[1]) > tolerance):
                print(f"well separated {n1}, {n2}")
                letftover_g2[n2] = v2
            else:
                raise ValueError(f"Groups are not well separated: {v1} {v2}")
        g2 = letftover_g2
    if letftover_g2:
        max_idx = max(g1.keys()) + 1
        for k,v in letftover_g2.items():
            g1[max_idx] = v
            g2_to_g1_map[k] = max_idx
    return g1, g2_to_g1_map

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

    # with open(structure, 'r') as f:
    #    parsed = full_parse(f)

    metadata = parsed[grouping].extract_data()
    joint_metadata = {n : [] for n in parsed[grouping].metadata_names}
    #print(joint_metadata)
    #print(metadata)
    for _, metadata_item in metadata.items():# iterate over images
        for name,values in metadata_item.items(): # iterate over different metadata categories
            joint_metadata[name].append(values)
    #print(joint_metadata)
    tolerances = [parsed[grouping].tolerances[k] for k in joint_metadata.keys()]
    #print(tolerances)

    groups_for_images = list(joint_metadata.values())[0] # FIXME just works for one metadata name atm
    metadata_name = list(joint_metadata.keys())[0]
    tolerance = tolerances[0]
    import random
    # desired output is a dict of group index to list of filepairs.
    #groups_for_images = np.array([g + random.uniform(-0.01, 0.01) for g in groups_for_images])

    group_idx_to_image_idx, groups, images_to_groups = assign_(groups_for_images, tolerance)
    images_to_order = {img:i for i,img in enumerate(parsed[grouping]._images_to_metadata.keys())}
    #print(groups)
    file_to_groups = {}
    file_to_identifiers = {} # map of integrated_expt file to good identifiers

    for i, fp in enumerate(integrated_files):
        expts = load.experiment_list(fp.expt, check_format=False)
        if good_crystals_data:
            good_crystals_this = good_crystals_data[str(fp.expt)]
            good_identifiers = good_crystals_this.identifiers
            if not good_crystals_this.keep_all_original:
                expts.select_on_experiment_identifiers(good_identifiers)
        #indices = np.array([expt.imageset.indices()[0] for expt in expts])
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
        #print(f"saved {len(expts_0)} expts to group {g}")
    return filesdict

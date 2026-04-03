# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Convert :class:`single_cell_parser.cell.Cell` objects to ``SWC`` morphologies.
"""
import numpy as np
import warnings
from pathlib import Path
import logging
logger = logging.getLogger("ISF").getChild(__name__)

SWC_LABEL_MAP = {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}
REVERSE_SWC_LABEL_MAP = {v: k for k, v in SWC_LABEL_MAP.items()}

def _get_swc_lines_per_section(
    cell, 
    skip_myelin=False, 
    remap_sections=None
):
    """Write out a cell object to swc format::
    
        index type x y z radius parent
        
    Args:
        cell (:class:`single_cell_parser.cell.Cell`): 
            A cell object. 
            Must contain the ``sections`` attribute returning a generator for NEURON sections.
        skip_myelin (bool):
            If True, myelin will not be written to the resulting .swc file.
        remap_sections (dict): 
            A dictionary mapping section indices to a custom label. 
            Custom labels can often be re-assigned to a type of choice anyways after loading the SWC morphology.
            This feature is useful for temporarily remapping the label of same-type only-child sections, preserving
            the fact that they are different sections in SWC. 

    Returns:
        List[List[List]]: 
            Nested list of swc lines (index, type, x, y, z, radius, parent), organized per section.
    """          
    # Remap sections to a custom type
    remap_sections = remap_sections or dict()
    only_child_sections = _get_only_child_sections(cell)
    # Default types
    label_map = {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}
    
    # Construct the per-section swc lines
    swc_lines_per_section = []
    n = 1
    for sec_ind, sec in enumerate(cell.sections):
        parent = sec.parent
        parent_sec_ind = cell.sections.index(parent) if parent is not None else None
        
        if sec_ind in only_child_sections \
        and sec.label == parent.label \
        and not (sec_ind in remap_sections or parent_sec_ind in remap_sections):
            warnings.warn(
                "Section {} is an only child of the parent section {} with the same label \"{}\". " +\
                "SWC will not be able to differentiate the two sections. This may induce undesirable behavior. " +\
                "Notably, segmentation often works on a section-per-section basis, and will deviate if two different sections are considered as one by SWC. " +\
                "Please consider remapping the section label/type via the keyword argument `remap_sections`.".format(sec_ind, parent_sec_ind, sec.label))
        
        if sec.label == "Soma":
            x, y, z = np.mean(sec.pts, axis=0)
            radius = sec.diam/2
            label_nr = 1
            parent = -1
            swc_line = [[n, label_nr, x, y, z, radius, parent]]
            swc_lines_per_section.append(swc_line)
            n += 1
        else:
            if sec.label == "Myelin" and skip_myelin: continue
            
            # Infer the section type
            if sec_ind in remap_sections: 
                label_nr = remap_sections[sec_ind]
            elif sec.label in label_map: 
                label_nr = label_map[sec.label]
            else: 
                label_nr = -1

            swc_lines_this_section = []
            
            # calculate the amount of points in the parent sections, not including the current section
            n_parent_points = sum([len(pts) for pts in swc_lines_per_section[:parent_sec_ind+1]])
            # label_nr = f"{label_nr}{i:05}"  # use a custom label for each section explicitly. this goes against the grain of swc.
            
            for pt_ind, pt in enumerate(sec.pts):
                x, y, z = pt
                # diamList is not a robust way to fetch point diameters
                # cell_modify_functions.scale_apical scales D per point, but does not update diamList
                # However, we want to segmentize AS IF the diam has not been scaled, for reproducibility
                # And afterwards scale the diameter
                radius = sec.diamList[pt_ind]/2
                # radius = sec.diam3d(pt_ind) / 2  # more robust way to fetch updated D
                parent_point = n_parent_points if pt_ind == 0 else n - 1
                swc_line = [n, label_nr, x, y, z, radius, parent_point]
                swc_lines_this_section.append(swc_line)
                n += 1
            swc_lines_per_section.append(swc_lines_this_section)
    return swc_lines_per_section

def _get_only_child_sections(cell):
    """Check if a cell has sections that are only children.
    
    Only children sections are child sections that are connected via a non-branching point, yet where both sections still
    have a different section number. This is not uncommon for e.g. the axon hillock and axon initial segment.
    
    Args:
        cell (:class:`single_cell_parser.cell.Cell`): The cell object to check.
        
    Returns:
        dict: Dictionary mapping only-child sections to their parent section.
    """
    direct_desc_sections = dict()
    for sec_ind, sec in enumerate(cell.sections):
        if sec.parent and len(sec.parent.children()) == 1:
            direct_desc_sections[sec_ind] = cell.sections.index(sec.parent)
    return direct_desc_sections
    

def cell_to_swc(cell, of, skip_myelin=False, remap_sections=None):
    """Write out a cell object to swc format::
    
        index type x y z radius parent
        
    Args:
        cell (:class:`single_cell_parser.cell.Cell`): 
            A cell object. 
            Must contain the ``sections`` attribute returning a generator for NEURON sections.
        skip_myelin (bool):
            If True, myelin will not be written to the resulting .swc file.
        remap_sections (dict): 
            A dictionary mapping section indices to a custom label. 
            Custom labels can often be re-assigned to a type of choice anyways after loading the SWC morphology.
            This feature is useful for temporarily remapping the label of same-type only-child sections, preserving
            the fact that they are different sections in SWC. 
            
    Note:
        The default labels recognized by SWC are: {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}

    Returns:
        List[List[List]]: 
            Nested list of swc lines (index, type, x, y, z, radius, parent), organized per section.
    """
    remap_sections = remap_sections or dict()
    swc_lines_per_section = _get_swc_lines_per_section(
        cell, 
        skip_myelin=skip_myelin, 
        remap_sections=remap_sections
    )
            
    swc_lines = []
    for swc_lines_section in swc_lines_per_section:
        for line in swc_lines_section:
            swc_lines.append(line)
    
    with open(of, 'w+') as f:
        for line in swc_lines:
            line = [str(e) for e in line]
            f.write(' '.join(line))
            f.write('\n')  
            
            
def hoc_to_swc(
    hoc_fn, 
    of,
    axon=True,
    skip_myelin=False, 
    remap_sections=None):
    """Convert a :ref:`hoc_file_format` morphology file to swc format.
    
    Args:
        hoc_fn (str): Path to the :ref:`hoc_file_format` morphology file.
        of (str): Output path for the resulting swc file.
        skip_myelin (bool):
            If True, myelin will not be written to the resulting .swc file.
        remap_sections (dict): 
            A dictionary mapping section indices to a custom label. 
            Custom labels
        axon (bool):
            Whether or not to include the axon in the resulting swc file.
            Default is `True``.

    Attention:
        When :param:`axon` is set to True, the axon is built according to :meth:`~single_cell_parser.cell_parser.CellParser._create_ais_Hay2013`,
        and has nothing to do with any axon that may be present in the :ref:`hoc_file_format` file.
    """
    from single_cell_parser.cell_parser import CellParser
    cell_parser = CellParser(hoc_fn)
    cell_parser.spatialgraph_to_cell(axon=axon)
    cell_to_swc(
        cell_parser.cell, 
        of, 
        skip_myelin=skip_myelin, 
        remap_sections=remap_sections
    )


def parse_swc(swc_filepath):
    """
    Extract point coordinate information.

    Args:
        swc_filepath (file): Path to the swc file to be converted.

    Returns:
        dict: Dictionary mapping point IDs to their properties (type, coords, radius, parent, children).
    """
    points = {}
    with open(swc_filepath, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            n, t, x, y, z, r, p = map(float, line.split())
            points[int(n)] = {
                "type": int(t),
                "coords": (x, y, z),
                "radius": r,
                "parent": int(p),
                "children": [],
            }
    for point_id, point_info in points.items():
        parent_id = point_info["parent"]
        if parent_id != -1:
            points[parent_id]["children"].append(point_id)
    return points


def _traverse(point_id, sec_name, parent_name, points_dict, sections):
    """Recursively build the section directory from a non-soma starting point.

    Traverse from `point_id`, collecting all points that belong to the current
    section (i.e. all points until a branch point). Saves the section, then recurses
    for each child.

    Child section names at branch points are derived from ``REVERSE_SWC_LABEL_MAP``
    if the child's type is a known label; otherwise they are named ``{sec_name}_{i}``.

    Args:
        point_id (int): Starting point ID.
        sec_name (str): HOC name for this section.
        parent_name (str): HOC name of the parent section.
        points_dict (dict): Full point dictionary from :func:`parse_swc`.
        sections (list): Accumulator; section dicts are appended here in traversal order.
    """
    current_points = []
    current_id = point_id
    while True:
        x, y, z = points_dict[current_id]["coords"]
        r = points_dict[current_id]["radius"]
        current_points.append((x, y, z, r * 2))
        children_id = points_dict[current_id]["children"]
        if len(children_id) != 1: # branch point
            break
        current_id = children_id[0]
    
    sections.append({
        "name": sec_name,
        "parent_name": parent_name,
        "points": current_points,
    })
    children_id = points_dict[current_id]["children"]
    for i, child_id in enumerate(children_id):
        type = points_dict[child_id]["type"]
        if type in REVERSE_SWC_LABEL_MAP:
            child_sec_name = REVERSE_SWC_LABEL_MAP[type]
        else:
            child_sec_name = f"{sec_name}_{i}"
        _traverse(child_id, child_sec_name, sec_name, points_dict, sections)


def build_section_directory(root_id, points_dict):
    """Build an ordered list of section records from an SWC point dictionary.

    Traverses the morphology tree starting from the soma root and produces one
    record per HOC section, including the soma as the first entry. Each record
    contains the section name, its parent section name (``None`` for soma), and
    the ordered list of 3D points (x, y, z, diameter) belonging to that section.

    Args:
        root_id (int): Point ID of the soma root (parent == -1).
        points_dict (dict): Full point dictionary from :func:`parse_swc`.

    Returns:
        list of dict: Ordered section records, each with keys ``"name"`` (str),
        ``"parent_name"`` (str or ``None``), and ``"points"``
        (list of ``(x, y, z, diameter)`` tuples). The soma section is always first
        and has ``"parent_name": None``.

    Raises:
        ValueError: If no soma points (type 1) are found in the SWC file.
    """
    # Extract soma points 
    soma_points = []
    for pid, info in points_dict.items():
        if not info["type"] == 1: # not soma, skip
            continue
        x, y, z = info["coords"]
        r = info["radius"]
        soma_points.append((x, y, z, r * 2))
    sections = [{"name": "soma", "parent_name": None, "points": soma_points}]
    current_id = root_id
    #  identify the child points from soma
    # these are the starting points for the main branches
    while True:
        children_id = points_dict[current_id]["children"]
        if len(children_id) != 1 or points_dict[children_id[0]]["type"] != 1:
            break
        current_id = children_id[0]
    counters = {}
    for i, child_id in enumerate(points_dict[current_id]["children"]):
        type = points_dict[child_id]["type"]
        label = REVERSE_SWC_LABEL_MAP.get(type, f"type{type}")
        counters[type] = counters.get(type, 0) + 1
        child_sec_name = f"{label}_{counters[type]}_0"
        _traverse(child_id, child_sec_name, "soma", points_dict, sections)
    return sections


def complete_soma(sections):
    """Expand a single-point soma to a 3-point cable representation.

    When the soma section has only one point, two additional points are added
    symmetrically along the y-axis at ±radius from the original point, matching
    the convention used when loading such morphologies.

    Args:
        sections (list of dict): Section records as returned by
            :func:`build_section_directory`. The soma section must be first.

    Returns:
        list of dict: A copy of ``sections`` with the soma's ``"points"`` replaced
        by the 3-point cable expansion.
    """
    # check that the first section is the soma and has only one point
    if len(sections) == 0 or len(sections[0]["points"]) != 1:
        raise ValueError(
            "Expected the first section to be the soma with exactly one point. " +\
            "Cannot complete soma structure."
        )
    xs, ys, zs, ds = sections[0]["points"][0]
    rs = ds / 2
    expanded = [
        (xs, ys - rs, zs, ds),
        (xs, ys, zs, ds),
        (xs, ys + rs, zs, ds),
    ]
    return [{**sections[0], "points": expanded}] + sections[1:]


def write_hoc(sections, hoc_filepath):
    """Write a HOC morphology file from a pre-built section directory.

    The soma section is identified by ``parent_name=None`` and is written first
    without a ``connect`` statement.

    Args:
        sections (list of dict): Ordered section records as returned by
            :func:`build_section_directory`, with soma points already complete.
        hoc_filepath (str): Output path for the HOC file.
    """
    with open(hoc_filepath, "w") as f:
        for sec in sections:
            if sec["parent_name"] is None: 
                # start the file with the soma section without newlines
                f.write(f"{{create {sec['name']}}}")
            elif sec["parent_name"] is 
            else:
                f.write(f"\n\n{{create {sec['name']}}}")
                f.write(f"\n{{connect {sec['name']}(0), {sec['parent_name']}(1)}}")
            f.write(f"\n{{access {sec['name']}}}\n{{nseg = 1}}\n{{pt3dclear()}}")
            for x, y, z, d in sec["points"]:
                f.write(f"\n{{pt3dadd({x}, {y}, {z}, {d})}}")


def swc_to_hoc(swc_filepath, hoc_filepath):
    """Convert a SWC morphology file to HOC format.
    
    Args:
        swc_filepath (str): Path to the SWC file to be converted.
        hoc_filepath (str): Output path for the HOC file.

    Raises:
        ValueError: If no soma points (type 1) are found in the SWC file.
    """
    points_dict = parse_swc(swc_filepath)
    root_id = None
    for pid, info in points_dict.items():
        if info["parent"] == -1:
            root_id = pid
            break
    sections = build_section_directory(root_id, points_dict)
    if len(sections[0]["points"]) == 1:
        sections = complete_soma(sections)
        logger.warning("One soma point transformed to a cable structure of three points")
    write_hoc(sections, hoc_filepath)
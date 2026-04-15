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
Read and write :ref:`swc_file_format` morphologies.
"""
from __future__ import annotations
from typing import Any
import numpy as np
import warnings
from pathlib import Path
import logging
from ._edge import _Edge
logger = logging.getLogger("ISF").getChild(__name__)

SWC_LABEL_MAP = {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}
REVERSE_SWC_LABEL_MAP = {v: k for k, v in SWC_LABEL_MAP.items()}

def _get_swc_lines_per_section(
    sections, 
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
    only_child_sections = _get_only_child_sections(sections)
    # Default types
    label_map = {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}
    
    # Construct the per-section swc lines
    swc_lines_per_section = []
    n = 0
    for sec_ind, sec in enumerate(sections):
        parent = sec.parent
        if parent == None:
            # Soma
            parent_sec_ind = -1
        else:
            parent_sec_ind = sections.index(parent)
        
        if sec_ind in only_child_sections \
        and sec.label == parent.label \
        and not (sec_ind in remap_sections or parent_sec_ind in remap_sections):
            warnings.warn(
                f"Section {sec_ind} is an only child of the parent section {parent_sec_ind} with the same label \"{sec.label}\". " +\
                "SWC will not be able to differentiate the two sections. This may induce undesirable behavior. " +\
                "Notably, segmentation often works on a section-per-section basis, and will deviate if two different sections are considered as one by SWC. " +\
                "Please consider remapping the section label/type via the keyword argument `remap_sections`."
            )
        
        if sec.label == "Myelin" and skip_myelin: continue
        
        # Infer the section type
        if sec_ind in remap_sections: 
            label_nr = remap_sections[sec_ind]
        elif sec.label in label_map: 
            label_nr = label_map[sec.label]
        else: 
            label_nr = -1

        swc_lines_this_section = []
        
        for pt_ind_this_sec, pt in enumerate(sec.pts):
            x, y, z = pt
            if parent == None and pt_ind_this_sec == 0: 
                parent_point = -1
            elif pt_ind_this_sec == 0: 
                # The amount of points in the parent sections, 
                # not including the current section or parent section
                n_prev_points = sum([
                    len(pts) 
                    for pts in swc_lines_per_section[:parent_sec_ind]
                    ])
                n_points_before_connect = np.round(sec.parentx * len(parent.pts))
                parent_point = n_prev_points + n_points_before_connect
            else: 
                parent_point = n
            # diamList is not a robust way to fetch point diameters
            # cell_modify_functions.scale_apical scales D per point, but does not update diamList
            # However, we want to segmentize AS IF the diam has not been scaled, for reproducibility
            # And afterwards scale the diameter
            radius = sec.diamList[pt_ind_this_sec]/2
            # radius = sec.diam3d(pt_ind) / 2  # more robust way to fetch updated D
            swc_line = [n + 1, label_nr, x, y, z, radius, parent_point]
            swc_lines_this_section.append(swc_line)
            n += 1
        swc_lines_per_section.append(swc_lines_this_section)
    return swc_lines_per_section

def _get_only_child_sections(sections):
    """Check if a cell has sections that are only children.
    
    Only children sections are child sections that are connected via a non-branching point, yet where both sections still
    have a different section number. This is not uncommon for e.g. the axon hillock and axon initial segment.
    
    Args:
        cell (:class:`single_cell_parser.cell.Cell`): The cell object to check.
        
    Returns:
        dict: Dictionary mapping only-child sections to their parent section.
    """
    direct_desc_sections = dict()
    for sec_ind, sec in enumerate(sections):
        if sec.parent and len(sec.parent.children()) == 1:
            direct_desc_sections[sec_ind] = sections.index(sec.parent)
    return direct_desc_sections
    

def write_swc(sections, of, skip_myelin=False, remap_sections=None):
    """Write out a cell object to swc format::
    
        index type x y z radius parent
        
    Args:
        sections (List[:class:`nrn.Section`]): 
            A list of neuron ``Section`` objects.
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
        sections=sections, 
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
            
            
def swc_to_point_dict(swc_filepath):
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
            if line.startswith("#") or not line.strip(): continue
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


def _calc_soma_x(sections, point_id, points_dict):
    """Infer where along the parent section (x) a given point connects

    This function is only applicable when the :paramref:`sections` are organized
    in the same order as the point IDs. 
    When parsing SWC files, this is not necessarily true, as parsing SWC will iterate
    child sections depth-first, potentially parsing a section whose point IDs exceed
    the amount of already parsed points. 
    However, if we assume all branches connect at x=1, except for the soma,
    we can safely assume the soma has already been parsed.
    """
    parent_sec_id = 0  # soma
    # estimated x coordinate along parent section - only works because it's the soma
    parent_section_x = points_dict[point_id]['parent'] / len(sections[parent_sec_id].edgePts)
    assert parent_section_x <= 1., f"Relative coordinate must be <= 1, but is: {parent_section_x}"
    return parent_section_x


def _traverse(point_id, sec_name, sec_label, parent_sec_id, points_dict, sections):
    """Recursively build the section directory from a non-soma starting point.

    Traverse from `point_id`, collecting all points that belong to the current
    section (i.e. all points until a branch point). Saves the section, then recurses
    for each child.

    Child section names at branch points are derived from ``REVERSE_SWC_LABEL_MAP``
    if the child's type is a known label; otherwise they are named ``{sec_name}_{i}``.

    Args:
        point_id (int): Starting point ID.
        sec_name (str): Full name for this section.
        parent_name (str): Full name of the parent section.
        points_dict (dict): Full point dictionary from :func:`parse_swc`.
        sections (list): Accumulator; section dicts are appended here in traversal order.
    """
    # Create initial edge
    edge = _Edge()
    edge.edgePts = []
    edge.diameterList = []
    edge.label = sec_label
    edge.hocLabel = sec_name
    edge.parentConnect = 1.  # assume connect at end of parent, unless specified otherwise
    edge.parentID = parent_sec_id

    if parent_sec_id == 0:          
        # infer where along soma sections connect - no other section x supported
        parent_section_x = _calc_soma_x(sections, point_id, points_dict)
        edge.parentConnect = parent_section_x

    current_pt_id = point_id
    while True:
        x, y, z = points_dict[current_pt_id]["coords"]
        r = points_dict[current_pt_id]["radius"]
        edge.edgePts.append((x, y, z))
        edge.diameterList.append(2*r)
        children_pt_id = points_dict[current_pt_id]["children"]
        if len(children_pt_id) != 1: break  # branchpoint
        current_pt_id = children_pt_id[0]
    
    sections.append(edge)

    # 2. create child edges

    children_pt_id = points_dict[current_pt_id]["children"]
    parent_sec_id= len(sections) - 1
    for i, child_id in enumerate(children_pt_id):
        section_type = points_dict[child_id]["type"]
        child_sec_label = REVERSE_SWC_LABEL_MAP[section_type]
        child_sec_name = f"{sec_name}_{i}"
        sections= _traverse(
            point_id=child_id, 
            sec_label=child_sec_label, 
            sec_name=child_sec_name, 
            parent_sec_id=parent_sec_id, 
            points_dict=points_dict, 
            sections=sections
        )

    return sections


def build_section_directory(root_ids, points_dict):
    """Build an ordered list of section records from an SWC point dictionary.

    Traverses the morphology tree starting from the soma root and produces one
    record per section, including the soma as the first entry. Each record
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
    edge = _Edge()
    edge.edgePts = []
    edge.diameterList = []
    edge.parentID = None
    edge.label = "Soma"
    edge.hocLabel = "Soma"
    for point_id, info in points_dict.items():
        if not info["type"] == 1: # not soma, skip
            continue
        x, y, z = info["coords"]
        r = info["radius"]
        edge.edgePts.append((x, y, z))
        edge.diameterList.append(r*2)

    sections = [edge]

    counters = {}
    for root_id in root_ids:
        for child_id in points_dict[root_id]["children"]:
            if child_id <= len(sections[0].edgePts): continue  # child is soma - already added
            section_type = points_dict[child_id]["type"]
            label = REVERSE_SWC_LABEL_MAP.get(section_type, f"type{section_type}")
            counters[section_type] = counters.get(section_type, 0) + 1
            child_sec_name = f"{label}_{counters[section_type]}_0"
            sections = _traverse(
                point_id=child_id, 
                sec_name=child_sec_name, 
                sec_label=label, 
                parent_sec_id=0, 
                points_dict=points_dict, 
                sections=sections
                )
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
    if len(sections) == 0 or len(sections[0].edgePts) != 1:
        raise ValueError(
            "Expected the first section to be the soma with exactly one point. " +\
            "Cannot complete soma structure."
        )
    x, y, z = sections[0].edgePts[0]
    d = sections[0].diameterList[0]
    expanded = [
        (x, y - d/2, z),
        (x, y, z),
        (x, y + d/2, z),
    ]
    sections[0].edgePts = expanded
    sections[0].diameterList = [d, d, d]
    return [sections[0]] + sections[1:]


def read_swc(
        swc_fn,
        remap_labels=None
    ):
    """Read a SWC morphology file.
    
    Args:
        swc_fn (str): Path to the :ref:`swc_file_format` file to be converted.
        remap_labels (dict[str, str]): 
            Mapping between labels in the :ref:`hoc_file_format` and actual label used in ISF.
            If a label is mapped to ``None``, it is not read in its entirety. This can be useful to e.g.
            create a custom AIS morphology instead of the one in the morphology file, as done in :class:`~single_cell_parser.cell_parser.CellParser._create_ais_Hay2013`

    Raises:
        ValueError: If no soma points (type 1) are found in the :ref:`swc_file_format` file.
    """
    remap_labels = remap_labels or {}
    remap_labels = {k.lower(): v for k, v in remap_labels.items()}
    points_dict = swc_to_point_dict(swc_fn)
    soma_root_ids = [
        idx 
        for idx in points_dict 
        if points_dict[idx]['type'] == 1
        and len(points_dict[idx]['children']) > 1
        ]
    sections = build_section_directory(
        root_ids=soma_root_ids, 
        points_dict=points_dict
    )
    soma_section = sections[0]
    if len(soma_section.edgePts) == 1:
        sections = complete_soma(sections)
        logger.warning("One soma point transformed to a cable structure of three points")

    edge_list = []
    insert_order = {}
    for i, sec in enumerate(sections):
        insert_order[sec.parentID] = i

        if sec.label.lower() != 'soma' and sec.parentID:
            if sec.parentID not in insert_order:
                raise IOError(f"Logical error: parent '{sec.parentID}' of section '{sec.label}' was not found.")

        if sec.label.lower() in remap_labels:
            if remap_labels[sec.label] == None: continue
            else: sec.label = remap_labels[sec.label.lower()]
        if sec.is_valid(): edge_list.append(sec)
        else: raise IOError(f"Logical error reading SWC file: invalid segment '{sec.label}'")

    return edge_list

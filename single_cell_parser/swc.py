import numpy as np
import warnings

SWC_LABEL_MAP = {'Soma': 1, "AIS": 2, "Dendrite": 3, "ApicalDendrite": 4, "Myelin": 5}

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
    remap_sections = remap_sections or dict()
    only_child_sections = _get_only_child_sections(cell)
    swc_lines_per_section = []
    n = 1
    for sec_ind, sec in enumerate(cell.sections):
        parent = sec.parent
        parent_sec_ind = cell.sections.index(parent) if parent is not None else None
        
        if sec_ind in only_child_sections \
        and sec.label == parent.label \
        and not (sec_ind in remap_sections or parent_sec_ind in remap_sections):
            warnings.warn(
                "Section {} is an only child of the parent section {} with the same label \"{}\". "
                "SWC will not be able to differentiate the two sections. This may induce undesirable behavior. "
                "Notably, segmentation often works on a section-per-section basis, and will deviate if two different sections are considered as one by SWC. "
                "If you want to preserve this information in SWC, consider remapping one of these sections to a custom type via the keyword argument `remap_sections`.".format(
                    sec_ind, parent_sec_ind, sec.label))
        
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
            elif sec.label in SWC_LABEL_MAP: 
                label_nr = SWC_LABEL_MAP[sec.label]
            else: 
                label_nr = -1

            swc_lines_this_section = []
            
            # calculate the amount of points in the parent sections, not including the current section
            n_parent_points = sum([len(pts) for pts in swc_lines_per_section[:parent_sec_ind+1]])
            # label_nr = f"{label_nr}{i:05}"  # use a custom label for each section explicitly. this goes against the grain of swc.
            
            for pt_ind, pt in enumerate(sec.pts):
                x, y, z = pt
                radius = sec.diamList[pt_ind]/2
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
    

def cell_to_swc(
    cell, 
    of, 
    skip_myelin=False, 
    remap_sections=None
):
    """Write out a :class:`~single_cell_parser.cell.Cell` object to swc format.
        
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



    
import sys
from pathlib import Path
import os
import Interface as I
import math as m
logger = I.logger
sys.setrecursionlimit(5000)  

def parse_swc(swc_file):

    points = {}
    parent_point = -1

    # Open file and differentiate the lines
    with open(swc_file, 'r') as f:
        for line in f:
            if line.startswith('#'): continue

            # Create a dict to organize each point's info
            n, t, x, y, z, r, p = map(float, line.split())
            points[int(n)] ={
                'type' : int(t),
                'coords' : (x,y,z),
                'radius' : r,
                'parent' : int(p)
            }

    # Iterate over points to disocover the children of each point
    for point_id, point_info in points.items():
        point_info['children'] = []

    for point_id, point_info in points.items():
        parent_id = point_info['parent']

        if parent_id != -1:
            points[parent_id]['children'].append(point_id)

    return points

def traverse(point_id, sec_id, points_dict, primary_branch, basal_branch, f):


    """
        1st condition: current point has only 1 child
            - Add this child to the section the parent point belongs as well and continue linearly

        2nd condition: current point is a branch point with more than one child
            - For each child, create a new section and add the current branch point in new section (therefore last 
              point of previous section and first point of new section is the current branch point)
        
        3rd condition: current point is the end of a branch
            - It is already added to the section the parent belongs to in the beginning of the code
            - Therefore the traversing continues for the other child of the directly previous branch point, until the end point of that branch 
    """
    
    children_id = points_dict[point_id]['children']
    x,y,z = points_dict[point_id]['coords']
    r = points_dict[point_id]['radius']

    
    # This way we avoid adding the root point before the creation of the soma
    if sec_id != 'soma':
        f.write(f'\n{{pt3dadd{x,y,z,(r*2)}}}')

    # Detect start/end of sections according to the conditions described above
    if len(children_id) == 1:
        traverse(children_id[0], sec_id, points_dict, primary_branch, basal_branch, f)
    
    if len(children_id) > 1:
        if sec_id == 'soma':

            for i in range(len(children_id)):

                if points_dict[children_id[i]]['type'] == 4:
                    primary_branch = 1
                    sec_id = f'apical_1_0'

                elif points_dict[children_id[i]]['type'] == 2:
                    sec_id = 'axon' 
                   
                else:
                    basal_branch += 1     # For each of the other children of the soma we simply add one as they are all basal dendrites
                    sec_id = f'BasalDendrite_{basal_branch}_0'

                f.write(f'\n\n{{create {sec_id}}}')
                f.write(f'\n{{connect {sec_id}(0), soma(1)}}')
                f.write(f'\n{{access {sec_id}}}\n{{nseg = 1}}\n{{pt3dclear()}}')
                

                traverse(children_id[i], sec_id, points_dict, primary_branch, basal_branch, f)
            
        else:
            for i in range(len(children_id)):
                
                if points_dict[children_id[i]]['type'] == 2:
                    sec_id_copy = sec_id
                    sec_id = 'axon' 
                    
                else:
                    sec_id_copy = sec_id    # We keep the parent section id in memory for when we come back to traverse again for the other child (or children)
                    sec_id = f'{sec_id}_{i}'
                
                f.write(f'\n\n{{create {sec_id}}}')
                f.write(f'\n{{connect {sec_id}(0), {sec_id_copy}(1)}}')
                f.write(f'\n{{access {sec_id}}}\n{{nseg = 1}}\n{{pt3dclear()}}')
                

                traverse(children_id[i], sec_id, points_dict, primary_branch, basal_branch, f)
                sec_id = sec_id_copy
                
    if len(children_id) == 0:
        return


def complete_soma(root_id, points_dict, file_name, soma_structure):

    xs, ys, zs = points_dict[root_id]['coords']
    rs = (points_dict[root_id]['radius'])

    if soma_structure == 'cable':
        logger.warning('One soma point transformed to a cable structure of three points')

        y2 = ys-rs
        y3 = ys+rs

        file_name.write(f'\n{{nseg = 1}}' f'\n{{pt3dclear()}}' f'\n{{pt3dadd{xs,y2,zs,(rs*2)}}}' f'\n{{pt3dadd{xs,ys,zs,(rs*2)}}}' f'\n{{pt3dadd{xs,y3,zs,(rs*2)}}}')
    
    elif soma_structure == 'soma' :

        file_name.write(f'\n{{nseg = 1}}' f'\n{{pt3dclear()}}' f'\n{{pt3dadd{xs,ys,zs,rs}}}')

        for point_id, point_info in points_dict.items():
            if point_info['type'] == 1:
                x, y, z = points_dict[point_id]['coords']
                r = (points_dict[point_id]['radius'])*2
                file_name.write(f'\n{{pt3dadd{x,y,z,r}}}')


"""
Arg soma: Used to autocomplete missing points of the soma
    - 'cable' to make the soma a cable-like structure
    - 'soma = soma' to keep the structure of the soma as it is in the swc file
"""

def swc_to_hoc(swc_file):

    points_dict = parse_swc(swc_file)
    root_id = None
    soma = 'cable'
    # Detect root-soma
    for point_id, point_info in points_dict.items():
        if point_id == 2 and point_info['type'] == 1:
            soma = 'soma'
        if point_info['parent'] == -1:
            root_id = point_id
            

    sec = 'soma'

    with open(file_path, "w") as f:
    
        f.write(f'{{create soma}}\n{{access soma}}')
        complete_soma(root_id, points_dict, f, soma_structure = soma)
        traverse(root_id, sec, points_dict, primary_branch = 0, basal_branch = 0, f=f)
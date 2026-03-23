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
logger = I.logger
sys.setrecursionlimit(10000)  


swc = Path("/to/your/swc_file.swc")
folder_path = "/path/to/output/folder" # Where the hoc file will be saved
file_path = os.path.join(folder_path, "output_name.hoc")
os.makedirs(folder_path, exist_ok=True)


"""

    Converts swc file format to hoc file format
        - No need to input any arguments. 
        - Just define the paths above and the rest is handled by the converter 

    NOTE:
        - If soma consists of only 1 point, the resulting hoc file will describe a soma of 3 points, with the 
        original soma point being at the center and all the sections connecting only to this point.

        - If the soma consists of more than one point, the resulting hoc file will maintain the same structure of 
        the soma as it is in the swc file.

"""

def parse_swc(swc_file):
    """
    Extract and organize point coordinate information.
    
    
    Args:
        swc_file (file): The file to be converted.
        
    Returns:
        dict: Dictionary mapping point IDs to their properties (type, coords, radius, parent, children).
    """

    points = {}

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

    # Iterate over points to discover the children of each point
    for point_id, point_info in points.items():
        point_info['children'] = []

    for point_id, point_info in points.items():
        parent_id = point_info['parent']

        if parent_id != -1:
            points[parent_id]['children'].append(point_id)

    return points

def traverse(point_id, sec_id, points_dict, apical_branch, basal_branch, f):
    """
    Starting from the root(soma) point, this function traverses through all point coordinates
    to identify and name sections/branches with the correpsodning points that make up a section
     while at the same time writes in the output file the resulting structure in hoc format

    
    Args:
        point_id (int): ID of a point.
        sec_id (str): Section/branch label.
        points_dict (dict): Point coords organized in a dict from the previous function (parse_swc).
        apical_branch (int):Apical branch ID.
        basal_branch (int): Basal branch ID.
        f (file): open file handle where the HOC code is written

        
    Returns:
        None (writes morphology structure directly to the output file)

    """

    children_id = points_dict[point_id]['children']
    x,y,z = points_dict[point_id]['coords']
    r = points_dict[point_id]['radius']

    # This way we avoid adding the root point before the creation of the soma
    if sec_id != 'soma':
        f.write(f'\n{{pt3dadd{x,y,z,(r*2)}}}')

    # Detect start/end of sections according to the conditions described above
    if len(children_id) == 1:
        traverse(children_id[0], sec_id, points_dict, apical_branch, basal_branch, f)

    if len(children_id) > 1:
        if sec_id == 'soma':

            for i in range(len(children_id)):

                if points_dict[children_id[i]]['type'] == 4:
                    apical_branch += 1
                    sec_id = f'apical_{apical_branch}_0'

                elif points_dict[children_id[i]]['type'] == 2:
                    sec_id = 'axon' 
                    
                else:
                    basal_branch += 1     # For each of the other children of the soma we simply add one as they are all basal dendrites
                    sec_id = f'BasalDendrite_{basal_branch}_0'

                f.write(f'\n\n{{create {sec_id}}}')
                f.write(f'\n{{connect {sec_id}(0), soma(1)}}')
                f.write(f'\n{{access {sec_id}}}\n{{nseg = 1}}\n{{pt3dclear()}}')
                
                traverse(children_id[i], sec_id, points_dict, apical_branch, basal_branch, f)
        
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
                
                traverse(children_id[i], sec_id, points_dict, apical_branch, basal_branch, f)
                sec_id = sec_id_copy
            
    if len(children_id) == 0:
        return


def complete_soma(root_id, points_dict, f, soma_structure):
    """
    Depending on the structure of the soma in the swc file, this function will either add two 
    more points to the soma section if soma consists of only 1 point or the structure of the soma will remain as 
    it is in the swc file if soma consists of more than one point.
    
    
    Args:
        root_id (int): ID of original soma point.
        points_dict (dict): Point information mapped to point ID
        f (file): Open file handle where the HOC code is written.
        soma_structure (str): Defines if soma structure is kept the same or not.
        
    Returns:
        None (writes morphology structure directly to the output file)
    """

    xs, ys, zs = points_dict[root_id]['coords']
    rs = (points_dict[root_id]['radius'])

    if soma_structure == 'cable':
        logger.warning('One soma point transformed to a cable structure of three points')

        y2 = ys-rs
        y3 = ys+rs

        f.write(f'\n{{nseg = 1}}' f'\n{{pt3dclear()}}' f'\n{{pt3dadd{xs,y2,zs,(rs*2)}}}' f'\n{{pt3dadd{xs,ys,zs,(rs*2)}}}' f'\n{{pt3dadd{xs,y3,zs,(rs*2)}}}')
    
    elif soma_structure == 'soma' :

        f.write(f'\n{{nseg = 1}}' f'\n{{pt3dclear()}}' f'\n{{pt3dadd{xs,ys,zs,rs}}}')

        for point_id, point_info in points_dict.items():
            if point_info['type'] == 1:
                x, y, z = points_dict[point_id]['coords']
                r = (points_dict[point_id]['radius'])*2
                f.write(f'\n{{pt3dadd{x,y,z,r}}}')


def swc_to_hoc(swc_file):
    """
    This function finds the root point (soma) and integrates all previous functions to conduct the conversion.
    
    
    Args:
        swc_file (file): The file ot be converted.
    Returns:
        None (writes morphology structure directly to the output file)
    """

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
        traverse(root_id, sec, points_dict, apical_branch = 0, basal_branch = 0, f=f)

swc_to_hoc(swc)
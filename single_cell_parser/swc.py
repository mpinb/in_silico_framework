import numpy as np
import warnings

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
        n_hillock_sections (int):
            Interpret the first ``n`` axonal sections as a hillock.
            NEURON allows to define separate sections that are direct descendants, such as the AIS
            being the direct and only child of the axon hillock. This information is lost in swc if
            they are the same label, since the second section's parent is simply the last point of the
            first section. This can be mitigated by assigning different labels to both.
            Passing an integer to this arg will force this writer to interpret the first ``n`` sections with label
            ``"AIS"`` to be assigned the label ``"Hillock"`` (label number ``6``) instead.
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
    n_assigned_hillock_sections = 0
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
        n_hillock_sections (int):
            Interpret the first ``n`` axonal sections as a hillock.
            NEURON allows to define separate sections that are direct descendants, such as the AIS
            being the direct and only child of the axon hillock. This information is lost in swc if
            they are the same label, since the second section's parent is simply the last point of the
            first section. This can be mitigated by assigning different labels to both.
            Passing an integer to this arg will force this writer to interpret the first ``n`` sections with label
            ``"AIS"`` to be assigned the label ``"Hillock"`` (label number ``6``) instead.
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
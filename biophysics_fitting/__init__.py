"""
This package contains code to generate and analyze biophysically detailed multi-compartmental models (MCM).

It provides two ways to generate mutli-compartmental models:

    1. BluePyOpt :cite:`Van_Geit_Gevaert_Chindemi_Roessert_Courcol_Muller_Schuermann_Segev_Markram_2016`, a Multi-Objective Evolutionary Algorithm (MOEA): :py:mod:`~biophysics_fitting.MOEA_EH_minimal`.
    2. An exploration algorithm: :py:mod:`~biophysics_fitting.exploration_from_seedpoint`.

The MOEA does not require any a priori assumptions on biophysical parameters to find a MCM, but fails to explore the full diversity of possible MCMs. 
On the other hand, the exploration approach can explore the full diversity of possible biophysical models, but also requires a MCM as a seedpoint in order to start. 
If you need to generate models from scratch, we recommend using the MOEA algorithm to find at least a single model, and then using this as a seedpoint for the exploration algorithm.
"""

import pandas as pd
import logging

logger = logging.getLogger("ISF").getChild(__name__)

RANGE_VARS_APICAL = [
    'NaTa_t.ina', 'Ca_HVA.ica', 'Ca_LVAst.ica', 'SKv3_1.ik', 'SK_E2.ik',
    'Ih.ihcn', 'Im.ik'
]
RANGE_VARS_ALL_CHANNELS = RANGE_VARS_APICAL + [
    'Nap_Et2.ina', 'K_Pst.ik', 'K_Tst.ik'
]


def connected_to_dend_beyond(cell, sec, beyond_dist, n_children_required=2):
    """
    Check if a given section is connected to dendrites that reach beyon :paramref:`beyond_dist`.
    Given a :class:`~single_cell_parser.cell.Cell` object and section number, 
    this method returns True if at least :paramref:`n_children_required` children 
    of the branchpoint reach beyond :paramref:`dist`.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        sec (int): Index of Cell section
        beyond_dist (float): Distance threshold
        n_children_required (int, optional): Least amount of children required. Defaults to 2.

    Returns:
        bool: Whether or not two of the section's children reach beyond :paramref:`beyond_dist`
    """
    if cell.distance_to_soma(sec, 1) > beyond_dist:  # and sec.label in ('ApicalDendrite', 'Dendrite'):
        return True
    else:
        dummy = sum(
            connected_to_dend_beyond(
                cell,
                c,
                beyond_dist,
                n_children_required=1)
            for c in sec.children()
            # if sec.label in ('ApicalDendrite', 'Dendrite')
        )
        if dummy >= n_children_required:
            return True
        else:
            return False


def get_inner_sec_dist_list(
    cell, 
    select=['ApicalDendrite', 'Dendrite'],
    connected_to_dend_beyond_distance=1000,
    z_offset=706,
    ):
    """
    Find all sections that are connected to dendrites that reach beyond a certain distance.
    Useful for filtering out outer terminating dendrites.
        
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        select (list, optional): Selection of sections to consider, based on their label. Defaults to ['ApicalDendrite', 'Dendrite'].
        connected_to_dend_beyond_distance (int, optional): Distance threshold (in um). Defaults to 1000 um.
        z_offset (int|float, optional): Offset for z-value. Defaults to 706 um (the average pia distance of a rat barrel cortex).

    Returns:
        dict: Dictionary mapping the z-coordinate (float) of each section point to the section (:class:`~single_cell_parser.cell.PySection`) object, including only sections that pass the filter.
    """
    #    sec_dist_dict = {cell.distance_to_soma(sec, 1.0): sec
    sec_dist_dict = {
        sec.pts[-1][2] - z_offset: sec
        for sec in cell.sections
        if connected_to_dend_beyond(cell, sec, connected_to_dend_beyond_distance) and sec.label in select
    }
    return sec_dist_dict


def get_branching_depth(cell, sec, beyond_dist=1000):
    """
    Given a Cell object and a section number, this method returns the branching depth (i.e. branching order) of that section.
    It counts the amount of sections that have children beyond some distance :paramref:`beyond_dist` inbetween the soma and the given section :paramref:`sec`.

    If this number is 0, that means that the given section, and all its parent sections up to the soma,
    have no children (that exceed a distance to soma of :paramref:`beyond_dist`).

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        sec (int): The section number

    Returns:
        int: Amount of sections between :paramref:`sec` and soma that have at least 2 children that are further from the soma than :paramref:`beyond_dist`
    """
    depth = connected_to_dend_beyond(cell, sec, beyond_dist)
    if sec.parent.label.lower() == 'soma':
        return depth
    else:
        return depth + get_branching_depth(cell, sec.parent)


def get_branching_depth_series(
    cell,
    z_offset=706
    ):
    """
    Find the branching depth of the inner sections of a :class:`~single_cell_parser.cell.Cell`.
        
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        z_offset (int | float, optional): Z coordinate offset for :py:meth:`get_inner_sec_dist_list`.
            Defaults to 706 um.

    Returns:
        pd.Series: contains the distance to :paramref:z_offset as index and a tuple (branching depth, section) as value
        
    Note:
        Careful: z-depth only accurate for D2-registered cells!
    """

    inner_sections = get_inner_sec_dist_list(cell, z_offset=z_offset)
    import six
    inner_sections_branching_depth = {
        k: (get_branching_depth(cell, sec), sec)
        for k, sec in six.iteritems(inner_sections)
    }
    inner_sections_branching_depth = pd.Series(inner_sections_branching_depth)
    return inner_sections_branching_depth


def get_main_bifurcation_section(
    cell,
    ):
    """
    Find the main bifurcation of a cell.
    This is the unique inner section whose branching depth is 1.
    In some morphologies, this section is unique, and no other sections are inner sections with branching depth 1.
    This is True for e.g. pyramidal cells with an apical dendrite.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object for which to find the main bifurcation section.
        assert_unique (bool, optional): whether or not to check if this section is unique in the morphology.
            Default: True
            
    Raises:
        AssertionError: If there are multiple sections who are both inner, and have branching depth 1. This means that there is no "main" bifurcation in the morphology.
    
    Returns:
        :class:`~single_cell_parser.cell.PySection`: The unique section that contains the main bifurcation.
    
    """
    sec_dist_list_filtered = get_first_order_bifurcation_sections(cell)
    assert len(sec_dist_list_filtered) == 1
    return sec_dist_list_filtered[0]


def get_first_order_bifurcation_sections(
    cell
    ):
    """
    Find all sections that are both inner sections, and are of branching order 1.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object for which to find the main bifurcation section.

    Returns:
        list: A list of :class:`~single_cell_parser.cell.PySection` sections that are both inner sections, and are of branching order 1. 
    """
    sec_dist_list = get_branching_depth_series(cell)
    sec_dist_list_filtered = [depth_sec_tuple[1] for depth_sec_tuple in sec_dist_list if depth_sec_tuple[0] == 1]
    return sec_dist_list_filtered
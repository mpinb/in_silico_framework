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
    """Given a :class:`~single_cell_parser.cell.Cell` object and section number, 
    this method returns true if at least two children of the branchpoint reach beyond dist

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        sec (int): Index of Cell section
        beyond_dist (float): Distance threshold
        n_children_required (int, optional): Least amount of children required. Defaults to 2.

    Returns:
        bool: Whether or not two of the section's children reach beyond ``beyond_dist``
    """
    if cell.distance_to_soma(
            sec, 1
    ) > beyond_dist:  # and sec.label in ('ApicalDendrite', 'Dendrite'):
        return True
    else:
        dummy = sum(
            connected_to_dend_beyond(cell,
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


def get_inner_sec_dist_list(cell, select=['ApicalDendrite', 'Dendrite']):
    """TODO: wat does this method do? Why take the y-value of the last point in a section and subtract 706?

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        select (list, optional): Selection of sections to consider, based on their label. Defaults to ['ApicalDendrite', 'Dendrite'].

    Returns:
        dict: _description_
    """
    #    sec_dist_dict = {cell.distance_to_soma(sec, 1.0): sec
    sec_dist_dict = {
        sec.pts[-1][2] - 706: sec
        for sec in cell.sections
        if connected_to_dend_beyond(cell, sec, 1000) and sec.label in select
    }
    return sec_dist_dict


def get_branching_depth(cell, sec, beyond_dist=1000):
    """Given a Cell object and a section number, this method returns the amount of sections that have children
    beyond some distance ``beyond_dist`` inbetween the soma and the given section.

    If this number is 0, that means that the given section, and all its parent sections up to the soma,
    have no children that exceed a distance to soma of ``beyond_dist``.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object
        sec (int): The section number

    Returns:
        int: Amount of sections between ``sec`` and soma that have at least 2 children that are further from the soma than ``beyond_dist``
    """
    depth = connected_to_dend_beyond(cell, sec, beyond_dist)
    if sec.parent.label.lower() == 'soma':
        return depth
    else:
        return depth + get_branching_depth(cell, sec.parent)


def get_branching_depth_series(cell):
    """Careful: z-depth only accurate for D2-registered cells!
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The Cell object

    Returns:
        pd.Series: contains the pia distance as index and a tuple (biforcation order, section) as value
    """

    inner_sections = get_inner_sec_dist_list(cell)
    import six
    inner_sections_branching_depth = {
        k: (get_branching_depth(cell, sec), sec)
        for k, sec in six.iteritems(inner_sections)
    }
    inner_sections_branching_depth = pd.Series(inner_sections_branching_depth)
    return inner_sections_branching_depth


def get_main_bifurcation_section(cell):
    sec_dist_list = get_branching_depth_series(cell)
    sec_dist_list_filtered = [sec[1] for sec in sec_dist_list if sec[0] == 1]
    assert len(sec_dist_list_filtered) == 1
    return sec_dist_list_filtered[0]
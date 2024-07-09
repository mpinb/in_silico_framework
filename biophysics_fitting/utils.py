'''
Created on Nov 01, 2018

@author: abast
'''

import numpy as np
from functools import partial


####################################
# selection of sections
####################################
def connected_to_structure_beyond(
    cell,
    sec,
    beyond_dist,
    beyond_struct=['ApicalDendrite'],
    n_children_required=1
    ):
    '''Checks if a :class:`~single_cell_parser.cell.Cell` section is connected to a structure
    at a soma distance larger than :paramref:`beyond_dist`. 
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        sec (:class:`~single_cell_parser.section.Section`): The section to check.
        beyond_dist (float): The distance from the soma to check.
        beyond_struct (list): The labels of the structures to check.
        n_children_required (int): The minimum number of children required to have a connection.
    
    This can be helpful to detect the main bifurcation of a L5PT, which is the bifurcation in which both children are connected to the tuft.'''
    if cell.distance_to_soma(sec, 1) > beyond_dist and sec.label in beyond_struct:
        return True
    else:
        sum_ = sum(
                connected_to_structure_beyond(cell, c, beyond_dist, n_children_required = 1)
                for c in sec.children()
                if sec.label in beyond_struct)
        if sum_ >= n_children_required:
            return True
        else:
            return False


connected_to_dend_beyond = partial(connected_to_structure_beyond,
                                   beyond_struct=['Dendrite', 'ApicalDendrite'])


def get_inner_sec_dist_dict(
    cell,
    beyond_dist=1000,
    beyond_struct=['ApicalDendrite'],
    n_children_required = 1):
    '''Get sections that connect to specific structures beyond a minimum distance.
    
    Fetches all sections that are connected to compartments with labels in :paramref:`beyond_struct`, and
    that have a minimum soma distance of :paramref:`beyond_dist`.
    This is useful to get sections of the apical trunk of an L5PT, filtering out oblique dendrites.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        beyond_dist (float): The minimum distance from the soma (um).
        beyond_struct (list): The labels of the structures to check.
        n_children_required (int): The minimum number of children required to have a connection.
        
    Returns:
        dict: A dictionary with the soma distance as key and the section as value.
        
    Note:
        See also: :py:meth:`~get_inner_section_at_distance` that returns the closest section at a specific distance, rather than all sections beyond some distance.
    '''
    sec_dist_dict = {
        cell.distance_to_soma(sec, 1.0): sec
        for sec in cell.sections
        if connected_to_structure_beyond(
            cell, sec, 
            beyond_dist,
            beyond_struct, 
            n_children_required = n_children_required)
    }
    return sec_dist_dict


def get_inner_section_at_distance(
    cell,
    dist,
    beyond_dist=1000,
    beyond_struct=['ApicalDendrite']
    ):
    '''Get sections that connect to specific structures at a particular distance.
    
    Fetches all sections that are connected to compartments with labels in :paramref:`beyond_struct`, and
    that have a soma distance of :paramref:`beyond_dist`.
    This is useful to get sections of the apical trunk of an L5PT, filtering out oblique dendrites.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma (um).
        beyond_dist (float): The minimum distance from the soma (um).
        beyond_struct (list): The labels of the structures to check.
        
    Returns:
        tuple: The section and the relative distance from the section to the soma. Only returns the section that's closest to the provided :paramref:`dist`.
        
    Note:
        See also: :py:meth:`~get_inner_sec_dist_dict` that returns all sections beyond some distance, rather than only the closest section at a specific distance.
    '''
    import six
    sec_dist_dict = get_inner_sec_dist_dict(cell, beyond_dist, beyond_struct)
    dummy = {k - dist: v for k, v in six.iteritems(sec_dist_dict) if k > dist}
    closest_sec = dummy[min(dummy)]
    x = (dist - cell.distance_to_soma(closest_sec, 0.0)) / closest_sec.L
    return closest_sec, x


def get_main_bifurcation_section(cell):
    '''Get the main bifurcation section of a cell
    
    Assumes the cell has a main bifurcation to begin with, such as a L5PT.
    A main bifuraction section is defined as a section::
    
        - with at least two children
        - whose parent is the soma.
        - (optional) whose children are beyond a certain distance (default: 1000 um). See :py:meth:`~get_inner_sec_dist_dict` for more information.
        
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        
    Returns:
        :class:`~single_cell_parser.section.Section`: The main bifurcation section.
    '''
    two_children_connected_list = get_inner_sec_dist_dict(cell, n_children_required = 2)
    two_children_connected_list = list(two_children_connected_list.values())
    sec = two_children_connected_list[0]
    while sec.parent() in two_children_connected_list:
        sec = sec.parent()
    return sec

def augment_cell_with_detailed_labels(cell):
    '''Augment section labels to discriminate the tuft, oblique, trunk and basal dendrites.
    
    Assigning these labels to section.label_detailed
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
    
    Returns: 
        None
        
    Note:
        This method is specific to L5PT neurons.
    '''
    def helper(secs):
        for sec in secs:
            sec.label_detailed = 'tuft'
            children = sec.children()
            helper(children)
    sec = get_main_bifurcation_section(cell)
    helper(sec.children())
    while sec != cell.soma:
        sec.label_detailed = 'trunk'
        sec = sec.parent
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            try:
                sec.label_detailed
            except AttributeError:
                 sec.label_detailed = 'oblique'
        elif sec.label in ['Dendrite', 'BasalDendrite']:
            sec.label_detailed = 'basal'
        else:
            sec.label_detailed = sec.label

#####################################
# read out Vm at section
#######################################


def tVec(cell):
    """Convenience method to convert a py:attr:`~single_cell_parser.cell.Cell.tVec` to a numpy array."""
    return np.array(cell.tVec)


def vmSoma(cell):
    """Convenience method to extract the soma voltage trace from a cell"""
    return np.array(cell.soma.recVList[0])


def vmMax(cell):
    """Calculate the maximum voltage of a cell at any timepoint, at any dendrite."""
    return np.max(
        [np.max(np.array(sec.recVList), axis=0) for sec in cell.sections],
        axis=0)


def _get_apical_sec_and_i_at_distance(cell, dist):
    """Get the apical section at a certain distance from the soma.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma (um).
        
    Returns:
        tuple: The section, the relative distance from the section to the soma, and the segment index.
    """
    sec, target_x = get_inner_section_at_distance(cell, dist)
    # roberts code to get closest segment
    mindx = 1
    for i in range(len(sec.segx)):
        dx = np.abs(sec.segx[i] - target_x)
        if dx < mindx:
            mindx = dx
            minSeg = i
    return sec, mindx, minSeg


def vmApical(cell, dist=None):
    """Fetch the membrane voltage of the apical dendrite at a certain distance from the soma.
    
    Assumes that the :class:`~single_cell_parser.cell.Cell` object has an apical dendrite::
    
        - It contains at least one section with the label "ApicalDendrite"
        - Such section exists at :paramref:`~dist` distance from the soma
        - The section has at least one child
        
    See :py:meth:`~get_inner_section_at_distance` for more information about which arguments can be used
    to define an apical section.

    """
    assert dist is not None
    sec, mindx, minSeg = _get_apical_sec_and_i_at_distance(cell, dist)
    return np.array(sec.recVList[minSeg])


def vmApical_position(cell, dist=None):
    sec, mindx, i = _get_apical_sec_and_i_at_distance(cell, dist)
    target_x = [seg for seg in sec][i].x
    index = np.argmin(np.abs(np.array(sec.relPts) - target_x))
    return sec.pts[index]


#########################################
# multiprocessing stuff that allows to evaluate code in a separate python / NEURON environment
#########################################

import multiprocessing.process
import cloudpickle


class Undemonize(object):
    '''A class used to resolve AssertionError: daemonic processes are not allowed to have children
    
    This might spawn child processes that do not terminate'''

    def __init__(self):
        self.p = multiprocessing.process.current_process()
        if 'daemon' in self.p._config:
            self.daemon_status_set = True
        else:
            self.daemon_status_set = False
        self.daemon_status_value = self.p._config.get('daemon')

    def __enter__(self):
        if self.daemon_status_set:
            del self.p._config['daemon']

    def __exit__(self, type, value, traceback):
        if self.daemon_status_set:
            self.p._config['daemon'] = self.daemon_status_value


import cloudpickle


def run_cloudpickled_remotely(queue):
    fun = cloudpickle.loads(queue.get())
    args = cloudpickle.loads(queue.get())
    queue.put(cloudpickle.dumps(fun(*args)))


def execute_in_child_process(fun):
    fun_cp = cloudpickle.dumps(fun)

    def fun(*args):
        queue = multiprocessing.Queue()
        queue.put(fun_cp)
        queue.put(cloudpickle.dumps(args))
        p = multiprocessing.Process(target=run_cloudpickled_remotely,
                                    args=(queue,))
        with Undemonize():
            p.start()
        p.join()
        out = cloudpickle.loads(queue.get())
        return out

    return fun


# def run_cloudpickled_remotely3(queue_to_child, queue_from_child):
#     fun = cloudpickle.loads(queue_to_child.get())
#     while True:
#         print('asd0')
#         args = cloudpickle.loads(queue_to_child.get())
#         print('asd1')
#         queue_form_child.put(cloudpickle.dumps(fun(*args)))
#         print('asd3')
#
# def execute_in_child_process_kept_alive(fun):
#     queue_to_child = multiprocessing.Queue()
#     queue_from_child = multiprocessing.Queue()
#     queue_to_child.put(cloudpickle.dumps(fun))
#     p = multiprocessing.Process(target=test.run_cloudpickled_remotely3,
#                                 args=(queue_to_child,queue_from_child))
#     with Undemonize():
#         p.start()
#     def fun(*args):
#         queue_to_child.put(cloudpickle.dumps(args))
#         out = cloudpickle.loads(queue_to_child.get())
#         return out
#     fun.process = p
#     return fun

from functools import partial


def pool_helper(callable_partial):
    callable_partial = cloudpickle.loads(callable_partial)
    return cloudpickle.dumps(callable_partial())


class VariableThatDoesNotGetPickled:

    def __init__(self, stored_item):
        self.stored_item = stored_item

    def __getstate__(self):
        return {'stored_item': None}


def execute_in_child_process_kept_alive(fun):
    pool_storage = VariableThatDoesNotGetPickled(
        None)  # None # multiprocessing.Pool(1)

    def _helper(*args, **kwargs):
        if pool_storage.stored_item is None:
            with Undemonize():
                pool_storage.stored_item = multiprocessing.Pool(1)
        p = cloudpickle.dumps(partial(fun, *args, **kwargs))
        out = pool_storage.stored_item.map(pool_helper, [p])[0]
        return cloudpickle.loads(out)

    #fun.pool = pool
    return _helper


class StreamToLogger(object):
    """
    Wrapper for a stream object that redirects writes to a logger instance.
    Can be used as a context manager::

        >>> with StreamToLogger() as sys.stdout:
        >>>    do_something()
    
    Used for reading in .hoc files that provide output due to various print statements in the `.hoc` file, or capturing NEURON output.
    """

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush()

    def flush(self):
        pass

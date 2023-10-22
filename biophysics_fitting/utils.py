'''
Created on Nov 01, 2018

@author: abast
'''

import numpy as np
from functools import partial


####################################
# selection of sections
####################################
def connected_to_structure_beyond(cell,
                                  sec,
                                  beyond_dist,
                                  struct_list=['Dendrite', 'ApicalDendrite']):
    if cell.distance_to_soma(sec, 1) > beyond_dist and sec.label in struct_list:
        return True
    else:
        return bool(
            sum(
                connected_to_dend_beyond(cell, c, beyond_dist)
                for c in sec.children()
                if sec.label in struct_list))


connected_to_dend_beyond = partial(connected_to_structure_beyond,
                                   struct_list=['Dendrite', 'ApicalDendrite'])


def get_inner_sec_dist_list(cell,
                            beyond_dist=1000,
                            beyond_struct=['ApicalDendrite']):
    '''returns sections, that are connected to compartments with labels in beyond_struct that have a minimum soma distance of
    beyond_dist. This is useful to get sections of the apical trunk filtering out oblique dendrites.'''
    sec_dist_dict = {
        cell.distance_to_soma(sec, 1.0): sec
        for sec in cell.sections
        if connected_to_structure_beyond(cell, sec, beyond_dist,
                                         ['ApicalDendrite'])
    }
    return sec_dist_dict


def get_inner_section_at_distance(cell,
                                  dist,
                                  beyond_dist=1000,
                                  beyond_struct=['ApicalDendrite']):
    '''Returns the section and relative position of that section, such that the soma distance (along the dendrite) is dist.
    Also, it is assured, that the section returned has children that have a soma distance beyond beyond_dist of the label in
    beyond_struct'''
    import six
    sec_dist_dict = get_inner_sec_dist_list(cell, beyond_dist, beyond_struct)
    dummy = {k - dist: v for k, v in six.iteritems(sec_dist_dict) if k > dist}
    closest_sec = dummy[min(dummy)]
    x = (dist - cell.distance_to_soma(closest_sec, 0.0)) / closest_sec.L
    return closest_sec, x


#####################################
# read out Vm at section
#######################################


def tVec(cell):
    return np.array(cell.tVec)


def vmSoma(cell):
    return np.array(cell.soma.recVList[0])


def vmMax(cell):
    return np.max(
        [np.max(np.array(sec.recVList), axis=0) for sec in cell.sections],
        axis=0)


def _get_apical_sec_and_i_at_distance(cell, dist):
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
    '''A hack to resolve AssertionError: daemonic processes are not allowed to have children
    
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
    Fake file-like stream object that redirects writes to a logger instance.
    Used for reading in .hoc files that provide output due to various print statements.
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

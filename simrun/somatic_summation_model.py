"""
.. deprecated:: 0.1.0
    This module is deprecated and will be removed in a future version.
    Functionality has been taken over by the :mod:`simrun.modular_reduced_model_inference` module.

:skip-doc:
"""

import numpy as np
from data_base.utils import convertible_to_int
from collections import defaultdict
from config.isf_logging import logger as isf_logger
logger = isf_logger.getChild(__name__)

logger.warning('Deprecation warning: This module is deprecated and will be removed in a future release.')


def roll_rows_independently(A, r):
    '''https://stackoverflow.com/questions/20360675/roll-rows-of-a-matrix-independently%5D'''
    if not isinstance(A, np.ndarray):
        raise ValueError()
    if not isinstance(r, np.ndarray):
        raise ValueError()
    rows, column_indices = np.ogrid[:A.shape[0], :A.shape[1]]
    # Use always a negative shift, so that column_indices are valid.
    # (could also use module operation)
    r[r < 0] += A.shape[1]
    column_indices = column_indices - r[:, np.newaxis]
    result = A[rows, column_indices]
    return result


#def roll_rows_independently(a, r):
#    '''https://stackoverflow.com/questions/20360675/roll-rows-of-a-matrix-independently%5D'''
#    from skimage.util.shape import view_as_windows as viewW
#
#    # Concatenate with sliced to cover all rolls
#    a_ext = np.concatenate((a,a[:,:-1]),axis=1)
#
#    # Get sliding windows; use advanced-indexing to select appropriate ones
#    n = a.shape[1]
#    return viewW(a_ext,(1,n))[np.arange(len(r)), (n-r)%n,0]


class ParseVT:

    def __init__(self, psp, dt=0.025, tStop=300):
        self.psp = psp
        self.dt = dt
        self.tStop = tStop  # tStop: end of simulated voltage traces
        self.tEnd = psp.tEnd  # tEnd: end of simulation of PSPs
        self.tStim = psp.tStim
        self.vt = psp.get_voltage_traces()
        self.vt_array = None
        self.vt_array_index = None
        self._compute_vt_array()

    def _compute_vt_array(self):
        tEnd = self.tEnd
        tStop = self.tStop
        dt = self.dt
        vt = self.vt
        psp = self.psp
        index = []
        array = []
        for celltype in sorted(self.vt.keys()):
            for synapse_id in range(len(vt[celltype][1.][1.][2])):
                index.append((celltype, synapse_id))
                t, v = vt[celltype][1.][1.][2][synapse_id], vt[celltype][1.][
                    1.][3][synapse_id]
                t, v = np.arange(0, tEnd,
                                 dt), np.interp(np.arange(0, tEnd, dt), t, v)
                t_baseline, v_baseline = vt[celltype][1.][1.][0], vt[celltype][
                    1.][1.][1]
                t_baseline, v_baseline = np.arange(0, tEnd, dt), np.interp(
                    np.arange(0, tEnd, dt), t_baseline, v_baseline)
                cutoff_index = int(np.round(psp.tStim / dt))
                out = (v - v_baseline)[cutoff_index:]
                out = np.concatenate(
                    [out, np.zeros(int(tStop / dt) - len(out))])
                array.append(out)
        self.vt_array = np.array(array)
        self.vt_array_index = {i: lv for lv, i in enumerate(index)}

    def _get_num_index(self, indices):
        return [self.vt_array_index[i] for i in indices]

    def get_vt_by_synapses(self, indices):
        indices = self._get_num_index(indices)
        return self.vt_array[indices, :]

    #def _get_offsets_and_indices_from_sa(self, sa):
    #    activation_columns = [c for c in sa.columns if I.utils.convertible_to_int(c)]
    #    synapses = []
    #    offsets = []
    #    for lv, (name, data) in enumerate(sa.iterrows()):
    #        synapse_type = data.synapse_type
    #        synapse_ID = data.synapse_ID
    #        for c in activation_columns:
    #            activation_time = data[c]
    #            if I.np.isnan(activation_time):
    #                break
    #            synapses.append((synapse_type, synapse_ID))
    #            offsets.append(activation_time)
    #    offsets = (I.np.array(offsets) / self.dt).astype(int)
    #    return synapses, offsets

    def _get_offsets_and_indices_from_sa(self, sa):
        activation_columns = [c for c in sa.columns if convertible_to_int(c)]
        synapses = []
        offsets = []
        dt = self.dt
        for c in activation_columns:
            sa_dummy = sa[['synapse_type', 'synapse_ID', c]].dropna()
            offsets.extend(sa_dummy[c] / dt)
            synapses.extend(
                list(zip(sa_dummy.synapse_type, sa_dummy.synapse_ID)))
        #offsets = (I.np.array(offsets) / dt).astype('i8')
        return synapses, np.array(offsets).astype(int)

    def parse_sa(self, sa, weights=None):
        synapses, offsets = self._get_offsets_and_indices_from_sa(sa)
        array = self.get_vt_by_synapses(synapses)
        if weights is not None:
            c = np.array([weights[s] for s in synapses])
            array = (array.T * c).T
        extended_array = np.concatenate(
            [np.zeros(array.shape), array,
             np.zeros(array.shape)], axis=1)
        extended_array_rolled = roll_rows_independently(
            extended_array, offsets)[:, array.shape[1]:array.shape[1] * 2]
        return np.arange(0, self.tStop,
                         self.dt), extended_array_rolled.sum(axis=0)

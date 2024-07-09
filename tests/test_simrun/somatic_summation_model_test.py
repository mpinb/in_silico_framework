from . import decorators
from . import context
import numpy as np
import pandas as pd
from Interface import defaultdict_defaultdict
from simrun.somatic_summation_model import *


class FakePSP:

    def __init__(self, tEnd=3, tStim=1):
        self.tEnd = tEnd
        self.tStim = tStim

    def get_voltage_traces(self):
        out = defaultdict_defaultdict()
        converter = lambda l: list(l)
        out['Generic1'][1.][1.][0] = converter([0, 1, 2, 3])
        out['Generic1'][1.][1.][1] = converter([0, 1, 0, 0])
        out['Generic1'][1.][1.][2] = list([[0, 1, 2, 3], [0, 1, 2, 3],
                                           [0, 1, 2, 3]])
        out['Generic1'][1.][1.][3] = list([[0, 1.1, 0, 0], [0, 1.2, 0, 0],
                                           [0, 1.3, 0, 0]])
        out['Generic2'][1.][1.][0] = converter([0, 1, 2, 3])
        out['Generic2'][1.][1.][1] = converter([0, 1, 1, 0])
        out['Generic2'][1.][1.][2] = list([[0, 1, 2, 3], [0, 1, 2, 3],
                                           [0, 1, 2, 3]])
        out['Generic2'][1.][1.][3] = list([[0, 1.1, 1.1, 0], [0, 1.2, 1.1, 0],
                                           [0, 1.3, 1.1, 0]])

        return out
        pass


def _get_pvt(tEnd=3, tStim=1, dt=1, tStop=5):
    psp = FakePSP(tEnd, tStim)
    pvt = ParseVT(psp, dt=dt, tStop=tStop)
    return pvt


def get_fake_synapse_activation_dataframe():
    index = ['sim_trial_index_1', 'sim_trial_index_1']
    columns = ['synapse_type', 'synapse_ID', 0, 1, 2]
    array = [['Generic1', 0, 0, 10, np.NaN], ['Generic2', 1, 5, 15, 25]]
    return pd.DataFrame(array, columns=columns, index=index)


class TestSomaticSummationModel:
    #@decorators.testlevel(1)
    def test_roll_rows_independently(self):
        A = np.array([[1, 2, 3], [2, 3, 4], [3, 4, 5]])
        A_rolled = roll_rows_independently(A, np.array([1, 0, -1]))
        A_expected = np.array([[3, 1, 2], [2, 3, 4], [4, 5, 3]])
        np.testing.assert_array_equal(A_rolled, A_expected)

    def test_compute_vt_array(self):
        pvt = _get_pvt(3, 1, 1, 5)
        assert pvt.vt_array.shape == (6, 5)
        pvt = _get_pvt(3, 1, 1, 6)
        assert pvt.vt_array.shape == (6, 6)
        pvt = _get_pvt(3, 1, .5, 6)
        assert pvt.vt_array.shape == (6, 12)
        vt_array_index_expected = {
            ('Generic1', 0): 0,
            ('Generic1', 1): 1,
            ('Generic1', 2): 2,
            ('Generic2', 0): 3,
            ('Generic2', 1): 4,
            ('Generic2', 2): 5
        }
        assert pvt.vt_array_index == vt_array_index_expected
        pvt = _get_pvt(3, 1, 1, 5)
        vt_array_expected = np.array([[0.1, 0., 0., 0., 0.],
                                      [0.2, 0., 0., 0., 0.],
                                      [0.3, 0., 0., 0., 0.],
                                      [0.1, 0.1, 0., 0., 0.],
                                      [0.2, 0.1, 0., 0., 0.],
                                      [0.3, 0.1, 0., 0., 0.]])
        np.testing.assert_array_almost_equal(pvt.vt_array, vt_array_expected)
        pvt = _get_pvt(3, 0, 1, 5)
        vt_array_expected = np.array([[0., 0.1, 0., 0., 0.],
                                      [0., 0.2, 0., 0., 0.],
                                      [0., 0.3, 0., 0., 0.],
                                      [0., 0.1, 0.1, 0., 0.],
                                      [0., 0.2, 0.1, 0., 0.],
                                      [0., 0.3, 0.1, 0., 0.]])
        np.testing.assert_array_almost_equal(pvt.vt_array, vt_array_expected)
        pvt = _get_pvt(3, 0.5, 1, 5)
        np.testing.assert_array_almost_equal(pvt.vt_array, vt_array_expected)
        pvt = _get_pvt(3, 0.6, 1, 5)
        vt_array_expected = np.array([[0.1, 0., 0., 0., 0.],
                                      [0.2, 0., 0., 0., 0.],
                                      [0.3, 0., 0., 0., 0.],
                                      [0.1, 0.1, 0., 0., 0.],
                                      [0.2, 0.1, 0., 0., 0.],
                                      [0.3, 0.1, 0., 0., 0.]])
        np.testing.assert_array_almost_equal(pvt.vt_array, vt_array_expected)

    def test_get_offsets_and_indices_from_sa(self):
        sa = get_fake_synapse_activation_dataframe()
        pvt = _get_pvt(3, 1, 1, 5)
        synapses, offsets = pvt._get_offsets_and_indices_from_sa(sa)
        synapses_expected = [('Generic1', 0), ('Generic2', 1), ('Generic1', 0),
                             ('Generic2', 1), ('Generic2', 1)]
        offsets_expected = np.array([0, 5, 10, 15, 25])
        assert synapses == synapses_expected
        np.testing.assert_array_almost_equal(offsets, offsets_expected)

    def test_parse_sa_without_weights(self):
        pvt = _get_pvt(3, 1, 1, 30)
        t, v = pvt.parse_sa(get_fake_synapse_activation_dataframe())
        t_expected = np.array([
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
            19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29
        ])
        v_expected = np.array([
            0.1, 0., 0., 0., 0., 0.2, 0.1, 0., 0., 0., 0.1, 0., 0., 0., 0., 0.2,
            0.1, 0., 0., 0., 0., 0., 0., 0., 0., 0.2, 0.1, 0., 0., 0.
        ])
        np.testing.assert_array_almost_equal(t, t_expected)
        np.testing.assert_array_almost_equal(v, v_expected)

    def test_parse_sa_with_weights(self):
        pvt = _get_pvt(3, 1, 1, 30)
        t, v = pvt.parse_sa(get_fake_synapse_activation_dataframe(),
                            weights={
                                ('Generic1', 0): 3,
                                ('Generic2', 1): 2
                            })
        t_expected = np.array([
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
            19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29
        ])
        v_expected = np.array([
            0.3, 0., 0., 0., 0., 0.4, 0.2, 0., 0., 0., 0.3, 0., 0., 0., 0., 0.4,
            0.2, 0., 0., 0., 0., 0., 0., 0., 0., 0.4, 0.2, 0., 0., 0.
        ])
        np.testing.assert_array_almost_equal(t, t_expected)
        np.testing.assert_array_almost_equal(v, v_expected)

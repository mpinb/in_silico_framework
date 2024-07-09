from __future__ import absolute_import
#from ..context import *
from simrun.reduced_model.get_kernel import concatenate_return_boundaries, ReducedLdaModel,\
    compare_lists_by_none_values
import numpy as np
import pandas as pd
import pytest


def get_test_X_y(n_samples=1000, n_timepoints=100):
    X = np.random.randint(0, 21, size=(n_samples, n_timepoints))
    v1 = np.array([0] * 25 + [1] * 50 + [0] * 25)
    dummy = (np.dot(X, v1) - 500) / 20.
    y = dummy > np.random.rand(dummy.size)
    return X, y


def get_test_Rm(fresh_mdb):
    X, y = get_test_X_y(n_samples=5000)
    fresh_mdb['test_synapse_activation'] = X
    fresh_mdb['spike_times'] = pd.DataFrame(y).astype('f8').replace(
        0, np.NaN).replace(1, 100)
    Rm = ReducedLdaModel(['test_synapse_activation'], output_window_min = 99, output_window_max = 101, \
                    synapse_activation_window_width = 50)
    Rm.fit([fresh_mdb])
    return Rm


@pytest.mark.xfail(strict=False,
                   reason="This test is statistical, and may sometimes fail.")
def test_statistical_ReducedLdaModel_inference(fresh_mdb):
    '''compare model infered from test data to expectancy'''
    Rm = get_test_Rm(fresh_mdb)
    Rm.plot()  # make sure this can be executed

    assert 200 < np.array(Rm.lda_values).mean() < 400  ##!!
    assert Rm.lookup_series[0][150] == 0
    assert Rm.lookup_series[0][500] == 1
    assert 0.1 < Rm.lookup_series[0][350] < 0.9
    mean1, std1 = list(Rm.kernel_dict[0].values())[0][:25].mean(), list(
        Rm.kernel_dict[0].values())[0][:25].std()
    mean2, std2 = list(Rm.kernel_dict[0].values())[0][25:].mean(), list(
        Rm.kernel_dict[0].values())[0][25:].std()
    np.testing.assert_array_less(max([std1, std2]) / min([std1, std2]), 3)
    np.testing.assert_array_less(3, abs(mean1 - mean2) / max([std1, std2]))
    #import Interface as I
    #mdb = I.ModelDataBase('/nas1/Data_arco/project_src/in_silico_framework/test_model_data_base/data/already_initialized_mdb_for_compatibility_testing/', nocreate = True)
    #Rm.mdb_list = None
    #mdb['reduced_model'] = Rm


@pytest.mark.xfail(strict=False,
                   reason="This test is statistical, and may sometimes fail.")
def test_statistical_ReducedLdaModel_apply(fresh_mdb):
    '''compare model infered from test data to expectancy'''
    X, y = get_test_X_y(n_samples=5000)
    fresh_mdb['test_synapse_activation'] = X
    fresh_mdb['spike_times'] = pd.DataFrame(y).astype('f8').replace(
        0, np.NaN).replace(1, 100)
    Rm = ReducedLdaModel(['test_synapse_activation'], output_window_min = 99, output_window_max = 101, \
                    synapse_activation_window_width = 50, cache = False)
    Rm.fit([fresh_mdb])
    mn = 0
    res = Rm.apply_static(fresh_mdb, model_number=mn)
    np.testing.assert_equal(res.lda_values, Rm.lda_values[mn])


@pytest.mark.xfail(strict=False,
                   reason="This test is statistical, and may sometimes fail.")
def test_statistical_ReducedLdaModel_apply_data_outside_trainingsdata(
        fresh_mdb):
    '''compare model infered from test data to expectancy'''
    X, y = get_test_X_y(n_samples=5000)
    fresh_mdb['test_synapse_activation'] = X
    fresh_mdb['spike_times'] = pd.DataFrame(y).astype('f8').replace(
        0, np.NaN).replace(1, 100)
    Rm = ReducedLdaModel(['test_synapse_activation'], output_window_min = 99, output_window_max = 101, \
                    synapse_activation_window_width = 50, cache = False)
    Rm.fit([fresh_mdb])
    mn = 0
    res = Rm.apply_static({'test_synapse_activation': X - 10000},
                          model_number=mn)
    assert res.p_spike.values.mean() == 0
    res = Rm.apply_static({'test_synapse_activation': X + 10000},
                          model_number=mn)
    assert res.p_spike.values.mean() == 1  ##!!


def test_concatenate_return_boundaries():
    a = np.array([[1, 2, 3], [2, 3, 4]])
    b = a + 1
    c = (b + 1)[:, :2]

    values = [a, b, c]
    X, boundaries = concatenate_return_boundaries(values, axis=1)
    for lv, v in enumerate(values):
        np.testing.assert_equal(v, X[:, boundaries[lv][0]:boundaries[lv][1]])

    t_values = [np.transpose(v) for v in values]
    X_2, boundaries_2 = concatenate_return_boundaries(t_values, axis=0)
    assert boundaries == boundaries_2


def test_compare_lists_by_none_values():
    assert compare_lists_by_none_values(['', None, None], [1, None, None])
    assert not compare_lists_by_none_values(['', None, None],
                                            [None, None, None])
    assert not compare_lists_by_none_values(['', None, None], [None, '', None])
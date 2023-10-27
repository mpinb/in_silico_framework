import numpy as np
from pandas.util.testing import assert_frame_equal
import dask 
from model_data_base.IO.LoaderDumper import dask_to_csv, numpy_to_npy, pandas_to_parquet, dask_to_parquet, \
                                pandas_to_msgpack, to_pickle, pandas_to_pickle, dask_to_msgpack, \
                                dask_to_categorized_msgpack, to_cloudpickle, reduced_lda_model
from tests.test_simrun2.reduced_model.get_kernel_test import get_test_Rm
from numpy.testing import assert_array_equal
from model_data_base.utils import df_colnames_to_str
import pytest
import six

def robust_del_fun(mdb, key):
    try:
        del mdb[key]
    except KeyError:
        pass


def clean_up(mdb):
    robust_del_fun(mdb, 'synapse_activation2')
    robust_del_fun(mdb, 'voltage_traces2')
    robust_del_fun(mdb, 'test')


def data_frame_generic_small(mdb, pdf, ddf, dumper, client=None):
    """
    This function provides a generic way to test dumpers for dataframes.

    Args:
        mdb (ModelDataBase): An instance of the ModelDataBase class.
        pdf (pd.DataFrame): A pandas DataFrame.
        ddf (dask.DataFrame): A dask DataFrame.
        dumper (string or dumper): A string or dumper object.
        client (distrubuted.Client, optional): A distributed client object. Defaults to None.
    """
    #index not set
    clean_up(mdb)
    if client is None:
        mdb.setitem('test', ddf, dumper=dumper)
    else:
        mdb.setitem('test', ddf, dumper=dumper, client=client)
    dummy = mdb['test']
    a = dask.compute(dummy)[0].reset_index(drop=True)
    b = pdf.reset_index(drop=True)
    if dumper in (pandas_to_parquet, dask_to_parquet):
        b = df_colnames_to_str(b)
    assert_frame_equal(a, b)
    
    #sorted index set
    clean_up(mdb)
    if client is None:
        mdb.setitem('test', ddf.set_index(0), dumper=dumper)
    else:
        mdb.setitem('test', ddf.set_index(0), dumper=dumper, client=client)
    dummy = mdb['test']
    a = dask.compute(dummy)[0]
    b = pdf.set_index(0)
    if dumper in (pandas_to_parquet, dask_to_parquet):
        b = df_colnames_to_str(b)
        b.index.name = str(b.index.name)
    assert_frame_equal(a, b)

def test_dask_to_csv_small(fresh_mdb, pdf, ddf):
    data_frame_generic_small(fresh_mdb, pdf, ddf, dask_to_csv)

def test_dask_to_msgpack_small(fresh_mdb, pdf, ddf, client):
    data_frame_generic_small(fresh_mdb, pdf, ddf, dask_to_msgpack,
        client=client)

def test_dask_to_categorized_msgpack_small(fresh_mdb, pdf, ddf, client):
    data_frame_generic_small(fresh_mdb, pdf, ddf, dask_to_categorized_msgpack,
        client=client)

def test_pandas_to_msgpack_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), pandas_to_msgpack)

@pytest.mark.skipif(six.PY2, reason="Pandas DataFrames objects have no attribute `to_parquet` in Python 2.")
def test_pandas_to_parquet_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), pandas_to_parquet)

@pytest.mark.skipif(six.PY2, reason="Pandas DataFrames objects have no attribute `to_parquet` in Python 2.")
def test_dask_to_parquet_small(fresh_mdb, pdf, ddf, client):
    data_frame_generic_small(fresh_mdb, pdf, ddf, dask_to_parquet, client=client)

def test_pandas_to_pickle_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), pandas_to_pickle)

def test_to_pickle_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), to_pickle)

def test_to_cloudpickle_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), to_cloudpickle)

def test_self_small(fresh_mdb, pdf):
    data_frame_generic_small(fresh_mdb, pdf, pdf.copy(), 'self')

def test_numpy_to_npy(fresh_mdb, pdf):

    def fun(x):
        clean_up(fresh_mdb)
        fresh_mdb.setitem('test', x, dumper=numpy_to_npy)
        dummy = fresh_mdb['test']
        assert_array_equal(dummy, x)

    fun(np.random.randint(5, size=(100, 100)))
    fun(np.random.randint(5, size=(100,)))
    fun(np.array([]))

def test_reduced_lda_model(fresh_mdb):
        Rm = get_test_Rm(fresh_mdb)
        # does not change the original object
        st = Rm.st
        lda_values = Rm.lda_values
        lda_value_dicts = Rm.lda_value_dicts
        mdb_list = Rm.mdb_list

        fresh_mdb.setitem('rm', Rm, dumper=reduced_lda_model)

        assert st is Rm.st
        assert lda_values is Rm.lda_values
        assert lda_value_dicts is Rm.lda_value_dicts
        assert mdb_list is Rm.mdb_list

        # can be loaded
        Rm_reloaded = fresh_mdb['rm']

        # is functional
        Rm_reloaded.plot()
        fresh_mdb.setitem('rm2', Rm_reloaded, dumper=reduced_lda_model)
        Rm_reloaded.get_lookup_series_for_different_refractory_period(10)
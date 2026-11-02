import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import dask.dataframe as dd
from pandas.testing import assert_frame_equal
import dask 
from config import isf_is_using_legacy_mdb
from data_base.IO.LoaderDumper import (
    numpy_to_npy, 
    pandas_to_parquet, 
    dask_to_parquet,
    pandas_to_msgpack, 
    to_pickle, 
    pandas_to_pickle, 
    dask_to_msgpack,
    dask_to_categorized_msgpack, 
    to_cloudpickle, 
    reduced_lda_model,
    )
from data_base.IO.LoaderDumper.meta import read_object_meta
from tests.test_simrun.reduced_model.get_kernel_test import get_test_Rm
from numpy.testing import assert_array_equal
import pytest
import six

def robust_del_fun(db, key):
    try:
        del db[key]
    except KeyError:
        pass


def clean_up(db):
    robust_del_fun(db, 'synapse_activation2')
    robust_del_fun(db, 'voltage_traces2')
    robust_del_fun(db, 'test')

def small_numpy_dump(x, db, dumper):
    clean_up(db)
    db.set('test', x, dumper=dumper)
    dummy = db['test']
    assert_array_equal(dummy, x)

def small_data_frame_test(db, pdf, ddf, dumper, client=None):
    """
    This function provides a generic way to test dumpers for dataframes.

    Args:
        db (DataBase): An instance of the DataBase class.
        pdf (pd.DataFrame): A pandas DataFrame.
        ddf (dask.DataFrame): A dask DataFrame.
        dumper (string or dumper): A string or dumper object.
        client (distrubuted.Client, optional): A distributed client object. Defaults to None.
    """
    #index not set
    clean_up(db)
    if client is None:
        db.set('test', ddf, dumper=dumper)
    else:
        db.set('test', ddf, dumper=dumper, client=client)
    dummy = db['test']
    a = dask.compute(dummy)[0].reset_index(drop=True)
    b = pdf.reset_index(drop=True)
    assert_frame_equal(a, b)
    
    #sorted index set
    clean_up(db)
    if client is None:
        db.set('test', ddf.set_index(0), dumper=dumper)
    else:
        db.set('test', ddf.set_index(0), dumper=dumper, client=client)
    dummy = db['test']
    a = dask.compute(dummy)[0]
    b = pdf.set_index(0)
    assert_frame_equal(a, b)

def test_dask_to_msgpack_small(empty_db, pdf, ddf, client):
    small_data_frame_test(empty_db, pdf, ddf, dask_to_msgpack,
        client=client)

def test_dask_to_categorized_msgpack_small(empty_db, pdf, ddf, client):
    small_data_frame_test(empty_db, pdf, ddf, dask_to_categorized_msgpack,
        client=client)

def test_pandas_to_msgpack_small(empty_db, pdf):
    small_data_frame_test(empty_db, pdf, pdf.copy(), pandas_to_msgpack)

@pytest.mark.skipif(six.PY2, reason="Pandas DataFrames objects have no attribute `to_parquet` in Python 2.")
def test_pandas_to_parquet_small(empty_db, pdf):
    small_data_frame_test(empty_db, pdf, pdf.copy(), pandas_to_parquet)

@pytest.mark.skipif(six.PY2, reason="Pandas DataFrames objects have no attribute `to_parquet` in Python 2.")
def test_dask_to_parquet_small(empty_db, pdf, ddf, client):
    small_data_frame_test(empty_db, pdf, ddf, dask_to_parquet, client=client)

def _partition_files(savedir):
    return sorted(os.path.join(savedir, f) for f in os.listdir(savedir) if f.endswith('.parquet'))


def _all_none_then_int_arrays():
    pdf = pd.DataFrame({'a': [None, None, np.array([1, 2])], 'b': [1., 2., 3.]}, index=pd.Index([0, 1, 2]))
    return pdf, dd.from_delayed([dask.delayed(pdf.iloc[:2]), dask.delayed(pdf.iloc[2:])], meta=pdf.iloc[:0])


def test_dask_to_parquet_writes_every_partition_with_schema_and_compression(tmp_path):
    pdf, ddf = _all_none_then_int_arrays()
    schema = pa.schema([('a', pa.list_(pa.float64())), ('b', pa.float64()), ('__index_level_0__', pa.int64())])
    dask_to_parquet.dump(ddf, str(tmp_path), schema=schema, compression='zstd')
    assert len(_partition_files(str(tmp_path))) == 2
    for path in _partition_files(str(tmp_path)):
        assert pq.read_schema(path).equals(schema)
        assert pq.ParquetFile(path).metadata.row_group(0).column(0).compression == 'ZSTD'
    loaded = dask_to_parquet.Loader(read_object_meta(str(tmp_path))).get(str(tmp_path)).compute()
    assert list(loaded.index) == [0, 1, 2]
    assert loaded['a'].iloc[0] is None and list(loaded['a'].iloc[2]) == [1., 2.]


def test_dask_to_parquet_default_infers_schema_per_partition(tmp_path, client):
    pdf, ddf = _all_none_then_int_arrays()
    dask_to_parquet.dump(ddf, str(tmp_path), client=client)
    types = [pq.read_schema(path).field('a').type for path in _partition_files(str(tmp_path))]
    assert types == [pa.null(), pa.list_(pa.int64())]
    for path in _partition_files(str(tmp_path)):
        assert pq.ParquetFile(path).metadata.row_group(0).column(0).compression == dask_to_parquet.COMPRESSION.upper()


def test_pandas_to_pickle_small(empty_db, pdf):
    small_data_frame_test(empty_db, pdf, pdf.copy(), pandas_to_pickle)

def test_to_pickle_small(empty_db, pdf):
    small_data_frame_test(empty_db, pdf, pdf.copy(), to_pickle)

def test_to_cloudpickle_small(empty_db, pdf):
    small_data_frame_test(empty_db, pdf, pdf.copy(), to_cloudpickle)

def test_default_small(empty_db, pdf):
    # unspecified dumper, should be to_cloudpickle
    small_data_frame_test(empty_db, pdf, pdf.copy(), None)

def test_numpy_to_npy(empty_db, pdf):
    small_numpy_dump(np.random.randint(5, size=(100, 100)), empty_db, numpy_to_npy)
    small_numpy_dump(np.random.randint(5, size=(100,)), empty_db, numpy_to_npy)
    small_numpy_dump(np.array([]), empty_db, numpy_to_npy)

def test_reduced_lda_model(empty_db):
        Rm = get_test_Rm(empty_db)
        # does not change the original object
        st = Rm.st
        lda_values = Rm.lda_values
        lda_value_dicts = Rm.lda_value_dicts
        db_list = Rm.db_list

        empty_db.set('rm', Rm, dumper=reduced_lda_model)

        assert st is Rm.st
        assert lda_values is Rm.lda_values
        assert lda_value_dicts is Rm.lda_value_dicts
        assert db_list is Rm.db_list

        # can be loaded
        Rm_reloaded = empty_db['rm']

        # is functional
        Rm_reloaded.plot()
        empty_db.set('rm2', Rm_reloaded, dumper=reduced_lda_model)
        Rm_reloaded.get_lookup_series_for_different_refractory_period(10)

@pytest.mark.skipif(isf_is_using_legacy_mdb(), reason="numpy_to_zarr is not implemented for mdb.")
def test_numpy_to_zarr(empty_db):
    from data_base.IO.LoaderDumper import numpy_to_zarr
    small_numpy_dump(np.random.randint(5, size=(100, 100)), empty_db, numpy_to_zarr)
    small_numpy_dump(np.random.randint(5, size=(100,)), empty_db, numpy_to_zarr)
    small_numpy_dump(np.array([]), empty_db, numpy_to_zarr)
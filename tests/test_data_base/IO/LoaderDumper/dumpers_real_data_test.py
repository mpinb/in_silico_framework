from data_base.data_base import DataBase
from pandas.util.testing import assert_frame_equal
from data_base.IO.LoaderDumper import dask_to_msgpack, dask_to_categorized_msgpack
import tempfile


def robust_del_fun(db, key):
    try:
        del db[key]
    except KeyError:
        pass


def real_data_generic(db_, dumper_, client_=None):
    """Helper method for further tests
    Does not ask for any fixtures

    Args:
        db_ (DataBase): db
        dumper_ (dumper object): the dumper object. Must have a dump() method
        client_ (distributed.Client, optional): client object. Defaults to None.
    """
    if client_ is None:
        db_.set('voltage_traces2', db_['voltage_traces'], dumper=dumper_)
    else:
        db_.set(
            'voltage_traces2',
            db_['voltage_traces'],
            dumper=dumper_,
            client=client_)
    dummy = db_['voltage_traces2']
    b = db_['voltage_traces'].compute(scheduler="multiprocessing")
    a = dummy.compute(scheduler="multiprocessing")
    assert_frame_equal(a, b, check_column_type=False)

    if client_ is None:
        db_.set(
            'synapse_activation2',    
            db_['synapse_activation'],
            dumper=dumper_)
    else:
        db_.set(
            'synapse_activation2',
            db_['synapse_activation'],
            dumper=dumper_,
            client=client_)
    dummy = db_['synapse_activation2']
    b = db_['synapse_activation'].compute(scheduler="multiprocessing")
    a = dummy.compute(scheduler="multiprocessing")
    assert_frame_equal(a, b)


def test_dask_to_categorized_msgpack_real_data(client, fresh_db):
    real_data_generic(db_=fresh_db,
                      dumper_=dask_to_categorized_msgpack,
                      client_=client)


def test_dask_to_msgpack_real_data(client, fresh_db):
    real_data_generic(db_=fresh_db, dumper_=dask_to_msgpack, client_=client)

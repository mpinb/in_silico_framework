from pandas.util.testing import assert_frame_equal
from data_base.model_data_base.IO.LoaderDumper import dask_to_msgpack, dask_to_categorized_msgpack


def robust_del_fun(mdb, key):
    try:
        del mdb[key]
    except KeyError:
        pass


def real_data_generic(mdb_, dumper_, client_=None):
    """Helper method for further tests
    Does not ask for any fixtures

    Args:
        mdb_ (DataBase): mdb
        dumper_ (dumper object): the dumper object. Must have a dump() method
        client_ (distributed.Client, optional): client object. Defaults to None.
    """
    if client_ is None:
        mdb_.setitem('voltage_traces2', mdb_['voltage_traces'], dumper=dumper_)
    else:
        mdb_.setitem('voltage_traces2',
                     mdb_['voltage_traces'],
                     dumper=dumper_,
                     client=client_)
    dummy = mdb_['voltage_traces2']
    b = mdb_['voltage_traces'].compute(scheduler="multiprocessing")
    a = dummy.compute(scheduler="multiprocessing")
    assert_frame_equal(a, b, check_column_type=False)

    if client_ is None:
        mdb_.setitem('synapse_activation2',
                     mdb_['synapse_activation'],
                     dumper=dumper_)
    else:
        mdb_.setitem('synapse_activation2',
                     mdb_['synapse_activation'],
                     dumper=dumper_,
                     client=client_)
    dummy = mdb_['synapse_activation2']
    b = mdb_['synapse_activation'].compute(scheduler="multiprocessing")
    a = dummy.compute(scheduler="multiprocessing")
    assert_frame_equal(a, b)


def test_dask_to_categorized_msgpack_real_data(client, fresh_mdb):
    real_data_generic(mdb_=fresh_mdb,
                      dumper_=dask_to_categorized_msgpack,
                      client_=client)


def test_dask_to_msgpack_real_data(client, fresh_mdb):
    real_data_generic(mdb_=fresh_mdb, dumper_=dask_to_msgpack, client_=client)

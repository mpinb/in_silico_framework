import dask.dataframe
import pandas as pd
import pytest
import six
from pandas.util.testing import assert_frame_equal


# functions for generating a dask dataframe
def get_pdf(character):
    '''constructs a pandas dataframe with indexes [character]1, ..., [character]5'''
    index = [character + str(i) for i in range(5)]
    return pd.DataFrame({'A': [1, 2, 3, 4, 5]}, index=index)


def get_ddf():
    '''constructs dask dataframe out of pandas dataframes via the .from-delayed method with indexes A1, A2, A3, ... F3, F3, F4'''
    delayed_list = [dask.delayed(get_pdf)(x) for x in 'ABCDEF']
    return dask.dataframe.from_delayed(delayed_list)


@pytest.mark.skipif(six.PY2,
                    reason="Skip to see why Py2 errors - TEMPORARY, pls fix")
def test_join_operation_of_dask():
    '''Tests the join operation of dask. Should be ok if dask >= 0.10.2
    Compare https://stackoverflow.com/questions/38416836/result-of-join-in-dask-dataframes-seems-to-depend-on-the-way-the-dask-datafram'''
    #generate dask dataframes, that will be joined
    ddf1 = get_ddf()
    ddf2 = dask.dataframe.from_pandas(pd.DataFrame({'B': [1, 2, 3]},
                                                   index=['A0', 'B1', 'C3']),
                                      npartitions=2)

    #recreate ddf1 by converting it to a pandas dataframe and afterwards to a dask dataframe
    ddf1_from_pandas = dask.dataframe.from_pandas(ddf1.compute(), npartitions=3)

    #compute joins
    dask_from_delayed_join = ddf1.join(ddf2, how='inner')
    pandas_join = ddf1.compute().join(ddf2.compute(), how='inner')
    dask_from_pandas_join = ddf1_from_pandas.join(ddf2, how='inner')

    assert_frame_equal(pandas_join, dask_from_delayed_join.compute())
    assert_frame_equal(pandas_join, dask_from_pandas_join.compute())
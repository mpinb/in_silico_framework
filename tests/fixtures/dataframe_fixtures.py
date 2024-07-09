import pytest
import pandas as pd
import dask.dataframe as dd
import six

@pytest.fixture
def pdf():
    """Returns a pandas DataFrame with various types. No column has mixed value types though.

    Returns:
        pd.DataFrame: A dataframe
    """
    pdf = pd.DataFrame({
        0: [1,2,3,4,5,6], 
        1: ['1', '2', '3', '1', '2', '3'], 
        '2': [False, True, True, False, True, False], 
        'myname': ['bla', 'bla', 'bla', 'bla', 'bla', 'bla']
        })
    return pdf

@pytest.fixture
def ddf(pdf):
    ddf = dd.from_pandas(pdf, npartitions=2)
    return ddf
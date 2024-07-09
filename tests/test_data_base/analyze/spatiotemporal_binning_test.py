from data_base.analyze.spatiotemporal_binning import *
import numpy as np
import pandas as pd


class TestSpatioTemporalBinning:

    def setup_class(self):
        self.test_dataframe = {
            'distance': [0, 0, 1, 4, 5, 5.3, 5.4],
            '1': [10, np.NaN, 10, 11, 20, 20, 20],
            '2': [15, np.NaN, 11, 12, 21, 30, 30],
            '3': [np.NaN, np.NaN, 11.5, 30, np.NaN, np.NaN, np.NaN]
        }

        self.test_dataframe = pd.DataFrame(self.test_dataframe)

    def test_binning_small_pandas_df(self):
        '''binning a smale pandas.DataFrame'''
        a = universal(self.test_dataframe, 'distance', 5, 0, 30, 5)
        b = np.array([[0, 0, 6, 1, 0, 1], [0, 0, 0, 0, 4, 2]])
        np.testing.assert_array_equal(a, b)

    def test_binning_dask_dataframe(self):
        '''binning dask dataframes has to deliver the same
        results as binning pandas dataframes'''
        ddf = dd.from_pandas(self.test_dataframe, npartitions=2)
        a = universal(ddf, 'distance', 5, 0, 30, 5)
        b = np.array([[0, 0, 6, 1, 0, 1], [0, 0, 0, 0, 4, 2]])
        np.testing.assert_array_equal(a, b)

        ddf = dd.from_pandas(self.test_dataframe, npartitions=1)
        a = universal(ddf, 'distance', 5, 0, 30, 5)
        b = np.array([[0, 0, 6, 1, 0, 1], [0, 0, 0, 0, 4, 2]])
        np.testing.assert_array_equal(a, b)

        ddf = dd.from_pandas(self.test_dataframe, npartitions=3)
        a = universal(ddf, 'distance', 5, 0, 30, 5)
        b = np.array([[0, 0, 6, 1, 0, 1], [0, 0, 0, 0, 4, 2]])
        np.testing.assert_array_equal(a, b)

    def test_binning_real_data(self, fresh_db, client):
        '''binning dask dataframes has to deliver the same
        results as binning pandas dataframes'''
        assert 'synapse_activation' in list(fresh_db.keys())
        x = universal(
            client.compute(fresh_db['synapse_activation']).result(), 'soma_distance')
        y = universal(fresh_db['synapse_activation'], 'soma_distance')
        np.testing.assert_equal(x, y)

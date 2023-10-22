from ...context import *
from model_data_base.model_data_base import ModelDataBase
import tempfile
import numpy as np
from pandas.util.testing import assert_frame_equal
import dask.dataframe as dd
import pandas as pd
import dask
from  model_data_base.IO.LoaderDumper import dask_to_csv, numpy_to_npy, pandas_to_msgpack, \
                                to_pickle, pandas_to_pickle, dask_to_msgpack, \
                                dask_to_categorized_msgpack, to_cloudpickle, reduced_lda_model
from test_simrun2.reduced_model.get_kernel_test import get_test_Rm
from numpy.testing import assert_array_equal


def robust_del_fun(mdb, key):
    try:
        del mdb[key]
    except KeyError:
        pass


class TestDumperSmall:

    def setup_class(self):
        # set up model_data_base in temporary folder and initialize it.
        # This additionally is an implicit test, which ensures that the
        # initialization routine does not throw an error.
        self.path = tempfile.mkdtemp()
        self.mdb = model_data_base.ModelDataBase(self.path)
        self.pdf = pd.DataFrame({0: [1,2,3,4,5,6], 1: ['1', '2', '3', '1', '2', '3'], '2': [1, '2', 3, 1, '2', 3], \
                                 'myname': ['bla', 'bla', 'bla', 'bla', 'bla', 'bla']})
        self.ddf = dd.from_pandas(self.pdf, npartitions=2)
        #for to_csv methods, since it cannot provide support for mixed dtypes
        self.pdf2 = pd.DataFrame({0: [1,2,3,4,5,6], 1: ['1', '2', '3', '1', '2', '3'], '2': [1, 2, 3, 1, 2, 3], \
                                 'myname': ['bla', 'bla', 'bla', 'bla', 'bla', 'bla']})
        self.ddf2 = dd.from_pandas(self.pdf2, npartitions=2)
        assert self.ddf.npartitions > 1

    def teardown_class(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    def clean_up(self):
        robust_del_fun(self.mdb, 'synapse_activation2')
        robust_del_fun(self.mdb, 'voltage_traces2')
        robust_del_fun(self.mdb, 'test')

    def data_frame_generic_small(self, pdf, ddf, dumper, client=None):
        #index not set
        self.clean_up()
        if client is None:
            self.mdb.setitem('test', ddf, dumper=dumper)
        else:
            self.mdb.setitem('test', ddf, dumper=dumper, client=client)
        dummy = self.mdb['test']
        a = dask.compute(dummy)[0].reset_index(drop=True)
        b = pdf.reset_index(drop=True)
        assert_frame_equal(a, b)
        #sorted index set
        self.clean_up()
        if client is None:
            self.mdb.setitem('test', ddf.set_index(0), dumper=dumper)
        else:
            self.mdb.setitem('test',
                             ddf.set_index(0),
                             dumper=dumper,
                             client=client)
        dummy = self.mdb['test']
        a = dask.compute(dummy)[0]
        b = pdf.set_index(0)
        assert_frame_equal(a, b)

    def test_dask_to_csv_small(self):
        self.data_frame_generic_small(self.pdf2, self.ddf2, dask_to_csv)

    def test_dask_to_msgpack_small(self, client):
        self.data_frame_generic_small(self.pdf2,
                                      self.ddf2,
                                      dask_to_msgpack,
                                      client=client)

    def test_dask_to_categorized_msgpack_small(self, client):
        self.data_frame_generic_small(self.pdf2,
                                      self.ddf2,
                                      dask_to_categorized_msgpack,
                                      client=client)

    def test_pandas_to_msgpack_small(self):
        self.data_frame_generic_small(self.pdf, self.pdf, pandas_to_msgpack)

    def test_pandas_to_pickle_small(self):
        self.data_frame_generic_small(self.pdf, self.pdf, pandas_to_pickle)

    def test_to_pickle_small(self):
        self.data_frame_generic_small(self.pdf, self.pdf, to_pickle)

    def test_to_cloudpickle_small(self):
        self.data_frame_generic_small(self.pdf, self.pdf, to_cloudpickle)

    def test_self_small(self):
        self.data_frame_generic_small(self.pdf, self.pdf, 'self')

    def test_numpy_to_npy(self):

        def fun(x):
            self.clean_up()
            self.mdb.setitem('test', x, dumper=numpy_to_npy)
            dummy = self.mdb['test']
            assert_array_equal(dummy, x)

        fun(np.random.randint(5, size=(100, 100)))
        fun(np.random.randint(5, size=(100,)))
        fun(np.array([]))

    def test_reduced_lda_model(self, fresh_mdb):
        Rm = get_test_Rm(fresh_mdb)
        # does not change the original object
        st = Rm.st
        lda_values = Rm.lda_values
        lda_value_dicts = Rm.lda_value_dicts
        mdb_list = Rm.mdb_list

        self.mdb.setitem('rm', Rm, dumper=reduced_lda_model)

        assert st is Rm.st
        assert lda_values is Rm.lda_values
        assert lda_value_dicts is Rm.lda_value_dicts
        assert mdb_list is Rm.mdb_list

        # can be loaded
        Rm_reloaded = self.mdb['rm']

        # is functional
        Rm_reloaded.plot()
        self.mdb.setitem('rm2', Rm_reloaded, dumper=reduced_lda_model)
        Rm_reloaded.get_lookup_series_for_different_refractory_period(10)
import shutil
import os
import numpy as np
import pytest
import dask
import distributed
from ..context import *
from model_data_base.sqlite_backend.tuplecloudsqlitedict import SqliteDict, check_key


@dask.delayed
def write_data_to_dict(path, key):
    dict_ = SqliteDict(path, autocommit=True)
    data = np.random.rand(1000, 1000)
    dict_[key] = data


class TestTupleCloudSQLiteDict:

    def setup_class(self):
        self.tempdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tempdir, 'tuplecloudsql_test.db')
        self.db = SqliteDict(self.path, autocommit=True, flag='c')

    def teardown_class(self):
        self.db.close()
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_check_key(self):
        with pytest.raises(ValueError):
            check_key(1)
        check_key('1')
        with pytest.raises(ValueError):
            check_key((1,))
        check_key(('1',))
        with pytest.raises(ValueError):
            check_key('@')
        with pytest.raises(ValueError):
            check_key(('@asd', 'asd'))

    def test_str_values_can_be_assigned(self):
        db = self.db
        db['test'] = 'test'
        assert db['test'] == 'test'

    def test_tuple_values_can_be_assigned(self):
        db = self.db
        db[('test',)] = 'test'
        assert db[('test',)] == 'test'
        db[('test', 'abc')] = 'test2'
        assert db[('test', 'abc')] == 'test2'

    def test_pixelObject_can_be_assigned(self):
        db = self.db
        #plot figure and convert it to PixelObject
        import matplotlib.pyplot as plt
        from visualize._figure_array_converter import PixelObject
        fig = plt.figure()
        fig.add_subplot(111).plot([1, 5, 3, 4])
        po = PixelObject([0, 10, 0, 10], fig=fig)

        #save and reload PixelObject
        db[('test', 'myPixelObject')] = po
        po_reconstructed = db[('test', 'myPixelObject')]

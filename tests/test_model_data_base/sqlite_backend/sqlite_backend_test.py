import unittest
import shutil
import os
import time
import numpy as np
import dask
import distributed
from ..context import *
from .. import decorators

import pickle
from model_data_base.sqlite_backend.sqlite_backend import SQLiteBackend as SqliteDict

@dask.delayed
def write_data_to_dict(path, key):
    dict_ = SqliteDict(path)
    data = np.ones(shape = (1000,1000))*int(key)
    dict_[key] = data
            
class TestSQLiteBackend(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tempdir, 'tuplecloudsql_test.db')
        self.db = SqliteDict(self.path)
        
    def tearDown(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)
        distributed.client_object_duck_typed.restart()
        
    
    def test_str_values_can_be_assigned(self):
        db = self.db
        db['test'] = 'test'
        self.assertEqual(db['test'], 'test')
    
    def test_tuple_values_can_be_assigned(self):
        db = self.db
        db[('test',)] = 'test'
        self.assertEqual(db[('test',)], 'test')  
        db[('test','abc')] = 'test2'
        self.assertEqual(db[('test','abc')], 'test2')  
    
    @decorators.testlevel(1)            
    def test_pixelObject_can_be_assigned(self):
        db = self.db
        #plot figure and convert it to PixelObject
        import matplotlib.pyplot as plt
        from visualize._figure_array_converter import PixelObject
        fig = plt.figure()
        fig.add_subplot(111).plot([1,5,3,4])
        po = PixelObject([0, 10, 0, 10], fig = fig)
         
        #save and reload PixelObject
        db[('test', 'myPixelObject')] = po
        po_reconstructed = db[('test', 'myPixelObject')]
    
    @decorators.testlevel(1)            
    def test_concurrent_writes(self):
        keys = [str(lv) for lv in range(100)]
        job = {key: write_data_to_dict(self.path, key) for key in keys}
        job = dask.delayed(job)
         
        c = distributed.client_object_duck_typed
        c.compute(job).result()
         
        assert(set(self.db.keys()) == set(keys))
        for k in keys:
            np.testing.assert_equal(self.db[k][0,0], int(k))
            
        
        
        

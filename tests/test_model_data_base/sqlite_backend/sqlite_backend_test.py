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

def test_str_values_can_be_assigned(sqlite_db):
    db = sqlite_db
    db['test'] = 'test'
    assert db['test'] == 'test'

def test_tuple_values_can_be_assigned(sqlite_db):
    db = sqlite_db
    db[('test',)] = 'test'
    assert db[('test',)] == 'test'  
    db[('test','abc')] = 'test2'
    assert db[('test','abc')] == 'test2'  

def test_pixelObject_can_be_assigned(sqlite_db):
    db = sqlite_db
    #plot figure and convert it to PixelObject
    import matplotlib.pyplot as plt
    from visualize._figure_array_converter import PixelObject
    fig = plt.figure()
    fig.add_subplot(111).plot([1,5,3,4])
    po = PixelObject([0, 10, 0, 10], fig = fig)
        
    #save and reload PixelObject
    db[('test', 'myPixelObject')] = po
    po_reconstructed = db[('test', 'myPixelObject')]

#@decorators.testlevel(1)  
def test_concurrent_writes(sqlite_db, client):
    keys = [str(lv) for lv in range(100)]
    job = {key: write_data_to_dict(sqlite_db.path, key) for key in keys}
    job = dask.delayed(job)
        
    client.compute(job).result()
        
    assert(set(sqlite_db.keys()) == set(keys))
    for k in keys:
        np.testing.assert_equal(sqlite_db[k][0,0], int(k))
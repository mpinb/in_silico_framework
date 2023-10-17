import matplotlib
matplotlib.use('agg')

from .context import *
from . import decorators
from Interface import tempfile
from visualize.manylines import *
import pandas as pd
import dask.dataframe as dd
from visualize._figure_array_converter import PixelObject, show_pixel_object

savefigs = True

import distributed

class TestManyLines:
    def setup_class(self):
        self.df = pd.DataFrame({'1': [1,2,3,4,5], \
                           '2': [2,1,6,3,4], \
                           '3': [7,3,4,1,2], \
                           'attribute': ['a', 'a', 'a', 'b', 'b']})
        self.colormap = dict(a='r', b='b')
        self.tempdir = tempfile.mkdtemp()
        if savefigs: 
            print("""Testing manyilines plots. Output files are saved in {:s}. 
                Please make sure that they display the same data.""")
    
    def test_manylines_no_group(self, client):
        df = self.df.drop('attribute', axis = 1)
        ddf = dd.from_pandas(df, npartitions = 3)
        fig = plt.figure()
        manylines(df, axis = [1, 10, 1, 10], fig = fig, get = client.get)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_no_group_pandas.png'))
        fig = plt.figure()
        manylines(ddf, axis = [1, 10, 1, 10], fig = fig, get = client.get)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_no_group_dask.png'))
        plt.close()
    
    def test_manylines_grouped(self, client):
        df = self.df
        ddf = dd.from_pandas(df, npartitions = 3)
        fig = plt.figure()
        manylines(df, axis = [1, 10, 1, 10], \
                        groupby_attribute = 'attribute', \
                        colormap = self.colormap, fig = fig, get = client.get)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_grouped_pandas.png'))
        fig = plt.figure()        
        manylines(ddf, axis = [1, 10, 1, 10], \
                        groupby_attribute = 'attribute', \
                        colormap = self.colormap, fig = fig, get = client.get)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_grouped_dask.png'))
        plt.close()
    
    def test_manylines_no_group_returnPixelObject(self, client):
        df = self.df.drop('attribute', axis = 1)
        po = manylines(df, axis = [1, 10, 1, 10], returnPixelObject = True, get = client.get)
        assert isinstance(po, PixelObject)
        fig = plt.figure()
        show_pixel_object(po, fig = fig)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_no_group_po_pandas.png'))
        plt.close()
    
    def test_manylines_grouped_returnPixelObject(self, client):
        df = self.df
        ddf = dd.from_pandas(df, npartitions = 3)
        po = manylines(df, axis = [1, 10, 1, 10], \
                        groupby_attribute = 'attribute', \
                        colormap = self.colormap, \
                        returnPixelObject = True,
                        get = client.get)
        assert isinstance(po, PixelObject)        
        fig = plt.figure()
        show_pixel_object(po, fig = fig)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_grouped_po_pandas.png'))
        po = manylines(ddf, axis = [1, 10, 1, 10], \
                        groupby_attribute = 'attribute', \
                        colormap = self.colormap, \
                        returnPixelObject = True,
                        get = client.get)
        assert isinstance(po, PixelObject)
        fig = plt.figure()
        show_pixel_object(po, fig = fig)
        if savefigs: fig.savefig(os.path.join(self.tempdir, 'manylines_grouped_po_dask.png'))
        plt.close()
         
                     

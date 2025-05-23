import matplotlib, pytest, gc
matplotlib.use('agg')

from .context import *
from Interface import tempfile
from visualize.manylines import plt, manylines
import pandas as pd
import dask.dataframe as dd
from visualize._figure_array_converter import PixelObject, show_pixel_object



class TestManyLines:

    def setup_class(self):
        self.df = pd.DataFrame(
            {'1': [1,2,3,4,5], 
             '2': [2,1,6,3,4], 
             '3': [7,3,4,1,2],
             'attribute': ['a', 'a', 'a', 'b', 'b']})
        self.colormap = dict(a='r', b='b')
        self.tempdir = tempfile.mkdtemp()


    def teardown_class(self):
        plt.close("all")

    @pytest.mark.check_dask_health
    def test_manylines_no_group(self):
        df = self.df.drop('attribute', axis=1)
        ddf = dd.from_pandas(df, npartitions=3)
        fig = plt.figure()
        manylines(df, axis=[1, 10, 1, 10], ax=fig.gca(), scheduler="synchronous")
        fig = plt.figure()
        manylines(ddf, axis=[1, 10, 1, 10], ax=fig.gca(), scheduler="synchronous")
        plt.close()
        gc.collect()

    @pytest.mark.check_dask_health
    def test_manylines_grouped(self):
        df = self.df
        ddf = dd.from_pandas(df, npartitions=3)
        fig, ax = plt.subplots()
        manylines(
            df,
            axis = [1, 10, 1, 10], 
            groupby_attribute = 'attribute', 
            colormap = self.colormap, 
            ax = ax, 
            scheduler="synchronous")
        fig, ax = plt.subplots()
        manylines(
            ddf, 
            axis = [1, 10, 1, 10],
            groupby_attribute = 'attribute',
            colormap = self.colormap, 
            ax = ax, 
            scheduler="synchronous")
        plt.close()
        gc.collect()

    @pytest.mark.check_dask_health
    @pytest.mark.skipif(sys.platform == "darwin", reason="GUI can't be created in a non-main thread on OSX")
    def test_manylines_no_group_returnPixelObject(self, client):
        df = self.df.drop('attribute', axis=1)
        po = manylines(
            df,
            axis=[1, 10, 1, 10],
            returnPixelObject=True,
            scheduler=client)
        assert isinstance(po, PixelObject)
        fig, ax = plt.subplots()
        show_pixel_object(po, ax=ax)
        plt.close()
        gc.collect()

    @pytest.mark.check_dask_health
    @pytest.mark.skipif(sys.platform == "darwin", reason="GUI can't be created in a non-main thread on OSX")
    def test_manylines_grouped_returnPixelObject(self, client):
        df = self.df
        ddf = dd.from_pandas(df, npartitions=3)
        po = manylines(
            df, axis = [1, 10, 1, 10], \
            groupby_attribute = 'attribute', \
            colormap = self.colormap, \
            returnPixelObject = True,
            scheduler=client)
        assert isinstance(po, PixelObject)

        fig, ax = plt.subplots()
        show_pixel_object(po, ax=ax)
        po = manylines(
            ddf, 
            axis = [1, 10, 1, 10],
            groupby_attribute = 'attribute', \
            colormap = self.colormap, \
            returnPixelObject = True,
            scheduler=client)
        assert isinstance(po, PixelObject)
        fig, ax = plt.subplots()
        show_pixel_object(po, ax=ax)
        plt.close()
        gc.collect()

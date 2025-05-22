import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from visualize.rasterplot import rasterplot
import dask.dataframe as dd
import pandas as pd


class TestRasterplot:

    def setup_class(self):
        self.df = pd.DataFrame({'1': [1,2,3,4,5], \
                           '2': [2,1,6,3,4], \
                           '3': [7,3,4,1,2], \
                           'attribute': ['a', 'a', 'a', 'b', 'b']})

        self.colormap = dict(a='r', b='b')
    
    def teardown_class(self):
        plt.close("all")
    
    def test_pandas(self):
        fig = rasterplot(self.df, tlim=(0, 350))
        plt.close()

    def test_dask(self):
        ddf = dd.from_pandas(self.df, npartitions=2)
        fig = rasterplot(self.df, tlim=(0, 350))
        plt.close()

    def test_can_be_called_with_axes(self):
        fig = plt.figure(figsize=(15, 3))
        ax = fig.add_subplot(1, 1, 1)
        assert isinstance(rasterplot(self.df, tlim=(0, 350)), Figure)
        assert rasterplot(self.df, tlim=(0, 350), ax=ax) is fig
        plt.close()

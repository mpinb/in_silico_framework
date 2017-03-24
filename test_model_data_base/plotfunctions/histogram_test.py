import unittest
import numpy as np
from ..context import *
from model_data_base.plotfunctions.histogram import *

from model_data_base.analyze import temporal_binning

class Tests(unittest.TestCase):
        
        
    
    def setUp(self):
        self.pdf = pd.DataFrame({'blabla': ['a', 1, 3], \
                                '1': [1, 5, 10], \
                                '2': [15, 1, 30], \
                                '3': [np.NaN, 1, 45]})
        
        self.testhist = temporal_binning.universal(self.pdf, bin_size = 10, min_time = 0)
    
    def test_histogram_can_be_called_with_tuple(self):
         histogram(self.testhist)
                  
    def test_histogram_can_be_called_with_series(self):
        from  matplotlib.figure import Figure
        from matplotlib.axes import Axes
        fig = plt.figure(figsize = (15,3))
        ax = fig.add_subplot(1,1,1)
        pds = pd.Series({'A': self.testhist, 'labelB': self.testhist})
        self.assertIsInstance(histogram(pds), Figure)
        self.assertIs(histogram(pds, fig = fig), fig)
        self.assertIs(histogram(pds, fig = ax), ax)                          
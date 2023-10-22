import numpy as np
from .context import *
from visualize.histogram import *

from model_data_base.analyze import temporal_binning


class TestHistogram:

    def setup_class(self):
        self.pdf = pd.DataFrame({'blabla': ['a', 1, 3], \
                                '1': [1, 5, 10], \
                                '2': [15, 1, 30], \
                                '3': [np.NaN, 1, 45]})

        self.testhist = temporal_binning.universal(self.pdf,
                                                   bin_size=10,
                                                   min_time=0)

    def test_histogram_can_be_called_with_tuple(self):
        histogram(self.testhist)
        plt.close()

    def test_histogram_can_be_called_with_series(self):
        from matplotlib.figure import Figure
        from matplotlib.axes import Axes
        fig = plt.figure(figsize=(15, 3))
        ax = fig.add_subplot(1, 1, 1)
        pds = pd.Series({'A': self.testhist, 'labelB': self.testhist})
        assert isinstance(histogram(pds), Figure)
        assert histogram(pds, fig=fig) is fig
        assert histogram(pds, fig=ax) is ax
        plt.close()

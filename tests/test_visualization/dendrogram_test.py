from visualize.dendrogram import Dendrogram, DendrogramStatistics
import matplotlib.pyplot as plt
from tests import setup_synapse_activation_experiment
import gc

class TestDendrogram:
    def setup_class(self):
        self.cell = setup_synapse_activation_experiment()
    
    def teardown_class(self):
        plt.close("all")

    def test_dendrogram(self):
        d = Dendrogram(self.cell)
        ax = d.plot()
        ax.set_xlabel('Distance from soma ($\mu m$)')
        fig = d.plot()
        plt.close()
        gc.collect()

    def test_dendrogram_statistics(self):
        ds = DendrogramStatistics(self.cell)
        fig = ds.plot()
        plt.close()
        gc.collect()
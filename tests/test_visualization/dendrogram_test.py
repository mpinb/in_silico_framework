from visualize.dendrogram import Dendrogram, DendrogramStatistics
import matplotlib.pyplot as plt
from tests import setup_synapse_activation_experiment

class TestDendrogram:
    def setup_class(self):
        self.cell = setup_synapse_activation_experiment()
    
    def test_dendrogram(self):
        d = Dendrogram(self.cell)
        ax = d.plot()
        ax.set_xlabel(r'Distance from soma ($\mu m$)')
        fig = d.plot()

    def test_dendrogram_statistics(self):
        ds = DendrogramStatistics(self.cell)
        fig = ds.plot()
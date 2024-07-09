"""
Visualization toolbox. Provides modules for visualizing cell morphologies, ion currents, membrane voltage, rasterplots, PSTHs...

Authors: Arco Bast, Maria Royo, Bjorge Meulemeester
"""

from .cell_morphology_visualizer import CellMorphologyVisualizer
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import numpy as np
import logging

logger = logging.getLogger("ISF").getChild(__name__)

def svg2emf(filename, path_to_inkscape="/usr/bin/inkscape"):
    '''
    Converts svg to emf, which can be imported in word using inkscape.
    
    Args:
        filename (str): the filename of the svg file
        path_to_inkscape (str): the path to the inkscape binary
    
    Returns:
        None
    '''
    command = ' '.join([
        'env -i', path_to_inkscape, "--file", filename, "--export-emf",
        filename[:-4] + ".emf"
    ])
    logger.info(os.system(command))
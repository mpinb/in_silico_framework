# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""Visualization toolbox. 
Provides modules for efficiently visualizing cell morphologies, ion currents, voltage traces, rasterplots, histograms, and PSTHs.
"""

from .cell_morphology_visualizer import CellMorphologyVisualizer
import matplotlib.pyplot as plt
from single_cell_parser import CellParser
import os
import logging

logger = logging.getLogger("ISF").getChild(__name__)

def svg2emf(filename, path_to_inkscape="/usr/bin/inkscape"):
    '''Converts svg to emf, which can be imported in Word using inkscape.
    
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


def plot_hoc(hoc_file, **kwargs):
    """Plot a hoc file using matplotlib.

    Instatiate a :py:class:`CellMorphologyVisualizer` object to plot a morphology from a :ref:`hoc_file_format` file.
    
    Args:
        hoc_file (str): The path to the :ref:`hoc_file_format` file
        show (bool): Whether to show the plot
        **kwargs: additional arguments to pass to :py:meth:`CellMorphologyVisualizer.plot`

    Returns:
        :py:class:`matplotlib.pyplot.Figure`: The figure object
    """
    cp = CellParser(hoc_file)
    cp.spatialgraph_to_cell()
    cell = cp.cell
    cmv = CellMorphologyVisualizer(cell) 
    fig = cmv.plot(**kwargs)
    return fig
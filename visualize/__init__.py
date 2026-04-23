# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


def plot_morphology(fn, **kwargs):
    """Plot a :ref:`morphology_file_format` file using matplotlib.

    Instatiate a :class:`CellMorphologyVisualizer` object to plot a morphology from a :ref:`morphology_file_format` file.
    
    Args:
        fn (str): The path to the :ref:`morphology_file_format` file
        kwargs: additional arguments to pass to :meth:`~visualize.cell_morphology_visualizer.CellMorphologyVisualizer.plot`

    Returns:
        :class:`~matplotlib.figure.Figure`: The figure object

    Example::
    
        from visualize import plot_hoc
        fn = "getting_started/example_data/anatomical_constraints/86_C2_center.hoc"
        plot_hoc(fn)
        
    .. figure:: ../../_static/_images/86_hoc.png

    """
    cp = CellParser(fn=fn)
    cp.spatialgraph_to_cell()
    cell = cp.cell
    cmv = CellMorphologyVisualizer(cell) 
    fig = cmv.plot(**kwargs)
    return fig

plot_hoc = plot_morphology
plot_swc = plot_morphology

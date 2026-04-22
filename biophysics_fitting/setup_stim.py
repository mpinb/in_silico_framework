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
r"""
This module provides methods to set up stimuli by adding recording/injection pipettes to :py:class:`~single_cell_parser.cell.Cell` objects.

Stimulus types included in this module are:

- Step current injection at the soma
- EPSP injection on an "ApicalDendrite" section at a given distance from the soma
"""

import neuron
from . import utils

h = neuron.h


def _append(cell, name, item):
    """Append an item to a :py:class:`~single_cell_parser.Cell.cell` object.
    
    This is used to add e.g. injection/recording pipettes to the cell.
    
    Args:
        cell (object): The cell object.
        name (str): The name of the attribute to append to.
        item (object): The item to append.
        
    Returns:
        None. Adds :paramref:`item` to the :paramref:`cell` under the name :paramref:`name`."""
    try:
        getattr(cell, name)
    except AttributeError:
        setattr(cell, name, [])
    getattr(cell, name).append(item)


def setup_soma_step(cell, amplitude=None, delay=None, duration=None, dist=0):
    """Setup up a step current at the soma, or a given :paramref:`dist` from the soma.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        amplitude (float): The amplitude of the step current.
        delay (float): The delay of the step current.
        duration (float): The duration of the step current.
        dist (float): The distance from the soma to the recording/injection site.
        
    Returns:
        None. Adds a step current pipette to the cell under the name 'iclamp'.
    """
    if dist == 0:
        sec = cell.soma
        x = 0.5
    else:
        sec, x = utils.get_inner_section_at_distance(cell, dist)
    iclamp = h.IClamp(x, sec=sec)
    iclamp.delay = delay  # give the cell time to reach steady state
    iclamp.dur = duration  # 5ms rectangular pulse
    iclamp.amp = amplitude  # 1.9 ?? todo ampere
    _append(cell, name='iclamp', item=iclamp)


def setup_apical_epsp_injection(
    cell,
    dist=None,
    amplitude=None,
    delay=None,
    rise=1.0,
    decay=5
    ):
    """Setup an EPSP injection at a given distance from the soma.
    
    This method assumes the :paramref:`cell` has a soma and an apical dendrite.
    It checks so by means of section label: it must contain a section 
    labeled "ApicalDendrite". See :py:meth:`~biophysics_fitting.utils.get_inner_section_at_distance` for more information.
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma to the injection site (um).
        amplitude (float): The amplitude of the EPSP (nA).
        delay (float): The delay of the EPSP (ms).
        rise (float): The rise time constant of the EPSP (ms).
        decay (float): The decay time constant of the EPSP (ms).
        
    Returns:
        None. Adds an EPSP injection pipette to the cell under the name 'epsp'."""
    sec, x = utils.get_inner_section_at_distance(cell, dist)
    iclamp2 = h.epsp(x, sec=sec)
    iclamp2.onset = delay
    iclamp2.imax = amplitude
    iclamp2.tau0 = rise  # rise time constant
    iclamp2.tau1 = decay  # decay time constant
    _append(cell, name='epsp', item=iclamp2)
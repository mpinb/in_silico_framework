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

Stimulus types include the stimuli used by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`:

- a bAP (backpropagating AP) stimulus.
- a BAC (bAP-Activated :math:`Ca^{2+}`) stimulus.
- Three step current stimuli with amplitudes :math:`[0.619, 0.793, 1.507]\ nA`.
    
"""

import neuron
from . import utils
from ..setup_stim import setup_soma_step, setup_apical_epsp_injection

h = neuron.h


def setup_bAP(cell, delay=295):
    """Setup a bAP (backpropagating action potential) stimulus for the cell.
    
    Soma:
    
    - shape = step
    - amplitude = 1.9 nA
    - delay = 295 ms
    - duration = 5 ms
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        delay (float): The delay of the bAP stimulus (ms).
        
    Returns:
        None. Adds a bAP stimulus to the cell.
    """
    setup_soma_step(cell, amplitude=1.9, delay=delay, duration=5)


def setup_BAC(cell, dist=970, delay=295):
    """Setup a BAC (bAP-activated Ca2+-spike) stimulus for the cell.
    
    Soma:

    - shape = step    
    - amplitude = 1.9 nA
    - delay = 295 ms
    - duration = 5 ms
        
    Apical dendrite:

    - shape = epsp
    - amplitude = 0.5 nA
    - distance = 970 um (default)
    - delay = 300 ms
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma to the recording site (um).
        delay (float): The delay of the BAC stimulus (ms).
        
    Returns:
        None. Adds a BAC stimulus to the cell.
    """
    try:
        len(
            delay
        )  # check if delay is iterable ... alternative checks were even more complex
    except TypeError:
        setup_soma_step(cell, amplitude=1.9, delay=delay, duration=5)
        setup_apical_epsp_injection(
            cell,
            dist=dist,
            amplitude=.5,
            delay=delay + 5)
    else:
        for d in delay:
            setup_BAC(cell, dist=dist, delay=d)


def setup_StepOne(cell, delay=700):
    """Setup a step current stimulus at the soma:
         
    - amplitude = 0.619 nA
    - delay = 700 ms
    - duration = 2000 ms   
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        delay (float): The delay of the step current stimulus (ms).
    
    Returns:
        None. Adds a step current stimulus to the cell.
    """
    setup_soma_step(cell, amplitude=0.619, delay=delay, duration=2000)


def setup_StepTwo(cell, delay=700):
    """Setup a step current stimulus at the soma:
          
    - amplitude = 0.793 nA
    - delay = 700 ms
    - duration = 2000 ms      
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        delay (float): The delay of the step current stimulus (ms).
        
    Returns:
        None. Adds a step current stimulus to the cell.
    """
    setup_soma_step(cell, amplitude=0.793, delay=delay, duration=2000)


def setup_StepThree(cell, delay=700):
    """Setup a step current stimulus at the soma:
          
    - amplitude = 1.507 nA
    - delay = 700 ms
    - duration = 2000 ms   
           
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        delay (float): The delay of the step current stimulus (ms).
        
    Returns:
        None. Adds a step current stimulus to the cell.
    """
    setup_soma_step(cell, amplitude=1.507, delay=delay, duration=2000)

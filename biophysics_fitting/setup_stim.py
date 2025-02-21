"""
This module provides methods to set up stimuli by adding recording/injection pipettes to :py:class:`~single_cell_parser.cell.Cell` objects.

Stimulus types included in this module are:

- Step current injection at the soma
- EPSP injection on an "ApicalDendrite" section at a given distance from the soma
- The stimuli used by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`:
    - a bAP (backpropagating AP) stimulus.
    - a BAC (bAP-Activated :math:`Ca^{2+}`) stimulus.
    - Three step current stimuli with amplitudes :math:`[0.619, 0.793, 1.507]\ nA`.
    
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
    _append(cell, 'iclamp', iclamp)


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
    _append(cell, 'epsp', iclamp2)


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

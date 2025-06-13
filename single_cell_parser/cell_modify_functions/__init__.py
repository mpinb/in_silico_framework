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

"""Modify the cell after it is initalized.

Such a function can for example be used to scale the apical dendrite diameter.

If a cell has been modified this way, the cell parameter file contains the key ``cell_modify_functions``
in its neuron section. This is a nested dictionary, where the keys are the names of the cell modification
functions, and the values are the keyword arguments as a dictionary.

See also:
    The :ref:`cell_parameters_format` file format.

Example::

    >>> cell_parameters.neuron.cell_modify_functions
    {'scale_apical': {'scale': 1.5}}
    >>> from single_cell_parser.cell_modify_functions import get
    >>> fun = get('scale_apical')
    >>> fun
    <function scale_apical at 0x7f0c3f2b6e18>
    >>> print(fun.__doc__)
    Scale the apical dendrite of a cell.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        scale (float): The scaling factor.
        compartment (str): The compartment to scale.
            If "ApicalDendrite", the cell is assumed to have sections with label "ApicalDendrite".
            If "Trunk", the cell is assumed to have ``detailed_labels`` assigned manually, or by :py:meth:`biophysics_fitting.utils.augment_cell_with_detailed_labels`.
            Currently, only "ApicalDendrite" and "Trunk" are supported compartments.
    
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The scaled cell.

    Raises:
        ValueError: If the compartment is not "ApicalDendrite" or "Trunk".

"""

# These kind of modifying functions have caused a lot of trouble in the past, as it 
# had not been specified in the neuron parameterfile. No record of whether a modification
# had been applied was saved alongside the simulation data.
# Now, it is in the neruon parameter file under the key "cell_modify_functions".

import importlib

__author__ = "Arco Bast"
__date__ = "2019-02-16"


def get(funname):
    """Get a cell modification function by their name.
    
    Cell modify functions are defined in this module, and can be retrieved by name.
    Each cell modify function is defined in a module that has the same name as the function itself.
    For example, the full path to 
    :py:meth:`~single_cell_parser.cell_modify_functions.scale_apical.scale_apical` is
    :py:meth:`single_cell_parser.cell_modify_functions.scale_apical.scale_apical`.
    To make it easier to retrieve the function, this function provides API to simply fetch them by name.
    
    Example:
    
        >>> from single_cell_parser.cell_modify_functions import get
        >>> fun = get('scale_apical')
        >>> fun
        <function scale_apical at 0x7f0c3f2b6e18>
        >>> print(fun.__file__)
        single_cell_parser/cell_modify_functions/scale_apical.py
        
    Returns:
        Callable: the cell modification function.
    """
    module = importlib.import_module(__name__ + '.' + funname)
    fun = getattr(module, funname)
    return fun

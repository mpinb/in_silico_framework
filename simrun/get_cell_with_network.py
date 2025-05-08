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

"""Build a cell with realized synapses from a :ref:`cell_parameters_format` file and a :ref:`network_parameters_format` file.
"""
import single_cell_parser as scp


def get_cell_with_network(neuron_param, network_param, cache=True):
    """Build a cell with realized synapses from a :ref:`cell_parameters_format` file and a :ref:`network_parameters_format` file.
    
    This method creates a new network embedding for the :py:class:`~single_cell_parser.cell.Cell` based on the :ref:`network_parameters_format` file.
    
    Args:
        neuron_param (:py:class:`~single_cell_parser.parameters.ParameterSet`): The :ref:`cell_parameters_format`.
        network_param (:py:class:`~single_cell_parser.parameters.ParameterSet`): The :ref:`network_parameters_format`.
    
    Returns:
        callable: A callable that returns a :py:class:`~single_cell_parser.cell.Cell` and :py:class:`~single_cell_parser.network.NetworkMapper` when called.
    
    See also:
        :py:mod:`simrun.parameters_to_cell` for rebuilding **and** simulating the cell and network from 
        an existing network realization (:ref:`syn_file_format` file) it.
    """
    cell = scp.create_cell(neuron_param.neuron)
    nwMapMutable = [False]  # list that stores current network, always of length 1

    def fun():
        # start with resetting cell and network in case they have previously been used
        cell.re_init_cell()
        if nwMapMutable[0]:
            nwMapMutable[0].re_init_network()
        for sec in cell.sections:
            sec._re_init_vm_recording()
            sec._re_init_range_var_recording()
        
        # initializing network
        nwMap = scp.NetworkMapper(
            cell, 
            network_param.network,
            neuron_param.sim)
        nwMap.create_saved_network2()
        nwMapMutable[0] = nwMap
        
        # special case: a second evokedNW exists in cell.evokedNW
        try:
            cell.evokedNW.re_init_network()
            par = neuron_param['neuron']['cell_modify_functions']['synaptic_input']
            synaptic_input = scp.cell_modify_functions.get('synaptic_input')
            synaptic_input(cell, **par.as_dict())
        except AttributeError:  # if cell.evokedNW does not exist:
            pass  # do nothing
        return cell, nwMap

    return fun
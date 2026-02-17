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

"""Add synaptic activations to the cell from a network.
"""
import single_cell_parser as scp
import logging

logger = logging.getLogger("ISF").getChild(__name__)
logger.warning(
    "The cell_modify_function synaptic_input is experimental! Make sure synapses "
    "are being activated as you expect and have the effect you expect!"
    )


def synaptic_input(
        cell,
        network_param=None,
        synapse_activation_file=None,
        tStop=None):
    """Add synaptic activations to the cell from a network.
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        network_param (str | dict | :py:class:`~single_cell_parser.parameters.NTParameterSet`): The :ref:`network_parameters_format`.
        synapse_activation_file (str, optional): 
            The :ref:`syn_activation_format` file with existing synapse activations.
            If None, synapse activations are generated from scratch using :py:meth:`~single_cell_parser.network.NetworkMapper.create_saved_network2`.
        tStop (float): The simulation stop time.

    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The cell with the synaptic input set up as the ``evokedNW`` attribute.
    """
    net = scp.build_parameters(network_param)
    sim = scp.NTParameterSet({'tStop': tStop})
    evokedNW = scp.NetworkMapper(cell, net.network, sim)
    if synapse_activation_file is None:
        logger.info('Activating synapses')
        evokedNW.create_saved_network2()
    else:
        evokedNW.reconnect_saved_synapses(synapse_activation_file)

    cell.evokedNW = evokedNW
    return cell

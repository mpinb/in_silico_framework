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

'''Create anatomical and functional network realizations.

For more fine-grained control over the creation of anatomical network realizations, please refer to :mod:`singlecell_input_mapper.singlecell_input_mapper`.
'''

import os, time
from .io.amira import read_scalar_field
from .io.connectivity import write_cell_synapse_locations
from . import cell_parser
from .synapse_mapper import SynapseMapper
from .network import NetworkMapper
from .parameters import build_parameters
import neuron
__author__  = 'Robert Egger'
__date__    = '2013-02-01'


def create_synapse_realization(
    pname,
    write_synapses=False
    ):
    """
    Create a synapse realization from a :ref:`network_parameters_format` file.
    
    Args:
        pname (str): :ref:`network_parameters_format` file.

    .. deprecated:: 0.4.0
        write_synapses has been deprecated.
    """
    parameters = build_parameters(pname)
    cellParam = parameters.network.post
    preParam = parameters.network.pre

    parser = cell_parser.CellParser(cellParam.filename)
    parser.spatialgraph_to_cell()
    cell = parser.cell
    for preType in list(preParam.keys()):
        synapseFName = preParam[preType].synapses.distributionFile
        synDist = read_scalar_field(synapseFName)
        mapper = SynapseMapper(cell, synDist)
        mapper.create_synapses(preType)

    for synType in list(cell.synapses.keys()):
        name = parameters.info.outputname
        name += '_'
        name += synType
        name += '_syn_realization'
        uniqueID = str(os.getpid())
        timeStamp = time.strftime('%Y%m%d-%H%M')
        name += '_' + timeStamp + '_' + uniqueID
        synapseList = []
        for syn in cell.synapses[synType]:
            synapseList.append(syn.coordinates)
        tmpSyns = {}
        tmpSyns[synType] = cell.synapses[synType]
        write_cell_synapse_locations(name + '.syn', tmpSyns, cell.id)


def create_functional_network(cellParamName, nwParamName):
    '''Create fixed functional connectivity based on ``convergence``.
    
    Creates anatomical realizations based on the ``convergence`` parameter (i.e. cell type specific connection probability, see :func:`~single_cell_parser.network.NetworkMapper.create_functional_realization`).
    For more fine-grained control over anatomically consistent network realizations, please refer to :mod:`singlecell_input_mapper.singlecell_input_mapper`,
    The results of the :mod:`singlecell_input_mapper.map_single_cell_inputs` can be read in with :func:`~single_cell_parser.network.NetworkMapper.create_saved_network2`.
    
    Args:
        cellParamName (str): Parameter file of postsynaptithe c neuron
        nwParamName (str): :ref:`network_parameters_format` file.
    '''
    preParam = build_parameters(cellParamName)
    neuronParam = preParam.neuron
    nwParam = build_parameters(nwParamName)
    for mech in list(nwParam.NMODL_mechanisms.values()):
        neuron.load_mechanisms(mech)
    parser = cell_parser.CellParser(neuronParam.filename)
    parser.spatialgraph_to_cell()
    nwMap = NetworkMapper(parser.cell, nwParam)
    nwMap.create_functional_realization()

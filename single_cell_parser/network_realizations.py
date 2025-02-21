'''Create anatomical and functional network realizations.

For more fine-grained control over the creation of anatomical network realizations, please refer to :py:mod:`singlecell_input_mapper.singlecell_input_mapper`.
'''

import os, time
from . import reader
from . import writer
from . import cell_parser
from .synapse_mapper import SynapseMapper
from .network import NetworkMapper
from sumatra.parameters import build_parameters
import neuron
__author__  = 'Robert Egger'
__date__    = '2013-02-01'


def create_synapse_realization(pname):
    """Create a synapse realization from a :ref:`network_parameters_format` file."""
    parameters = build_parameters(pname)
    cellParam = parameters.network.post
    preParam = parameters.network.pre

    parser = cell_parser.CellParser(cellParam.filename)
    parser.spatialgraph_to_cell()
    cell = parser.cell
    for preType in list(preParam.keys()):
        synapseFName = preParam[preType].synapses.distributionFile
        synDist = reader.read_scalar_field(synapseFName)
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
        writer.write_landmark_file(name, synapseList)
        tmpSyns = {}
        tmpSyns[synType] = cell.synapses[synType]
        writer.write_cell_synapse_locations(name + '.syn', tmpSyns, cell.id)


def create_functional_network(cellParamName, nwParamName):
    '''Create fixed functional connectivity based on ``convergence``.
    
    Creates anatomical realizations based on the ``convergence`` parameter (i.e. cell type specific connection probability, see :py:meth:`~single_cell_parser.network.NetworkMapper.create_functional_realization`).
    For more fine-grained control over anatomically consistent network realizations, please refer to :py:mod:`singlecell_input_mapper.singlecell_input_mapper`,
    The results of the :py:mod:`singlecell_input_mapper.map_single_cell_inputs` can be read in with :py:meth:`~single_cell_parser.network.NetworkMapper.create_saved_network2`.
    
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
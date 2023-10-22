'''
Created on Feb 1, 2013

Implements standard scripts for
anatomical and functional network realizations.

@author: regger
'''

import os, time
from . import reader
from . import writer
from . import cell_parser
from .synapse_mapper import SynapseMapper
from .network import NetworkMapper
from sumatra.parameters import build_parameters
import neuron


def create_synapse_realization(pname):
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
    '''
    Public interface:
    used for creating fixed functional connectivity.
    cellParamName - parameter file of postsynaptic neuron
    nwParamName - parameter file of anatomical network
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
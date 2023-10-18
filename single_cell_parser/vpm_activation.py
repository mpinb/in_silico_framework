'''
Created on Apr 21, 2012

@author: robert
'''

import neuron
from . import reader
from . import cell_parser
from . import synapse_mapper as smap
from . import sim_control
import numpy as np
import logging
log = logging.getLogger("ISF").getChild(__name__)

'''anatomical parameters'''
# ? look @ vpm -> L5tt mapping results
# vpm -> L4 about 0.4; therefore 0.2 good guess
convergence = 0.2
# ? look @ vpm -> L5tt mapping results
divergence = 0.2
# Oberlaender 2011
vpmCellNr = 285
# Brecht 2002
vpmActiveFrac = 0.65

'''functional parameters'''
# mean VPM firing time after whisker deflection
# Brecht 2002
vpmDelay = 10.0 + 5.0
# stddev of Gaussian distribution describing
# firing times of VPM relay cells
vpmWidth = 1.7
# nr of spikes fired by VPM relay cells after whisker deflection
vpmSpikes = 1
# efficacy of VPM synapses (-> release probability)
efficacy = 1.0
# synaptic strength [microSiemens]
strength = 0.001

def _assign_functional_synapses(cell, preSynCells):
    '''assigns functional synapses to fixed anatomical synapses'''
#    set up functional connectivity
    nrPresynCells = len(preSynCells)
    for i in range(len(cell.synapses['VPM'])):
        syn = cell.synapses['VPM'][i]
        if i < nrPresynCells:
            syn.activate_hoc_syn(preSynCells[i], cell, weight=strength)
        else:
            n = np.random.randint(nrPresynCells)
            syn.activate_hoc_syn(preSynCells[n], cell, weight=strength)
    
def _assign_anatomical_synapses(cell=None):
    if cell is None:
        fname = '93_CDK080806_marcel_3x3_registered_zZeroBarrel.hoc.am-14678.hoc'
        parser = cell_parser.CellParser(fname)
        parser.spatialgraph_to_cell()
#        parser.insert_passive_membrane('Soma')
#        parser.insert_passive_membrane('Dendrite')
#        parser.insert_passive_membrane('ApicalDendrite')
#        parser.insert_passive_membrane('Axon')
#        parser.insert_hh_membrane('Soma')
#        parser.insert_hh_membrane('Dendrite')
#        parser.insert_hh_membrane('ApicalDendrite')
#        parser.insert_hh_membrane('Axon')
        
        from sumatra.parameters import build_parameters
        parameters = build_parameters('../sim_parameter_template.param')
        cellParams = parameters.network.post.L5tt
        for label in list(cellParams.keys()):
            parser.insert_membrane_properties(label, cellParams[label].properties)
            parser.insert_range_mechanisms(label, cellParams[label].mechanisms.range)
        
        synapseFName = 'SynapseCount.14678.am'
        synDist = reader.read_scalar_field(synapseFName)
        mapper = smap.SynapseMapper(parser.cell, synDist)
        mapper.create_synapses('VPM')
        return parser.cell
    else:
#        TODO: implement variation of anatomical synapses
#            (location within voxels can vary)
        pass

def run_sim():
#    load VecStim as VPM spike generators
#    best way: set NRN_NMODL_PATH environment variable
#    mech_str = '/home/regger/bin/nrn-7.2/share/examples/nrniv/netcon/x86_64/.libs/libnrnmech.so'
#    load_flag = neuron.h.nrn_load_dll(mech_str)
#    if not load_flag:
#        err_str = 'Failed to load NMODL mechanism from ' + mech_str
#        raise RuntimeError(err_str)
    
    cell = _assign_anatomical_synapses()
    
    pVec = np.random.rand(vpmCellNr)
    presynCellIDs = np.where(pVec < convergence)[0]
    vpmConnectedCells = [neuron.h.VecStim() for ID in presynCellIDs]
#    set up spike times and active cells
    spikeTimes = []
    pVec = np.random.rand(vpmCellNr)
    activeCells = np.where(pVec < vpmActiveFrac)[0]
    for i in range(len(presynCellIDs)):
        ID = presynCellIDs[i]
        if ID in activeCells:
            spikeT = vpmDelay + vpmWidth*np.random.randn()
            spikeT = max(spikeT, 0.1)
            spikeTVec = neuron.h.Vector([spikeT])
#            necessary to keep hoc Vectors in a persistent object during simulation
#            because VecStim mod file does not implement reference counting
            spikeTimes.append(spikeTVec)
            vpmConnectedCells[i].play(spikeTVec)
    
    log.info('{:d} active & connected VPM cells!'.format(len(spikeTimes)))
    _assign_functional_synapses(cell, vpmConnectedCells)
    
    sim = sim_control.SimControl(cell=cell, sim_time=30, dt=0.025, T=6)
    sim.go()
    sim.show()
    
#    simName = '/disk1/regger/SynapseMapper/vpm_test0/time_series0'
#    import writer
#    writer.write_cell_simulation(simName, cell, ['Vm'], sim.rec_t)

def main():
    run_sim()

if __name__ == '__main__':
    main()
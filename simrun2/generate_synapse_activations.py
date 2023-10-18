'''
Created 2017
@author: arco
'''
import time
import numpy as np
import dask
from dask import delayed
import neuron
h = neuron.h
import single_cell_parser as scp
import single_cell_parser.analyze as sca
from .seed_manager import get_seed
from .utils import *
import os
import socket
import logging
log = logging.getLogger("ISF").getChild(__name__)

def _evoked_activity(cellParamName, evokedUpParamName, dirPrefix = '', seed = None, nSweeps = 1000, tStop = 345):
    '''
    pre-stimulus ongoing activity
    and evoked activity
    
    sim name: str, describing the simulation
    cellParamName: str, Path to cell parameter file, containing information about:
        - info: autor, date, name
        - NMODL_mechanisms: path to NEURON mechanisms
        - neuron: 
            -path to hoc-file
            - per subcellular compartment (Soma, AIS, ...):
                - electrical properties
                - mechanisms
    evokedUpParamName: str, Path to network parameter file, containing information about:
                            - autor, name, date
                            - for each cell-type: 
                                synapse: release probability, path to distribution file, receptor and associated parameters
                                connectionFile: path to connection file
                                cell number
                                celltype: pointcell, spiketrain
    '''
    assert seed is not None
    np.random.seed(seed)
    log.info("seed: %i" % seed)
    neuronParameters = scp.build_parameters(cellParamName)
    evokedUpNWParameters = scp.build_parameters(evokedUpParamName) ##sumatra function for reading in parameter file
    scp.load_NMODL_parameters(neuronParameters)
    scp.load_NMODL_parameters(evokedUpNWParameters)
    cellParam = neuronParameters.neuron
    paramEvokedUp = evokedUpNWParameters.network
    
    cell = scp.create_cell(cellParam)
            
    uniqueID = 'seed' + str(seed) + '_pid' + str(os.getpid())
    dirName = os.path.join(dirPrefix, 'results', \
                           time.strftime('%Y%m%d-%H%M') + '_' + str(uniqueID))
    if not os.path.exists(dirName):
        os.makedirs(dirName)
    with open(os.path.join(dirName, 'hostname_' + socket.gethostname()), 'w') as f:
        pass  


    #tOffset = 0.0 # avoid numerical transients

    neuronParameters.sim.tStop = tStop
    #dt = neuronParameters.sim.dt
    
    nRun = 0
    out = []
    while nRun < nSweeps:
        synParametersEvoked = paramEvokedUp
    
        startTime = time.time()
        evokedNW = scp.NetworkMapper(cell, synParametersEvoked, neuronParameters.sim)
        evokedNW.create_saved_network2()
        stopTime = time.time()
        setupdt = stopTime - startTime
        log.info('Network setup time: %.2f s' % setupdt)
                
        synTypes = list(cell.synapses.keys())
        synTypes.sort()
        
        log.info('writing simulation results')
        fname = 'simulation'
        fname += '_run%04d' % nRun
        
        t = None
        synName = dirName + '/' + fname + '_synapses.csv'
        out.append(synName)
        log.info('computing active synapse properties')
        sca.compute_synapse_distances_times(synName, cell, t, synTypes)
        preSynCellsName = dirName + '/' + fname + '_presynaptic_cells.csv'
        scp.write_presynaptic_spike_times(preSynCellsName, evokedNW.cells)
        
        nRun += 1
        
        cell.re_init_cell()
        evokedNW.re_init_network()
        
        log.info('-------------------------------')
    
    log.info('writing simulation parameter files')
    neuronParameters.save(os.path.join(dirName, 'neuron_model.param'))
    evokedUpNWParameters.save(os.path.join(dirName, 'network_model.param'))
    return out
    
def generate_synapse_activations(cellParamName, evokedUpParamName, dirPrefix = '', \
                                 nSweeps = 1000, nprocs = 40, tStop = 345, silent = True):
    '''Generates nSweeps*nprocs synapse activation files and puts them in
    the folder dirPrefix/results/simName. Returns delayed object, which can
    be computed with an arbitrary dask scheduler. For each process, a new
    seed is generated using the seed generator.
    
    Parameters:
        cellParamName: str, Path to cell parameter file, containing information about:
            - info: autor, date, name
            
            - NMODL_mechanisms: path to NEURON mechanisms
            - neuron: 
                -path to hoc-file
                - per subcellular compartment (Soma, AIS, ...):
                    - electrical properties
                    - mechanisms
        evokedUpParamName: str, Path to network parameter file, containing information about:
                                - autor, name, date
                                - for each cell-type: 
                                    synapse: release probability, path to distribution file, receptor and associated parameters
                                    connectionFile: path to connection file
                                    cell number
                                    celltype: pointcell, spiketrain
        nSweeps: number of synapse activations per process
        nprocs: number of independent processes
        tStop: time in ms at which the synaptic input should stop.
        
    Returns: Delayed object. Can be computed with arbitrary scheduler.
    Computing delayed object returns: List of lists. Each child list contains the paths
        of the synapse activation files generated by one worker'''
    
    myfun = lambda seed: _evoked_activity(cellParamName, evokedUpParamName,\
                                         dirPrefix = dirPrefix, seed = seed, nSweeps = nSweeps, \
                                         tStop = tStop)
    if silent:
        myfun = silence_stdout(myfun)
        
    d = [dask.delayed(myfun)(get_seed()) for i in range(nprocs)]
    return dask.delayed(lambda *args: args)(d) #return single delayed object, that computes everything




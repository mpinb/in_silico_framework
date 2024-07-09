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

logger = logging.getLogger("ISF").getChild(__name__)


def _evoked_activity(
    cellParamName,
    evokedUpParamName,
    dirPrefix='',
    seed=None,
    nSweeps=1000,
    tStop=345):
    '''Calculate and write synapse activations and presynaptic spike times for pre-stimulus ongoing activity and evoked activity.
    
    Synapse activation files are generated with :py:meth:`single_cell_parser.analyze.compute_synapse_distances_times`.
    Spike time files are generated with :py:meth:`single_cell_parser.analyze.write_presynaptic_spike_times`.
    
    Args:
        cellParamName (str): 
            Path to a cell parameter file (e.g. getting_started/example_data/biophysical_constraints/*.param), 
            containing information about the neuron morphology (link to a .hoc file) and biophysical properties.
            See :py:meth:`~single_cell_parser.create_cell` for more information on the structure and contents of this filetype
        evokedUpParamName (str): 
            Path to network parameter file (e.g. getting_started/example_data/functional_constraints/network.param),
            containing information on synapse and network parameters per cell type. See :py:meth:`~singlecell_input_mapper.evoked_network_param_from_template.create_network_parameter`
            for more information on the structure and contents of this filetype
        dirPrefix (str): 
            Prefix for the directory where the results are stored.
        seed (int): 
            Seed for the random number generator.
        nSweeps (int): 
            Amount of times to run the simulation with the same parameter configuration.
        tStop (float): 
            Time in ms at which the simulation should stop.
        
    Returns:
        list: List of paths to the synapse activation files.
    '''
    assert seed is not None
    np.random.seed(seed)
    logger.info("seed: %i" % seed)
    
    # Read parameter files.
    neuronParameters = scp.build_parameters(cellParamName)
    evokedUpNWParameters = scp.build_parameters(
        evokedUpParamName)  # sumatra function for reading in parameter file
    scp.load_NMODL_parameters(neuronParameters)
    scp.load_NMODL_parameters(evokedUpNWParameters)
    cellParam = neuronParameters.neuron
    paramEvokedUp = evokedUpNWParameters.network

    cell = scp.create_cell(cellParam)  # create scp cell object from params

    uniqueID = 'seed' + str(seed) + '_pid' + str(os.getpid())
    dirName = os.path.join(
        dirPrefix, 
        'results',
        time.strftime('%Y%m%d-%H%M') + '_' + str(uniqueID))
    if not os.path.exists(dirName):
        os.makedirs(dirName)
    with open(
        os.path.join(
            dirName, 
            'hostname_' + socket.gethostname()),
        'w') as f:
        pass

    #tOffset = 0.0 # avoid numerical transients

    neuronParameters.sim.tStop = tStop
    #dt = neuronParameters.sim.dt

    nRun = 0  # number of sweeps
    out = []  # output *_synapses.csv names
    while nRun < nSweeps:
        synParametersEvoked = paramEvokedUp

        startTime = time.time()
        
        # Create network. 
        evokedNW = scp.NetworkMapper(
            cell, 
            synParametersEvoked,
            neuronParameters.sim
            )
        # Add synapses
        evokedNW.create_saved_network2()
        stopTime = time.time()
        setupdt = stopTime - startTime
        logger.info('Network setup time: %.2f s' % setupdt)

        synTypes = list(cell.synapses.keys())
        synTypes.sort()

        logger.info('writing simulation results')
        fname = 'simulation'
        fname += '_run%04d' % nRun

        t = None
        
        # synapse type - synapse ID - soma distance -section ID - section pt ID - dendrite label - activation times
        synName = dirName + '/' + fname + '_synapses.csv'
        out.append(synName)
        logger.info('computing active synapse properties')
        sca.compute_synapse_distances_times(synName, cell, t, synTypes)
        
        # presynaptic cell type - cell ID - spike times
        preSynCellsName = dirName + '/' + fname + '_presynaptic_cells.csv'
        scp.write_presynaptic_spike_times(preSynCellsName, evokedNW.cells)

        nRun += 1

        cell.re_init_cell()
        evokedNW.re_init_network()

        logger.info('-------------------------------')

    logger.info('writing simulation parameter files')
    neuronParameters.save(os.path.join(dirName, 'neuron_model.param'))
    evokedUpNWParameters.save(os.path.join(dirName, 'network_model.param'))
    return out

def generate_synapse_activations(
    cellParamName,
    evokedUpParamName,
    dirPrefix = '',
    nSweeps = 1000, 
    nprocs = 40, 
    tStop = 345, 
    silent = True):
    '''Generates nSweeps*nprocs synapse activation files and puts them in
    the folder dirPrefix/results/simName. Returns delayed object, which can
    be computed with an arbitrary dask scheduler. For each process, a new
    seed is generated using the seed generator.
    
    Parameters:
        cellParamName (str): 
            Path to a cell parameter file (e.g. getting_started/example_data/biophysical_constraints/*.param), 
            containing information about the neuron morphology (link to a .hoc file) and biophysical properties.
            See :py:meth:`~single_cell_parser.create_cell` for more information on the structure and contents of this filetype
        evokedUpParamName (str): 
            Path to network parameter file (e.g. getting_started/example_data/functional_constraints/network.param),
            containing information on synapse and network parameters per cell type. See :py:meth:`~singlecell_input_mapper.evoked_network_param_from_template.create_network_parameter`
            for more information on the structure and contents of this filetype
        nSweeps: number of synapse activations per process
        nprocs: number of independent processes
        tStop: time in ms at which the synaptic input should stop.
        
    Args:
        cellParamName (str): Path to cell parameter file. 
        
    Returns: 
        dask.delayed: Can be computed with arbitrary scheduler. 
        Computing delayed object returns: List of lists. Each child list contains the paths
        of the synapse activation files generated by one worker
    '''

    myfun = lambda seed: _evoked_activity(cellParamName, evokedUpParamName,\
                                         dirPrefix = dirPrefix, seed = seed, nSweeps = nSweeps, \
                                         tStop = tStop)
    if silent:
        myfun = silence_stdout(myfun)

    d = [dask.delayed(myfun)(get_seed()) for i in range(nprocs)]
    return dask.delayed(lambda *args: args)(
        d)  #return single delayed object, that computes everything

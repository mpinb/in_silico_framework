'''
Generate synapse activation files.

This module creates :ref:`syn_activation_format` files based on the parameters in 
the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files, but does not keep track of what happens
with the postsynaptic neuron during these activations.

The usecase of generating these synapse activations without actually saving or keeping track of the postsynaptic activity, is solely
for the purpose of analyzing the synapse activations and presynaptic spike times. It allows for modularity between the steps of creating 
synapse activations and simulating their effect on the postsynaptic neuron.

These :ref:`syn_activation_format` files can afterwards be used to re-run simulations afterwards with the :py:mod:`simrun.run_existing_synapse_activations` module.
To generate :ref:`syn_activation_format` files **and** simulate the effect on the postsynaptic neuron model in one go, use the :py:mod:`simrun.run_new_simulations` module instead.

.. hint::
   If the postsynaptic neuron is not simulated, why does this module need the :ref:`cell_parameters_format`?
   On the one hand, it needs morphoplogical information in order to connect these synapses. The :ref:`cell_parameters_format` contains 
   a backlink to the original :ref:`hoc_file_format` file, which contains the morphological information. But then why not start from the :ref:'hoc_file_format' file directly?
   Because this module does in fact create a biophsyically detailed neuron model to pass to :py:class:`~single_cell_parser.network.NetworkMapper` to create the network,
   despite the fact that the postsynaptic activity is not saved.
   
   
See also:
    :py:mod:`simrun.run_new_simulations` for running simulations.

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

__author__ = 'Arco Bast'
__date__ = '2017'


def _evoked_activity(
    cellParamName,
    evokedUpParamName,
    dirPrefix='',
    seed=None,
    nSweeps=1000,
    tStop=345):
    '''Calculate and write synapse activations and presynaptic spike times.
    
    This function calculates the synapse activations and presynaptic spike times for a single cell.
    
    Synapse activation files are generated with :py:meth:`single_cell_parser.analyze.compute_synapse_distances_times`.
    Spike time files are generated with :py:meth:`single_cell_parser.analyze.write_presynaptic_spike_times`.
    
    Args:
        cellParamName (str): 
            Path to a :ref:`cell_parameters_format` file, 
            containing information about the neuron morphology (link to a :ref:`hoc_file_format` file) and biophysical properties.
        evokedUpParamName (str): 
            Path to :ref:`network_parameters_format` file, containing information on synapse and network parameters per cell type.
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
    '''Generates :paramref:`nSweeps` * :paramref:`nprocs` synapse activation files and writes them to
    the folder ``dirPrefix/results/simName``. 
    
    For each process, a new seed is generated using the seed generator.
    
    Parameters:
        cellParamName (str): 
            Path to a :ref:`cell_parameters_format` file, 
            containing information about the neuron morphology (link to a :ref:`hoc_file_format` file) and biophysical properties.
        evokedUpParamName (str): 
            Path to a :ref:`network_parameters_format` file,
            containing information on synapse and network parameters per cell type. 
        nSweeps: number of synapse activations per process
        nprocs: number of independent processes
        tStop: time in ms at which the synaptic input should stop.
        
    Args:
        cellParamName (str): Path to cell parameter file. 
        
    Returns: 
        dask.delayed: Can be computed with arbitrary scheduler. 
        Computing delayed object returns List of lists. Each child list contains the paths
        of the synapse activation files generated by one worker
        
    See also:
        :py:mod:`simrun.seed_manager` for seed generation.
    '''

    myfun = lambda seed: _evoked_activity(
        cellParamName, 
        evokedUpParamName,
        dirPrefix = dirPrefix, 
        seed = seed, 
        nSweeps = nSweeps, 
        tStop = tStop)
    if silent:
        myfun = silence_stdout(myfun)

    d = [dask.delayed(myfun)(get_seed()) for i in range(nprocs)]
    return dask.delayed(lambda *args: args)(
        d)  #return single delayed object, that computes everything

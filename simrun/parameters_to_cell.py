from __future__ import absolute_import
from ._matplotlib_import import *
import sys
import time
import os, os.path
import glob
#for some reason, the neuron import works on the florida servers only works if tables was imported first
import tables
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
import numpy as np

h = neuron.h
import dask
from .seed_manager import get_seed
from .utils import *

def parameters_to_cell(
    neuronParam, 
    networkParam, 
    synfile = None,
    dirPrefix = '', 
    tStop = 345.0, 
    scale_apical = None,
    range_vars = None, 
    allPoints=False,
    cell = None, 
    evokedNW = None):
    """Rebuild and simulate a network-embedded cell.
    
    Rebuild the cell from a :ref:`cell_params_format` file.
    If specified, the synapses in the :ref:`syn_file_format` file are reconnected and simulated according to the
    parameters defined in the :ref:`network_params_format` file. If no :ref:`syn_file_format` file is provided,
    a new network embedding is created based on the :ref:`network_params_format` file.
    
    Args:
        neuronParam (str): Path to :ref:`cell_params_format` file. 
        networkParam (str): Path to :ref:`network_params_format` file.
        synfile (str): Path to the realized synapses in :ref:`syn_file_format` format.
        dirPrefix (str): Prefix for the directory where the results are stored.
        tStop (float): Time in ms at which the simulation should stop.
        scale_apical (callable, DEPRECATED): Function to scale the apical dendrite.
        range_vars (str or list): Range variables to record.
        allPoints (bool): Record all points in the cell.
        cell (Cell): A cell object to use for the simulation.
        evokedNW (NetworkMapper): A network object to use for the simulation.
        
    .. deprecated:: 0.1
        The `scale_apical` argument is deprecated. 
        Use the `cell_modify_funs` key in the :ref:`cell_params_format` file instead.
        
    Returns:
        tuple: A tuple containing the :py:class:`~single_cell_parser.cell.Cell` and the evoked network (:py:class:`~single_cell_parser.network.Networkmapper`).
    """

    neuronParam = load_param_file_if_path_is_provided(neuronParam)
    networkParam = load_param_file_if_path_is_provided(networkParam)

    if cell is None:
        cell = scp.create_cell(
            neuronParam.neuron,
            scaleFunc=scale_apical,
            allPoints=allPoints)

    neuronParam.sim.tStop = tStop
    dt = neuronParam.sim.dt

    if evokedNW is None:
        evokedNW = scp.NetworkMapper(
            cell, 
            networkParam.network,
            neuronParam.sim)
    if synfile is None:
        evokedNW.create_saved_network2()
    else:
        evokedNW.reconnect_saved_synapses(synfile)

    if range_vars is not None:
        if isinstance(range_vars, str):
            range_vars = [range_vars]
        for var in range_vars:
            cell.record_range_var(var)

    tVec = h.Vector()
    tVec.record(h._ref_t)
    cell.t = tVec
    scp.init_neuron_run(
        neuronParam.sim,
        vardt=False)  #trigger the actual simulation
    return cell, evokedNW
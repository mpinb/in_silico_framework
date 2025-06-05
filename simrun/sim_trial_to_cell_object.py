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

"""Recreate and resimulate a single simulation trial from parameter files and return the cell object.

This module provides a function to rebuild a network-embedded neuron model from 
a :py:class:`~data_base.data_base.DataBase`. it also allows to change the :ref:`cell_parameters_format`, 
:ref:`network_parameters_format`, and :ref:`syn_activation_format` data before resimulating the trial.

See also:
    To rebuild and re-simulate a :py:mod:`simrun` simulation from parameter files instead of a :py:class:`~data_base.data_base.DataBase`, 
    please refer to :py:mod:`~simrun.parameters_to_cell` instead.
"""


import os, os.path
from ._matplotlib_import import *
import sys
import time
import glob, shutil
import tempfile
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
from data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
import numpy as np
import pandas as pd
from .utils import *
import logging

logger = logging.getLogger("ISF").getChild(__name__)

h = neuron.h


def convertible_to_int(x):
    """Check if a value can be converted to an integer.
    
    :skip-doc:
    
    Args:
        x: Value to check.
        
    Returns:
        bool: True if the value can be converted to an integer, False otherwise.
    """
    try:
        int(x)
        return True
    except:
        return False


def synapse_activation_df_to_roberts_synapse_activation(sa):
    """Convert a synapse activation dataframe to a dictionary of synapse activations.
    
    :skip-doc:
    
    Args:
        sa (pd.DataFrame): A :ref:`syn_activation_format` dataframe.
        
    Returns:
        dict: A dictionary of synapse activations.
    
    Example:

        >>> sa = pd.DataFrame({
        ...     'synapse_ID': [1, 2, 3],
        ...     'section_ID': [1, 2, 3],
        ...     'section_pt_ID': [1, 2, 3],
        ...     'synapse_type': ['AMPA', 'GABA', 'NMDA'],
        ...     'soma_distance': [0, 0, 0],
        ...     '0': [1, 2, 3],
        ...     '1': [4, 5, 6],
        ...     '2': [7, 8, 9]
        ... })
        >>> synapse_activation_df_to_roberts_synapse_activation(sa)
        {'AMPA': [(1, 1, 1, [1, 4, 7], 0)],
         'GABA': [(2, 2, 2, [2, 5, 8], 0)],
         'NMDA': [(3, 3, 3, [3, 6, 9], 0)]}

    """
    synapses = dict()
    import six
    for index, values in sa.iterrows():
        if not values.synapse_type in synapses:
            synapses[values.synapse_type] = []
        synTimes = [
            v for k, v in six.iteritems(values)
            if convertible_to_int(k) and not np.isnan(v)
        ]
        tuple_ = values.synapse_ID, values.section_ID, values.section_pt_ID, synTimes, values.soma_distance
        synapses[values.synapse_type].append(tuple_)
    return synapses


def simtrial_to_cell_object(
    db,
    sim_trial_index,
    compute = True, 
    allPoints = False,
    scale_apical = None, 
    range_vars = None, 
    silent = True,
    neuron_param_modify_functions = [],
    network_param_modify_functions = [],
    synapse_activation_modify_functions = [],
    additional_network_params = [],
    tStop = 345
    ):
    r"""Recreate and resimulate a single simulation trial from parameter files and return the cell object.
    
    This method also provides functionality to adapt the parameters of the cell, network, and synapse activation data
    before resimulating the trial. The network and neuron parameter modify functions should take the
    respective parameter dictionaries as input and return the modified dictionaries.
    Synapse activation modify functions should take the synapse activation data as input and return the modified data.
    
    Args:
        db (:py:class:`data_base.dataBase`): A simrun-initialized database object.
        sim_trial_index (int): Index of the simulation trial in the database.
        range_vars (str | list): Range variables to record.
        scale_apical (callable, DEPRECATED): Function to scale the apical dendrites.
        allPoints (bool): If True, skip :math:`d-\lambda` segmentation and simulate at high resolution.
        compute (bool): If True, compute the simulation. Otherwise return the simulation-ready :py:class:`~single_cell_parser.cell.Cell` object.
        tStop (float): Stop time of the simulation.
        neuron_param_modify_functions (list): List of functions to modify the neuron parameters.
        network_param_modify_functions (list): List of functions to modify the network parameters.
        synapse_activation_modify_functions (list): List of functions to modify the synapse activation data.
        silent (bool): If True, suppress all output.
        
    .. deprecated:: 0.1.0
        The `scale_apical` argument is deprecated and will be removed in a future version.
        Use the `cell_modify_functions` key in the :ref:`cell_parameters_format` file instead.
        
    See also:
        :py:func:`simrun.sim_trial_to_cell_object.trial_to_cell_object` 
        to recreate a single simulation trial from parameter files instead of a database.
        
    See also:
        :py:mod:`data_base.db_initializers.init_simrun_general` to initialize a database object
        from raw `simrun` output, i.e. a "simrun-initialized" database object.
    
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The simulation-ready or simulated cell object.
    """
    stdout_bak = sys.stdout
    if silent == True:
        sys.stdout = open(os.devnull, "w")

    try:
        parameter_table = db['parameterfiles']
        cellName = parameter_table.loc[sim_trial_index].hash_neuron
        cellName = os.path.join(db['parameterfiles_cell_folder'], cellName)
        networkName = parameter_table.loc[sim_trial_index].hash_network
        networkName = os.path.join(db['parameterfiles_network_folder'],
                                   networkName)
        sa = db['synapse_activation'].loc[sim_trial_index].compute()
        dummy =  trial_to_cell_object(
            cellName = cellName, \
            networkName = networkName, \
            synapse_activation_file = sa, \
            range_vars = range_vars,
            scale_apical = scale_apical,
            allPoints = allPoints,
            compute = compute,
            tStop = tStop,
            neuron_param_modify_functions = neuron_param_modify_functions,
            network_param_modify_functions = network_param_modify_functions,
            synapse_activation_modify_functions = synapse_activation_modify_functions,
            additional_network_params = additional_network_params  # TODO   unused
            )
    finally:
        if silent == True:
            sys.stdout = stdout_bak

    return dummy


def trial_to_cell_object(
    name = None, 
    cellName = None, 
    networkName = None, 
    synapse_activation_file = None,
    range_vars = None, 
    scale_apical = None, 
    allPoints = False, 
    compute = True, 
    tStop = 345,
    neuron_param_modify_functions = [],
    network_param_modify_functions = [],
    synapse_activation_modify_functions = [],
    additional_network_params = []  # TODO: unused
    ):
    r"""Recreate and resimulate a single simulation trial from parameter files and return the cell object.
    
    This method also provides functionality to adapt the parameters of the cell, network, and synapse activation data
    before resimulating the trial. The network and neuron parameter modify functions should take the
    respective parameter dictionaries as input and return the modified dictionaries.
    Synapse activation modify functions should take the synapse activation data as input and return the modified data.
    
    
    Args:
        cellName (str): Name of the :ref:`cell_parameters_format` file.
        networkName (str): Name of the :ref:`network_parameters_format` file.
        synapse_activation_file (str | pandas.DataFrame): 
            Path to the :ref:`syn_activation_format` file or 
            a pandas DataFrame containing the synapse activation data.
        range_vars (str | list): Range variables to record.
        scale_apical (callable, DEPRECATED): Function to scale the apical dendrites.
        allPoints (bool): If True, skip :math:`d-\lambda` segmentation and simulate at high resolution.
        compute (bool): If True, compute the simulation. Otherwise return the simulation-ready :py:class:`~single_cell_parser.cell.Cell` object.
        tStop (float): Stop time of the simulation.
        neuron_param_modify_functions (list): List of functions to modify the neuron parameters.
        network_param_modify_functions (list): List of functions to modify the network parameters.
        synapse_activation_modify_functions (list): List of functions to modify the synapse activation data.
        
    .. deprecated:: 0.1.0
        The `scale_apical` argument is deprecated and will be removed in a future version.
        Use the `cell_modify_functions` key in the :ref:`cell_parameters_format` file instead.
        
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The simulation-ready or simulated cell object.
    """
    tempdir = None

    try:
        #if pandas dataframe instead of path is given: convert pandas dataframe to file
        if isinstance(synapse_activation_file, pd.DataFrame):
            tempdir = tempfile.mkdtemp()
            for fun in synapse_activation_modify_functions:
                synapse_activation_file = fun(synapse_activation_file)

            syn = synapse_activation_df_to_roberts_synapse_activation(
                synapse_activation_file)
            synfile = syn
        elif isinstance(synapse_activation_file, str):
            synfile = synapse_activation_file
            if len(synapse_activation_modify_functions) > 0:
                raise NotImplementedError()
        
        # set up simulation
        # simName = name
        cellName = cellName
        evokedUpParamName = networkName
        neuronParameters = load_param_file_if_path_is_provided(cellName)
        evokedUpNWParameters = load_param_file_if_path_is_provided(
            evokedUpParamName)
        additional_network_params = [
            scp.build_parameters(p) for p in additional_network_params
        ]  # TODO: unused?
        for fun in network_param_modify_functions:
            evokedUpNWParameters = fun(evokedUpNWParameters)
        for fun in neuron_param_modify_functions:
            neuronParameters = fun(neuronParameters)
        scp.load_NMODL_parameters(neuronParameters)
        scp.load_NMODL_parameters(evokedUpNWParameters)
        cellParam = neuronParameters.neuron
        paramEvokedUp = evokedUpNWParameters.network
        vTraces = []
        tTraces = []

        #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical)
        cell = scp.create_cell(
            cellParam,
            scaleFunc=scale_apical,
            allPoints=allPoints)
        cell.re_init_cell()

        tOffset = 0.0  # avoid numerical transients
        tStop = tStop
        neuronParameters.sim.tStop = tStop
        dt = neuronParameters.sim.dt
        offsetBin = int(tOffset / dt + 0.5)
        nRun = 0
        synParametersEvoked = paramEvokedUp
        startTime = time.time()
        evokedNW = scp.NetworkMapper(
            cell, 
            synParametersEvoked,
            neuronParameters.sim)
        evokedNW.re_init_network()
        evokedNW.reconnect_saved_synapses(synfile)

        if range_vars is not None:
            if isinstance(range_vars, str):
                range_vars = [range_vars]
            for var in range_vars:
                cell.record_range_var(var)

        if compute:
            tVec = h.Vector()
            tVec.record(h._ref_t)
            startTime = time.time()
            scp.init_neuron_run(
                neuronParameters.sim,
                vardt=False)  # trigger the actual simulation
            stopTime = time.time()
            simdt = stopTime - startTime
            logger.info('NEURON runtime: {:.2f} s'.format(simdt))
            t = np.array(tVec)
            vmSoma = np.array(cell.soma.recVList[0])
            cell.t = np.array(t[offsetBin:])
            cell.vmSoma = np.array(vmSoma[offsetBin:])
    except:
        raise
    finally:
        if tempdir is not None:
            shutil.rmtree(tempdir)
    return cell

"""Recreate and resimulate network-embedded neuron simulation from a simrun-initialized database.

This module provides a function to resimulate a network-embedded neuron simulation from a simrun-initialized database.
It allows to modify either the cell or the network with modification functions.
The database is expected to have been initialized with :py:mod:`data_base.isf_data_base.db_initializers.init_simrun_general`. 
The function :py:func:`rerun_db` takes a database and a directory as input and resimulates the network-embedded neuron simulation for each simulation trial in the database. 
The results are stored in the specified directory.

See also:
    :py:mod:`~data_base.isf_data_base.db_initializers.init_simrun_general` for initializing a database from raw :py:mod:`simrun` output.

See also:
    :py:mod:`~single_cell_parser.cell_modify_functions` and :py:mod:`~single_cell_parser.network_modify_functions` 
    for example functions to modify the :ref:`cell_params_format` and :ref:`network_params_format`.
"""

import single_cell_parser as scp
import single_cell_parser.analyze as sca
import os
import time
import neuron
import dask
import numpy as np
import pandas as pd
from biophysics_fitting.utils import execute_in_child_process
from .utils import *
import logging

logger = logging.getLogger("ISF").getChild(__name__)


def convertible_to_int(x):
    """Check if a string can be converted to an integer.
    
    :skip-doc:"""
    try:
        int(x)
        return True
    except:
        return False


def synapse_activation_df_to_roberts_synapse_activation(sa):
    """Convert a synapse activation dataframe to a dictionary of synapse activations.
    
    :skip-doc:
    
    Args:
        sa (pd.DataFrame): A :ref:`synapse_activation_format` dataframe.
        
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


def _evoked_activity(
    db,
    stis,
    outdir,
    tStop=None,
    neuron_param_modify_functions=[],
    network_param_modify_functions=[],
    synapse_activation_modify_functions=[],
    additional_network_params=[],
    recreate_cell_every_run=None,
    parameterfiles=None,
    neuron_folder=None,
    network_folder=None,
    sa=None
    ):
    """
    :skip-doc:
    
    Recreate and resimulate a network-embedded neuron simulation from a simrun-initialized database.
    
    This method recreates the network-embedded neuron simulation from the parameter files in the simrun-initialized database.
    It allows to adapt the cell parameters, network parameters, and the synaptic activation patterns with modification functions.
    The results are stored in the specified directory, relative to the original unmodified simulation results.
    
    This is a private function invoked by :py:func:`rerun_db`.
    
    
    Args:
        stis (list): List of simulation trial indices to be resimulated.
        outdir (str): Directory where the simulation results are stored, relative to the original simulation results.
        tStop (float): Time in ms at which the simulation should stop.
        neuron_param_modify_functions (list): List of functions which take :py:class:`NTParameterSet` neuron parameters and may return it changed.
        network_param_modify_functions (list): List of functions which take :py:class:`NTParameterSet` network parameters and may return it changed.
        synapse_activation_modify_functions (list): List of functions which take a :ref:`synapse_activation_format` dataframe and may return it changed.
        additional_network_params (list): List of additional :ref:`network_parameters_format` files to be used in the simulation.
        parameterfiles (pd.DataFrame): A dataframe containing the parameter files for the simulation trials. Should always be present in a simrun-initialized database under the key ``paremeterfiles``.
        neuron_folder (str): Path to the folder containing the neuron parameter files.
        network_folder (str): Path to the folder containing the network parameter files.
        sa (pd.DataFrame): A dataframe containing the :ref:`synapse_activation_format` dataframe. Should always be present in a simrun-initialized database under the key ``synapse_activation``.
        
    See also:
        :py:mod:`~data_base.isf_data_base.db_initializers.init_simrun_general` for initializing a database from raw :py:mod:`simrun` output and its available keys. 
    """
    logger.info('saving to ', outdir)
    import neuron
    h = neuron.h
    sti_bases = [s[:s.rfind('/')] for s in stis]
    if not len(set(sti_bases)) == 1:
        raise NotImplementedError
    sti_base = sti_bases[0]
    sa = sa.content
    logger.info('start loading synapse activations')
    sa = sa.loc[stis].compute(scheduler="synchronous")
    logger.info('done loading synapse activations')
    sa = {s: g for s, g in sa.groupby(sa.index)}

    outdir_absolute = os.path.join(outdir, sti_base)
    if not os.path.exists(outdir_absolute):
        os.makedirs(outdir_absolute)

    parameterfiles = parameterfiles.loc[stis]
    parameterfiles = parameterfiles.drop_duplicates()
    if not len(parameterfiles) == 1:
        raise NotImplementedError()

    neuron_name = parameterfiles.iloc[0].hash_neuron
    neuron_param = scp.build_parameters(neuron_folder.join(neuron_name))
    network_name = parameterfiles.iloc[0].hash_network
    network_param = scp.build_parameters(network_folder.join(network_name))
    additional_network_params = [scp.build_parameters(p) for p in additional_network_params]
    for fun in network_param_modify_functions:
        network_param = fun(network_param)
    for fun in neuron_param_modify_functions:
        neuron_param = fun(neuron_param)

    scp.load_NMODL_parameters(neuron_param)
    scp.load_NMODL_parameters(network_param)
    cell = scp.create_cell(neuron_param.neuron, scaleFunc=None)

    vTraces = []
    tTraces = []
    recordingSiteFiles = neuron_param.sim.recordingSites
    recSiteManagers = []
    for recFile in recordingSiteFiles:
        recSiteManagers.append(sca.RecordingSiteManager(recFile, cell))

    if tStop is not None:
        neuron_param.sim.tStop = tStop

    for lv, sti in enumerate(stis):
        startTime = time.time()
        sti_number = int(sti[sti.rfind('/') + 1:])
        syn_df = sa[sti]

        syn_df = sa[sti]
        for fun in synapse_activation_modify_functions:
            syn_df = fun(syn_df)

        syn = synapse_activation_df_to_roberts_synapse_activation(syn_df)

        evokedNW = scp.NetworkMapper(
            cell, 
            network_param.network,
            neuron_param.sim)
        evokedNW.reconnect_saved_synapses(syn, include_silent_synapses = True)
        additional_evokedNWs = [
            scp.NetworkMapper(cell, p.network, neuron_param.sim)
            for p in additional_network_params
        ]
        for additional_evokedNW in additional_evokedNWs:
            additional_evokedNW.create_saved_network2()
        stopTime = time.time()
        setupdt = stopTime - startTime
        logger.info('Network setup time: {:.2f} s'.format(setupdt))

        synTypes = list(cell.synapses.keys())
        synTypes.sort()

        logger.info('Testing evoked response properties run {:d} of {:d}'.format(
            lv + 1, len(stis)))
        tVec = h.Vector()
        tVec.record(h._ref_t)
        startTime = time.time()
        scp.init_neuron_run(
            neuron_param.sim,
            vardt=False)  #trigger the actual simulation
        stopTime = time.time()
        simdt = stopTime - startTime
        logger.info('NEURON runtime: {:.2f} s'.format(simdt))

        vmSoma = np.array(cell.soma.recVList[0])
        t = np.array(tVec)
        cell.t = t  ##
        vTraces.append(np.array(vmSoma[:])), tTraces.append(np.array(t[:]))
        for RSManager in recSiteManagers:
            RSManager.update_recordings()

        logger.info('writing simulation results')
        fname = 'simulation'
        fname += '_run%07d' % sti_number

        synName = outdir_absolute + '/' + fname + '_synapses.csv'
        logger.info('computing active synapse properties')
        sca.compute_synapse_distances_times(
            synName, cell, t,
            synTypes)  #calls scp.write_synapse_activation_file
        preSynCellsName = outdir_absolute + '/' + fname + '_presynaptic_cells.csv'
        scp.write_presynaptic_spike_times(preSynCellsName, evokedNW.cells)

        cell.re_init_cell()
        evokedNW.re_init_network()
        for additional_evokedNW in additional_evokedNWs:
            additional_evokedNW.re_init_network()

        logger.info('-------------------------------')
    vTraces = np.array(vTraces)
    dendTraces = []
    uniqueID = sti_base.strip('/').split('_')[-1]
    scp.write_all_traces(
        outdir_absolute + '/' + uniqueID + '_vm_all_traces.csv', t[:], vTraces)
    for RSManager in recSiteManagers:
        for recSite in RSManager.recordingSites:
            tmpTraces = []
            for vTrace in recSite.vRecordings:
                tmpTraces.append(vTrace[:])
            recSiteName = outdir_absolute + '/' + uniqueID + '_' + recSite.label + '_vm_dend_traces.csv'
            scp.write_all_traces(recSiteName, t[:], tmpTraces)
            dendTraces.append(tmpTraces)
    dendTraces = np.array(dendTraces)

    logger.info('writing simulation parameter files')
    neuron_param.save(
        os.path.join(outdir_absolute, uniqueID + '_neuron_model.param'))
    network_param.save(
        os.path.join(outdir_absolute, uniqueID + '_network_model.param'))

class Opaque:
    """Wrapper class to make objects opaqye to dask
    
    Opaque-wrapped objects are not loaded into memory by dask.
    This is useful when passing large objects to dask functions that do not need to be loaded necessarily.
    """
    def __init__(self, content):
        self.content = content


def rerun_db(
    db,
    outdir,
    tStop=None,
    neuron_param_modify_functions=[],
    network_param_modify_functions=[],
    synapse_activation_modify_functions=[],
    stis=None,
    silent=False,
    additional_network_params=[],
    child_process=False):
    """Recreate and resimulate a network-embedded neuron simulation from a simrun-initialized database.
    
    This method recreates the network-embedded neuron simulation from the parameter files in the simrun-initialized database.
    It allows to adapt the cell parameters, network parameters, and the synaptic activation patterns with modification functions.
    The results are stored in the specified directory, relative to the original unmodified simulation results.
    
    Args:
        db (:py:class:`~data_base.DataBase`): A simrun-initialized database to resimulate.
        stis (list): List of simulation trial indices to be resimulated.
        outdir (str): Directory where the simulation results are stored, relative to the original simulation results.
        tStop (float): Time in ms at which the simulation should stop.
        neuron_param_modify_functions (list): List of functions which take :py:class:`NTParameterSet` neuron parameters and may return it changed.
        network_param_modify_functions (list): List of functions which take :py:class:`NTParameterSet` network parameters and may return it changed.
        synapse_activation_modify_functions (list): List of functions which take a :ref:`synapse_activation_format` dataframe and may return it changed.
        additional_network_params (list): List of additional :ref:`network_parameters_format` files to be used in the simulation.
        silent (bool): If True, suppresses output from the simulation.
        child_process (bool): If True, runs the simulation in a child process.
        
    Returns:
        list: A list of dask delayed objects. When computed with a dask scheduler, it writes the simulation results to the specified directory.
        
    See also:
        :py:mod:`~data_base.isf_data_base.db_initializers.init_simrun_general` for initializing a database from raw :py:mod:`simrun` output and its available keys. 
    """
    parameterfiles = db['parameterfiles']
    neuron_folder = db['parameterfiles_cell_folder']
    network_folder = db['parameterfiles_network_folder']
    sa = db['synapse_activation']
    # without the opaque object, dask tries to load in the entire dataframe before passing it to _evoked_activity
    sa = Opaque(sa)
    if stis is not None:
        parameterfiles = parameterfiles.loc[stis]
    sim_trial_index_array = parameterfiles.groupby('path_neuron').apply(
        lambda x: list(x.index)).values
    delayeds = []

    myfun = _evoked_activity

    if silent:
        myfun = silence_stdout(myfun)

    if child_process:
        myfun = execute_in_child_process(myfun)

    myfun = dask.delayed(myfun)
    logger.info('outdir is', outdir)
    for stis in sim_trial_index_array:
        d = myfun(
            db,
            stis,
            outdir,
            tStop=tStop,
            neuron_param_modify_functions=neuron_param_modify_functions,
            network_param_modify_functions=network_param_modify_functions,
            synapse_activation_modify_functions=
            synapse_activation_modify_functions,
            parameterfiles=parameterfiles.loc[stis],
            neuron_folder=neuron_folder,
            network_folder=network_folder,
            sa=sa,
            additional_network_params=additional_network_params)
        delayeds.append(d)
    return delayeds
import os, os.path
from ._matplotlib_import import *
import sys
import time
import glob, shutil
import tempfile
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
from model_data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
import numpy as np
import pandas as pd
from .utils import *
import logging

logger = logging.getLogger("ISF").getChild(__name__)

h = neuron.h


def convertible_to_int(x):
    try:
        int(x)
        return True
    except:
        return False


def synapse_activation_df_to_roberts_synapse_activation(sa):
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

def simtrail_to_cell_object(mdb, sim_trail_index, compute = True, allPoints = False, \
                            scale_apical = None, range_vars = None, silent = True,
                            neuron_param_modify_functions = [],
                            network_param_modify_functions = [],
                            synapse_activation_modify_functions = [],
                            additional_network_params = [],
                            tStop = 345):
    '''Resimulates simulation trail and returns cell object.
    Expects Instance of ModelDataBase and sim_trail index.
    The mdb has to contain the paths to the parameterfiles at the following location: 
        ('parameterfiles', 'cellName')
        ('parameterfiles', 'networkName')
        
    Keyword arguments:
        compute (default: True): If true, a cell object is returned. If false, the respective
                            delayed object is returned
        allPoints (default: False): if True, the cell will be simulated at very high resolution.
                            This mode might be useful for high quality visualizations.
        scale_apical: function that gets called after the cell is set up. 
        range_vars: range variables that should be recorded
        silent: If True, nothing will be written to stdout                    
    '''
    stdout_bak = sys.stdout
    if silent == True:
        sys.stdout = open(os.devnull, "w")

    try:
        metadata = mdb['metadata']
        metadata = metadata[metadata.sim_trail_index == sim_trail_index]
        assert len(metadata) == 1
        m = metadata.iloc[0]
        parameter_table = mdb['parameterfiles']
        cellName = parameter_table.loc[sim_trail_index].hash_neuron
        cellName = os.path.join(mdb['parameterfiles_cell_folder'], cellName)
        networkName = parameter_table.loc[sim_trail_index].hash_network
        networkName = os.path.join(mdb['parameterfiles_network_folder'],
                                   networkName)
        sa = mdb['synapse_activation'].loc[sim_trail_index].compute()
        dummy =  trail_to_cell_object(cellName = cellName, \
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
                                    additional_network_params = additional_network_params)
    finally:
        if silent == True:
            sys.stdout = stdout_bak

    return dummy


import tempfile
# def trail_to_cell_object(name = None, cellName = None, networkName = None, synapse_activation_file = None, \
#                     range_vars = None, scale_apical = None, allPoints = False, compute = True, tStop = 345,
#                     neuron_param_modify_functions = [],
#                     network_param_modify_functions = [],
#                     synapse_activation_modify_functions = [],
#                     additional_network_params = []):
#     tempdir = None

#     try:
#         #if pandas dataframe instead of path is given: convert pandas dataframe to file
#         if isinstance(synapse_activation_file, pd.DataFrame):
#             tempdir = tempfile.mkdtemp()
#             for fun in synapse_activation_modify_functions:
#                 synapse_activation_file = fun(synapse_activation_file)

#             syn = synapse_activation_df_to_roberts_synapse_activation(
#                 synapse_activation_file)
#             synfile = syn
#         elif isinstance(synapse_activation_file, str):
#             synfile = synapse_activation_file
#             if len(synapse_activation_modify_functions) > 0:
#                 raise NotImplementedError()
#         #set up simulation
#         simName = name
#         cellName = cellName
#         evokedUpParamName = networkName
#         neuronParameters = load_param_file_if_path_is_provided(cellName)
#         evokedUpNWParameters = load_param_file_if_path_is_provided(
#             evokedUpParamName)
#         additional_network_params = [
#             scp.build_parameters(p) for p in additional_network_params
#         ]
#         for fun in network_param_modify_functions:
#             evokedUpNWParameters = fun(evokedUpNWParameters)
#         for fun in neuron_param_modify_functions:
#             neuronParameters = fun(neuronParameters)
#         scp.load_NMODL_parameters(neuronParameters)
#         scp.load_NMODL_parameters(evokedUpNWParameters)
#         cellParam = neuronParameters.neuron
#         paramEvokedUp = evokedUpNWParameters.network
#         vTraces = []
#         tTraces = []

#         #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical)
#         cell = scp.create_cell(cellParam,
#                                scaleFunc=scale_apical,
#                                allPoints=allPoints)
#         cell.re_init_cell()

#         tOffset = 0.0  # avoid numerical transients
#         tStop = tStop
#         neuronParameters.sim.tStop = tStop
#         dt = neuronParameters.sim.dt
#         offsetBin = int(tOffset / dt + 0.5)
#         nRun = 0
#         synParametersEvoked = paramEvokedUp
#         startTime = time.time()
#         evokedNW = scp.NetworkMapper(cell, synParametersEvoked,
#                                      neuronParameters.sim)
#         evokedNW.re_init_network()
#         # rieke add 
#         additional_evokedNWs = [
#             scp.NetworkMapper(cell, p.network, neuronParameters.sim)
#             for p in additional_network_params
#         ]
#         for additional_evokedNW in additional_evokedNWs:
#             additional_evokedNW.create_saved_network2()
            
#         for additional_evokedNW in additional_evokedNWs:
#             additional_evokedNW.re_init_network()
#         # /rieke add
#         evokedNW.reconnect_saved_synapses(synfile)
        
#         if range_vars is not None:
#             if isinstance(range_vars, str):
#                 range_vars = [range_vars]
#             for var in range_vars:
#                 cell.record_range_var(var)

#         if compute:
#             tVec = h.Vector()
#             tVec.record(h._ref_t)
#             startTime = time.time()
#             scp.init_neuron_run(neuronParameters.sim,
#                                 vardt=False)  #trigger the actual simulation
#             stopTime = time.time()
#             simdt = stopTime - startTime
#             logger.info('NEURON runtime: {:.2f} s'.format(simdt))
#             t = np.array(tVec)
#             vmSoma = np.array(cell.soma.recVList[0])
#             cell.t = np.array(t[offsetBin:])
#             cell.vmSoma = np.array(vmSoma[offsetBin:])
#     except:
#         raise
#     finally:
#         if tempdir is not None:
#             shutil.rmtree(tempdir)
#     return cell



def trail_to_cell_object(name = None, cellName = None, networkName = None, synapse_activation_file = None, \
                    range_vars = None, scale_apical = None, allPoints = False, compute = True, tStop = 345,
                    neuron_param_modify_functions = [],
                    network_param_modify_functions = [],
                    synapse_activation_modify_functions = [],
                    additional_network_params = []):
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
        #set up simulation
        simName = name
        cellName = cellName
        evokedUpParamName = networkName
        neuronParameters = load_param_file_if_path_is_provided(cellName)
        evokedUpNWParameters = load_param_file_if_path_is_provided(
            evokedUpParamName)
        
        for fun in network_param_modify_functions:
            evokedUpNWParameters = fun(evokedUpNWParameters)
        for fun in neuron_param_modify_functions:
            neuronParameters = fun(neuronParameters)
        
        additional_network_params = [
            scp.build_parameters(p) for p in additional_network_params
        ]
        
        # merge additional network parameters
        for additional_network_param in additional_network_params:
            evokedUpNWParameters = merge_network_parameters(
                evokedUpNWParameters, additional_network_param
                )
        
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
            neuronParameters.sim
            )
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
            scp.init_neuron_run(neuronParameters.sim,
                                vardt=False)  #trigger the actual simulation
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


def merge_network_parameters(netw1, netw2):
    """Merge two network parameter configurations

    Given two network parameters, add the parameters configuring the presynaptic celltypes of the second to the first, if they do not exist in the first.
    Usually, different network parameters belong to different networks entirely. However, there are cases in which you want to re-simulate from existing synaptic activations,
    and you do not know from which network each synaptic activation originates. See e.g. :py:meth:`~simrun2.sim_trail_to_cell_object.trail_to_cell_object`.
    For this reason, it may be useful to merge network parameters, such that a :class:`~single_cell_parser.network.NetworkMapper` object can be instantiated, and such that
    it knows what the weight distribution and receptor types are correpsonding to potentially newly defined presynaptic cell types.

    Args:
        netw1 (dict): The first network parameters
        netw2 (dict) The second network parameters

    Raises:
        NotImplementedError: If the second network parameters contains presynaptic celltypes that also exist in the first. In this case, it is unclear which one should take precedence.

    Returns:
        dict: The updated network parameters, now containing the presynaptic cell types that exist in :paramref:netw2

    """
    if netw1.info != netw2.info:
        logger.warning("Network parameters do not have the same info.\nNetwork 1 info: {}\nNetwrok 2 info: {}".format(
        netw1.info, netw2.info))
    if netw1.NMODL_mechanisms != netw2.NMODL_mechanisms:
        logger.warning("Network parameters do not have the same NMODL_mechanisms.\nNetwork 1 NMODL_mechanisms: {}\nNetwrok 2 NMODL_mechanisms: {}".format(
        netw1.NMODL_mechanisms, netw2.NMODL_mechanisms))
        
    for presyn_type in netw2.network.keys():
        if presyn_type not in netw1.keys():
            logger.info("Adding presynaptic celltype {} to network parameters".format(presyn_type))
            netw1.network[presyn_type] = netw2.network[presyn_type]
        else:
            raise NotImplementedError(
                "Merging two network parameter files that both define parameters for the same presynaptic cell-type is not supported."
                "I don't know how to merge this."
                "Which weight distribution and receptor types take precedence?")
    return netw1
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

log = logging.getLogger("ISF").getChild(__name__)

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
        additional_network_params = [
            scp.build_parameters(p) for p in additional_network_params
        ]
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
        cell = scp.create_cell(cellParam,
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
        evokedNW = scp.NetworkMapper(cell, synParametersEvoked,
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
            scp.init_neuron_run(neuronParameters.sim,
                                vardt=False)  #trigger the actual simulation
            stopTime = time.time()
            simdt = stopTime - startTime
            log.info('NEURON runtime: {:.2f} s'.format(simdt))
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

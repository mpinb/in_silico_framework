import single_cell_parser as scp
import single_cell_analyzer as sca
import os
import time
import neuron
import dask
import numpy as np
import pandas as pd
from biophysics_fitting.utils import execute_in_child_process
from .utils import *

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
        synTimes = [v for k, v in six.iteritems(values) if convertible_to_int(k) and not np.isnan(v)]
        tuple_ = values.synapse_ID, values.section_ID, values.section_pt_ID, synTimes, values.soma_distance
        synapses[values.synapse_type].append(tuple_)
    return synapses


def _evoked_activity(mdb, stis, outdir, tStop = None, 
                     neuron_param_modify_functions = [],
                     network_param_modify_functions = [],
                     synapse_activation_modify_functions = [],
                     parameterfiles = None,
                     neuron_folder = None,
                     network_folder = None,
                     sa = None):
    import neuron
    h = neuron.h
    sti_bases = [s[:s.rfind('/')] for s in stis]
    if not len(set(sti_bases)) == 1:
        raise NotImplementedError
    sti_base = sti_bases[0]
    sa = sa.content
    sa = sa.loc[stis].compute(get = dask.get)
    sa = {s:g for s,g in sa.groupby(sa.index)}
    
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
        
        sti_number = int(sti[sti.rfind('/')+1:])
        syn_df = sa[sti]
        
        syn_df = sa[sti]
        for fun in synapse_activation_modify_functions:
            syn_df = fun(syn_df)
            
        syn = synapse_activation_df_to_roberts_synapse_activation(syn_df)
        
        evokedNW = scp.NetworkMapper(cell, network_param.network, neuron_param.sim)
        evokedNW.reconnect_saved_synapses(syn)
                    
        stopTime = time.time()
        setupdt = stopTime - startTime
        print('Network setup time: {:.2f} s'.format(setupdt))
                
        synTypes = list(cell.synapses.keys())
        synTypes.sort()
        
        print('Testing evoked response properties run {:d} of {:d}'.format(lv+1, len(stis)))
        tVec = h.Vector()
        tVec.record(h._ref_t)
        startTime = time.time()
        scp.init_neuron_run(neuron_param.sim, vardt=False) #trigger the actual simulation
        stopTime = time.time()
        simdt = stopTime - startTime
        print('NEURON runtime: {:.2f} s'.format(simdt))
        
        vmSoma = np.array(cell.soma.recVList[0])
        t = np.array(tVec)
        cell.t = t ##
        vTraces.append(np.array(vmSoma[:])), tTraces.append(np.array(t[:]))
        for RSManager in recSiteManagers:
            RSManager.update_recordings()
        
        print('writing simulation results')
        fname = 'simulation'
        fname += '_run%07d' % sti_number
        
        synName = outdir_absolute + '/' + fname + '_synapses.csv'
        print('computing active synapse properties')
        sca.compute_synapse_distances_times(synName, cell, t, synTypes) #calls scp.write_synapse_activation_file
        preSynCellsName = outdir_absolute + '/' + fname + '_presynaptic_cells.csv'
        scp.write_presynaptic_spike_times(preSynCellsName, evokedNW.cells)        
        
        cell.re_init_cell()
        evokedNW.re_init_network()

        print('-------------------------------')
    vTraces = np.array(vTraces)
    dendTraces = []
    uniqueID = sti_base.strip('/').split('_')[-1]
    scp.write_all_traces(outdir_absolute+'/'+uniqueID+'_vm_all_traces.csv', t[:], vTraces)
    for RSManager in recSiteManagers:
        for recSite in RSManager.recordingSites:
            tmpTraces = []
            for vTrace in recSite.vRecordings:
                tmpTraces.append(vTrace[:])
            recSiteName = outdir_absolute +'/' + uniqueID + '_' + recSite.label + '_vm_dend_traces.csv'
            scp.write_all_traces(recSiteName, t[:], tmpTraces)
            dendTraces.append(tmpTraces)
    dendTraces = np.array(dendTraces)
    
    print('writing simulation parameter files')
    neuron_param.save(os.path.join(outdir_absolute, uniqueID + '_neuron_model.param'))
    network_param.save(os.path.join(outdir_absolute, uniqueID+ '_network_model.param'))        
        
class Opaque:
    
    def __init__(self, content):
        self.content = content
        
def rerun_mdb(mdb, outdir, tStop = None,
                     neuron_param_modify_functions = [],
                     network_param_modify_functions = [],
                     synapse_activation_modify_functions = [], 
                     stis = None,
                     silent = False, 
                     child_process = False):
    parameterfiles = mdb['parameterfiles']
    neuron_folder = mdb['parameterfiles_cell_folder']
    network_folder = mdb['parameterfiles_network_folder']
    sa = mdb['synapse_activation'] 
    # without the opaque object, dask tries to load in the entire dataframe before passing it to _evoked_activity
    sa = Opaque(sa)
    if stis is not None:
        parameterfiles = parameterfiles.loc[stis]
    sim_trial_index_array = parameterfiles.groupby('path_neuron').apply(lambda x: list(x.index)).values
    delayeds = []
    
    myfun = _evoked_activity
    
    if silent:
        myfun = silence_stdout(myfun)
    
    if child_process:
        myfun = execute_in_child_process(myfun)
    
    myfun = dask.delayed(myfun)
    
    for stis in sim_trial_index_array:
        d = myfun(mdb, stis, outdir, tStop = tStop,
                             neuron_param_modify_functions = neuron_param_modify_functions,
                             network_param_modify_functions = network_param_modify_functions,
                             synapse_activation_modify_functions = synapse_activation_modify_functions,
                             parameterfiles = parameterfiles,
                             neuron_folder = neuron_folder,
                             network_folder = network_folder,
                             sa = sa)
        delayeds.append(d)
    return delayeds
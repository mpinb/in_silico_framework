'''This module has three parts.

First: class to manage synaptic strength fitting
Second: functions to simulate PSPs
Third: functions to analyze PSPs'''

import warnings
import Interface as I
activate_functional_synapse = I.network.activate_functional_synapse
from .utils import get_cellnumbers_from_confile, split_network_param_in_one_elem_dicts
from .get_cell_with_network import get_cell_with_network
from biophysics_fitting.hay_evaluation import objectives_BAC, objectives_step
import logging
log = logging.getLogger(__name__)

###############################
# First part: class to manage synaptic strength fitting
###############################
class PSPs:
    '''main class for calculation of ePSP amplitudes and synaptic strength fitting'''
    def __init__(self, neuron_param = None, confile = None, gExRange = [0.5, 1.0, 1.5, 2.0], 
                 AMPA_component = 1, NMDA_component = 1, vardt = True,
                 mode = 'cells', exc_inh = 'exc',
                 tStim = 110, tEnd = 150):
        ''' 
        neuron_param: I.scp.NTParameterSet structure specifying the biophysical model
        confile: path to .con-file of the network realization that should be used
        gExRange: synaptic strength values to be checked
        vardt: should the variable step size solver be used=
        '''
        assert('neuron' in list(neuron_param.keys()))
        self.neuron_param = neuron_param
        self.confile = confile
        self.gExRange = gExRange
        self.vardt = vardt
        self.AMPA_component = AMPA_component
        self.NMDA_component = NMDA_component
        self.mode = mode
        self.tStim = tStim
        self.tEnd = tEnd
        self._keys = []
        self._delayeds = []
        self._simfun = I.dask.delayed(run_ex_synapses)
        self.futures = None
        self.result = None
        
        if exc_inh == 'exc':
            self.network_param = generate_ex_network_param_from_network_embedding(self.confile)
        elif exc_inh == 'inh':
            self.network_param = generate_inh_network_param_from_network_embedding(self.confile)
        self.network_params_by_celltype = split_network_param_in_one_elem_dicts(self.network_param)
        
        self._setup_computation(exc_inh)
        
    def _setup_computation(self, exc_inh):
        if exc_inh == 'exc':
            log.info('setting up computation for exc cells')
            for n in self.network_params_by_celltype:
                assert(len(list(n.network.keys())) == 1)
                celltype = list(n.network.keys())[0]
                n.network[celltype]['synapses']
                for gEx in self.gExRange:
                    self._keys.append((celltype, gEx*self.AMPA_component, gEx*self.NMDA_component))
                    d = self._simfun(I.cloudpickle.dumps(self.neuron_param), I.cloudpickle.dumps(n), 
                                     celltype, gAMPA = gEx*self.AMPA_component, 
                                     gNMDA = gEx*self.NMDA_component, vardt = self.vardt, 
                                     mode = self.mode,
                                     tStim = self.tStim, tEnd = self.tEnd)
                    self._delayeds.append(d)
        elif exc_inh == 'inh':
            log.info('setting up computation for inh cells')
            for n in self.network_params_by_celltype:
                assert(len(list(n.network.keys())) == 1)
                celltype = list(n.network.keys())[0]
                n.network[celltype]['synapses']
                for gEx in self.gExRange:
                    self._keys.append((celltype, gEx, gEx))
                    d = self._simfun(I.cloudpickle.dumps(self.neuron_param), I.cloudpickle.dumps(n), 
                                     celltype, gGABA = gEx, 
                                     vardt = self.vardt, 
                                     mode = self.mode,
                                     tStim = self.tStim, tEnd = self.tEnd)
                    self._delayeds.append(d)                
        
    def run(self, client, rerun = False):
        '''start running computation on dask.distributed.Client
        client: dask.distributedClient object
        
        rerun: If True, a computation can be restarted. Otherwise, 
                calling this function has no effect if the 
                computation is already running'''
        if (self.futures is None) or rerun:
            self.result = None
            self.futures = client.compute(self._delayeds)
    
    def get_voltage_traces(self):
        '''Returns voltage and timing of all synapse activations.
        Fetches results from the cluster.'''
        if self.result is None:
            self.result = [f.result() for f in self.futures]
            assert(len(self._keys) == len(self.result))   
            del self.futures
            self.futures = 'done'  
        out = I.defaultdict_defaultdict()
        for lv, k in enumerate(self._keys):
            out[k[0]][k[1]][k[2]] = self.result[lv]
            # calculate maximum voltage in the respective simulation
            # list comprehension used to flatten the list
            max = I.np.max([x for x in self.result[lv][3] for x in x])
            #if  max > -45:
            #    errstr = "Result Nr {} has a maximum membrane potential of {} mV. ".format(lv, max) +\
            #             "Make sure, the cell does not depolarize during initialization "+\
            #             "as a suprathreashold activity can potentially change the PSP."
            #    warnings.warn(errstr)
                #if max > 0:
                #    raise RuntimeError(errstr)
        return out
    
    def get_voltage_and_timing(self, method = 'dynamic_baseline', merged = False, merge_celltype_kwargs = {}):
        '''calculate maxmimum and timing of the EPSPS
        method: dynamic_baseline: a simulation without any synaptic activation is 
            substracted from a simulation with cell activation. The maximum and 
            timepoint of maximum is returned
        method: constant_baseline: the voltage at t = 110ms (= directly before
            synapse activation) is considered as baseline and substracted
            from all voltages at all timepoints.
            The maximum and timepoint of the maximum after t = 110ms is 
            returned. 
        '''
        res = self.get_voltage_traces()
        if merged:
            res = merge_celltypes(res, **merge_celltype_kwargs)
        return get_voltage_and_timing(res, method, tStim = self.tStim, tEnd = self.tEnd)
        
    def get_summary_statistics(self, method = 'dynamic_baseline',
                               merge_celltype_kwargs = {},
                               ePSP_summary_statistics_kwargs = {}):
        vt = self.get_voltage_and_timing(method, 
                                         merged = True, 
                                         merge_celltype_kwargs=merge_celltype_kwargs)
        return ePSP_summary_statistics(vt, **ePSP_summary_statistics_kwargs)
    
    def get_optimal_g(self, 
                      measured_data, 
                      method = 'dynamic_baseline'):
        pdf = self.get_summary_statistics(method = method)
        pdf = pdf.reset_index()
        pdf = pdf.groupby('celltype').apply(linear_fit_pdf)
        pdf = I.pd.concat([pdf, measured_data], axis = 1)
        calculate_optimal_g(pdf)
        return pdf
    
    def visualize_psps(self, g = 1.0, method = 'dynamic_baseline', merge_celltype_kwargs={}, fig = None):
        psp = self
        vt = psp.get_voltage_and_timing(method, merged = True, 
                                        merge_celltype_kwargs=merge_celltype_kwargs)        
        #vt = I.simrun3.synaptic_strength_fitting.get_voltage_and_timing(vt, method)
        pdf = I.pd.concat([I.pd.Series([x[1] for x in vt[name][g][g]], name = name) 
             for name in list(vt.keys())], axis = 1)
        if fig is None:
            fig = I.plt.figure(figsize = (10,len(vt)*1.3))
        ax = fig.add_subplot(111)
        lower_bound = min(0, pdf.min().min())
        upper_bound = max(0, pdf.max().max())
        pdf.plot(kind = 'hist', 
                 subplots = True, 
                 bins = I.np.arange(lower_bound,upper_bound, 0.01), 
                 ax = ax)  
    
    def _get_cell_and_nw_map(self, network_param = None):
        neuron_param = self.neuron_param
        if network_param is None:
            network_param = self.network_param # psp.network_params_by_celltype[0]  
        cell_nw_generator = I.simrun3.get_cell_with_network.get_cell_with_network(neuron_param, 
                                                                                  network_param)
        cell, nwMap = cell_nw_generator()
        return cell, nwMap
    
    def get_synapse_coordinates(self, population, flatten = False, cell_indices=None):
        _, nwMap = self._get_cell_and_nw_map()
        cells = nwMap.cells[population]
        if cell_indices is not None:
            cells = [cells[lv] for lv in cell_indices]
        synapses = [c.synapseList for c in cells]
        syn_coordinates = [[syn.coordinates for syn in synlist] for synlist in synapses]
        if flatten:
            syn_coordinates = [x for x in syn_coordinates for x in x]
        return syn_coordinates

    def get_merged_synapse_coordinates(self, mergestring, flatten = False):
        _, nwMap = self._get_cell_and_nw_map()  
        cells = []
        for k in sorted(nwMap.cells.keys()):
            if not mergestring in k:
                continue
            log.info(k)
            cells.extend(nwMap.cells[k])
        synapses = [c.synapseList for c in cells]
        syn_coordinates = [[syn.coordinates for syn in synlist] for synlist in synapses]
        if flatten:
            syn_coordinates = [x for x in syn_coordinates for x in x]
        return syn_coordinates 
    
    def get_synapse_coordinates_with_psp_amplitude(self, population, g = 1.0, merged = True, select_synapses_per_cell = None):   
        if merged:
            coordinates = self.get_merged_synapse_coordinates(population)
            values = self.get_voltage_and_timing(merged = True, 
                                                 merge_celltype_kwargs=dict(detection_strings = [population]))
        else:
            coordinates = self.get_synapse_coordinates(population)
            values = self.get_voltage_and_timing(merged = False)
        values = [x[1] for x in values[population][g][g]]
        if select_synapses_per_cell is None:
            dummy = [list(c) + [v] for clist, v in zip(coordinates, values)
                     for c in clist]
        else:
            dummy = [list(c) + [v] for clist, v in zip(coordinates, values)
                     for c in clist if len(clist) == select_synapses_per_cell]            
        return I.np.array(dummy)
   
    #neuron_param = PSP_c2center_robert.neuron_param
    #############
    # changing the hoc_file: does it resolve the issue?
    #####################
    ####################
    

    def plot_vt(self, population, 
                opacity = 1, 
                g = 1.0, 
                merge = True, 
                merge_celltype_kwargs={},
                fig = None): 
        vt = self.get_voltage_traces() # d.compute(get = I.dask.get)
        if merge: 
            vt = merge_celltypes(vt, **merge_celltype_kwargs)
        vt = vt[population][g][g]
        if fig is None:
            fig = I.plt.figure(figsize = (10,5))
        fig.suptitle(population)            
        ax = fig.add_subplot(121)
        ax.plot(vt[0], vt[1], c = 'r')
        for lv in range(len(vt[2])):
            ax.plot(vt[2][lv], vt[3][lv], alpha = opacity, c = 'k')
        t_baseline,v_baseline = I.np.arange(0,self.tEnd,0.025), I.np.interp(I.np.arange(0,self.tEnd,0.025), 
                                                                      vt[0], vt[1])
        ax = fig.add_subplot(122)
        for lv in range(len(vt[2])):
            t,v = vt[2][lv], vt[3][lv]
            t,v = I.np.arange(0,self.tEnd,0.025), I.np.interp(I.np.arange(0,self.tEnd,0.025), t, v)
            ax.plot(t,v-v_baseline, alpha = opacity, c = 'k')       
         
    
#############################################
# Second part: functions to simulate PSPs 
#############################################
def set_ex_synapse_weight(syn, weight):
    if weight is not None:
        assert(len(weight) == 2)
        gAMPA = weight[0]
        gNMDA = weight[1]
        syn.weight = {'glutamate_syn': [gAMPA, gNMDA]}
    
def set_inh_synapse_weight(syn, weight):
    if weight is not None:
        gGABA = weight
        syn.weight = {'gaba_syn': gGABA}    

def run_ex_synapse(cell_nw_generator, neuron_param, network_param, celltype, preSynCellID, 
                   gAMPA = None, gNMDA = None, gGABA = None,
                   vardt = False, return_cell = False, synapseID = None, tEnd = None, tStim = None):
    '''core function, that actually activates a single synapse and runs the simulation.
    cell_nw_generator: simrun3.get_cell_with_network.get_cell_with_network
    neuron_param: single_cell_parser.NTParameterSet specifying biophysical properties
    network_param: single_cell_parser.NTParameterSet specifying network properties
    celltype: presynaptic celltype
    preSynCellID: number of presynaptic cell that should be activated. None: No cell will be activated.
    gEx: conductance of AMPA and NMDA component
    vardt: whether variable stepsize solver should be used
    synapse_ids: if None, all synapses assigned to the presynaptic cell get activated.
        if a list of integers, only synapses with the specified indices get acivated'''
    spikeTime = 0 
    assert(tStim is not None)
    assert(tEnd is not None)
    cell, nwMap = cell_nw_generator()
    
    # do not disable cells hat do not originate from this network_param
    # for cellType in nwMap.cells.keys(): 
    for cellType in list(network_param.network.keys()):
        for syn in cell.synapses[cellType]:
            syn.disconnect_hoc_synapse()
    
    synParameters = network_param.network[celltype]['synapses']
    
    for syn in cell.synapses[celltype]:
        syn.weight = {}
        if 'glutamate_syn' in list(synParameters.receptors.keys()):          
            syn.weight['glutamate_syn'] = [gAMPA, gNMDA]
        if 'gaba_syn' in list(synParameters.receptors.keys()): 
            syn.weight['gaba_syn'] = [gGABA]

    if preSynCellID is not None:
        assert(((gAMPA is not None) and (gNMDA is not None)) or (gGABA is not None))
        preSynCell = nwMap.cells[celltype][preSynCellID]
        if synapseID is None:
            synapse_list = preSynCell.synapseList
        else:
            synapse_list = [preSynCell.synapseList[synapseID]]       
        for syn in synapse_list:
            # syn.weight = {'glutamate_syn': [gAMPA, gNMDA]}  
            activate_functional_synapse(syn, cell, preSynCell, synParameters, releaseTimes = [tStim+spikeTime])
    
    neuron_param.sim.tStop = tEnd
    
    I.scp.init_neuron_run(neuron_param.sim, vardt = vardt)
    
    if return_cell:
        return cell
    
    t,v = I.np.array(cell.tVec), I.np.array(cell.soma.recVList)[0,:]


    # without the following lines, the simulation will crash from time to time
    try: 
        cell.evokedNW.re_init_network()
        log.info('found evokedNW attached to cell')
        log.info('explicitly resetting it.')
    except AttributeError:
        pass

    for cellType in list(nwMap.cells.keys()): 
        for syn in cell.synapses[cellType]:
            syn.disconnect_hoc_synapse()

    cell.re_init_cell()
    nwMap.re_init_network()
    
    return t,v

def run_ex_synapses(neuron_param, network_param, celltype, gAMPA = None, gNMDA = None, gGABA = None,
                    vardt = False,
                    tStim = None,
                    tEnd = None,
                    mode = 'cells'):
    '''method to consecutively calculate all EPSPs of all presynaptic cells of one celltype.'''

    neuron_param = I.scp.NTParameterSet(I.cloudpickle.loads(neuron_param).as_dict())
    network_param = I.scp.NTParameterSet(I.cloudpickle.loads(network_param).as_dict())    
    # with I.silence_stdout:
    cell_nw_generator = get_cell_with_network(neuron_param, network_param)
    cell, nwMap = cell_nw_generator()
    somaT, somaV, = [], []
    t_baseline, v_baseline = run_ex_synapse(cell_nw_generator, neuron_param, network_param, 
                                            celltype, None, gAMPA = gAMPA, gNMDA = gNMDA, gGABA = gGABA, 
                                            vardt = vardt, 
                                            tStim = tStim, tEnd = tEnd)
    n_cells = len(nwMap.connected_cells[celltype])
    if mode == 'cells':
        for preSynCellID in range(n_cells):
            log.info("Activating presyanaptic cell {} of {} cells of celltype {}".format(preSynCellID + 1, 
                                                                                      n_cells,
                                                                                      celltype))
            t,v = run_ex_synapse(cell_nw_generator, neuron_param, network_param, 
                                 celltype, preSynCellID, gAMPA, gNMDA, vardt = vardt,
                                 tStim = tStim, tEnd = tEnd)
            somaT.append(t), somaV.append(v)
        del cell_nw_generator, cell, nwMap
    if mode == 'synapses':
        for preSynCellID in range(n_cells):
            n_synapses = len(nwMap.cells[celltype][preSynCellID].synapseList)
            for preSynCellSynapseID in range(n_synapses):
                log.info("Activating synapse {} of presyanaptic cell {} of {} cells of celltype {}".format(preSynCellSynapseID + 1, 
                                                                                         preSynCellID + 1, 
                                                                                         n_cells,
                                                                                         celltype))
                t,v = run_ex_synapse(cell_nw_generator, neuron_param, network_param, 
                                     celltype, preSynCellID, gAMPA = gAMPA, gNMDA = gNMDA, 
                                     gGABA = gGABA, vardt = vardt,
                                     synapseID = preSynCellSynapseID,
                                     tStim = tStim, tEnd = tEnd)
                somaT.append(t), somaV.append(v)
        del cell_nw_generator, cell, nwMap        
    return t_baseline, v_baseline, somaT, somaV

def generate_ex_network_param_from_network_embedding(confile):
    '''returns a network parameter file that can be used to activate all presynaptic 
    conected cells as specified in confile:'''
    param_template = {'glutamate_syn': {'delay': 0.0,
      'parameter': {'decaynmda': 1.0,
                    'facilampa': 0.0,
                    'facilnmda': 0.0,
                    'tau1': 26.0,
                    'tau2': 2.0,
                    'tau3': 2.0,
                    'tau4': 0.1},
      'threshold': 0.0,
      'weight': [0.0, 1.0]}}
    
    out = I.defaultdict_defaultdict()
    import six
    for k, cellnumber in six.iteritems(get_cellnumbers_from_confile(confile)):
        if not k.split('_')[0] in I.excitatory:
            continue
        out['network'][k]['cellNr'] = cellnumber
        out['network'][k]['activeFrac'] = 1.0
        out['network'][k]['celltype'] = 'pointcell'
        out['network'][k]['spikeNr'] = 1
        out['network'][k]['spikeT'] = 10
        out['network'][k]['spikeWidth'] = 1.0
        out['network'][k]['synapses']['connectionFile'] = confile
        out['network'][k]['synapses']['distributionFile'] = confile[:-3] + 'syn'
        out['network'][k]['synapses']['receptors'] = param_template
    return I.scp.NTParameterSet(out) 

def generate_inh_network_param_from_network_embedding(confile):
    param_template = {'gaba_syn': {'delay': 0.0,
     'parameter': {'decaygaba': 1.0,
                   'decaytime': 20.0,
                   'e': -80.0,
                   'facilgaba': 0.0,
                   'risetime': 1.0},
     'threshold': 0.0,
     'weight': 1.0}}
    
    import six
    out = I.defaultdict_defaultdict()
    for k, cellnumber in six.iteritems(get_cellnumbers_from_confile(confile)):
        if not k.split('_')[0] in I.inhibitory:
            continue
        out['network'][k]['cellNr'] = cellnumber
        out['network'][k]['activeFrac'] = 1.0
        out['network'][k]['celltype'] = 'pointcell'
        out['network'][k]['spikeNr'] = 1
        out['network'][k]['spikeT'] = 10
        out['network'][k]['spikeWidth'] = 1.0
        out['network'][k]['synapses']['connectionFile'] = confile
        out['network'][k]['synapses']['distributionFile'] = confile[:-3] + 'syn'
        out['network'][k]['synapses']['receptors'] = param_template
    return I.scp.NTParameterSet(out)     

###############################################
# Third part: functions to analyze PSPs
###############################################
def get_voltage_and_timing(vt, method = 'dynamic_baseline', tStim = None, tEnd = None):
    '''calculate maxmimum and timing of the EPSPS
    vt: voltage traces, as returned by PSP.get_voltage_traces()
    method: dynamic_baseline: a simulation without any synaptic activation is 
        substracted from a simulation with cell activation. The maximum and 
        timepoint of maximum is returned
    method: constant_baseline: the voltage at t = 110ms (= directly before
        synapse activation) is considered as baseline and substracted
        from all voltages at all timepoints.
        The maximum and timepoint of the maximum after t = 110ms is 
        returned. 
    '''
    res = vt
    if method == 'dynamic_baseline':
        import six
        vt = {k: {k: {k: [get_tMax_vMax_baseline(v[0], v[1], v[2][lv], v[3][lv], tStim, tEnd)
                          for lv in range(len(v[2]))]
                      for k, v in six.iteritems(v)}
                  for k, v in six.iteritems(v)}
              for k, v in six.iteritems(res)}
    elif method == 'constant_baseline':
        vt = {k: {k: {k: [get_tMax_vMax(v[2][lv], v[3][lv], tStim, tEnd)
                          for lv in range(len(v[2]))]
                      for k, v in six.iteritems(v)}
                  for k, v in six.iteritems(v)}
              for k, v in six.iteritems(res)}
    else:
        errstr = 'method must be dynamic_baseline or constant_baseline'
        raise ValueError(errstr)
    return vt

def get_summary_statistics(self, method = 'dynamic_baseline',
                           merge_celltype_kwargs = {},
                           ePSP_summary_statistics_kwargs = {}):
    vt = self.get_voltage_and_timing(method, merged = True,
                                     merge_celltype_kwargs=merge_celltype_kwargs)
    vt = merge_celltypes(vt, **merge_celltype_kwargs)
    return ePSP_summary_statistics(vt, **ePSP_summary_statistics_kwargs)

def get_optimal_g(self, 
                  measured_data, 
                  method = 'dynamic_baseline',
                  threashold = 0.1):
    pdf = self.get_summary_statistics(method = method, threashold = threashold)
    pdf = pdf.reset_index()
    pdf = pdf.groupby('celltype').apply(linear_fit_pdf)
    pdf = I.pd.concat([pdf, measured_data], axis = 1)
    calculate_optimal_g(pdf)
    return pdf

def get_tMax_vMax_baseline(t_baseline,v_baseline, t,v, tStim = None, tEnd = None):
    '''this method calculates the ePSP amplitude by subtracting a voltage trace without
    any synapse activation from a voltage trace with synapse activation.
    t_basline, v_baseline: voltage trace without synapse activation
    t,v: voltage trace with synapse activation'''
    assert(tStim is not None)
    assert(tEnd is not None)    
    try:
        t,v = I.np.arange(0,tEnd,0.025), I.np.interp(I.np.arange(0,tEnd,0.025), t, v)
    except:
        raise RuntimeError() 
    t_baseline,v_baseline = I.np.arange(0,tEnd,0.025), I.np.interp(I.np.arange(0,tEnd,0.025), t_baseline, v_baseline)
    return get_tMax_vMax(t, v-v_baseline, tStim = tStim, tEnd = tEnd)
    # return I.sca.analyze_voltage_trace(v-v_baseline, t)

def analyze_voltage_trace(vTrace, tTrace):
    """
    takes neuron Vectors and finds time and
    amplitude of max voltage deflection (pos and negative direction)
    
    modified from single cell analyzer
    """
    v = I.np.array(vTrace)
    t = I.np.array(tTrace)
    max_abs_v = I.np.abs(v)
    maxT = t[I.np.argmax(max_abs_v)]
    maxV = v[I.np.argmax(max_abs_v)]
    return maxT, maxV

def get_tMax_vMax(t,v, tStim = None, tEnd = None):
    '''This method calculates the ePSP amplitude by subtracting the voltage
    directly before the epsp, which is supposed to be at 160ms, from the voltagetrace.'''
    assert(tStim is not None)
    assert(tEnd is not None)
    t,v = I.np.arange(0,tEnd,0.025), I.np.interp(I.np.arange(0,tEnd,0.025), t, v) 
    start_index = int(tStim - 1 / 0.025)
    stop_index = int(tStim / 0.025)
    baseline = I.np.median(v[start_index:stop_index]) # 1ms pre-stim
    v -= baseline
    return analyze_voltage_trace(v[stop_index:], t[stop_index:])

def merge_celltypes(vt, 
                    detection_strings = ['L2', 'L34', 'L4', 'L5st', 'L5tt', 'L6cc', 'L6ct', 'VPM_C2'], 
                    celltype_must_be_in = I.excitatory):
    '''concatenates voltagetraces of celltypes'''
    out = I.defaultdict_defaultdict()
    for detection_string in detection_strings:
        for celltype in sorted(vt.keys()):
            if not celltype.split('_')[0] in celltype_must_be_in:
                log.info('skipping {}'.format(celltype))
                continue
            for gAMPA in sorted(vt[celltype].keys()):
                for gNMDA in sorted(vt[celltype][gAMPA].keys()):
                    if detection_string in celltype:
                        # print celltype
                        if not isinstance(out[detection_string][gAMPA][gNMDA], list):
                            out[detection_string][gAMPA][gNMDA] = [vt[celltype][gAMPA][gNMDA][0],vt[celltype][gAMPA][gNMDA][1],[],[]]
                        out[detection_string][gAMPA][gNMDA][2].extend(vt[celltype][gAMPA][gNMDA][2])
                        out[detection_string][gAMPA][gNMDA][3].extend(vt[celltype][gAMPA][gNMDA][3])
                        
    return out

import six
def ePSP_summary_statistics(vt, threashold = 0.1, tPSPStart = 100.0):
    summaryData = []#I.defaultdict_defaultdict()
    for celltype, vt in six.iteritems(vt):
        for gAMPA, vt in six.iteritems(vt):
            for gNMDA, vt in six.iteritems(vt):
                t = list(v[0] for v in vt if v[1] >= threashold)                
                v = list(v[1] for v in vt if v[1] >= threashold)
                if len(t) == 0:
                    log.info(("skipping celltype {}, gAMPA {}, gNMDA {}: no response above threashold of {} found".format(celltype, gAMPA, gNMDA, threashold)))
                    continue
                out = {}                    
                out['epspMean'] = I.np.mean(v)
                out['epspStd'] = I.np.std(v)
                out['epspMed'] = I.np.median(v)
                out['epspMin'] = I.np.min(v)
                out['epspMax'] = I.np.max(v)
                out['tMean'] = I.np.mean(I.np.array(t)-tPSPStart)
                out['tStd'] = I.np.std(I.np.array(t)-tPSPStart)
                out['tMed'] = I.np.median(I.np.array(t)-tPSPStart)
                out['gNMDA'] = gNMDA
                out['gAMPA'] = gAMPA
                out['celltype'] = celltype
                summaryData.append(out)
    return I.pd.DataFrame(summaryData).set_index(['celltype', 'gAMPA', 'gNMDA'])

def linear_fit(gAMPANMDA, epsp):
    return I.np.polyfit(gAMPANMDA, epsp, 1)

def linear_fit_pdf(pdf):
    assert(pdf['gAMPA'].equals(pdf['gNMDA']))
    return I.pd.Series({'EPSP mean_offset': linear_fit(pdf.gAMPA, pdf.epspMean)[1],
                                       'EPSP mean_slope': linear_fit(pdf.gAMPA, pdf.epspMean)[0],
                                       'EPSP std_offset': linear_fit(pdf.gAMPA, pdf.epspStd)[1],
                                       'EPSP std_slope': linear_fit(pdf.gAMPA, pdf.epspStd)[0],
                                       'EPSP med_offset': linear_fit(pdf.gAMPA, pdf.epspMed)[1],
                                       'EPSP med_slope': linear_fit(pdf.gAMPA, pdf.epspMed)[0],
                                       'EPSP max_offset': linear_fit(pdf.gAMPA, pdf.epspMax)[1],
                                       'EPSP max_slope': linear_fit(pdf.gAMPA, pdf.epspMax)[0]})

def calculate_optimal_g(pdf):
    mean = (pdf['EPSP_mean_measured']-pdf['EPSP mean_offset']) / pdf['EPSP mean_slope']
    med = (pdf['EPSP_med_measured']-pdf['EPSP med_offset']) / pdf['EPSP med_slope']
    max_ = (pdf['EPSP_max_measured']-pdf['EPSP max_offset']) / pdf['EPSP max_slope']
    pdf['optimal g'] = (2 * mean + 2 * med + 1 * max_ ) * 1 / 5.
    pdf['optimal g mean'] = mean #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
    pdf['optimal g median'] = med #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
    pdf['optimal g max'] = max_ #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
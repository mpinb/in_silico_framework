import Interface as I
import numpy as np
import matplotlib.pyplot as plt
import os
import shutil
import dask
import pandas as pd

param_names = ['ephys.CaDynamics_E2_v2.apic.decay', 'ephys.CaDynamics_E2_v2.apic.gamma', 'ephys.CaDynamics_E2_v2.axon.decay', 'ephys.CaDynamics_E2_v2.axon.gamma',
    'ephys.CaDynamics_E2_v2.soma.decay', 'ephys.CaDynamics_E2_v2.soma.gamma', 'ephys.Ca_HVA.apic.gCa_HVAbar', 'ephys.Ca_HVA.axon.gCa_HVAbar',
    'ephys.Ca_HVA.soma.gCa_HVAbar', 'ephys.Ca_LVAst.apic.gCa_LVAstbar', 'ephys.Ca_LVAst.axon.gCa_LVAstbar', 'ephys.Ca_LVAst.soma.gCa_LVAstbar',
    'ephys.Ih.apic.linScale', 'ephys.Ih.apic.max_g', 'ephys.Im.apic.gImbar', 'ephys.K_Pst.axon.gK_Pstbar',
    'ephys.K_Pst.soma.gK_Pstbar', 'ephys.K_Tst.axon.gK_Tstbar', 'ephys.K_Tst.soma.gK_Tstbar', 'ephys.NaTa_t.apic.gNaTa_tbar',
    'ephys.NaTa_t.axon.gNaTa_tbar', 'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.axon.gNap_Et2bar', 'ephys.Nap_Et2.soma.gNap_Et2bar',
    'ephys.SK_E2.apic.gSK_E2bar', 'ephys.SK_E2.axon.gSK_E2bar', 'ephys.SK_E2.soma.gSK_E2bar', 'ephys.SKv3_1.apic.gSKv3_1bar',
    'ephys.SKv3_1.apic.offset', 'ephys.SKv3_1.apic.slope', 'ephys.SKv3_1.axon.gSKv3_1bar', 'ephys.SKv3_1.soma.gSKv3_1bar',
    'ephys.none.apic.g_pas', 'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas', 'ephys.none.soma.g_pas', 'scale_apical.scale']

whiskers = ['A1','A2','A3','A4','B1','B2','B3','B4','C1','C2','C3','C4','D1','D2','D3','D4','E1','E2','E3','E4','Alpha','Beta','Gamma','Delta']
def get_SWs():
    SW_2nd   = ['C2','C1','C2','C3','D2','D1','D4','D3','Delta','E2','E3','E4','B2','B1','B4','B3','C2','C1','C4','C3','C2','B2','E1','C2']
    whisker_pad = [['A1','A2','A3','A4'],
                ['B1','B2','B3','B4'],
                ['C1','C2','C3','C4'],
                ['D1','D2','D3','D4'],
                ['E1','E2','E3','E4']]
    SWs = {w:[] for w in whiskers}
    for row,r in enumerate(whisker_pad):
        for col, w in enumerate(r):
            for i in [-1,0,1]:
                for j in [-1,0,1]:
                    if row+i in range(len(whisker_pad)) and col+j in range(len(r)):
                        SWs[w].append(whisker_pad[row+i][col+j])

    for w in ['Alpha','Beta','A1','B1']:         SWs[w].append('Alpha')
    for w in ['Alpha','Beta','Gamma','B1','C1']: SWs[w].append('Beta')
    for w in ['Beta','Gamma','Delta','C1','D1']: SWs[w].append('Gamma')
    for w in ['Gamma','Delta','D1','E1']:        SWs[w].append('Delta')
    for w in ['A1','B1']:  SWs['Alpha'].append(w)
    for w in ['B1','C1']:  SWs['Beta'].append(w)
    for w in ['C1','D1']:  SWs['Gamma'].append(w)
    for w in ['D1','E1']:  SWs['Delta'].append(w)
    for w, SW2nd in zip(whiskers,SW_2nd): SWs[w].append(SW2nd)
    return SWs

center_pos = {
    '88': {'A1': 28, 'A2': 37, 'A3': 37, 'A4': 28, 'B1': 34, 'B2': 66, 'B3': 35, 'B4': 39, 
            'C1': 20, 'C2': 34, 'C3': 44, 'C4': 37, 'D1': 4, 'D2': 67, 'D3': 6, 'D4': 39, 
            'E1': 39, 'E2': 33, 'E3': 28, 'E4': 6, 'Alpha': 40, 'Beta': 41, 'Gamma': 29, 'Delta': 34},
    '64': {'A1': 30, 'A2': 27, 'A3': 39, 'A4': 23, 'B1': 24, 'B2': 8, 'B3': 12, 'B4': 34, 
            'C1': 19, 'C2': 50, 'C3': 72, 'C4': 31, 'D1': 5, 'D2': 24, 'D3': 37, 'D4': 38, 
            'E1': 36, 'E2': 37, 'E3': 32, 'E4': 3, 'Alpha': 31, 'Beta': 40, 'Gamma': 30, 'Delta': 35}, 
    '71': {'A1': 30, 'A2': 36, 'A3': 36, 'A4': 23, 'B1': 18, 'B2': 7, 'B3': 4, 'B4': 28, 
            'C1': 63, 'C2': 5, 'C3': 5, 'C4': 37, 'D1': 8, 'D2': 37, 'D3': 48, 'D4': 36, 
            'E1': 41, 'E2': 32, 'E3': 35, 'E4': 4, 'Alpha': 36, 'Beta': 38, 'Gamma': 30, 'Delta': 35},
    '89': {'A1': 28, 'A2': 35, 'A3': 34, 'A4': 27, 'B1': 34, 'B2': 2, 'B3': 10, 'B4': 32, 
            'C1': 14, 'C2': 64, 'C3': 1, 'C4': 32, 'D1': 37, 'D2': 60, 'D3': 48, 'D4': 35, 
            'E1': 41, 'E2': 32, 'E3': 37, 'E4': 3, 'Alpha': 30, 'Beta': 40, 'Gamma': 31, 'Delta': 37}, 
    '91': {'A1': 28, 'A2': 26, 'A3': 38, 'A4': 23, 'B1': 63, 'B2': 75, 'B3': 64, 'B4': 32, 
            'C1': 16, 'C2': 51, 'C3': 40, 'C4': 34, 'D1': 58, 'D2': 66, 'D3': 4, 'D4': 36, 
            'E1': 40, 'E2': 32, 'E3': 34, 'E4': 2, 'Alpha': 32, 'Beta': 38, 'Gamma': 31, 'Delta': 37}}

class SynapticStrengthFitting:
    def __init__(self, cell_param_file, confile):
        self.cell_param = I.scp.build_parameters(cell_param_file)
        sim_param = {'tStart': 0.0, 'tStop': 295, 'dt': 0.025, 'Vinit': -75.0, 'dt': 0.025, 'T': 34.0}
        for k,v in sim_param.items():
            self.cell_param.sim[k] = v
        self.confile = confile
        self.psp_object = I.simrun.synaptic_strength_fitting.PSPs(self.cell_param, self.confile)
        self.psps = None
        
    def run_synaptic_strength_fitting(self,client):
        self.psp_object.run(client)
        
    def check_fit_progress(self):
        print(self.psp_object.futures)
        
    def get_optimal_g(self,principal_column):
        vpm = 'VPM_'+principal_column
        measured_epsp = I.barrel_cortex.get_EPSP_measurement()
        index = list(measured_epsp.index)
        index[-1] = vpm
        measured_epsp.index= index
        self.optimal_g = self.psp_object.get_optimal_g(measured_epsp, merge_celltype_kwargs={'detection_strings':index})
        return self.optimal_g['optimal g']
    
def fit_synaptic_strength(cell_param_file, confile, client, principal_column):
    cell_param = I.scp.build_parameters(cell_param_file)
    sim_param = {'tStart': 0.0, 'tStop': 295, 'dt': 0.025, 'Vinit': -75.0, 'dt': 0.025, 'T': 34.0}
    for k,v in sim_param.items():
        cell_param.sim[k] = v
    psp = I.simrun.synaptic_strength_fitting.PSPs(cell_param, confile)
    psp.run(client)
    vpm = 'VPM_'+principal_column
    measured_epsp = I.barrel_cortex.get_EPSP_measurement()
    index = list(measured_epsp.index)
    index[-1] = vpm
    measured_epsp.index= index
    optimal_g = psp.get_optimal_g(measured_epsp, merge_celltype_kwargs={'detection_strings':index})
    syn_strength = optimal_g['optimal g'].to_dict()
    #print(syn_strength)
    return syn_strength

# This function was not used in the end, instead I.create_evoked_network_parameter was used
def create_network_param_file(path, syn,con,PSTH,syn_strength,evoked_columns, offset = 0,verbose = False):
    from copy import deepcopy
    template_EXC = {'cellNr': None,
                    'celltype': {'pointcell': {'distribution': 'PSTH_poissontrain_v2',
                                            'intervals': None,#None
                                            'offset': 0.0,
                                            'rates': None}},
                    'synapses': {'connectionFile': None,
                                'distributionFile': None,
                                'receptors': {'glutamate_syn': {
                                    'delay': 0.0,
                                    'parameter': {'decayampa': 1.0,
                                                'decaynmda': 1.0,
                                                'facilampa': 0.0,
                                                'facilnmda': 0.0,
                                                'tau1': 26.0,
                                                'tau2': 2.0,
                                                'tau3': 2.0,
                                                'tau4': 0.1},
                                    'threshold': 0.0,
                                    'weight': [None, None]}},
                                'releaseProb': 0.6}}
    template_INH = {'cellNr': None,
                'celltype': {'pointcell': {'distribution': 'PSTH_poissontrain_v2',
                                            'intervals': None,#None
                                            'offset': 0.0,
                                            'rates': None}},
                'synapses': {'connectionFile': None,
                                'distributionFile': None,
                                'receptors': {'gaba_syn': {
                                    'delay': 0.0,
                                    'parameter': {'decaygaba': 1.0,
                                                'decaytime': 20.0,
                                                'e': -80.0,
                                                'facilgaba': 0.0,
                                                'risetime': 1.0},
                                    'threshold': 0.0,
                                    'weight': 1.0}},
                                'releaseProb': 0.25}}
    template_info = {'author': 'abast', 'date': '23Sep2021', 'name': 'asd'}
    template_NMODL_mechanisms = {'VecStim': '/', 'synapses': '/'}
    def match_model_celltype_to_PSTH_celltype(celltype):
        if '_' in celltype: celltype = celltype.split('_')[0]
        if celltype in I.inhibitory or celltype == 'INH': key = 'INT'
        elif celltype in ('L4ss', 'L4py', 'L4sp'): key = 'L4ss'
        elif celltype == 'L5st': key = 'L5ST'
        elif celltype == 'L5tt': key = 'L5TT'
        elif celltype == 'L6cc': key = 'L6CC'
        elif celltype == 'VPM':  key = 'VPM'
        elif celltype in ('L2','L34'): key = 'L23'
        elif celltype in ('L6ct', 'L6ccinv'): key = 'inactive'
        else: raise ValueError(celltype)   
        if verbose: print('matching', celltype, 'to', key, 'PSTH')
        return key
        
    dict_, _ = I.scp.reader.read_functional_realization_map(con)
    connected_celltypes = dict_.keys()
    out = {}
    out['info'] = deepcopy(template_info)
    out['NMODL_mechanisms'] = deepcopy(template_NMODL_mechanisms)
    out['network'] = {}    
    for celltype in connected_celltypes:
        # set up template for celltype
        if (celltype in I.excitatory) or (celltype.split('_')[0] in I.excitatory):
            if verbose:
                print('assigning celltype', celltype, 'to excitatory template.')
            out['network'][celltype] = deepcopy(template_EXC)
            # awkward way of selecting the syn strength matching the current celltype
            synapse_strength_celltype = [x for x in syn_strength.keys() if x in celltype]
            assert(len(synapse_strength_celltype) == 1)
            synapse_strength_celltype = synapse_strength_celltype[0]
            if verbose:
                print('setting synapse strength of celltype', celltype, 'to synapse strength of',  synapse_strength_celltype)
            weight = syn_strength[synapse_strength_celltype]
            out['network'][celltype]['synapses']['receptors']['glutamate_syn']['weight'] = [weight, weight]
        elif (celltype in I.inhibitory) or (celltype.split('_')[0] in I.inhibitory):
            if verbose:
                print('assigning celltype', celltype, 'to inhibitory template.')
            out['network'][celltype] = deepcopy(template_INH)
        # fill template
        key = match_model_celltype_to_PSTH_celltype(celltype)
        bins, rates = PSTH[key]          
        bins = [b + offset for b in bins]
        bins[0] = 0
        if not celltype in ('INH', 'INH_S1'):
            if not evoked_columns == 'all':
                if not celltype.split('_')[1] in evoked_columns:
                    rates = np.ones_like(rates)*rates[0]
        out['network'][celltype]['celltype']['pointcell']['bins'] = list(bins)
        out['network'][celltype]['celltype']['pointcell']['rates'] = list(rates)
        n_connected_cells = max([x[1] for x in dict_[celltype]]) + 1# + 1 because counting starts at 0, so total number is + 1
        out['network'][celltype]['cellNr'] = n_connected_cells
        out['network'][celltype]['synapses']['connectionFile'] = con
        out['network'][celltype]['synapses']['distributionFile'] = syn
    if path is not None: I.scp.NTParameterSet(out).save(path) 
    return out

def create_neuron_param_file(path, param_names, param_values, hocfile):
    def get_neup_template():
        parameter_template = {
        'AIS': {
            'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}},
            'mechanisms': {'global': {},'range': {
            'CaDynamics_E2_v2': {'decay': None, 'gamma': None, 'spatial': 'uniform'},
            'Ca_HVA':           {'gCa_HVAbar': None, 'spatial': 'uniform'},
            'Ca_LVAst':         {'gCa_LVAstbar': None, 'spatial': 'uniform'},
            'Ih':               {'gIhbar': 8e-05, 'spatial': 'uniform'},
            'K_Pst':            {'gK_Pstbar': None, 'spatial': 'uniform'},
            'K_Tst':            {'gK_Tstbar': None, 'spatial': 'uniform'},
            'NaTa_t':           {'gNaTa_tbar': None, 'spatial': 'uniform'},
            'Nap_Et2':          {'gNap_Et2bar': None, 'spatial': 'uniform'},
            'SK_E2':            {'gSK_E2bar': None, 'spatial': 'uniform'},
            'SKv3_1':           {'gSKv3_1bar': None, 'spatial': 'uniform'},                              
            'pas':              {'e': -90, 'g': None, 'spatial': 'uniform'}}}},
        'ApicalDendrite': { 
            'properties': {'Ra': 100.0, 'cm': 2.0, 'ions': {'ek': -85.0, 'ena': 50.0}},
            'mechanisms': {'global': {},'range': {
            'CaDynamics_E2_v2': {'decay': None,'gamma': None, 'spatial': 'uniform'},
            'Ca_HVA':           {'begin': None, 'end': None,'gCa_HVAbar': None, 'outsidescale': 0.1, 'spatial': 'uniform_range'},
            'Ca_LVAst':         {'begin': None, 'end': None, 'gCa_LVAstbar': None, 'outsidescale': 0.01, 'spatial': 'uniform_range'},
            'Ih':               {'_lambda': 3.6161, 'distance': 'relative', 'gIhbar': 0.0002, 'linScale': 2.087, 'offset': -0.8696, 'max_g': None, 'spatial': 'capped_exponential', 'xOffset': 0.0},
            'Im':               {'gImbar': None, 'spatial': 'uniform'},
            'NaTa_t':           {'gNaTa_tbar': None, 'spatial': 'uniform'},
            'SK_E2':            {'gSK_E2bar': None, 'spatial': 'uniform'},
            'SKv3_1':           {'distance': 'relative', 'gSKv3_1bar': None, 'offset': None, 'slope': None, 'spatial': 'linear'},
            'pas':              {'e': -90, 'g': None, 'spatial': 'uniform'}}}},
        'Dendrite': {
            'properties': {'Ra': 100.0, 'cm': 2.0},
            'mechanisms': {'global': {},'range': {
            'Ih':               {'gIhbar': 0.0002, 'spatial': 'uniform'}, 'pas': {'e': -90.0, 'g': None, 'spatial': 'uniform'}}}},
        'Myelin': {
            'properties': {'Ra': 100.0, 'cm': 0.02},
            'mechanisms': {'global': {},'range': {
            'pas':              {'e': -90.0, 'g': 4e-05, 'spatial': 'uniform'}}}},
        'Soma': {
            'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}},
            'mechanisms': {'global': {},'range': {
            'CaDynamics_E2_v2': {'decay': None, 'gamma': None, 'spatial': 'uniform'},
            'Ca_HVA':           {'gCa_HVAbar': None, 'spatial': 'uniform'},
            'Ca_LVAst':         {'gCa_LVAstbar': None, 'spatial': 'uniform'},
            'Ih':               {'gIhbar': 8e-05, 'spatial': 'uniform'},
            'K_Pst':            {'gK_Pstbar': None, 'spatial': 'uniform'},
            'K_Tst':            {'gK_Tstbar': None, 'spatial': 'uniform'},
            'NaTa_t':           {'gNaTa_tbar': None, 'spatial': 'uniform'},
            'Nap_Et2':          {'gNap_Et2bar': None, 'spatial': 'uniform'},
            'SK_E2':            {'gSK_E2bar': None, 'spatial': 'uniform'},
            'SKv3_1':           {'gSKv3_1bar': None, 'spatial': 'uniform'},
            'pas':              {'e': -90, 'g': None, 'spatial': 'uniform'}}}},
        'cell_modify_functions': {'scale_apical': {'scale': None}},
        'filename': None,
        'discretization': {'max_seg_length': 50, 'f': 100}}
        
        neuron_template = I.scp.NTParameterSet(parameter_template)
        neup_template = {
        'neuron':neuron_template, 
        'NMODL_mechanisms': {},
        'sim': {
            'Vinit': -75.0,
            'T': 34.0,
            'tStart': 0.0,
            'tStop': 745,
            'dt': 0.025,
            'recordingSites': ['recSites.landmarkAscii']}}
        return neup_template
    def fill_template_biophysical_params(param_names, param_values):
        parameter_template = get_neup_template()
        compartment_map={'apic':'ApicalDendrite','axon':'AIS','soma':'Soma','dend':'Dendrite'}
        for name, value in zip(param_names,param_values):
            items = name.split('.')
            if len(items) == 4:
                mechanism, compartment, mechanism_param = items[1:]
                if mechanism == 'none' and mechanism_param == 'g_pas':
                    mechanism = 'pas'
                    mechanism_param = 'g'
                parameter_template['neuron'][compartment_map[compartment]]['mechanisms']['range'][mechanism][mechanism_param] = float(value)
            elif len(items) == 2:
                parameter_template['neuron']['cell_modify_functions'][items[0]][items[1]] = float(value)
            else:
                raise ValueError(name)
        return parameter_template
    def get_bifurcation(cell):
        from ibs_projects.hot_zone import Dendrogram
        d = Dendrogram(cell)
        d._compute_main_bifurcation_section()
        return d.main_bifur_dist
    def get_outsidescale_sections(cell):
        from biophysics_fitting.utils import get_inner_sec_dist_dict
        inner_sections = get_inner_sec_dist_dict(cell)
        outsidescale_sections = [lv for lv, sec in enumerate(cell.sections) if sec.label == 'ApicalDendrite' and sec not in inner_sections.values()]
        return outsidescale_sections
    def write_recording_sites_file(recsite_path, bifur, cell):
        rec_sites = {
            'BAC.hay_measure.recSite': bifur - 10 - 180,
            'BAC.stim.dist': bifur - 10 - 180,
            'bAP.hay_measure.recSite1':bifur - 10 - 180,
            'bAP.hay_measure.recSite2':bifur - 10,
            'crit_freq.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq.hay_measure.recSite2':bifur - 10,
            'crit_freq1.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq1.hay_measure.recSite2':bifur - 10,         
            'crit_freq2.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq2.hay_measure.recSite2':bifur - 10,  
            'crit_freq3.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq3.hay_measure.recSite2':bifur - 10,
            'crit_freq4.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq4.hay_measure.recSite2':bifur - 10,
            'crit_freq5.hay_measure.recSite1':bifur - 10 - 180, 
            'crit_freq5.hay_measure.recSite2':bifur - 10,
            'chirp.hay_measure.recSite2':bifur - 10,
            'chirp_dend.hay_measure.recSite2':bifur - 10}
        from biophysics_fitting.utils import vmApical_position
        landmark_positions = [vmApical_position(cell, dist = d) for d in [rec_sites['bAP.hay_measure.recSite1'], rec_sites['bAP.hay_measure.recSite2']]]
        I.scp.write_landmark_file(recsite_path, landmark_positions)

    from ibs_projects.hot_zone import get_cell_object_from_hoc
    cell = get_cell_object_from_hoc(hocfile)
    neup = fill_template_biophysical_params(param_names, param_values)
    bifur = get_bifurcation(cell)
    hotzone = [bifur - 100, bifur + 100]
    outsidescale_sections = get_outsidescale_sections(cell)
    neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_HVA']['begin']   = hotzone[0]
    neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_HVA']['end']     = hotzone[1]
    neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_LVAst']['begin'] = hotzone[0]
    neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_LVAst']['end']   = hotzone[1]
    if len(outsidescale_sections)>0:
        neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_HVA']['outsidescale_sections']   = outsidescale_sections
        neup['neuron']['ApicalDendrite']['mechanisms']['range']['Ca_LVAst']['outsidescale_sections'] = outsidescale_sections
    neup['neuron']['filename'] = hocfile
    recording_site_file = hocfile.replace(".hoc", ".landmarkAscii")
    write_recording_sites_file(recording_site_file, bifur, cell)
    neup['sim']['recordingSites'] = [recording_site_file]
    if path is not None: I.scp.NTParameterSet(neup).save(path)
    return neup

def save_delayeds_in_slurm_folder(delayeds,dir_nr,cores = 1,memory='4000'):
    dir_slurm = mdb['slurm'].join(dir_nr)
    if os.path.exists(dir_slurm): 
        shutil.rmtree(dir_slurm)
    os.mkdir(dir_slurm)
    save_delayeds_in_folder(dir_slurm, delayeds, 10000, cores =cores,memory=memory)
    print('cd '+dir_slurm)
    print('sbatch slurm.sh')

def get_con_syn_hoc_files(mdb,morph,column,pos):
    hoc_file_directory = mdb[morph]['network_embeddings'].join(column+'_grid')
    hocfile = hoc_file_directory.join('pos_{}.hoc'.format(pos))
    con = None; syn = None
    dir_name = None
    for f in os.listdir(hoc_file_directory):
        ne = hoc_file_directory.join(f)
        if f.startswith('pos_{}'.format(pos)+'_synapses'):
            if os.path.isdir(ne):
                dir_name = ne
                for f2 in os.listdir(ne):
                    if f2.endswith('.con'):   con = ne.join(f2)
                    elif f2.endswith('.syn'): syn = ne.join(f2)
    assert con is not None
    assert syn is not None
    return con,syn,hocfile,dir_name
    
def change_synapse_weights(param, g_optimal, pop=I.barrel_cortex.excitatory):
    for key in list(param['network'].keys()):
        celltype = key.split('_')[0]
        if celltype in pop:  # I.excitatory:
            index = [x for x in g_optimal.keys() if x in celltype]
            assert len(index) == 1
            g = g_optimal[index[0]]
            param['network'][key]['synapses']['receptors']['glutamate_syn']['weight'] = [g, g]
    
def change_ongoing_interval(n, factor = 1, pop = I.inhibitory):
    for c in n.network.keys():
        celltype, location = c.split('_')
        if not celltype in pop:
            continue
        x = n.network[c]
        if isinstance(x.celltype, str):
            assert(x.celltype == 'spiketrain')
            x.interval = x.interval * factor
        else:
            x.celltype.spiketrain.interval = x.celltype.spiketrain.interval * factor
            
def change_evoked_INH_scaling(param, factor):
    for key in param.network.keys():
        if key.split('_')[0] in I.barrel_cortex.inhibitory:
            if param.network[key].celltype == 'spiketrain':
                continue
            prob = param.network[key].celltype.pointcell.probabilities
            prob = list(map(lambda x: x * factor, prob))
            param.network[key].celltype.pointcell.probabilities = prob
            
def plot_input_populations_PSTHs(netp,legend=False):
    def intervals_to_bins(intervals,probabilities):
        bins = []
        new_probs = []
        for i in range(1,len(intervals)):
            bins.append(intervals[i-1][1])
            new_probs.append(probabilities[i-1])
            if intervals[i][0] != intervals[i-1][1]:
                bins.append(intervals[i][0])
                new_probs.append(0)
        assert len(bins) == len(new_probs)
        c = -1
        for b,np in zip(bins,new_probs):
            if np != 0:
                c += 1
                assert intervals[c][1] == b and probabilities[c] == np
        return bins,new_probs
    
    plt.figure(figsize=(7,5))
    for pop in netp['network'].keys():
        #if pop.split('_')[0] in I.inhibitory:
            if isinstance(netp['network'][pop]['celltype'], dict):
                assert 'pointcell' in netp['network'][pop]['celltype'].keys()
                pointcell = netp['network'][pop]['celltype']['pointcell']
                assert pointcell['distribution'] == 'PSTH'
                intervals = pointcell['intervals']
                probabilities = pointcell['probabilities']
                bins,new_probs = intervals_to_bins(intervals,probabilities)
                plt.step(bins,new_probs,label=pop)
    if legend:
        leg = plt.legend(bbox_to_anchor=(1.04, 1),ncol=4); leg.get_frame().set_linewidth(0.0)
    plt.xlabel('Time (ms)',size=14); plt.ylabel('Probability',size=14)
    plt.title('Input populations PSTHs',size=16); plt.show()

def get_rate_from_spike_times_single_trial(st,discard=145,duration=3200):
    st = st[st>discard]
    st = np.array(st)
    st = st[~np.isnan(st)]
    time = (duration-discard)/1000
    if len(st)==0: rate = 0
    elif len(st)<5 and len(st)>0: rate = len(st)/time
    else:
        isi = np.diff(st)/1000
        rate = 1/np.mean(isi)
    if np.isnan(rate): rate=0
    return rate

@dask.delayed
def plot_ongoing_vt(sub_mdb,column,model_nr,name,n_trials_per_inh=1,fitted_inh_only = True):
    vt = sub_mdb['voltage_traces']
    #vt = vt.set_index(vt.index, sorted=True)
    st = sub_mdb['spike_times']
    index = st.index
    idxs2 = [i for i in index if 'model_'+str(model_nr) in i]
    n_rows = 40; n_cols = 2
    idxs4 = []
    for pos in range(1,n_rows*n_cols+1):
        idxs5 = [i for i in idxs2 if 'pos_{}/'.format(pos) in i]
        INH_scaling_list = []
        for i in range(len(idxs5)):
            INH_scaling = float(idxs5[i].split('/')[2].split('_')[1])
            
            if fitted_inh_only:
                if INH_scaling in [float(i) for i in INHongoing[column][model_nr][pos]]:
                    if INH_scaling_list.count(INH_scaling)< n_trials_per_inh : # Show only one trial per INH scaling that gives a good fit
                        INH_scaling_list.append(INH_scaling)
                        idxs4.append(idxs5[i])
            else:
                if len(INHongoing[column][model_nr][pos])>0:
                    max_inh = max([float(i) for i in INHongoing[column][model_nr][pos]])
                else:
                    max_inh = 2
                if INH_scaling <= max_inh:
                    if INH_scaling_list.count(INH_scaling)< n_trials_per_inh : # Show only one trial per INH scaling that gives a good fit
                        INH_scaling_list.append(INH_scaling)
                        idxs4.append(idxs5[i])
                        
    vts = vt.loc[idxs4].compute()
    idx_matrix = np.arange(1,n_rows*n_cols+1).reshape((n_rows,n_cols))
    fig, axs = plt.subplots(n_rows,n_cols,figsize=(25,4*n_rows))
    fig.suptitle('column '+column+ ', model '+str(model_nr))
    for pos in range(1,n_rows*n_cols+1):
        x,y = np.where(idx_matrix == pos)
        idxs5 = [i for i in idxs4 if 'pos_{}/'.format(pos) in i]
        for i in range(len(idxs5)):
            axs[x[0],y[0]].plot(40*i + vts.loc[idxs5[i]],linewidth=0.7,c='black')
        axs[x[0],y[0]].set_title('cell '+str(pos))
        axs[x[0],y[0]].set_xlabel('time (ms)')
        axs[x[0],y[0]].set_yticks([])
    plt.tight_layout(); plt.savefig(name); plt.close()#plt.show()
    
def plot_response_trials(sub_mdb,whisker,index):
    sub_sub_mdb = sub_mdb[whisker+'_whisker_stimuli']
    vt = sub_sub_mdb['voltage_traces']
    if index == None:
        st = sub_sub_mdb['spike_times']
        index = st.index

    vts = vt.loc[index].compute()
    vts.columns = vts.columns - 245
    plt.figure(figsize=(25,int(len(index)/10)))
    plt.title('column '+column+ ', model '+str(model_nr)+', '+ whisker+' stimuli')
    for i in range(len(index)):
        plt.plot(20*i + vts.loc[index[i]],linewidth=0.7,c='black')
    plt.xlabel('time (ms)')
    plt.xlim(-50,100)
    plt.show()

def plot_sim_trials_not_delayed(sub_mdb, column, model_nr, whisker,index=[],n_rows = 20, n_cols = 4):
    sub_sub_mdb = sub_mdb[whisker+'_whisker_stimuli']
    vt = sub_sub_mdb['voltage_traces']
    if len(index) == 0:
        st = sub_sub_mdb['spike_times']
        index = st.index
    
    print(len(index))

    
    idx_matrix = np.arange(1,n_rows*n_cols+1).reshape((n_rows,n_cols))
    fig, axs = plt.subplots(n_rows,n_cols,figsize=(25,14*n_rows))
    fig.suptitle('column '+column+ ', model '+str(model_nr)+', '+ whisker+' stimuli')
    
    idxs = []
    for pos in range(1,n_rows*n_cols+1):
        idxs += [i for i in index if i.startswith('pos_'+str(pos))][0:100]
    vts = vt.loc[idxs].compute()
    vts.columns = vts.columns - 245
    
    print(len(idxs))
    
    for pos in range(1,n_rows*n_cols+1):
        x,y = np.where(idx_matrix == pos)
        idxs_ = [i for i in idxs if i.startswith('pos_'+str(pos))]
        vts_ = vts.loc[idxs_]
        if len(idxs_) != 0:
            if len(idxs_)<100: n_trials = len(idxs_)
            else: n_trials = 100
            for i in range(n_trials):
                axs[x[0],y[0]].plot(20*i + vts.loc[idxs_[i]],linewidth=0.7,c='black')
        axs[x[0],y[0]].set_title('cell '+str(pos))
        axs[x[0],y[0]].axvline(x=0,c='black')
        axs[x[0],y[0]].set_xlabel('time (ms)')
        axs[x[0],y[0]].set_xlim(-60,100)
        axs[x[0],y[0]].set_yticks([])
    plt.tight_layout(); #plt.savefig(name); 
    plt.show()

def get_trial_names_with_response_type(st,
                            response_types=['singlet','doublet','triplet','quatriplet','quintuplet'],time_to_remove=245):
    def order_by_nan(df):
        idx = np.isnan(df.values).argsort(axis=1)
        df = pd.DataFrame(df.values[np.arange(df.shape[0])[:, None], idx], index=df.index, columns=df.columns)
        return df
    spike_times =st[st>time_to_remove]
    spike_times = order_by_nan(spike_times)
    spike_times.dropna(how='all',axis=0,inplace=True)
    spike_times.dropna(how='all',axis=1,inplace=True)
    bursts_df = get_st_pattern(spike_times)
    trials_responses = {}
    for r in response_types:
        trials_responses[r] = list(spike_times[bursts_df == r].dropna(how='all').index)
    return trials_responses
    
def has_plateau(vtrace, time_period=30, dt=0.025): 
    def isin(pattern, sequence):
        for i in range(len(sequence) - len(pattern) + 1):
            if sequence[i:i+len(pattern)] == pattern:
                return True
        return False
    high_voltage = vtrace.values > -40
    short_plateau = [1]*int(time_period/dt)
    is_short_plateau = isin(short_plateau, list(high_voltage))
    return is_short_plateau
    
n_spikes_dict={'singlet':1, 'doublet':2, 'triplet':3, 'quatriplet':4, 'quintuplet':5}
def get_st_pattern(st, event_maxtimes={0:0,1:10,2:30,3:35,4:40}, 
                event_names={0:'singlet', 1:'doublet', 2:'triplet',3:'quatriplet',4:'quintuplet'}):
    import spike_analysis.core
    sta2 = spike_analysis.core.SpikeTimesAnalysis(None)
    sta2._db['st'] = st  # sta.get('st_df')
    sta2.apply_extractor(
        spike_analysis.core.STAPlugin_annotate_bursts_in_st(
            event_maxtimes=event_maxtimes,event_names = event_names))
    return sta2.get('bursts_st')
    
@dask.delayed
def filter_data_remove_bursts(mdb_path, mdb_new_path, morph, column, model_nr, whisker):
    mdb_new = I.DataBase(mdb_new_path)
    mdb = I.DataBase(mdb_path)
    if 'sim_mdb_'+column+'_cells_model_{}'.format(model_nr) not in mdb[morph].keys(): return 
            
    sub_mdb = mdb[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]
    sub_mdb_new = mdb_new[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]

    print(morph,column,model_nr,whisker)
    sub_sub_mdb = sub_mdb[whisker+'_whisker_stimuli']
    sub_sub_mdb_new = sub_mdb_new[whisker+'_whisker_stimuli']

    sa = sub_sub_mdb['synapse_activation']
    st = sub_sub_mdb['spike_times']
    trials_info = {'n_trials':len(st.index)}

    trials_responses = get_trial_names_with_response_type(st)

    trials_with_bursts = []
    for r in trials_responses.keys():
        trials_info['n_'+r] = len(trials_responses[r])
        if r!='singlet': 
            trials_with_bursts = trials_with_bursts + trials_responses[r]

    trials = list(st.index)
    for i in trials_with_bursts: 
        if i in trials: trials.remove(i)
    print(trials_info)

    if 'spike_times' not in sub_sub_mdb_new.keys():
        sub_sub_mdb_new.set('spike_times', st.loc[trials], dumper=pandas_to_parquet)
    if 'synapse_activation' not in sub_sub_mdb_new.keys():
        sub_sub_mdb_new.set('synapse_activation', sa.loc[trials], dumper=to_cloudpickle)
    sub_sub_mdb_new['responses_types_info'] = pd.Series(trials_info)
    return trials_info
    
def filter_data_with_stuck_voltage(mdb_path, mdb_new_path, morph, column, model_nr, whisker):
    mdb_new = I.DataBase(mdb_new_path)
    mdb = I.DataBase(mdb_path)
    if 'sim_mdb_'+column+'_cells_model_{}'.format(model_nr) not in mdb[morph].keys(): return 
            
    sub_mdb = mdb[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]
    sub_mdb_new = mdb_new[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]

    print(morph,column,model_nr,whisker)
    sub_sub_mdb = sub_mdb[whisker+'_whisker_stimuli']
    sub_sub_mdb_new = sub_mdb_new[whisker+'_whisker_stimuli']

    sa = sub_sub_mdb['synapse_activation']
    st = sub_sub_mdb['spike_times']
    vt = sub_sub_mdb['voltage_traces']
    stuck_v = vt.apply(has_plateau, axis=1, meta=(None, 'bool')).compute()
    trials = st.index[stuck_v==False]

    if len(st.index)==len(trials):
        print('Voltage did not get stuck')
    else:
        if 'spike_times' not in sub_sub_mdb_new.keys():
            sub_sub_mdb_new.set('spike_times', st.loc[trials], dumper=pandas_to_parquet)
        if 'synapse_activation' not in sub_sub_mdb_new.keys():
            sub_sub_mdb_new.set('synapse_activation', sa.loc[trials], dumper=to_cloudpickle)

            
def filter_data_remove_bursts_and_stuck_voltage(mdb_path, mdb_new_path, morph, column, model_nr, whisker):
    
    from data_base.isf_data_base.IO.LoaderDumper import pandas_to_parquet, to_cloudpickle
    mdb_new = I.DataBase(mdb_new_path)
    mdb = I.DataBase(mdb_path)
    if 'sim_mdb_'+column+'_cells_model_{}'.format(model_nr) not in mdb[morph].keys(): return 
            
    sub_mdb = mdb[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]
    sub_mdb_new = mdb_new[morph]['sim_mdb_'+column+'_cells_model_{}'.format(model_nr)]

    print(morph,column,model_nr,whisker)
    sub_sub_mdb = sub_mdb[whisker+'_whisker_stimuli']
    sub_sub_mdb_new = sub_mdb_new[whisker+'_whisker_stimuli']
    #if 'spike_times' in sub_sub_mdb_new.keys() and 'synapse_activation' in sub_sub_mdb_new.keys(): return
    
    sa = sub_sub_mdb['synapse_activation']
    st = sub_sub_mdb['spike_times']
    vt = sub_sub_mdb['voltage_traces']
    stuck_v = vt.apply(has_plateau, axis=1, meta=(None, 'bool')).compute()
    trials_ok = st.index[stuck_v==False]
    
    stuck_v = stuck_v[stuck_v==True]
    
    #print(len(st.index))
    #if len(st.index)==len(trials_ok):
    #    print('Voltage did not get stuck')
    
    trials_info = {'n_trials':len(st.index)}
    trials_responses = get_trial_names_with_response_type(st)

    trials_with_bursts = []
    for r in trials_responses.keys():
        trials_info['n_'+r] = len(trials_responses[r])
        if r!='singlet': 
            trials_with_bursts = trials_with_bursts + trials_responses[r]

    trials = list(st.index)
    for i in trials_with_bursts: 
        if i in trials: trials.remove(i)
    
    #print(len(trials))
    for i in stuck_v.index:
        if i in trials: trials.remove(i)
    #print(len(trials))
    trials_info['n_trials_stuck_voltage'] = len(stuck_v.index)
    print(trials_info)
    
    #if 'spike_times' not in sub_sub_mdb_new.keys():
    sub_sub_mdb_new.set('spike_times', st.loc[trials], dumper=pandas_to_parquet)
    #if 'synapse_activation' not in sub_sub_mdb_new.keys():
    sub_sub_mdb_new.set('synapse_activation', sa.loc[trials], dumper=to_cloudpickle)
    sub_sub_mdb_new['responses_types_info'] = pd.Series(trials_info)
    return trials_info





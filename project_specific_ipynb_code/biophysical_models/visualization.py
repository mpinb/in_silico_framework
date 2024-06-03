import Interface as I

from single_cell_parser.analyze.synanalysis import compute_distance_to_soma
import biophysics_fitting.utils
from biophysics_fitting.utils import get_inner_sec_dist_dict
from biophysics_fitting.utils import get_inner_section_at_distance
from biophysics_fitting.ephys import spike_count

from matplotlib import gridspec
from matplotlib.gridspec import GridSpec

from typing import List
from copy import deepcopy
# from . import 


#definitions 
offsets = {'bAP.hay_measure':295, 
'BAC.hay_measure':295, 
'StepOne.hay_measure':700, 
'StepTwo.hay_measure':700, 
'StepThree.hay_measure':700, 
'crit_freq1.hay_measure':300, 
'crit_freq2.hay_measure':300, 
'crit_freq3.hay_measure':300, 
'crit_freq4.hay_measure':300, 
'crit_freq5.hay_measure':300, 
'chirp.hay_measure':300, 
'chirp_dend.hay_measure':300, 
'hyperpolarizing.hay_measure':1000, 
'dend_hyperpolarizing.hay_measure':1000}

durations = {'bAP.hay_measure':(-10,60), 
'BAC.hay_measure':(-10,300+60), 
'StepOne.hay_measure':(-250,2250), 
'StepTwo.hay_measure':(-250,2250), 
'StepThree.hay_measure':(-250,2250), 
'crit_freq1.hay_measure':(-10,120), 
'crit_freq2.hay_measure':(-10,90), 
'crit_freq3.hay_measure':(-10,60), 
'crit_freq4.hay_measure':(-10,50), 
'crit_freq5.hay_measure':(-10,50), 
'chirp.hay_measure':(-100,20100), 
'chirp_dend.hay_measure':(-100,20100), 
'hyperpolarizing.hay_measure':(-250,1250), 
'dend_hyperpolarizing.hay_measure':(-250,1250)}

# for apical conductances 
g_combinations_dict = {'K': ['Im', 'SK_E2','SKv3_1'],
                'Ca': ['Ca_HVA','Ca_LVAst'], 
                'Na': ['NaTa_t'], 
                'Ih': ['Ih']}

t_scale = {'bAP': 20, #ms
           'BAC': 50, 
           'crit': 20,
           'Step': 1000, 
           'hyper': 250, 
           'chirp': 2000}

v_scale = {'bAP': 20, #mV
            'BAC': 20, 
            'crit': 20,
            'Step': 20, 
            'hyper': 1,
            'chirp': 1}

definitions = {'offsets': offsets , 'durations': durations,
'g_combinations_dict': g_combinations_dict,
't_scale': t_scale,
'v_scale': v_scale}

#functions for conductance plots
def get_gbar_from_section(sec, g_name):
    gbars = []
    xs = []
    check = 0
    for seg_id, seg in enumerate(sec):
        if hasattr(seg, g_name):
            g_of_seg = getattr(seg, g_name)
            g = getattr(g_of_seg, f'g{g_name}bar')
            gbars.append(g)  
            xs.append(seg.x)
            check = 1
    if check == 0: 
        return None, None 
    relPts = [seg.x for seg in sec]
    return [compute_distance_to_soma(sec, x) for x in relPts], I.np.interp(relPts, xs, gbars)


def return_conductance_list(cell, g_name, soma = False):
    dist_and_gbar_list = []
    if soma: 
        soma_distance, gbars =  get_gbar_from_section(cell.soma, g_name)
        if soma_distance == None: 
            return None
        dist_and_gbar_list.extend(list(zip(soma_distance, gbars)))
    else: 
        for sec in get_inner_sec_dist_dict(cell).values():
            if sec.label == 'ApicalDendrite':
                soma_distance, gbars =  get_gbar_from_section(sec, g_name)
                if soma_distance == None: 
                    return None
                dist_and_gbar_list.extend(list(zip(soma_distance, gbars)))
                
    dist_and_gbar_list.sort()
    soma_dist_list = [x[0] for x in dist_and_gbar_list]
    gbar_list = [x[1] for x in dist_and_gbar_list]
    return soma_dist_list, gbar_list


def combine_conductances(cell,  g_combinations_dict): 
    out = {}
    for key, value in g_combinations_dict.items(): 
        out[key] = {}
        gbar_lists = []
        for item in value: 
            soma_dist_list, gbar_list = return_conductance_list(cell, item)
            gbar_lists.append(I.np.array(gbar_list))
        gbar_list = I.np.sum(gbar_lists, axis = 0)
        out[key]['soma_dist_list'] = soma_dist_list
        out[key]['gbar_list'] = gbar_list
    return out

    

def plot_AUC(evaluation, ax):
    freq_list = list(map(str, evaluation['crit_freq.Freq_list']))
    area_list = [evaluation['crit_freq.Area1'], evaluation['crit_freq.Area2'], evaluation['crit_freq.Area3'],
                 evaluation['crit_freq.Area4'], evaluation['crit_freq.Area5']]  
    ax.scatter(freq_list, area_list,  c = 'k', s=50)
    ax.set_ylabel('AUC (mV ms)', fontsize = 16)
    ax.set_xlabel('Frequency (Hz)', fontsize = 16)

    
    
def plot_res_objectives(evaluation, ax):
    values = [evaluation['chirp.res_freq.raw'], evaluation['chirp.res_freq_dend.raw'], 
             evaluation['chirp.transfer_dend.raw'], evaluation['chirp.synch_freq.raw']]
    names = ['Res.', 'Dend. Res.', 'Trans.' , 'Synch.']
#     names = ['Resonance', 'Dendritic Resonance', 'Transfer' , 'Synchronization']
    ax.scatter(names, values,  c = 'k', s=50)
    ax.set_ylabel('Frequency (Hz)', fontsize = 16)

    
    
def plot_IV(vt, ax): 
    frequency_list = []
    for key,value in vt.items(): 
        if 'Step' in key: 
            t = value['tVec']
            v = value['vList'][0]
            frequency_list.append(spike_count(t,v, thresh = 10)/2)
    amplitude_list = ['0.6', '0.8', '1.5'] # rounded to 1 decimal place 
    ax.plot(amplitude_list, frequency_list,  c = 'k') #, s=50)
    ax.set_ylabel('Frequency (Hz)', fontsize = 16)
    ax.set_xlabel('Amplitude (nA)', fontsize = 16)

    
    
def plot_Rin(evaluation, ax): 
    values = [evaluation['hyperpolarizing.Rin.raw'], evaluation['hyperpolarizing.Dend_Rin.raw']]
    names = ['Soma', 'Dendrite']
    ax.plot(names, values,  c = 'k', marker = '.', markersize = 20, linestyle='dashed')
    ax.set_ylabel(' Resistance (MΩ)', fontsize = 16)
    
    
# ploting functions 
def plot_vt_from_name_specific_ax(voltage_traces, name, ax, colors):
    vt = {k:v for k,v in voltage_traces.items() if (name in k)}
    cumulative_offset = 0
    for k,v in vt.items():
        t = vt[k]['tVec']
        v = vt[k]['vList']
        t = t - offsets[k]
        if durations:
            select = (t >= durations[k][0]) & (t <= durations[k][1])
        else:
            select = t >= -10
        t = t[select]
        v = [vv[select] for vv in v]
        
        if name == 'hyper':
            for vv,c in zip(v,['k', colors[-1]]):
                ax.plot(t + cumulative_offset,vv, color = c)

        elif name == 'chirp':
            v = [v[0], v[-1]]
            v = [vv - vv[0] for vv in v]
            for vv,c in zip(v,['k', colors[-1], colors[1]]):
                ax.plot(t + cumulative_offset,vv, color = c)
                
        else: 
            for vv,c in zip(v,['k', colors[0],colors[1]]):
                ax.plot(t + cumulative_offset,vv, color = c)
                
        cumulative_offset += t.max() - t.min() + 10
        
    #plot the scale bars     
    t_scalebar = [cumulative_offset - t_scale[name] , cumulative_offset]
    t_scalebar = [item + t_scalebar[1]*0.1 for item in t_scalebar]
    v_max = max(list(map(lambda x: max(x), v)))
    v_scalebar = [v_max - v_scale[name], v_max]
#     v_scalebar = [(item + abs(v_scalebar[1])*0.1) for item in v_scalebar] # I would need to use not the maximal v but the response to have this
    ax.plot([t_scalebar[1], t_scalebar[1]], v_scalebar, c = 'k')
    ax.plot(t_scalebar, [v_scalebar[1], v_scalebar[1]], c = 'k')

    
    
#plot morphology
def plot_morphology_specific_ax(m, ax_morph = None, colors = None, offset = None):
    '''needs a list of colors for plotting the markers of injection sites'''
    from project_specific_ipynb_code.hot_zone import get_cell_object_from_hoc
    path = m['fixed_params']['morphology.filename']
    cell = get_cell_object_from_hoc(path) 
    if not ax_morph: 
        I.plt.figure(figsize = (5,15))
        ax_morph = I.plt.gca()
    xs = [x[1]  for sec in cell.sections for x in sec.pts if sec.label in ['Dendrite', 'ApicalDendrite', 'Soma']]
    offset = min(xs)
    for sec in cell.sections:
        if not sec.label in ['Dendrite', 'ApicalDendrite', 'Soma']:
            continue
        xs = [x[1] - offset for x in sec.pts]
        zs = [x[2] for x in sec.pts]
        ax_morph.plot(xs,zs, c = 'k')
    ax_morph.set_aspect('equal')
    if colors:
        pts = []
        soma_distances = [0, 
                          m['fixed_params']['bAP.hay_measure.recSite1'], 
                          m['fixed_params']['bAP.hay_measure.recSite2'], 
                          400]
        for sd in soma_distances:
            sec, secx = I.biophysics_fitting.utils.get_inner_section_at_distance(cell, sd)
            pt_index = I.np.argmin(I.np.abs(secx - I.np.array(sec.relPts)))
            pts.append(sec.pts[pt_index])
        pts = I.np.array(pts)
        #     ax_morph.plot(pts[0,1],pts[0,2], marker = 'o', c = 'k', fillstyle = 'none', markersize = 20)
        ax_morph.plot(pts[1,1],pts[1,2], 'o', c = colors[0], markersize = 10)
        ax_morph.plot(pts[2,1],pts[2,2], 'o', c = colors[1], markersize = 10)
        ax_morph.plot(pts[3,1],pts[3,2], 'o', c = colors[2], markersize = 10)
    
    
   
def plot_conductance_profiles_nested_gs(cell, cond_combinations_dict, gs, fig): 
    gbar_dict = combine_conductances(cell, cond_combinations_dict)
#     fig, axes = I.plt.subplots(4,1)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])
    ax4 = fig.add_subplot(gs[3])
    axes_list = [ax1, ax2, ax3, ax4]
    for key, ax in zip(gbar_dict.keys(), axes_list):
        soma_dist_list = gbar_dict[key]['soma_dist_list']
        gbar_list = gbar_dict[key]['gbar_list']
        ax.fill_between(soma_dist_list, (10**4)*I.np.array(gbar_list), 0,  alpha=0.4, color = 'grey')
        ax.tick_params(labelbottom=False, labelleft=False, bottom = False,left = False)
        for spine in ax.spines.keys():
            ax.spines[spine].set_visible(False)
        ax.set_ylabel(str(key), fontsize = 16)    
    ax.set_xlabel('Distance to soma  (μm)', fontsize = 16)
        
        
        
def format_axes(fig = None, axes: List = None):
    '''need to give either a fig or axes (as list)'''
    if fig: 
        axes = fig.axes
    for ax in axes:
        ax.tick_params(labelbottom=False, labelleft=False)
        for key in ax.spines.keys():
            ax.spines[key].set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        
        
# objective graphs 
def format_objective_graph(ax): 
    ax.spines['bottom'].set_visible(True)
    ax.spines['left'].set_visible(True)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.margins(x=0.1, y =0.1)
    ax.tick_params(labelbottom=True, labelleft=True)
    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.get_xaxis().set_visible(True)
    ax.get_yaxis().set_visible(True)
    
        
        
def visualize_vt_new_figureset(vt, evaluation, m, save_dir = None, file_name = None, offsets = None, 
                               durations = None, colors = ['r' , 'b', 'g'], objective_graphs = True):
    voltage_traces = vt 
    from matplotlib.gridspec import GridSpec
    import project_specific_ipynb_code.hot_zone
#     import project_specific_ipynb_code.biophysical_models
    import biophysics_fitting.utils
    
    fig = I.plt.figure(figsize = (40,20), dpi = 200)
    gs = GridSpec(5, 6, figure=fig, hspace=0.4,wspace=0.2,width_ratios=[2,1,1,1,1,3])
    ax_morph = fig.add_subplot(gs[:-1, 0])
    ax_bAP = fig.add_subplot(gs[0, 1])
    ax_BAC = fig.add_subplot(gs[0, 2:-2])
    ax_CF = fig.add_subplot(gs[1, 1:-2])
    ax_res = fig.add_subplot(gs[2, 1:-2]) 
    ax_step = fig.add_subplot(gs[3, 1:-2])
    ax_hyperpolarizing = fig.add_subplot(gs[-1, 1:-2])
    ax_AUC = fig.add_subplot(gs[1,-2])
    ax_res_obj = fig.add_subplot(gs[2,-2])
    ax_IV = fig.add_subplot(gs[3,-2])
    ax_Rin = fig.add_subplot(gs[4,-2])
    
    ordered_stim_name_list = ['bAP', 'BAC', 'crit', 'Step', 'hyper', 'chirp']
    ax_list = [ax_bAP, ax_BAC, ax_CF,  ax_step, ax_hyperpolarizing, ax_res]
    for name, ax in zip(ordered_stim_name_list, ax_list):
        plot_vt_from_name_specific_ax(voltage_traces, name, ax, colors)
    plot_morphology_specific_ax(m, ax_morph, colors)
    format_axes(fig)
    
    if objective_graphs: 
        axes = [ax_AUC, ax_res_obj, ax_IV, ax_Rin]
        plot_AUC(evaluation, axes[0])
        plot_res_objectives(evaluation, axes[1])
        plot_IV(vt, axes[2])
        plot_Rin(evaluation, axes[3])
        for ax in axes:
            format_objective_graph(ax)
        axes[1].tick_params(labelrotation = 25)    
        
    return fig, gs


params_name_mapping = {
    'ephys.NaTa_t.soma.gNaTa_tbar': 's.Na_t',
    'ephys.Nap_Et2.soma.gNap_Et2bar': 's.Na_p',
    'ephys.K_Pst.soma.gK_Pstbar': 's.K_p',
    'ephys.K_Tst.soma.gK_Tstbar': 's.K_t',
    'ephys.SK_E2.soma.gSK_E2bar': 's.SK',
    'ephys.SKv3_1.soma.gSKv3_1bar': 's.Kv_3.1',
    'ephys.Ca_HVA.soma.gCa_HVAbar': 's.Ca_H',
    'ephys.Ca_LVAst.soma.gCa_LVAstbar': 's.Ca_L',
    'ephys.CaDynamics_E2.soma.gamma': 's.Y',
    'ephys.CaDynamics_E2.soma.decay': 's.T_decay',
    'ephys.none.soma.g_pas': 's.leak',
    'ephys.none.axon.g_pas': 'ax.leak',
    'ephys.none.dend.g_pas': 'b.leak',
    'ephys.none.apic.g_pas': 'a.leak',
    'ephys.NaTa_t.axon.gNaTa_tbar': 'ax.Na_t',
    'ephys.Nap_Et2.axon.gNap_Et2bar': 'ax.Na_p',
    'ephys.K_Pst.axon.gK_Pstbar': 'ax.K_p',
    'ephys.K_Tst.axon.gK_Tstbar': 'ax.K_t',
    'ephys.SK_E2.axon.gSK_E2bar': 'ax.SK',
    'ephys.SKv3_1.axon.gSKv3_1bar': 'ax.Kv_3.1',
    'ephys.Ca_HVA.axon.gCa_HVAbar': 'ax.Ca_H',
    'ephys.Ca_LVAst.axon.gCa_LVAstbar': 'ax.Ca_L',
    'ephys.CaDynamics_E2.axon.gamma': 'ax.Y',
    'ephys.CaDynamics_E2.axon.decay': 'ax.T_decay',
    'ephys.Im.apic.gImbar': 'a.I_m',
    'ephys.NaTa_t.apic.gNaTa_tbar': 'a.Na_t',
    'ephys.SKv3_1.apic.gSKv3_1bar': 'a.Kv_3.1',
    'ephys.Ca_HVA.apic.gCa_HVAbar': 'a.Ca_H',
    'ephys.Ca_LVAst.apic.gCa_LVAstbar': 'a.Ca_L',
    'ephys.SK_E2.apic.gSK_E2bar': 'a.SK',
    'ephys.CaDynamics_E2.apic.gamma': 'a.Y',
    'ephys.CaDynamics_E2.apic.decay': 'a.T_decay',
    'ephys.SKv3_1.apic.offset': 'a.Kv_3.1_offset',
    'ephys.SKv3_1.apic.slope': 'a.Kv_3.1_slope',
    'scale_apical.scale': 'a.scale'
}


ordered_all_params = [ 's.leak',
 'ax.leak',
 'b.leak',
 'a.leak',
 's.Ca_H',
 's.Ca_L',
 's.K_p',
 's.K_t',
 's.Kv_3.1',
 's.Na_p',
 's.Na_t',
 's.SK',
 's.T_decay',
 's.Y',
 'ax.Ca_H',
 'ax.Ca_L',
 'ax.K_p',
 'ax.K_t',
 'ax.Kv_3.1',
 'ax.Na_p',
 'ax.Na_t',
 'ax.SK',
 'ax.T_decay',
 'ax.Y',
 'a.Ca_H',
 'a.Ca_L',
 'a.I_m',
 'a.Kv_3.1',
 'a.Na_t',
 'a.SK',
 'a.T_decay',
 'a.Y',
 'a.Ih_linScale',
 'a.Ih_max',
 'a.Kv_3.1_offset',
 'a.Kv_3.1_slope',
 'a.scale']

## probably just add the new_params_name_mapping would make more sense 
def get_new_params_name_mapping(old_mapping): 
    #Ca v2
    ca_keys_v2_list = [key.split('.') for key in old_mapping.keys() if 'CaDynamics_E2' in key]
    ca_keys = [key for key in old_mapping.keys() if 'CaDynamics_E2' in key]
    for list_ in ca_keys_v2_list: 
        list_[1] = 'CaDynamics_E2_v2'
    ca_keys_v2 = [('.').join(list_) for list_ in ca_keys_v2_list]
    
    new_mapping = deepcopy(old_mapping)
    for old_key, new_key in zip(ca_keys, ca_keys_v2):
        new_mapping[new_key] = new_mapping[old_key]
        del new_mapping[old_key]
        
    #add Ih 
    new_mapping['ephys.Ih.apic.linScale'] = 'a.Ih_linScale'
    new_mapping['ephys.Ih.apic.max_g'] = 'a.Ih_max'
    
    return new_mapping
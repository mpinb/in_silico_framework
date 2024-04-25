import Interface as I

from single_cell_parser.analyze.synanalysis import compute_distance_to_soma
import biophysics_fitting.utils
from biophysics_fitting.utils import get_inner_sec_dist_dict
from biophysics_fitting.utils import get_inner_section_at_distance
from biophysics_fitting.ephys import spike_count

from matplotlib import gridspec
from matplotlib.gridspec import GridSpec
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


# objective graphs 
def format_objective_graph(ax): 
    ax.tick_params(labelbottom=True, labelleft=True)
    ax.spines['bottom'].set_visible(True)
    ax.spines['left'].set_visible(True)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.margins(x=0.1, y =0.1)
    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.get_xaxis().set_visible(True)
    ax.get_yaxis().set_visible(True)

    

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
    ax.set_ylabel(' Resistance (Ω)', fontsize = 16)
    
    
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
def plot_morphology_specific_ax(m, ax_morph, colors):
    from project_specific_ipynb_code.hot_zone import get_cell_object_from_hoc
    path = m['fixed_params']['morphology.filename']
    cell = get_cell_object_from_hoc(path) 
    pts = []
    soma_distances = [0, 
                      m['fixed_params']['bAP.hay_measure.recSite1'], 
                      m['fixed_params']['bAP.hay_measure.recSite2'], 
                      400]
    for sd in soma_distances:
        sec, secx = biophysics_fitting.utils.get_inner_section_at_distance(cell, sd)
        pt_index = I.np.argmin(I.np.abs(secx - I.np.array(sec.relPts)))
        pts.append(sec.pts[pt_index])
    pts = I.np.array(pts)
    I.plt.figure(figsize = (5,15))
    for sec in cell.sections:
        if not sec.label in ['Dendrite', 'ApicalDendrite', 'Soma']:
            continue
        xs = [x[1] for x in sec.pts]
        zs = [x[2] for x in sec.pts]
        ax_morph.plot(xs,zs, c = 'k')
#     ax_morph.plot(pts[0,1],pts[0,2], marker = 'o', c = 'k', fillstyle = 'none', markersize = 20)
    ax_morph.plot(pts[1,1],pts[1,2], 'o', c = colors[0], markersize = 10)
    ax_morph.plot(pts[2,1],pts[2,2], 'o', c = colors[1], markersize = 10)
    ax_morph.plot(pts[3,1],pts[3,2], 'o', c = colors[2], markersize = 10)
    ax_morph.set_aspect('equal')
    
    
    
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
        
        
        
def format_axes(fig):
    for ax in fig.axes:
        ax.tick_params(labelbottom=False, labelleft=False)
        for key in ax.spines.keys():
            ax.spines[key].set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        
        
        
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
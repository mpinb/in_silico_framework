import Interface as I
import numpy as np
from biophysics_fitting.simulator import run_fun
from biophysics_fitting.parameters import set_fixed_params, param_to_kwargs
from biophysics_fitting.setup_stim import setup_soma_step
from biophysics_fitting.utils import tVec, vmSoma, vmApical, vmMax
from biophysics_fitting.hay_complete_default_setup import interpolate_vt
from biophysics_fitting import utils
from functools import partial
from neuron import h 

######################################################
# Simulator which runs the crit. freq. protocols
######################################################

def _append(cell, name, item):
    try:
        getattr(cell, name)
    except AttributeError:
        setattr(cell, name, [])
    getattr(cell, name).append(item)
    
def setup_soma_step_with_current(cell, amplitude = None, delay = None, duration = None, dist = 0):
    if dist == 0: 
        sec = cell.soma
        x = 0.5
    else:
        sec, x = utils.get_inner_section_at_distance(cell, dist)   

    iclamp = h.IClamp(x, sec=sec)
    iclamp.delay = delay # give the cell time to reach steady state
    iclamp.dur = duration # 5ms rectangular pulse
    iclamp.amp = amplitude # 1.9 ?? todo ampere

    iList = h.Vector()
    iList.record(iclamp._ref_i)

    _append(cell, 'iclamp', iclamp)
    _append(cell, 'iList', iList)

def setup_crit_freq_n(cell, delay=None, freq = None, amplitude = None, n_stim = None, duration = None):
    t = 1000/freq 
    #print(delay)
    if isinstance(amplitude, list):
        amplitudes = amplitude
    else:
        amplitudes = [amplitude] * n_stim
    for i in range(n_stim):  
            setup_soma_step_with_current(cell, amplitude = amplitudes[i], delay = delay, duration = duration)
            #print(delay)
            delay += t

def record_crit_freq(cell, recSite1 = None, recSite2 = None):
    assert(recSite1 is not None)
    assert(recSite2 is not None)
    return {'tVec': tVec(cell), 
            'vList': (vmSoma(cell), vmApical(cell, recSite1), vmApical(cell, recSite2)),
            'iList': np.array(cell.iList)}

def modify_simulator_to_run_crit_freq_stimuli(s, delay = None, tStop = None, n_stim = None, freq_list = None, amplitude = None, duration = None):
    """typical defaults: delay = 300, tStop = 700, n_stim = 4, freq_list = [35, 50, 100, 150, 200], amplitude = 4, duration = 2"""
    run_fun_crit_freq_n = partial(run_fun, T = 34.0, Vinit = -75.0, dt = 0.025, 
                                 recordingSites = [], tStart = 0.0, tStop = tStop, vardt = True)
    for i in range(1, len(freq_list)+1, 1): 
        s.setup.stim_run_funs.append([f'crit_freq{i}.run', param_to_kwargs(run_fun_crit_freq_n)])
    
    for i, freq in enumerate(freq_list, 1): 
        s.setup.stim_setup_funs.append([f'crit_freq{i}.stim', param_to_kwargs(I.partial(setup_crit_freq_n, 
                                                                                        freq = freq, 
                                                                                        amplitude = amplitude,
                                                                                        n_stim = n_stim,
                                                                                        duration = duration,
                                                                                        delay = delay))])
        
    for i in range(1, len(freq_list)+1, 1): 
        s.setup.stim_response_measure_funs.append([f'crit_freq{i}.hay_measure', param_to_kwargs(record_crit_freq)])

######################################################
# Evaluator which can evaluate the crit. freq. protocols
######################################################

# todo Su: if function is not new, can you import it instead?

def get_stim_times(delay, freq_list, n_stim): 
    stim_times = {}
    for freq in freq_list: 
        stim_time = delay
        stim_time_list = []
        t = 1000/freq
        for i in range(n_stim): 
            stim_time_list.append(stim_time)
            stim_time += t
        stim_times[str(freq)] = stim_time_list
        
    return stim_times

def find_nearest_time(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]

def get_rounded_stim_times(delay, freq_list, n_stim):
    stim_times = get_stim_times(delay, freq_list, n_stim)
    possible_time_points = [0, 0.025, 0.05, 0.075, 0.1]
    
    new_stim_times = {}
    for freq in freq_list:
        new_stim_times[str(freq)] = []
        for stim_time in stim_times[str(freq)]: 
            if stim_time %1 != 0:
                d = stim_time %1 %0.1
                dd = find_nearest_time(possible_time_points, d)
                stim_time =  I.np.around(stim_time - d + dd, 3)
                
            new_stim_times[str(freq)].append(stim_time)
    return new_stim_times

def find_crossing(v, thresh):
    '''Original NEURON doc:
    Function that giving a threshold returns a list of two vectors
    The first is the crossing up of that threshold
    The second is the crossing down of that threshold
    
    Extended doku by Arco: returns [[],[]] if the number of crossing up vs crossing down is not equal.'''
    assert(thresh is not None)
    avec = []
    bvec = [] 
    ef = 0
    # added by arco to resolve failure of spike detection if value is exactly the threshold
    v = I.np.array(v) > thresh
    thresh = 0.5
    # end added by arco
    for i, vv in enumerate(v):
        if i == 0: 
            continue
        if (vv > thresh) and (v[i-1] < thresh):
            avec.append(i)
            ef = 1
        else:
            if (vv < thresh) and (v[i-1] > thresh):
                if ef: # added by arco: we just want to detect crossing down if we detected crossing up before, might otherwise be initialization artifact
                    bvec.append(i)
    if (len(avec) != len(bvec)) and ef == 1:
        return [avec,bvec]
        #return [[],[]]
    return [avec, bvec]

def spike_count(t,v, thresh = None):
    return len(find_crossing(v, thresh)[0])

def get_spike_n_per_interval(voltage_traces, soma_threshold, delay, freq_list, n_stim, a): #v and t need to be interpolated 
    stim_times = get_rounded_stim_times(delay, freq_list, n_stim)
    
    interval_spike_counts = {} 
    for i, key in enumerate(stim_times.keys()):
        if not i + 1 == a: # skip all but the stimulus protocol contained in voltage_traces
            continue
        # add a 'false stim time' to detect the AP after the last stim
        period = I.np.around(stim_times[key][1] - stim_times[key][0], 3)
        stim_times[key].append(stim_times[key][-1]+ period)
        
#         interval_spike_counts[key] = {}
        interval_spike_counts[key] = []
        
        #v = interpolate_vt(voltage_traces)[f'crit_freq{i+1}.hay_measure']['vList'][0]
        #t = interpolate_vt(voltage_traces)[f'crit_freq{i+1}.hay_measure']['tVec']
        v = voltage_traces['vList'][0]
        t = voltage_traces['tVec']        
        t = I.np.around(t, 3)
        
        for i in range(len(stim_times[key])-1):
            interval_start = stim_times[key][i]
            interval_end = stim_times[key][i+1]
            
            interval_start = np.where(t == interval_start)[0][0] #-1
            interval_end = np.where(t == interval_end)[0][0] #+1
            
            v_int = v[interval_start: interval_end]
            t_int = t[interval_start: interval_end]
            n = spike_count(t_int,v_int,thresh=soma_threshold)

#             interval_spike_counts[key][f'interval{i}'] = n 
            interval_spike_counts[key].append(n) 
    assert(len(interval_spike_counts) == 1)
    key = list(interval_spike_counts.keys())[0]
    return interval_spike_counts[key]  

# todo Su (low priority): we have several interpolate_vt functions. Can we make one general one?
# def interpolate_vt(voltage_trace_):
#     out = {}
#     for k in voltage_trace_:
#         t = voltage_trace_[k]['tVec']
#         t_new = np.arange(0, max(t), 0.025)
#         vList_new = [np.interp(t_new, t, v) for v in voltage_trace_[k]['vList']] # I.np.interp
#         out[k] = {'tVec': t_new, 'vList': vList_new}
#         if 'iList' in voltage_trace_[k]:
#             iList_new = [np.interp(t_new, t, i) for i in voltage_trace_[k]['iList']]
#             out[k] = {'tVec': t_new, 'vList': vList_new, 'iList': iList_new, str(k): k}  
#     return out

class Crit_freq: 
    def __init__(self, 
                 delay = None,
                 freq_list = None,
                 n_stim = None,
                 # definitions ={'Area':('Area',0,0),
                 #                'Freq_list':('Freq_list',0,0), 
                 #                'NumSpike':('NumSpike',0,0)},
                 soma_threshold = 0):
        assert(n_stim is not None)
        self.delay = delay
        # self.definitions = definitions
        self.n_stim = n_stim
        self.freq_list = freq_list
        self.soma_threshold = soma_threshold
        
    def get(self, **voltage_traces): 
        out = {}
        for name in ['Area', 'Freq_list', 'NumSpike']:
            out.update(getattr(self, name)(voltage_traces))
        return out   
    
    def NumSpike(self, voltage_traces):
        a = ([k for k,v in voltage_traces.items() if 'crit_freq' in k][0].split('.'))[0][-1]
        a = int(a)
        return {f'crit_freq.n_spikes{a}': get_spike_n_per_interval(voltage_traces, self.soma_threshold, self.delay, self.freq_list, self.n_stim, a)}
        
    def Area(self, voltage_traces, returning_to_rest = 2): 
        a = ([k for k,v in voltage_traces.items() if 'crit_freq' in k][0].split('.'))[0][-1]
        freq = self.freq_list[int(a)-1]
        
        t = voltage_traces['tVec']
        v = voltage_traces['vList']

        b = np.where(t == (self.delay))[0][0]
        c = np.where(t == (self.delay+-10))[0][0]
        d = np.where(t == int(self.delay+((1000/freq)*4)))[0][0]

        baseline = np.average(v[2][c:b])
        v = v - baseline
        v[v<0] = 0
        end = [(n, x) for n,x in enumerate(v[2]) if abs(x)<returning_to_rest and n>d]
        if len(end)>0: 
            end = end[0][0]
            area = (I.np.trapz(v[2][b:end]))/1000
        else: 
            area = float('nan')# 0 
                
        return {f'crit_freq.Area{a}': area}
    
    def Freq_list(self, voltage_traces): 
        return {'crit_freq.Freq_list': self.freq_list}
    
# Todo: make sure nan works as expected 
    
def find_Crit_freq(evaluation, freq_list = None):
    '''finalize function which gets called with the evaluation dict'''
    ### in case crit. frequency stimuli have not been simulated, do not cause an error
    for stim in range(1, len(freq_list)+1):
        key = f'crit_freq.n_spikes{stim}'
        if not key in evaluation:
            return evaluation
    ### end of 'in case no crit. frequency stimuli have been simulated, do not cause an error'

    if evaluation['crit_freq.num_spikes_error'] > 0: # stimuli didn't work, cannot determine crit. frequency
        evaluation['crit_freq.Crit_freq'] = float('nan')
    
    else: # stimuli did work and we can compute the crit freq
        area_list = [v for k,v in evaluation.items() if 'Area' in k]
        freq_list =  evaluation['crit_freq.Freq_list']
        area_ratio = dict([(freq,area_plus/area) for area, area_plus, freq in zip(area_list, (area_list[1:]), freq_list[1:])])
        if max(area_ratio.values())> 1.5: 
            evaluation['crit_freq.Crit_freq'] = max(area_ratio, key = area_ratio.get)
        else:
            evaluation['crit_freq.Crit_freq'] = float('nan')
    
    evaluation['crit_freq.frequency_error'] = crit_freq_error(evaluation['crit_freq.Crit_freq'])
    
    return evaluation #{'crit_freq.' + k:v for k,v in dict_.items()}

def crit_freq_error(value):
    '''compute error from crit freq to match the empirical range (Larkum 1999, Kole 2007, Kole 2006, Berger )'''
    if I.np.isnan(value):
        return 10 # 10 would be the error of one stimulus not evoking 1 AP
    allowed_min = 60 # min of distribution
    allowed_max = 200 # max of distribution
    bulk_min = 70 # lower bound on bulk of distribution
    bulk_max = 110 # upper bound on bulk of distribution
    target_error_representing_cutoff = 3.2 # cutoff for other bAP and BAC objectives
    
    if bulk_min <= value <= bulk_max:
        return 0
    if allowed_min <= value <= allowed_max:
        return 1    
    
    width = (allowed_max - allowed_min) / 2
    center = (allowed_max + allowed_min) / 2
    out = I.np.abs(value - center) / (width / target_error_representing_cutoff)    
    return out

def check_AllStimuliWork(evaluation, freq_list = None):
    ### in case crit. frequency stimuli have not been simulated, do not cause an error
    for stim in range(1, len(freq_list)+1):
        key = f'crit_freq.n_spikes{stim}'
        if not key in evaluation:
            return evaluation
    ### end of 'in case no crit. frequency stimuli have been simulated, do not cause an error'
    
    out = []
    for stim in range(1, len(freq_list)+1):
        key = f'crit_freq.n_spikes{stim}'
        # print(key, evaluation[key])
        out.extend(evaluation[key])
    out = I.np.array(out)
    error = out-1 # correct number of spikes are represented as 0, to little -1, too much +1
    error = 10*error**2 # correct number of spikes are represented as 0, not correct is 10
    error = sum(error)
    evaluation['crit_freq.num_spikes_error'] = error

    return evaluation

def put_name_of_stimulus_in_crit_freq_voltage_traces_dict(vt):
    for k,v in vt.items():
        if 'crit_freq' in k:
            v[k] = k
    return vt

def modify_evaluator_to_evaluate_crit_freq_stimuli(e, freq_list = None, delay = None, n_stim = None, soma_threshold = -20):
    for i in range(1, len(freq_list)+1, 1):
        cf = Crit_freq(freq_list = freq_list,
                       delay = delay, n_stim = n_stim, soma_threshold = soma_threshold)
        e.setup.evaluate_funs.append([f'crit_freq{i}.hay_measure',cf.get,f'crit_freq{i}.features'])
    e.setup.pre_funs.append(put_name_of_stimulus_in_crit_freq_voltage_traces_dict)
    e.setup.finalize_funs.append(I.partial(check_AllStimuliWork, freq_list = freq_list))
    e.setup.finalize_funs.append(I.partial(find_Crit_freq, freq_list = freq_list))    


    

    
######################################################
# Combiner which can evaluate the crit. freq. protocols
######################################################

def modify_combiner_to_add_crit_freq_error(c, freq_list = None):
    c.setup.append('crit_freq.error', ['crit_freq.num_spikes_error', 'crit_freq.frequency_error'])
    
######################################################
# visualize critical frequency 
######################################################

def visualize_crit_freq(voltage_traces, delay = None, tStop = None, n_stim = None, freq_list = None, present_mode = False):
    """typical defaults: delay = 300, tStop = 700, n_stim = 4, freq_list = [35, 50, 100, 150, 200]"""
    
    t1 = voltage_traces['crit_freq1.hay_measure']['tVec']
    v1 = voltage_traces['crit_freq1.hay_measure']['vList'] 

    t2 = voltage_traces['crit_freq2.hay_measure']['tVec']
    v2 = voltage_traces['crit_freq2.hay_measure']['vList']

    t3 = voltage_traces['crit_freq3.hay_measure']['tVec']
    v3 = voltage_traces['crit_freq3.hay_measure']['vList']

    t4 = voltage_traces['crit_freq4.hay_measure']['tVec']
    v4 = voltage_traces['crit_freq4.hay_measure']['vList']

    t5 = voltage_traces['crit_freq5.hay_measure']['tVec']
    v5 = voltage_traces['crit_freq5.hay_measure']['vList']

    t_list = [t1, t2, t3, t4, t5]
    v_list = [v1, v2, v3, v4, v5]
    v_name = ['v1', 'v2', 'v3', 'v4', 'v5']

    if not present_mode:
        stim = {}

        for i,f in zip(range(1,6),freq_list):
            stim[f'v{i}'] = [delay + (1000/f)*i for i in range(4)]

        fig, axes = I.plt.subplots(2, 3, figsize=(20, 10))
        fig.tight_layout(pad=2.0)

        row=[0]*3+[1]*3
        clm=[0,1,2]*2

        #     fig.savefig(f'vtplots{name}.png')
        #     fig.savefig(f'vtplots14_new.svg')

        for a,b,c,i,y,freq in zip(t_list,v_list,range(1,6),row, clm, freq_list): 
            axes[i,y].plot(a, b[0], color='b')
            axes[i,y].plot(a, b[2], alpha=0.7)
            axes[i,y].set_title(str(freq)+'Hz')
            for d in stim[f'v{c}']:
                 axes[i,y].axvline(x=d, color='r', ls = '--', alpha=0.4)

        area_list = []
        for i,f in zip(range(1,6),freq_list):

            t = interpolate_vt(voltage_traces)[f'crit_freq{i}.hay_measure']['tVec']
            v = interpolate_vt(voltage_traces)[f'crit_freq{i}.hay_measure']['vList']

            b = np.where(t == (delay))[0][0]
            c = np.where(t == (delay+-10))[0][0]
            d = np.where(t == int(delay+((1000/f)*4)))[0][0]

            baseline = np.average(v[2][c:b])
            v = v - baseline

            end = [(n, x) for n,x in enumerate(v[2]) if abs(x)<0.2 and n>d]
            if len(end)>0: 
                end = end[0][0]
                area_list.append((I.np.trapz(v[2][b:end]))/1000)
            else: 
                area_list.append(0)
        #     I.plt.plot(t[b:end], v[2][b:end])

        #     print(end)
        #     I.plt.plot(t,v[2])

        area_name = [str(freq)+ 'Hz' for freq in freq_list]
        axes[1,2].scatter(area_name, area_list)

    else: 
        
    # getting the currents 
        currents = {}

        for i in range(1,6): 
            currents[f'i{i}'] = voltage_traces[f'crit_freq{i}.hay_measure']['iList'][0].copy()
            for y in range(1,4):
                currents[f'i{i}'] += voltage_traces[f'crit_freq{i}.hay_measure']['iList'][y].copy()

        # just traces  
        fig, axes = I.plt.subplots(2, 5, figsize=(25, 6), sharex=True, sharey='row', gridspec_kw={'height_ratios': [4, 1]})

        for t, v, i, ax_y, freq in zip(t_list, v_list, currents.keys(), range(6), freq_list):
            axes[0,ax_y].plot(t, v[0], color = 'k')
            axes[0,ax_y].plot(t, v[2], color = 'r')
            for key in axes[0,ax_y].spines.keys():
                axes[0,ax_y].spines[key].set_visible(False)
            axes[0, ax_y].set_xlim(xmin=250, xmax=450)

            axes[0,ax_y].get_xaxis().set_visible(False)
            axes[0,ax_y].get_yaxis().set_visible(False)

            axes[1,ax_y].plot(t, currents[i], color = 'k')
            axes[1,ax_y].set_ylim(top=3.1)
            for key in axes[1,ax_y].spines.keys():
                axes[1,ax_y].spines[key].set_visible(False)

            axes[1,ax_y].get_xaxis().set_visible(False)
            axes[1,ax_y].get_yaxis().set_visible(False)

            axes[0, ax_y].set_title(str(freq)+'Hz')
            axes[0, ax_y].title.set_fontsize('xx-large')

        I.plt.show()
        
        
######################################################
# for iterating through different current amplitudes 
######################################################

#to do: Clean this up 

def check_spikes(interval_spike_counts): 
    spike_check = []
    # three options (per frequency: increase (1), decrease(-1) or just right(0)) 
    for spike_count in interval_spike_counts: 
        if any(item>1 for item in spike_count):
            spike_check.append(-1)
        elif 0 in spike_count:
            spike_check.append(1)
        elif all(item == 1 for item in spike_count):
            spike_check.append(0)
    return spike_check

def iterate_over_current_until_one_spike_per_interval(clean_mdb = None, p = None, current_range = None, start_current = None,
                                                     soma_threshold = None, delay = None, freq_list = None, n_stim = None):
    '''Takes a minimal simulator (from a mdb with only bAP, BAC and crit_freq stimuli with specified morhoplogy clean_mdb = mdb[morphology]), 
    adds the crit_freq to the s, tries different current amplitudes until there is one spike per interval for all frequencies
    make sure the start_current is within the current_range'''
    
    output = {}
    amplitude = start_current 
    s = clean_mdb['get_Simulator'](clean_mdb)
    modify_simulator_to_run_crit_freq_stimuli(s, delay = delay, tStop = 700, n_stim = n_stim, freq_list = freq_list, amplitude = amplitude, duration = 2)
    voltage_traces = interpolate_vt(s.run(p))
    interval_spike_counts = []
    a = 0 
    for k,v in voltage_traces.items(): 
        if 'crit_freq' in k: 
            a += 1 
            interval_spike_counts.append(get_spike_n_per_interval(v, soma_threshold, delay, freq_list, n_stim, a))
    spike_check = check_spikes(interval_spike_counts)
    
    step_size = current_range[1] - current_range[0]
    
    amplitude_found = False 
    done = False 
    while done == False and amplitude in current_range: 
        if all(check == -1 for check in spike_check) or set(spike_check) == {0,-1}:
            amplitude += -step_size
        if all(check == 1 for check in spike_check) or set(spike_check) == {0,1}:
            amplitude += step_size        
        if all(check == 0 for check in spike_check):
            amplitude_found = True 
            done = True
        if len(set(spike_check)) == 3: 
            done = True 
        amplitude = I.np.around(amplitude, 3)
        
        s = clean_mdb['get_Simulator'](clean_mdb)
        modify_simulator_to_run_crit_freq_stimuli(s, delay = delay, tStop = 700, n_stim = n_stim, freq_list = freq_list, amplitude = amplitude, duration = 2)
        voltage_traces = interpolate_vt(s.run(p))
        interval_spike_counts = []
        a = 0
        for k,v in voltage_traces.items(): 
            if 'crit_freq' in k: 
                a += 1 
                interval_spike_counts.append(get_spike_n_per_interval(v, soma_threshold, delay, freq_list, n_stim, a))
        spike_check = check_spikes(interval_spike_counts)
        
#     output['spike_check'] = spike_check
#     output['amplitude_found'] = amplitude_found
#     output['amplitude'] = amplitude
#     output['voltage_traces'] = voltage_traces
        
#     return output
    return amplitude

    
'''The content of this module is mostly a reimplementation of the Hay et.al. 2011 methods used for extracting features'''
import Interface as I

def trace_check(t,v,
                stim_onset=None, 
                stim_duration=None,
                minspikenum=None,
                soma_threshold=None,
                returning_to_rest=2,
                max_prestim_dendrite_depo=-50, vmax = None, ## added by arco
                name = ''):
    n = spike_count(t,v,thresh=soma_threshold)
    out = {}
    # check that at least minspikenum are present
    out[name+'.check_minspikenum'] = n >= minspikenum
    # print(minspikenum)
    # check that voltage base (mean potential from 0.5 to 0.75 * stim_delay) is maxmimum 
    # returning_to_rest deeper than last reported voltage
    b = voltage_base(t,v,stim_onset)
    out[name+'.check_returning_to_rest'] = v[-1] < b + returning_to_rest
    # check that there are no spikes before stimulus onset
    crossing_up, crossing_down = find_crossing(v,soma_threshold)
    try:
        t_first_spike = t[crossing_up[0]]
        t_last_spike = t[crossing_up[-1]]

    except IndexError:
        out[name+'.check_no_spike_before_stimulus'] = True
        out[name+'.check_last_spike_before_deadline'] = True 
    else:
        out[name+'.check_no_spike_before_stimulus'] = t_first_spike >= stim_onset
        deadline = stim_duration*1.05 +stim_onset
        out[name+'.check_last_spike_before_deadline'] = deadline >= t_last_spike
    if vmax is None:
        out[name+'.check_max_prestim_dendrite_depo'] = float('nan')
    else:
        out[name+'.check_max_prestim_dendrite_depo'] = trace_check_max_prestim_dendrite_depo(t,vmax,stim_onset, max_prestim_dendrite_depo)
    return out

def trace_check_max_prestim_dendrite_depo(t,vmax,stim_onset,max_prestim_dendrite_depo = None):
    '''added by arco to check whether anywhere in the dendrite there is a spike before stimulus onset'''
    select = t<stim_onset
    return max(vmax[select]) <= max_prestim_dendrite_depo

def trace_check_err(t,v,stim_onset=None, stim_duration=None, punish = 250):
    select = (t>=stim_onset-100) & (t<=stim_onset+stim_duration/2.)
    v=v[select]
    t=t[select]
    var_fact = 1e-1
    # print('trace variance is ', I.np.var(v), I.np.var(v)*var_fact, stim_onset, stim_duration)
    return max(75,punish - I.np.var(v)*var_fact)

def find_crossing_old(v, thresh):
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

def find_crossing(v,thresh):
    '''Original NEURON doc:
    Function that giving a threshold returns a list of two vectors
    The first is the crossing up of that threshold
    The second is the crossing down of that threshold
    
    Extended doku by Arco: returns [[],[]] if the number of crossing up vs crossing down is not equal.
    This is the vectorized fast version of find_crossing_old. 
    '''    
    v = I.np.array(v) > thresh
    thresh = 0.5    
    upcross = I.np.where((v[:-1]<thresh) & (v[1:]>thresh))[0] + 1
    downcross = I.np.where((v[:-1]>thresh) & (v[1:]<thresh))[0] + 1
    if len(upcross) == 0:
        return [[],[]]
    downcross = downcross[downcross > upcross[0]]
    #if len(upcross) != len(downcross):
    #    return [[],[]]
    return [list(upcross), list(downcross)]

def voltage_base(t, v, stim_delay):
    try:
        ta = I.np.nonzero(t>=0.5*stim_delay)[0][0] # list(t >= 0.5*stim_delay).index(True)
        ts = I.np.nonzero(t>=0.75*stim_delay)[0][0] # list(t >= 0.75*stim_delay).index(True)
    except IndexError:
        return v[0]
    else:
        return v[ta:ts+1].mean()
    
def voltage_base2(voltage_traces, recSiteID, t0):
    t = voltage_traces['baseline']['tVec']
    v = voltage_traces['baseline']['vList']['recSiteID']
    i = I.np.argmin(I.np.abs(t-t0))
    return v[i]

def spike_count(t,v, thresh = None):
    return len(find_crossing(v, thresh)[0])

# AP_height is the mean amplitude of all detected spikes. Amplitude is max depolarization 
# occuring during a spike. If there is no spike, returns 20 times standard deviation
def AP_height_check_1AP(t,v, thresh=None):
    return len(find_crossing(v,thresh)) >= 1

def AP_height(t, v, thresh=None):
    out = [max(v[ti:tj]) for ti,tj in zip(*find_crossing(v, thresh))]
    return I.np.array(out)

def AP_width(t,v,thresh):
    w = [t[tk] - t[ti] for ti, tk in zip(*find_crossing(v, thresh))]
    return I.np.array(w)

AP_width_check_1AP = AP_height_check_1AP

def AP_width(t,v,thresh):
    w = [t[tk] - t[ti] for ti, tk in zip(*find_crossing(v, thresh))]
    return I.np.array(w)

AP_width_check_1AP = AP_height_check_1AP

# Original: Computes the minimum membrane potential in between consecutive spikes 
# and returns the mean of these values. Returns 20*std if less than 2 spikes.
def AHP_depth_abs_check_2AP(t,v,thresh=None):
    return spike_count(t,v,thresh=thresh) >= 2

def AHP_depth_abs(t,v,thresh=None):
    apIndexList = I.np.array(find_crossing(v,thresh))
    apIndexList = [(apIndexList[1,lv],apIndexList[0,lv+1]) for lv in range(apIndexList.shape[1]-1)] # the gaps
    return I.np.array([min(v[ti:tj]) for ti,tj in apIndexList])

# Original: Returns 20std if no spike has been detected. Returns 20std if there are less than two 
# somatic APs. Returns 20*std if peak of Ca spike preceedes second somatic spike. 
def BAC_caSpike_height_check_1_Ca_AP(t,v,v_dend,thresh=None):
    #print(spike_count(t,v_dend,thresh))
    return spike_count(t,v_dend,thresh) == 1

def BAC_caSpike_height_check_gt2_Na_spikes(t,v,v_dend,thresh=None):
    #print(spike_count(t,v,thresh))
    return spike_count(t,v,thresh) >= 2

def BAC_caSpike_height_check_Ca_spikes_after_Na_spike(t,v,v_dend, n = 2,thresh=None):
    t_max_Ca = t[v_dend==max(v_dend)][0]
    t_nth_spike = t[find_crossing(v,thresh)[0][n-1]]
    #print(t_max_Ca, t_nth_spike)
    return t_max_Ca >= t_nth_spike

def BAC_caSpike_height(t,v,v_dend,ca_thresh=-55,tstim=295):
    '''returns heights of Ca spikes after tstim'''
    hs = AP_height(t,v_dend,ca_thresh)
    i = next((lv for lv, i in enumerate(find_crossing(v_dend, ca_thresh)[0]) if t[i] >= tstim))
    return hs[i]

# Original: Returns 20 * std if no ca spike has been found. Computes width of Ca spike at caSpikethresh = -55mV
# Returs abs. deviation in ms from the mean experiental width. 
# In case of 2 spikes, 7 is substracted from the mean experimental width
# In case, more than one Ca spike is present, the mean width is returned
BAC_caSpike_width_check_1_Ca_AP = BAC_caSpike_height_check_1_Ca_AP
def BAC_caSpike_width(t,v,v_dend,thresh=None):
    return AP_width(t,v_dend,thresh)[0]

# Original: Returns 20*std if no spike is detected, or if the amplitude of the dendritic potential 
# is larger than the somatic amplitude. Somatic and dendritic amplitude are calculated 
# as difference between the voltage_base at the respective recording site and the maximum depolarization.
def BPAPatt_check_relative_height(t,v_soma,v_dend,bAP_thresh = None,stim_onset=None):
    return BPAPatt(t,v_soma,bAP_thresh,stim_onset) / BPAPatt(t,v_dend,bAP_thresh,stim_onset) > 1

def BPAPatt_check_1_AP(t,v_soma,thresh=None,stim_onset=None):
    return spike_count(t,v_soma,thresh) == 1

def BPAPatt(t,v_dend, thresh = '+2mV',stim_onset = None):
    b2 = voltage_base(t,v_dend,stim_onset) # 295 is the delay of the bAP stim
    if thresh == '+2mV':
        thresh = b2 + 2
        #print(thresh)
    h2 = AP_height(t,v_dend, thresh)
    # added by arco ... it seems like the hay algorithm discards events in the first half of the 
    # initialization period. I here discard events before the stimulus.
    i = next((lv for lv, i in enumerate(find_crossing(v_dend, thresh)[0]) if t[i] >= stim_onset))
    return h2[i]-b2

# Original: return 20*std if number of spikes is different than 2 or 3
# return 20*std if V(t = 295+45) > -55 computes the deviation of the mean 
# ISI from the experimental mean
def BAC_ISI_check_2_or_3_APs(t,v,thresh=None):
    n = spike_count(t,v,thresh=thresh)
    return (n==2) or (n==3)

def BAC_ISI_check_repolarization(t,v,stim_end = None, repolarization = None):
    i = I.np.nonzero(t >= stim_end)[0][0]
    return v[i] < repolarization

def BAC_ISI(t,v,thresh=None):
    spikes = find_crossing(v, thresh)[0]
    ISI_1 = t[spikes[1]] - t[spikes[0]]
    if len(spikes) == 3:
        ISI_2 = t[spikes[2]] - t[spikes[1]]
    else:
        ISI_2 = ISI_1
    return 0.5*(ISI_1+ISI_2)

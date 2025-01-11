'''
The content of this module is mostly a reimplementation of the Hay et.al. 2011 methods used for extracting features.
See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
'''
import numpy as np


def trace_check(
        t,
        v,
        stim_onset=None,
        stim_duration=None,
        minspikenum=None,
        soma_threshold=None,
        returning_to_rest=2,
        max_prestim_dendrite_depo=-50,
        vmax=None,  ## added by arco
        name=''):
    """
    Check the properties of a voltage trace::
    
        1. Check that at least minspikenum are present.
        2. Check if it properly returns to rest.
        3. Check that there are no spikes before stimulus onset (in soma or dendrite).
        4. Check if last spike is before deadline.
        5. Check that the maximum dendritic depolarization before stimulus onset is not too large.

    Args:
        t (array): Time array.
        v (array): Voltage array.
        stim_onset (float): Time of stimulus onset.
        stim_duration (float): Duration of stimulus.
        minspikenum (int): Minimum number of spikes required.
        soma_threshold (float): Threshold voltage for spike detection.
        returning_to_rest (float): Voltage difference between last reported voltage and voltage base.
        max_prestim_dendrite_depo (float): Maximum dendritic depolarization before stimulus onset.
        vmax (float): Maximum voltage.
        name (str): Name of the trace.

    Returns:
        dict: Dictionary containing the results of the checks.
    """
    n = spike_count(t, v, thresh=soma_threshold)
    out = {}
    # check that at least minspikenum are present
    out[name + '.check_minspikenum'] = n >= minspikenum
    # print(minspikenum)
    # check that voltage base (mean potential from 0.5 to 0.75 * stim_delay) is maxmimum
    # returning_to_rest deeper than last reported voltage
    b = voltage_base(t, v, stim_onset)
    out[name + '.check_returning_to_rest'] = v[-1] < b + returning_to_rest
    # check that there are no spikes before stimulus onset
    crossing_up, crossing_down = find_crossing(v, soma_threshold)
    try:
        t_first_spike = t[crossing_up[0]]
        t_last_spike = t[crossing_up[-1]]
    except IndexError:
        out[name + '.check_no_spike_before_stimulus'] = True
        out[name + '.check_last_spike_before_deadline'] = True
    else:
        out[name +
            '.check_no_spike_before_stimulus'] = t_first_spike >= stim_onset
        deadline = stim_duration * 1.05 + stim_onset
        out[name + '.check_last_spike_before_deadline'] = \
            deadline >= t_last_spike
    
    if vmax is None:
        out[name + '.check_max_prestim_dendrite_depo'] = float('nan')
    else:
        out[name + '.check_max_prestim_dendrite_depo'] = \
            trace_check_max_prestim_dendrite_depo(
                t, 
                vmax, 
                stim_onset, 
                max_prestim_dendrite_depo
            )
    return out


def trace_check_max_prestim_dendrite_depo(
    t,
    vmax,
    stim_onset,
    max_prestim_dendrite_depo=None
    ):
    '''
    Check whether anywhere in the dendritic, there is a spike before stimulus onset
    
    Args:
        t (array): Time array.
        vmax (array): The voltage maximum, taken over all dendrites, at each given timepoint.
        stim_onset (float): Time of stimulus onset (ms).
        max_prestim_dendrite_depo (float): 
            Maximum dendritic depolarization before stimulus onset (mV).
            If some dendrite section exceeds this value, it is considered a spike.
            
    Returns:
        bool: Whether or not a spike is detected before stimulus onset.
    '''
    select = t < stim_onset
    return max(vmax[select]) <= max_prestim_dendrite_depo


def trace_check_err(
    t, 
    v, 
    stim_onset=None, 
    stim_duration=None, 
    punish=250
    ):
    """
    Returns a basic trace error that penalizes traces with low variance.
    Useful for an evolutionary algorithm, when the voltage trace is not spiking yet, and
    spike-related error functions cannot be applied yet. This tells the algorithm to 
    reward variance in a non-spiking voltage trace -- at least something is happening.
    
    Args:
        t (array): Time array.
        v (array): Voltage array.
        stim_onset (float): Time of stimulus onset.
        stim_duration (float): Duration of stimulus.
        punish (float): Baseline penalty for low variance. 
            Default: 250 mV^2.
    """
    select = (t >= stim_onset - 100) & (t <= stim_onset + stim_duration / 2.)
    v = v[select]
    t = t[select]
    var_fact = 1e-1
    # print('trace variance is ', np.var(v), np.var(v)*var_fact, stim_onset, stim_duration)
    return max(75, punish - np.var(v) * var_fact)


def find_crossing_old(v, thresh):
    '''
    Original NEURON doc:
    Function that giving a threshold returns a list of two vectors
    The first is the crossing up of that threshold
    The second is the crossing down of that threshold
    
    Note:
        Extended by Arco: returns [[],[]] if the number of crossing up vs crossing down is not equal.
    '''
    assert thresh is not None
    avec = []
    bvec = []
    ef = 0
    # added by arco to resolve failure of spike detection if value is exactly the threshold
    v = np.array(v) > thresh
    thresh = 0.5
    # end added by arco
    for i, vv in enumerate(v):
        if i == 0:
            continue
        if (vv > thresh) and (v[i - 1] < thresh):
            avec.append(i)
            ef = 1
        else:
            if (vv < thresh) and (v[i - 1] > thresh):
                if ef:  # added by arco: we just want to detect crossing down if we detected crossing up before, might otherwise be initialization artifact
                    bvec.append(i)
    if (len(avec) != len(bvec)) and ef == 1:
        return [avec, bvec]
        #return [[],[]]
    return [avec, bvec]


def find_crossing(v, thresh):
    '''
    Original NEURON doc:
    Function that giving a threshold returns a list of two vectors
    The first is the crossing up of that threshold
    The second is the crossing down of that threshold
    
    Args:
        v (array): Voltage array.
        thresh (float): Threshold voltage (mV).
        
    Returns:
        list: List of index vectors. One for upcrossing, one for downcrossing.
    '''
    v = np.array(v) > thresh
    thresh = 0.5
    upcross = np.where((v[:-1] < thresh) & (v[1:] > thresh))[0] + 1
    downcross = np.where((v[:-1] > thresh) & (v[1:] < thresh))[0] + 1
    if len(upcross) == 0:
        return [[], []]
    downcross = downcross[downcross > upcross[0]]
    #if len(upcross) != len(downcross):
    #    return [[],[]]
    return [list(upcross), list(downcross)]


def voltage_base(t, v, stim_delay):
    """Calculates the mean voltage between 0.5 * stim_delay and 0.75 * stim_delay.

    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        stim_delay (float): Delay time of the stimulus.

    Returns:
        float: Mean voltage between 0.5*stim_delay and 0.75*stim_delay.
    """
    try:
        ta = np.nonzero(
            t >= 0.5 *
            stim_delay)[0][0]  # list(t >= 0.5*stim_delay).index(True)
        ts = np.nonzero(
            t >= 0.75 *
            stim_delay)[0][0]  # list(t >= 0.75*stim_delay).index(True)
    except IndexError:
        return v[0]
    else:
        return v[ta:ts + 1].mean()


def voltage_base2(
    voltage_traces,
    t0,
    recSiteID='recSiteID',
    ):
    """Fetch the voltage at a given time point t0 for a specific recording site ID.

    Args:
        voltage_traces (dict): A dictionary containing voltage traces for different recording sites.
        recSiteID (int): The ID of the recording site for which the voltage is to be returned.
        t0 (float): The time point at which the voltage is to be returned.

    Returns:
        The voltage at time point t0 for the specified recording site ID.
    """
    t = voltage_traces['baseline']['tVec']
    v = voltage_traces['baseline']['vList'][recSiteID]
    i = np.argmin(np.abs(t - t0))
    return v[i]


def spike_count(t, v, thresh=None):
    """
    Counts the number of spikes in a voltage trace.

    Args:
        t (array_like): Time values of the voltage trace, in seconds.
        v (array_like): Voltage values of the trace, in volts.
        thresh (float, optional): Spike detection threshold, in volts. If not specified, the threshold
            will be set to the mean of the voltage trace.

    Returns:
        int: The number of spikes detected in the trace.
    """
    
    return len(find_crossing(v, thresh)[0])


# AP_height is the mean amplitude of all detected spikes. Amplitude is max depolarization
# occuring during a spike. If there is no spike, returns 20 times standard deviation
def AP_height_check_1AP(t, v, thresh=None):
    """
    Determines if an action potential (AP) is present in a voltage trace by checking if the voltage crosses a given threshold.
    
    Args:
        t (array-like): Array of time values corresponding to the voltage trace.
        v (array-like): Array of voltage values for the trace.
        thresh (float, optional): The voltage threshold to use for detecting the AP. If None, defaults to the maximum voltage
            value divided by 2.
    
    Returns:
        bool: True if at least one AP is detected in the voltage trace, False otherwise.
    """
    
    return len(find_crossing(v, thresh)) >= 1


def AP_height(t, v, thresh=None):
    """
    Computes the amplitude of each action potential (AP) in a voltage trace.
    
    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        thresh (float, optional): AP threshold voltage. If None, uses the default threshold of find_crossing().
    
    Returns:
        numpy.ndarray: Array of AP amplitudes.
    """
    out = [max(v[ti:tj]) for ti, tj in zip(*find_crossing(v, thresh))]
    return np.array(out)


def AP_width(t, v, thresh):
    """
    Calculates the action potential (AP) width of a given voltage trace `v` with respect to a given threshold `thresh`.
    
    Args:
        t (numpy.ndarray): Array of time values corresponding to the voltage trace `v`.
        v (numpy.ndarray): Array of voltage values.
        thresh (float): Threshold voltage value for detecting AP onset and offset.
        
    Returns:
        numpy.ndarray: Array of AP widths (in seconds) for each detected AP in the voltage trace `v`.
    """
    w = [t[tk] - t[ti] for ti, tk in zip(*find_crossing(v, thresh))]
    return np.array(w)


AP_width_check_1AP = AP_height_check_1AP


def AP_width(t, v, thresh):
    """
    Calculates the action potential (AP) width given the time and voltage arrays and a threshold value.

    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        thresh (float): Threshold value for detecting AP.

    Returns:
        numpy.ndarray: Array of AP widths.
    """
    w = [t[tk] - t[ti] for ti, tk in zip(*find_crossing(v, thresh))]
    return np.array(w)


AP_width_check_1AP = AP_height_check_1AP


# Original: Computes the minimum membrane potential in between consecutive spikes
# and returns the mean of these values. Returns 20*std if less than 2 spikes.
def AHP_depth_abs_check_2AP(t, v, thresh=None):
    """
    Determines whether there are at least two action potentials (APs) in the voltage trace `v` 
    within the time range `t` that cross the threshold `thresh`.
    
    Args:
        t (numpy.ndarray): The time range of the voltage trace.
        v (numpy.ndarray): The voltage trace.
        thresh (float, optional): The threshold voltage for detecting APs. Defaults to None.
    
    Returns:
        bool: True if there are at least two APs in the voltage trace `v` within the time range `t` 
        that cross the threshold `thresh`, False otherwise.
    """
    return spike_count(t, v, thresh=thresh) >= 2


def AHP_depth_abs(t, v, thresh=None):
    """
    Calculates the absolute afterhyperpolarization (AHP) depth for a given voltage trace.
    
    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        thresh (float, optional): Threshold voltage for action potential detection. Defaults to None.
    
    Returns:
        numpy.ndarray: Array of AHP depths, one for each action potential in the voltage trace.
    """
    apIndexList = np.array(find_crossing(v, thresh))
    apIndexList = [(apIndexList[1, lv], apIndexList[0, lv + 1])
                   for lv in range(apIndexList.shape[1] - 1)]  # the gaps
    return np.array([min(v[ti:tj]) for ti, tj in apIndexList])


# Original: Returns 20std if no spike has been detected. Returns 20std if there are less than two
# somatic APs. Returns 20*std if peak of Ca spike preceedes second somatic spike.
def BAC_caSpike_height_check_1_Ca_AP(t, v, v_dend, thresh=None):
    """
    Checks if there is exactly one calcium spike in the dendritic voltage trace.

    Args:
        t (array): Time array.
        v (array): Somatic voltage array.
        v_dend (array): Dendritic voltage array.
        thresh (float, optional): Spike detection threshold. Defaults to None.

    Returns:
        bool: True if there is exactly one calcium spike in the dendritic voltage trace, False otherwise.
    """
    return spike_count(t, v_dend, thresh) == 1


def BAC_caSpike_height_check_gt2_Na_spikes(t, v, v_dend, thresh=None):
    """Checks if the number of spikes in the voltage trace is greater than or equal to 2.

    Args:
        t (array): Array of time values.
        v (array): Array of voltage values.
        v_dend (array): Array of dendritic voltage values.
        thresh (float, optional): Spike detection threshold. Defaults to None.

    Returns:
        bool: True if the number of spikes is greater than or equal to 2, False otherwise.
    """
    return spike_count(t, v, thresh) >= 2


def BAC_caSpike_height_check_Ca_spikes_after_Na_spike(
    t,
    v,
    v_dend,
    n=2,
    thresh=None):
    """Checks if a calcium spike occurs after the nth sodium spike.

    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        v_dend (numpy.ndarray): Array of dendritic voltage values.
        n (int, optional): The number of the sodium spike to check for.
            Defaults to 2.
        thresh (float, optional): The voltage threshold for detecting spikes.
            If None, defaults to the maximum value of v divided by 10.
            Defaults to None.

    Returns:
        bool: True if a calcium spike occurs after the nth sodium spike,
            False otherwise.
    """
    t_max_Ca = t[v_dend == max(v_dend)][0]
    t_nth_spike = t[find_crossing(v, thresh)[0][n - 1]]
    return t_max_Ca >= t_nth_spike


def BAC_caSpike_height(t, v, v_dend, ca_thresh=-55, tstim=295):
    """
    Returns the height of the calcium spike after tstim.

    Args:
        t (array-like): Time array.
        v (array-like): Voltage array.
        v_dend (array-like): Dendritic voltage array.
        ca_thresh (float, optional): Calcium threshold. Defaults to -55.
        tstim (float, optional): Time of stimulation. Defaults to 295.

    Returns:
        float: Height of the calcium spike.
    """
    hs = AP_height(t, v_dend, ca_thresh)
    i = next((lv for lv, i in enumerate(find_crossing(v_dend, ca_thresh)[0])
              if t[i] >= tstim))
    return hs[i]


# Original: Returns 20 * std if no ca spike has been found. Computes width of Ca spike at caSpikethresh = -55mV
# Returs abs. deviation in ms from the mean experiental width.
# In case of 2 spikes, 7 is substracted from the mean experimental width
# In case, more than one Ca spike is present, the mean width is returned
BAC_caSpike_width_check_1_Ca_AP = BAC_caSpike_height_check_1_Ca_AP


def BAC_caSpike_width(t, v, v_dend, thresh=None):
    """
    Calculates the width of a calcium spike action potential.
    
    Args:
        t (array-like): The time values of the action potential.
        v (array-like): The voltage values of the action potential.
        v_dend (array-like): The voltage values of the dendrite.
        thresh (float, optional): The threshold voltage for the action potential.
        
    Returns:
        float: The width of the calcium spike action potential.
    """
    return AP_width(t, v_dend, thresh)[0]


# Original: Returns 20*std if no spike is detected, or if the amplitude of the dendritic potential
# is larger than the somatic amplitude. Somatic and dendritic amplitude are calculated
# as difference between the voltage_base at the respective recording site and the maximum depolarization.
def BPAPatt_check_relative_height(t, v_soma, v_dend, bAP_thresh=None, stim_onset=None):
    """
    Computes the ratio of the backpropagating action potential (bAP) amplitude at the soma and dendrite
    and returns True if the ratio is greater than 1, False otherwise.

    Args:
        t (numpy.ndarray): Array of time points.
        v_soma (numpy.ndarray): Array of voltage values at the soma.
        v_dend (numpy.ndarray): Array of voltage values at the dendrite.
        bAP_thresh (float, optional): Threshold for detecting bAPs. Defaults to None.
        stim_onset (float, optional): Time point of the stimulus onset. Defaults to None.

    Returns:
        bool: True if the ratio of bAP amplitude at soma and dendrite is greater than 1, False otherwise.
    """
    return BPAPatt(t, v_soma, bAP_thresh, stim_onset) / BPAPatt(t, v_dend, bAP_thresh, stim_onset) > 1
def BPAPatt_check_relative_height(
    t,
    v_soma,
    v_dend,
    bAP_thresh=None,
    stim_onset=None):
                                  
    return BPAPatt(t, v_soma, bAP_thresh, stim_onset) / BPAPatt(
        t, v_dend, bAP_thresh, stim_onset) > 1


def BPAPatt_check_1_AP(t, v_soma, thresh=None, stim_onset=None):
    """
    Checks if there is exactly one action potential in the somatic voltage trace.
    
    Args:
    - t (array): time array [ms]
    - v_soma (array): somatic voltage trace [mV]
    - thresh (float): spike threshold [mV]
    - stim_onset (float): time of stimulus onset [ms]
    
    Returns:
    - bool: True if there is exactly one action potential, False otherwise
    """
    return spike_count(t, v_soma, thresh) == 1


def BPAPatt(t, v_dend, thresh='+2mV', stim_onset=None):
    """
    Computes the amplitude of the backpropagating action potential (bAP) at the dendrite.

    Args:
        t (array): Time array.
        v_dend (array): Dendritic voltage array.
        thresh (str or float): Threshold voltage for detecting the bAP. Default is '+2mV'.
        stim_onset (float): Time of the stimulus onset. Default is None.

    Returns:
        float: Amplitude of the bAP at the dendrite.
    """
    b2 = voltage_base(t, v_dend, stim_onset)  # 295 is the delay of the bAP stim
    if thresh == '+2mV':
        thresh = b2 + 2
        #print(thresh)
    h2 = AP_height(t, v_dend, thresh)
    # added by arco ... it seems like the hay algorithm discards events in the first half of the
    # initialization period. I here discard events before the stimulus.
    i = next((lv for lv, i in enumerate(find_crossing(v_dend, thresh)[0])
              if t[i] >= stim_onset))
    return h2[i] - b2


# Original: return 20*std if number of spikes is different than 2 or 3
# return 20*std if V(t = 295+45) > -55 computes the deviation of the mean
# ISI from the experimental mean
def BAC_ISI_check_2_or_3_APs(t, v, thresh=None):
    """Check if there are 2 or 3 action potentials (APs) in a given voltage trace for a BAC stimulus.
    
    Args:
        t (array): Array of time values.
        v (array): Array of voltage values.
        thresh (float, optional): Spike threshold. Defaults to None.
    
    Returns:
        bool: True if there are 2 or 3 APs, False otherwise.
    """
    n = spike_count(t, v, thresh=thresh)
    return (n == 2) or (n == 3)


def BAC_ISI_check_repolarization(t, v, stim_end=None, repolarization=None):
    """
    Checks if the membrane potential has repolarized to a certain value after a stimulus for a BAC stimulus.

    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of membrane potential values.
        stim_end (float, optional): Time at which the stimulus ends. Defaults to None.
        repolarization (float, optional): Value to which the membrane potential should repolarize. Defaults to None.

    Returns:
        bool: True if the membrane potential has repolarized to the specified value, False otherwise.
    """
    i = np.nonzero(t >= stim_end)[0][0]
    return v[i] < repolarization


def BAC_ISI(t, v, thresh=None):
    """
    Computes the Inter-Spike Interval (ISI) of a voltage trace for a BAC stimulus.
    
    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        thresh (float, optional): Voltage threshold for spike detection. Defaults to None.
    
    Returns:
        float: Burst Averaged Inter-Spike Interval (BAC ISI) value.
    """
    spikes = find_crossing(v, thresh)[0]
    ISI_1 = t[spikes[1]] - t[spikes[0]]
    if len(spikes) == 3:
        ISI_2 = t[spikes[2]] - t[spikes[1]]
    else:
        ISI_2 = ISI_1
    return 0.5 * (ISI_1 + ISI_2)

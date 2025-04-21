import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hot_zone import event_rasterplot
from data_base.analyze.temporal_binning import universal as temporal_binning

def plot_input_populations_activity_histogram(time_bins,rates,population_labels,ylim=None,xlim=None,figsize=(6,4)):
    '''
    Plots the activity time histogram of different populations.
    Args:
        - time_bins: temporal bins of the histogram
        - rates: firing rates of the different populations at those time bins
        - population_labels: names of the different populations
        - xlim
        - ylim
        - figsize
    '''
    len_t = len(time_bins)
    plt.figure(figsize=figsize)
    for rate,label in zip(rates,population_labels):
        plt.step(time_bins[0:len_t-1],rate,label=label)
    plt.legend(loc="upper left")
    plt.xlabel('Time (ms)',size=14)
    plt.ylabel('Firing rate (Hz)',size=14)
    plt.title('Input populations PSTHs',size=16)
    if ylim != None:
        plt.ylim(ylim)
    if xlim != None:
        plt.xlim(xlim)
    plt.show()
    
    
def plot_activity_histogram_for_all_response_types(spike_times,dendritic_spike_times,offset,tStop,bin_size,plot_orientation='horizontal', start_time = -700, grid=False,
                            ylims = [[0,20],[0,6],[0,20],[0,20]]):
    '''
    Plots the activity time histogram for different response types: singlets, doublets, triplets, Ca2+ APs.
    Args:
        - spike_times
        - dendritic_spike_times
        - offset: until time 0
        - tStop
        - bin_size
        - plot_orientation: 'vertical', 'horizontal', 'square'
        - start_time
        - grid
        - ylims
    '''
    n_trials = spike_times.shape[0]
    assert n_trials==dendritic_spike_times.shape[0]
    spike_times = spike_times - offset
    dendritic_spike_times = dendritic_spike_times - offset
    
    if plot_orientation == 'vertical':
        fig, axs = plt.subplots(4, figsize=(6, 16))
        ids = [0,1,2,3]
    elif plot_orientation == 'horizontal':
        fig, axs = plt.subplots(1,4, figsize=(22, 3))
        ids = [0,1,2,3]
    elif plot_orientation == 'square':
        fig, axs = plt.subplots(2, 2, figsize=(15, 8))
        ids = [[0,0],[1,0],[0,1],[1,1]]
    else:
        raise('Plot orientation not defined!')

    freq_conv = 1000/(bin_size*n_trials)
    
    for i,response_type,ylim in zip(ids,['singlet', 'doublet', 'triplet'],ylims):
        sts = [pd.concat([get_response(spike_times.iloc[trial],response_type) for trial in range(n_trials)])]
        bins = [temporal_binning(st, min_time = -offset, max_time = tStop-offset, bin_size = bin_size,normalize=False) for st in sts]
        bin_values = [b[1] for b in bins]
        bin_values_array = np.array(bin_values)
        bin_values_mean = np.mean(bin_values_array, axis = 0)
        bins_all_cells = (bins[0][0], bin_values_mean)
        len_t = len(bins_all_cells[0])
        if plot_orientation == 'vertical' or plot_orientation == 'horizontal':
            axis = axs[i]
        else:
            axis = axs[i[0],i[1]]
        axis.step(bins_all_cells[0][1:len_t],bins_all_cells[1]*freq_conv)
        axis.axvline(0, c='black')
        axis.set_title(response_type,size=14)
        axis.set_xticks(np.array(range(int(start_time/200), int(tStop/200)+1))*200, minor=False)
        if grid:
            axis.yaxis.grid(True, which='major')
            axis.xaxis.grid(True, which='major')
        axis.set_xlim(start_time,tStop-offset)
        axis.set_ylim(ylim)
        axis.set_ylabel('Frequency (Hz)')
        if plot_orientation == 'horizontal' or plot_orientation == 'square' and i == [1,0]:
            axis.set_xlabel('Time (ms)')

    sts = [pd.concat([pd.DataFrame(list(dendritic_spike_times.iloc[trial])) for trial in range(n_trials)])]
    bins = [temporal_binning(st, min_time = -offset, max_time = tStop-offset, bin_size = bin_size,normalize=False) for st in sts]
    bin_values = [b[1] for b in bins]
    bin_values_array = np.array(bin_values)
    bin_values_mean = np.mean(bin_values_array, axis = 0)
    bins_all_cells = (bins[0][0], bin_values_mean)
    len_t = len(bins_all_cells[0])
    if plot_orientation == 'vertical' or plot_orientation == 'horizontal':
        axis = axs[ids[-1]]
    else:
        axis = axs[ids[-1][0],ids[-1][1]]
    axis.step(bins_all_cells[0][1:len_t],bins_all_cells[1]*freq_conv)
    axis.axvline(0, c='black')
    axis.set_title('Ca2+ APs',size=14)
    axis.set_xticks(np.array(range(int(start_time/200), int(tStop/200)+1))*200, minor=False)
    if grid:
        axis.yaxis.grid(True, which='major')
        axis.xaxis.grid(True, which='major')
    axis.set_ylim(ylims[-1])
    plt.xlim(start_time,tStop-offset)
    sns.despine()
    plt.xlabel('Time (ms)')
    plt.ylabel('Frequency (Hz)')
    plt.show()   

def plot_activity_histogram(spike_times,offset,tStop,bin_size,figsize=(6, 4), start_time = -700, grid=False, ylim = [0,20]):
    '''
    Plots the activity time histogram (based on the total spikecount).
    Args:
        - spike_times
        - offset: until time 0
        - tStop
        - bin_size
        - figsize
        - start_time
        - grid
        - ylims
    '''
    n_trials = spike_times.shape[0]
    spike_times = spike_times - offset
    freq_conv = 1000/(bin_size*n_trials)
    sts = [pd.concat([pd.DataFrame(list(spike_times.iloc[trial])) for trial in range(n_trials)])]
    bins = [temporal_binning(st, min_time = -offset, max_time = tStop-offset, bin_size = bin_size,normalize=False) for st in sts]
    bin_values = [b[1] for b in bins]
    bin_values_array = np.array(bin_values)
    bin_values_mean = np.mean(bin_values_array, axis = 0)
    bins_all_cells = (bins[0][0], bin_values_mean)
    len_t = len(bins_all_cells[0])
    
    fig = plt.figure(figsize=figsize)
    axs = plt.gca()
    plt.step(bins_all_cells[0][1:len_t],bins_all_cells[1]*freq_conv)
    plt.axvline(0, c='black')
    plt.title('All spikes',size=16)
    axs.set_xticks(np.array(range(int(start_time/200), int(tStop/200)+1))*200, minor=False)
    if grid:
        axs.yaxis.grid(True, which='major')
        axs.xaxis.grid(True, which='major')
    plt.xlim(start_time,tStop-offset)
    plt.ylim(ylim)
    plt.ylabel('Frequency (Hz)')
    plt.xlabel('Time (ms)')
    sns.despine()
    plt.show() 
    
    bins = [temporal_binning(st, min_time = 0, max_time = tStop-offset, bin_size = bin_size,normalize=False) for st in sts]
    bin_values = [b[1] for b in bins]
    bin_values_array = np.array(bin_values)
    bin_values_array = bin_values_array[~np.isnan(bin_values_array)]
    mean_freq = np.mean(bin_values_array)*freq_conv
    print('Mean spiking frequency from time 0 to end: {}'.format(mean_freq))
    
def plot_rasterplot(spike_times,dendritic_spike_times,time=[],modulation=[],figsize=(8,4)):
    '''
    Plots the rasterplot resulting from running a simulation for several trials
    Args:
        - spike_times
        - dendritic_spike_times
        - time: optional, in case another trace is to be plotted
        - modulation: optional, in case another trace is to be plotted
        - figsize
    '''
    fig = plt.figure(dpi = 120, figsize = figsize)
    ax = fig.add_subplot(111)
    event_rasterplot(spike_times[::-1]-offset, dendritic_spike_times[::-1]-offset, ax = ax)
    plt.axvline(0)
    if len(modulation) != 0:
        plt.plot(time[0:len(time)-1],(modulation*5+50),c='blue')
    plt.show()
    
def plot_mean_vm_whisking(voltage, q1 = 0.1, q2 = 0.9, start_time = 0, end_time = 1000, phase = 0):
    '''
    Plots the average voltage trace obtained after running a simulation for several trials, together with the data between the quartiles q1 and q2. 
    Also, the data is plotted with a whisking trace starting with a phase of phase (0 by default).
    Args:
        - voltage: voltage traces for many trials
        - q1
        - q2
        - start_time
        - end_time
        - phase: starting phase of the sinusoidal whisking trace
    '''
    v = voltage.compute()
    v_mean = v.mean(axis=0)
    v_min = v.quantile(q1,axis=0)
    v_max = v.quantile(q2,axis=0)
    v_mean.index -= offset
    v_min.index -= offset
    v_max.index -= offset
    mean_v = v_mean.loc[start_time+whisk_cycle_duration:end_time].mean()
    t = np.arange(start_time, end_time, 0.025)
    n_bins=len(t)
    modulation = -0.05
    whisking   =np.full(n_bins,(mean_v)*(1+ modulation*np.sin(np.linspace(0,2*np.pi*n_whisk_cycles,n_bins)+phase)))

    fig = plt.figure()
    plt.fill_between(t, v_min[start_time:end_time], v_max[start_time:end_time], alpha=0.2,label='Vm between perc.=25 and perc.=75')
    plt.plot(t,v_mean.loc[start_time:end_time],label='mean Vm at time=t')
    plt.plot([start_time,end_time],[mean_v,mean_v],c='grey',label='mean Vm along trial')
    plt.step(t,whisking,c='black',label='whisking')
    plt.xticks(np.array(range(int(start_time/whisk_cycle_duration), int(end_time/whisk_cycle_duration)+1))*whisk_cycle_duration)
    plt.xlabel('Time (ms)',size=14)
    plt.ylabel('Somatic Vm (mv)',size=14)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    plt.xlim(start_time,end_time)
    plt.ylim(-66,-55)
    plt.show()
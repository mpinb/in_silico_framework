import Interface as I
import numpy as np
import pandas as pd
import shutil
import os
import spike_analysis.core
import matplotlib.pyplot as plt
import scipy
from project_specific_ipynb_code.bottleneck_project.helper_functions import get_binsize

def get_response(spike_times,response_type): # move from project specific to model_data_base/analyse 
    sta = spike_analysis.core.SpikeTimesAnalysis(None)
    sta._db['spike_times'] = spike_times
    sta.apply_extractor(spike_analysis.core.STAPlugin_bursts('bursts_edf','spike_times'))
    sta.apply_extractor(spike_analysis.core.STAPlugin_extract_column_in_filtered_dataframe(
                                                                                   name = response_type+'_times', 
                                                                                   column_name = 'event_time',
                                                                                   source = 'bursts_edf',
                                                                                   select = {'event_class': response_type}))
    return I.pd.DataFrame(sta.get(response_type+'_times'))

def delete_simulation_results(mdb,output_name):
    if output_name in mdb['mdbs'].keys():
        del mdb['mdbs'][output_name]
    else:
        print('-- mdb ' + output_name + ' does not exist, could not be removed')
    results_path = mdb['results']+'/'+output_name
    if os.path.exists(results_path):
        shutil.rmtree(results_path)
    else:
        print('-- results path ' + results_path + ' does not exist, could not be removed')
        
def rate_in_interval(spike_times,tstart,tstop): # model_data_base/analyse
    '''
    Provides the spike rate in a given interval per trial
    '''
    spikes_over_offset = (spike_times[tstart<spike_times]<tstop)
    sum_spikes = spikes_over_offset.sum(axis=1)
    rates_for_trials = sum_spikes/((tstop-tstart)/1000)
    return rates_for_trials

def get_input_populations_activity_histogram(ca,bins,offset,plot=True,ylims=None,population_labels = ['INH', ('L2','L34'), 'L4', 'L5st', 'L5tt', 'L6cc','VPM']):  
    # ca: cell activation dataframe      project specific
    '''
    delayeds = ca.to_delayed()
    @I.dask.delayed
    def helper(ddf_partition):
        celltype = ca.cell_type.split('_').str[0].map(dict_)  L5tt_C2
        return ca.groupy([ca.index, celltype]).apply(lambda x: I.temporal_binning(x, min_time, max_time, bin_size))
    delayeds = [helper(d) for d in delayeds]
    '''
    
    I.temporal_binning()
    rates = []
    for pop in population_labels:
        if type(pop) == tuple:
            sts = ca.loc[(ca['presynaptic_cell_type'].str.contains(pop[0])) | (ca['presynaptic_cell_type'].str.contains(pop[1]))].compute()
        else:
            sts = ca.loc[ca['presynaptic_cell_type'].str.contains(pop)].compute()
        sts = sts.drop(columns = ['presynaptic_cell_type','cell_ID'])
        n_cells = sts.shape[0]
        sts = sts.values.flatten()
        sts = sts[~np.isnan(sts)]
        sts = sts - offset
        
        counts, bins = np.histogram(sts,bins)
        r = counts*1000/(bin_width*n_cells)
        rates.append(r)
    if plot:
        plot_input_populations_PSTHs(bins,rates,population_labels,ylims=ylims)
      
def butter_lowpass_filter(data, cutoff, fs, order=2): # project specific
    from scipy import signal
    normal_cutoff = cutoff / (0.5*fs)
    # Get the filter coefficients 
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    y = signal.filtfilt(b, a, data)
    return y
        
def my_sin(x, freq, amplitude, phase, offset): # project specific
        return np.sin(x * freq*2*np.pi + phase) * amplitude + offset

def fit_sine(data, time, guess_freq, guess_amplitude,guess_phase, guess_offset, get_data_fit = True,plot=False): # project specific
    from scipy.optimize import curve_fit
    p0=[guess_freq, guess_amplitude,guess_phase, guess_offset]
    # recreate the fitted curve using the optimized parameters
    fit = curve_fit(my_sin, time, data, p0=p0) # 1st argument is the function we want to fit
    freq, amplitude, phase, offset = fit[0]
    data_fit = []
    if get_data_fit:
        data_fit = my_sin(time, *fit[0])
    if plot:
        plt.plot(time,data, label='data')#, '.')
        plt.plot(time,data_fit, label='after fitting')
        data_first_guess = my_sin(time, *p0)
        plt.plot(time,data_first_guess, label='first guess')
        plt.xlabel('Time'); plt.legend(); plt.show()
    return freq, amplitude, phase, offset, data_fit
        
def get_signals_phase_difference(voltage,whisking_phase,start_time,end_time,method='sine_fit',plot=False,dt=0.025):# project specific

    assert method in ['sine_fit','filter_trace']
    v_mean = voltage.compute().mean(axis=0)
    v_mean.index -= offset
    v_mean = v_mean[start_time:end_time] # average over many trials
    mean_v = v_mean.loc[start_time:end_time].mean() # single scalar mean value
    n_cycles = int((end_time-start_time)/whisk_cycle_duration)
    
    t = np.arange(start_time, end_time, dt)
    n_bins = len(t)
    whisking   = I.np.full(n_bins,(mean_v)*(1-0.02*I.np.sin(I.np.linspace(0,2*I.np.pi*n_cycles,n_bins)+whisking_phase)))
    
    if method == 'sine_fit':
        guess_freq = whisking_freq
        guess_amplitude = abs(mean_v*0.02)
        guess_phase = 0
        guess_offset = mean_v
        _,_,_,_,data_fit = fit_sine(v_mean, t/1000, guess_freq, guess_amplitude,guess_phase, guess_offset, plot=False)
        
        from statsmodels.tsa.stattools import ccf
        corr = ccf(data_fit, whisking)
        
    elif method == 'filter_trace':  
        fs = 1/dt
        vf = butter_lowpass_filter(v_mean, cutoff, fs)
        from statsmodels.tsa.stattools import ccf
        corr = ccf(vf, whisking)
        
    samples_per_cycle = int(whisk_cycle_duration/dt)
    t_ = t[0:samples_per_cycle]
    corr_ = corr[0:samples_per_cycle]
    max_corr = np.max(corr_)
    phase_diff = t_[np.argmax(corr_)]
    phase_diff_angle = round(360*(phase_diff-start_time)/whisk_cycle_duration) #2*np.pi
    if phase_diff_angle>=360:
        phase_diff_angle-=360  
    
    print('Estimated phase difference: {} degrees'.format(phase_diff_angle))
    print('Max. cross-correlation: {}'.format(max_corr))
    if plot:
        plt.figure()
        plt.plot(t,v_mean,c = 'lightgray',label='Vm')
        plt.plot(t,whisking,c='black',label='whisking')
        plt.plot(t,data_fit,label='Fitted sine')
        plt.xlabel('Lag (ms)')
        plt.legend(); plt.show()
    return phase_diff_angle, max_corr

# Sectioning the morphology
def get_spatial_bins_df(neuron_param_file, silent = True): # maybe in single cell parser.cell
    # Divides the sections that form a morphology in bins of equal length of approx 50 of length
    neup = I.scp.NTParameterSet(neuron_param_file)
    if silent:
        with I.silence_stdout:
            cell = I.scp.create_cell(neup.neuron)    
    sections_min_dist = [I.sca.synanalysis.compute_distance_to_soma(sec, 0) for sec in cell.sections]
    sections_max_dist = [I.sca.synanalysis.compute_distance_to_soma(sec, 1) for sec in cell.sections]
    binsize = []
    n_bins = []
    for lv, (s_mi, s_ma) in enumerate(zip(sections_min_dist, sections_max_dist)):
        if (cell.sections[lv].label != 'Soma'):
            binsize_, n_bins_ = get_binsize(s_ma-s_mi)
            binsize.append(binsize_)
            n_bins.append(n_bins_)
    spatial_bins_df = I.pd.DataFrame({'n_bins': n_bins, 'binsize': binsize})
    return spatial_bins_df

def get_dendritic_groups(cell):
    
    sections = np.arange(len(cell.sections))
    
    def unique(lists):
        result = []
        for i in lists:
            if i not in result:
                result.append(i)
        return result

    def get_child_sections_from_parent(sec): # Input is the parent, output are the child sections
        sec_branches = []
        for secn in sections:
            if cell.sections[secn].parent == cell.sections[sec]:
                sec_branches.append(secn)
        return sec_branches

    def recursive_branch(sect):   #NEEDS A RETURN SOMEWHERE
        br = get_child_sections_from_parent(sect)
        if len(br) in [0,1]:
            return
        else:
            dendrite.extend(br) #OR ITS BC THIS LIST DOESNT EXIST
            for sec2 in br:
                recursive_branch(sec2)

    def get_section_n(section):
        result = None
        for i,sec in enumerate(cell.sections):
            if sec == section:
                result = i
        return result

    def recursive_tuft_sections_filling(child):
        children = get_child_sections_from_parent(child)
        if len(children) == 0:
            return
        tuft_sections.extend(children)
        for child in children:
            recursive_tuft_sections_filling(child)
            
    dendritic_groups = {'basal':[],'trunk':[],'oblique':[],'tuft':[]}

    # Identify dendrites steming out of the soma and save them in the list dendrites_from_soma
    dendrites_from_soma = []
    for sec in sections:
        if sec == 0:
            continue
        dendrite = []
        if cell.sections[sec].parent.label =="Soma":
            dendrite.append(sec)
            recursive_branch(sec)
            dendrite = unique(dendrite)
            dendrite.reverse()
            dendrites_from_soma.append(dendrite)

    # Identify which of those dendrites is the apical dendrite and remove it from dendrites_from_soma
    for idx, d in enumerate(dendrites_from_soma):
        if cell.sections[d[0]].label=="ApicalDendrite":
            ApicalDendriteIndex = idx
    apical_dendrite = dendrites_from_soma[ApicalDendriteIndex]
    dendrites_from_soma.pop(ApicalDendriteIndex)
    dendritic_groups['basal'] = dendrites_from_soma

    # Identify which of the apical dendrite sections belong to the tuft
    bifurcation = I.biophysics_fitting.get_main_bifurcation_section(cell)
    bifurcation_sec = get_section_n(bifurcation)
    tuft_sections = []
    recursive_tuft_sections_filling(bifurcation_sec)
    dendritic_groups['tuft'] = tuft_sections

    # Identify which of the apical dendrite sections belong to the trunk
    trunk_sections = [bifurcation_sec]
    parent = get_section_n(cell.sections[bifurcation_sec].parent)
    while parent != 0:
        sec = parent
        trunk_sections.append(parent)
        parent = get_section_n(cell.sections[sec].parent)
    dendritic_groups['trunk'] = trunk_sections

    # The rest are the oblique dendrites
    oblique_sections = []
    for sec in apical_dendrite:
        if sec not in tuft_sections and sec not in trunk_sections:
            oblique_sections.append(sec)
    dendritic_groups['oblique'] = oblique_sections
    
    return dendritic_groups

def poisson_means_test(k1, n1, k2, n2, *, diff=0, alternative='two-sided'):
    # this is the implementation in a newer version of scipy 
    lmbd_hat2 = ((k1 + k2) / (n1 + n2) - diff * n1 / (n1 + n2))
    if lmbd_hat2 <= 0:
        return 0, 1
    var = k1 / (n1 ** 2) + k2 / (n2 ** 2)
    t_k1k2 = (k1 / n1 - k2 / n2 - diff) / np.sqrt(var)
    nlmbd_hat1 = n1 * (lmbd_hat2 + diff)
    nlmbd_hat2 = n2 * lmbd_hat2
    x1_lb, x1_ub = scipy.stats.poisson.ppf([1e-10, 1 - 1e-16], nlmbd_hat1)
    x2_lb, x2_ub = scipy.stats.poisson.ppf([1e-10, 1 - 1e-16], nlmbd_hat2)
    x1 = np.arange(x1_lb, x1_ub + 1)
    x2 = np.arange(x2_lb, x2_ub + 1)[:, None]
    prob_x1 = scipy.stats.poisson.pmf(x1, nlmbd_hat1)
    prob_x2 = scipy.stats.poisson.pmf(x2, nlmbd_hat2)
    lmbd_x1 = x1 / n1
    lmbd_x2 = x2 / n2
    lmbds_diff = lmbd_x1 - lmbd_x2 - diff
    var_x1x2 = lmbd_x1 / n1 + lmbd_x2 / n2
    with np.errstate(invalid='ignore', divide='ignore'):
        t_x1x2 = lmbds_diff / np.sqrt(var_x1x2)
    if alternative == 'two-sided':
        indicator = np.abs(t_x1x2) >= np.abs(t_k1k2)
    elif alternative == 'less':
        indicator = t_x1x2 <= t_k1k2
    else:
        indicator = t_x1x2 >= t_k1k2
    pvalue = np.sum((prob_x1 * prob_x2)[indicator])
    return t_k1k2, pvalue

def save_delayeds_in_folder(folder_, ds, files_per_folder = 100000):
    '''
    Function to save a list of delayed objects in a folder, so that they can be computed in parallel using slurm directly instead of dask.
    This is useful when I need more that 1000 nodes, dask does not scale good so it's better to launch slurm jobs directly.
    folder_: folder where to save the delayed objects
    ds: list of delayed objects
    '''
    
    dask2slrm_TEMPLATE = '''#!/bin/bash

    # Example of running python script with a job array

    #SBATCH -J dsk2slrm
    #SBATCH -p CPU
    #SBATCH --array=1-{}                    # how many tasks in the array
    #SBATCH -c 1                           # one CPU core per task
    #SBATCH -t 24:00:00
    #SBATCH -o run-%j-%a.out
    #SBATCH -e run-%j-%a.err
    #SBATCH --mem=8000


    # Run python script with a command line argument
    srun {} run.py $SLURM_ARRAY_TASK_ID 
    '''
    #SBATCH --output=none
    #SBATCH --error=none
    runpy_TEMPLATE = '''import os
    import sys
    import cloudpickle
    import dask
    path = '{}'
    n_folders = {}
    id_ = int(sys.argv[1])
    basedir = os.path.basename(path)
    subdir = str((id_ - 1) % n_folders)
    path_to_delayed = os.path.join(path, subdir, str(id_))
    if os.path.exists(path_to_delayed + '.done'):
        exit()
    with open(path_to_delayed, 'rb') as f:
        d = cloudpickle.load(f)
    dask.compute(d, scheduler = 'synchronous')
    os.rename(path_to_delayed, path_to_delayed+'.done')'''
    
    n_folders = int(I.np.ceil(len(ds) / files_per_folder))
    for lv, d in enumerate(ds):
        subdir = str(lv % n_folders)
        if not I.os.path.exists(folder_.join(subdir)):
            I.os.makedirs(folder_.join(subdir))
        with open(folder_.join(subdir).join(str(lv+1)), 'wb') as f:
            I.cloudpickle.dump(d, f)
    with open(folder_.join('slurm.sh'), 'w') as f:
        f.write(dask2slrm_TEMPLATE.format(len(ds)+1, I.sys.executable))
    with open(folder_.join('run.py'), 'w') as f:
        f.write(runpy_TEMPLATE.format(folder_, n_folders))
    print('Now go to the folder where the delayeds are saved and launch the SLURM job that executes them using the commands:')
    print('cd {}'.format(folder_))
    print('sbatch slurm.sh')
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import Interface as I
import dask
from simrun import modular_reduced_model_inference
from simrun.modular_reduced_model_inference import RaisedCosineBasis
from data_base.analyze.spike_detection import spike_in_interval
import reduced_model_output_paper

def calculate_filters(name, db_list, tmin, tmax, width = 80, n_splits = 1):
    rm = modular_reduced_model_inference.Rm(name, db = db_list, tmin = tmin, tmax = tmax, width = width)

    # make simulation data available to the reduced model
    D = modular_reduced_model_inference.DataExtractor_spatiotemporalSynapseActivation
    identifier = tuple(['synapse_activation_binned', 't1'] + ['__'.join(['EI', 'binned_somadist'])])
    rm.add_data_extractor('spatiotemporalSa', D(identifier))
    rm.add_data_extractor('st', modular_reduced_model_inference.DataExtractor_spiketimes())
    rm.add_data_extractor('y', modular_reduced_model_inference.DataExtractor_spikeInInterval())
    rm.add_data_extractor('ISI', modular_reduced_model_inference.DataExtractor_ISI())

    # define a strategy which evaluates simulation trials based on spatiotemporal filters
    RaisedCosineBasis_spatial  = RaisedCosineBasis(a = 3, c = 5, phis = np.arange(3,12, 1.5), width = 30, reversed_ = False)
    RaisedCosineBasis_temporal = RaisedCosineBasis(a = 2, c = 1, phis = np.arange(1,11, 0.5), width = 80, reversed_ = True)
    strategy = modular_reduced_model_inference.Strategy_spatiotemporalRaisedCosine('SAspatiotemporalRaisedCosine', 
                                RaisedCosineBasis_spatial, RaisedCosineBasis_temporal)
    rm.add_strategy(strategy)
    solver = modular_reduced_model_inference.Solver_COBYLA('cobyla')
    strategy.add_solver(solver)

    for lv in range(n_splits): # make 3 random train/test splits
        rm.DataSplitEvaluation.add_isi_dependent_random_split('ISI50_.7_{}'.format(lv),min_isi = 50, percentage_train=.7)
    return rm

def get_spatial_bin_level(key):
    """returns the index that relects the spatial dimension"""
    return key[-1].split("__").index("binned_somadist")

def get_sorted_keys_by_group(mdb, key, group):
        """returns keys sorted such that the first key is the closest to the soma"""       
        group = list(group)
        level = get_spatial_bin_level(key)
        keys = mdb[key].keys(recurse=True)
        keys = sorted(keys, key = lambda x: float(x[level].split("to")[0]))
        out = []
        for k in keys:
            k_copy = list(k[:])
            k_copy.pop(level)
            if k_copy == group:
                out.append(k)
        return out

def _get_spatiotemporal_input(mdb, key, group):
    """returns spatiotemporal input in the following dimensions:
    (trial, time, space)"""      
    keys = get_sorted_keys_by_group(mdb, key, group)
    out = [mdb[key][k] for k in keys]
    print(keys)
    return out
                
# calculate all the WNI values at relevant timepoints - we will need them again to estimate the ISI-dependent penalty
@dask.delayed
def calculate_WNI_values(morph, column, model_nr, whisker, SApath, kernel_dict, outdir):
    
    timebins = len(range(220, 271))  
    
    SAexc = _get_spatiotemporal_input(SApath,("synapse_activation_binned", "t1", "EI__binned_somadist"), ["EXC"])
    SAinh = _get_spatiotemporal_input(SApath,("synapse_activation_binned", "t1", "EI__binned_somadist"), ["INH"])
    
    SAexc = np.asarray(SAexc)
    SAinh = np.asarray(SAinh)
    
    n_cells = SAexc.shape[1]
    WNI_df = pd.DataFrame(index = range(n_cells), columns = range(220, 271))
    
    s_exc = kernel_dict['s_exc']
    s_inh = kernel_dict['s_inh']
    t_exc = kernel_dict['t_exc']
    t_inh = kernel_dict['t_inh']

    SAinh_cumulative = np.ndarray((n_cells, 400))
    SAexc_cumulative = np.ndarray((n_cells, 400))

    for t, timebin in enumerate(range(220-80, 271)): # for all timebins relevant to period of interest
        ## get excitatory and inhibitory input, spatially binned for the CURRENT timebin
        SAexc_timebin = SAexc[:, :, timebin]
        SAinh_timebin = SAinh[:, :, timebin]

        ## apply spatial kernel to the current timebin
        SAexc_timebin = sum([o*s for o, s in zip(SAexc_timebin, s_exc)])
        SAinh_timebin = sum([o*s for o, s in zip(SAinh_timebin, s_inh)])

        for cell in range(n_cells):
            SAinh_cumulative[cell][timebin] = SAinh_timebin[cell]
            SAexc_cumulative[cell][timebin] = SAexc_timebin[cell]
            
    ## apply temporal kernel to timebins of interest
    for t, timebin in enumerate(range(220, 271)):
#         print timebin
        for cell in range(n_cells):

            SAexc_window = SAexc_cumulative[cell][timebin-79:timebin+1]
            SAinh_window = SAinh_cumulative[cell][timebin-79:timebin+1]

            SAexc_window = sum([o*s for o, s in zip(SAexc_window, t_exc)])
            SAinh_window = sum([o*s for o, s in zip(SAinh_window, t_inh)])

            ## get weighted net input for each cell
            WNI = SAexc_window + SAinh_window
            WNI_df.iloc[cell, t] = WNI
    name = 'WNI_values__{}_whisker_stim.csv'.format(whisker)
    WNI_df.to_csv(outdir.join(name))

def group_bins(helper_df, min_items = 10):
    # https://codereview.stackexchange.com/questions/12753/taking-the-first-few-items-of-a-list-until-a-target-sum-is-exceeded/12759

    total_items = 0
    rows_to_group = []
    groupings = []

    for row in range(len(helper_df.index)):

        items = helper_df.iloc[row, 3]
        total_items += items # keep a running total of number of datapoints
        rows_to_group.append(row)

        if total_items >= min_items: # once we have enough datapoints, save the grouping and continue
            total_items = 0
            groupings.append(rows_to_group)
            rows_to_group = []

        elif row == range(len(helper_df.index))[-1]: # or if it's the last bin, which might get skipped otherwise 
            groupings.append([row])

    # check if the last bin is too small, merge with second to last if it is
    last_binsize = 0
    for row in groupings[-1]:
        last_binsize += helper_df.iloc[row, 3]

    if last_binsize < min_items:
        new_grouping = groupings[:-2]
        last_bins = groupings[-2:]
        new_grouping.append([i for sublist in last_bins for i in sublist])
        groupings = new_grouping
    
    return groupings

def signchange(x,y):
    if x / abs(x) == y / abs(y):
        return False
    else:
        return True

def linear_interpolation_between_pairs(X,Y, x, top = 'inf', bottom = 'min'):
    if x > max(X):
        if top == 'inf':
            result = np.inf
        elif top == 'max':
            result = max(Y)
    elif x < min(X):
        if bottom == 'inf':
            result = -np.inf
        elif bottom == 'min':
            result = min(Y)        
    elif float(x) in X: # don't need to interpolate, causes assertion error
        result = Y[X.index(x)]
    else:
        pair = [lv for lv in range(len(X)-1) if signchange(X[lv]-x, X[lv+1]-x)]
#         X[lv] <= x < X[lv + 1]]
        assert(len(pair) == 1)
        pair = pair[0]
        m = (Y[pair+1]-Y[pair]) / (X[pair+1]-X[pair])
        c = Y[pair]-X[pair]*m

        result = m*x+c
    return result

def variable_stepsize_nonlinearity(wni_values, spike_times, spike_before = None, lookup_series_stepsize = 3, min_items = 10):
    pdf2 = pd.DataFrame(dict(wni_values = wni_values, spike = spike_times))
    if spike_before is not None:
        pdf = pdf2[~spike_before]
    else:
        pdf = pdf2

    bins = range(int(np.floor(pdf['wni_values'].min())), int(np.floor(pdf['wni_values'].max())) + lookup_series_stepsize + 1, lookup_series_stepsize)
    pdf['bin'] = pd.cut(pdf['wni_values'], bins, include_lowest=True)

    helper_df = pd.DataFrame()

    edges = []
    spike_prob = []
    n_items = []
    spikes = []
    for b in set(pdf['bin']):
        b_pdf = pdf[pdf['bin'] == b]
        n_items.append(len(b_pdf))
        edges.append(int(b.left))
        spike_prob.append(np.mean(b_pdf['spike']))
        spikes.append(list(b_pdf['spike']))

    helper_df['bin_start'] = edges
    helper_df['spike_prob'] = spike_prob
    helper_df['spikes'] = spikes
    helper_df['n_items'] = n_items
    helper_df.sort_values('bin_start', inplace = True)

    bin_groupings = group_bins(helper_df, min_items = min_items)
    new_df = pd.DataFrame(columns = ['bin_start', 'spike_prob'], index = range(len(bin_groupings)))

    bin_starts = []
    spike_probs = []
    for g in bin_groupings:
        if len(g) == 1:
            bin_starts.append(helper_df.iloc[g[0], 0])
            spike_probs.append(helper_df.iloc[g[0], 1])
        else:
            bin_starts.append(helper_df.iloc[g[0], 0])
            spikes = []
            for row in g:
                spikes.append(helper_df.iloc[row, 2])

            spikes = [i for sublist in spikes for i in sublist]
            assert len(spikes) >= min_items
            spike_probs.append(np.mean(spikes))


    points = []
    for n, b in enumerate(bin_starts):
        midpoint = b + (lookup_series_stepsize * len(bin_groupings[n]))/2.
        points.append((midpoint, spike_probs[n]))

    points = sorted(points)
    x_points = [p[0] for p in points]
    y_points = [p[1] for p in points]

    diff = max(x_points) - min(x_points)
    index = np.arange(int(min(x_points) - 0.3 * diff), int(max(x_points) + 0.3 * diff))

    LUT = pd.Series(index = index)
    for i in index:
        LUT[i] = linear_interpolation_between_pairs(x_points,y_points, i, top = 'max')
        
    return LUT

def fetch_ISI_WNI_data(morph,column,model_nr, SWs,rm_inference_timepoint,mdb,mdb_data,twoparts=[]):
    st = pd.DataFrame()
    for whisker in SWs[column]:
        if whisker in twoparts:
            st = pd.concat([st,mdb_data[morph]['sim_mdb_'+column+'_cells_model_'+str(model_nr)][whisker+'_whisker_stimuli_1']['spike_times']])
            st = pd.concat([st,mdb_data[morph]['sim_mdb_'+column+'_cells_model_'+str(model_nr)][whisker+'_whisker_stimuli_2']['spike_times']])
        else:
            st = pd.concat([st,mdb_data[morph]['sim_mdb_'+column+'_cells_model_'+str(model_nr)][whisker+'_whisker_stimuli']['spike_times']])
    # is there a spike in the estimation period?
    st['spike_in_interval'] = spike_in_interval(st, rm_inference_timepoint, rm_inference_timepoint + 1)
    # how long ago was the most recent spike?
    st[st>rm_inference_timepoint] = np.NaN
    st['ISI'] = st.max(axis=1) - rm_inference_timepoint

    # collect WNI values and add them to the dataframe
    wni = pd.DataFrame()
    for whisker in SWs[column]:
        if whisker in twoparts:
            wni_path = mdb[morph][column]['model_{}'.format(model_nr)]['WNI_values'].join('WNI_values__{}_1_whisker_stim.csv'.format(whisker))
            wni = pd.concat([wni, pd.read_csv(wni_path)])
            wni_path = mdb[morph][column]['model_{}'.format(model_nr)]['WNI_values'].join('WNI_values__{}_2_whisker_stim.csv'.format(whisker))
            wni = pd.concat([wni, pd.read_csv(wni_path)])
        else:
            wni_path = mdb[morph][column]['model_{}'.format(model_nr)]['WNI_values'].join('WNI_values__{}_whisker_stim.csv'.format(whisker))
            wni = pd.concat([wni, pd.read_csv(wni_path)])

    st['wni_value'] = np.asarray(wni.loc[:, str(rm_inference_timepoint)])

    spike_df = st[st.spike_in_interval & (st.ISI > -80) & (st.ISI < 0)]
    no_spike_df = st[~st.spike_in_interval & (st.ISI > -80) & (st.ISI < 0)]
    
    spike_isi = spike_df['ISI']
    spike_wni = spike_df['wni_value']
    
    no_spike_isi = no_spike_df['ISI']
    no_spike_wni = no_spike_df['wni_value']

    return spike_isi, spike_wni, no_spike_isi, no_spike_wni, st

def get_isi_boundary_95(spike_isi, spike_wni):
    def signchange(x,y):
        if x / abs(x) == y / abs(y):
            return False
        else:
            return True
    
    def linear_interpolation_between_pairs(X,Y, x):
        if x > max(X):
            result = np.inf
        elif x < min(X):
            result = min(Y)
        elif float(x) in X: # don't need to interpolate, causes assertion error
            result = Y[X.index(x)]
        else:
            pair = [lv for lv in range(len(X)-1) if signchange(X[lv]-x, X[lv+1]-x)]
    #         X[lv] <= x < X[lv + 1]]
            assert(len(pair) == 1)
            pair = pair[0]
            m = (Y[pair+1]-Y[pair]) / (X[pair+1]-X[pair])
            c = Y[pair]-X[pair]*m

            result = m*x+c
        return result

    if len(list(zip(spike_isi, spike_wni))) < 2:
        return np.nan
    l = sorted(zip(spike_isi, spike_wni), key = lambda x: x[1]) # sort by WNI values
    to_drop = len(spike_wni) / 20 # drop lowest 5%
    l = l[int(to_drop):]
    l = sorted(l, key = lambda x: x[0], reverse = True) # sort by ISI again
    points = []
    points.append([l[0][0], l[0][1]])
    y_min = l[0][1]
    for x, y in l:
        if y < y_min:
            points.append([x, y])
            y_min = y
            
    x_points = [p[0] for p in points]
    y_points = [p[1] for p in points]

    ISI_boundary = pd.Series(index = range(-80, 0))

    for ISI in ISI_boundary.index:
        ISI_boundary[ISI] = linear_interpolation_between_pairs(x_points, y_points, ISI)
        
    return ISI_boundary

def plot_ISI_cloud(ax, spike_isi, spike_wni, no_spike_isi, no_spike_wni, s = 2):
    ax.scatter(no_spike_isi, no_spike_wni, c = 'k', s = s, rasterized = True)
    ax.scatter(spike_isi, spike_wni, c = 'r', s = s, rasterized = True)
    ax.legend(['no spike', 'spike'])
    ax.set_xlim(-85, 5)
    ax.set_ylim(-30, 120)
    ax.set_xlabel('inter spike interval (ms)')
    ax.set_ylabel('weighted net input')
    
def RM_plot(spatiotemporal_filters,nonlinearity,ISI_penalty,title,save=None):
    import seaborn as sns
    fig = plt.figure()
    my_suptitle = plt.suptitle(title, y = 1.05)

    ax1 = fig.add_subplot(2,2,1)
    ax2 = fig.add_subplot(2,2,3)
    filters = spatiotemporal_filters
    s_exc = filters['s_exc']
    s_inh = filters['s_inh']
    t_exc = filters['t_exc']
    t_inh = filters['t_inh']

    ax1.plot(s_exc, c = 'r')
    ax1.plot(s_inh, c = 'grey')
    ax1.set_xticks([0,10,20, 30])
    ax1.set_xticklabels([0, 500, 1000, 1500])
    ax1.set_xlabel('somadistance (um)')

    ax2.plot(t_exc, c = 'r')
    ax2.plot(t_inh, c = 'grey')
    ax2.set_xticks(range(0, 85, 10))
    ax2.set_xticklabels(range(-80, 5, 10))
    ax2.set_xlabel('time (ms)')

    ax1.set_ylim(-0.4, 1.2)
    ax2.set_ylim(-1.2, 1.2)
    ax1.set_ylabel('contribution to spiking')
    ax2.set_ylabel('contribution to spiking')
    ax2.set_xlim(-5, 80)
    
    nonlinearity = pd.Series(nonlinearity)
    nonlinearity.index = nonlinearity.index.astype(int)
    nonlinearity = nonlinearity.sort_index()
    ax3 = fig.add_subplot(2,2,2)
    ax3.plot(nonlinearity)
    #ax3.set_xlim(0,175)
    ax3.set_ylim(-0.1, 1.1)
    ax3.set_ylabel('AP probability')
    ax3.set_xlabel('WNI')

    penalty = pd.Series(ISI_penalty)
    penalty.index = penalty.index.astype(int)
    penalty = penalty.sort_index()
    ax4 = fig.add_subplot(2,2,4)
    ax4.plot(penalty)
    ax4.set_xlim(-40, 5)
    ax4.set_ylim(0,100)
    ax4.set_ylabel('WNI penalty')
    ax4.set_xlabel('time since last spike (ms)')
        
    plt.tight_layout()
    sns.despine()
    if save is not None: plt.savefig(save+'.pdf',bbox_inches='tight',bbox_extra_artists=[my_suptitle])
    plt.show()
    
def filters_plot(spatiotemporal_filters,title):
    import seaborn as sns
    fig = plt.figure(figsize=(8,3))
    plt.suptitle(title, y = 1.05)

    ax1 = fig.add_subplot(1,2,1)
    ax2 = fig.add_subplot(1,2,2)
    filters = spatiotemporal_filters
    s_exc = filters['s_exc']
    s_inh = filters['s_inh']
    t_exc = filters['t_exc']
    t_inh = filters['t_inh']

    ax1.plot(s_exc, c = 'r')
    ax1.plot(s_inh, c = 'grey')
    ax1.set_xticks([0,10,20, 30])
    ax1.set_xticklabels([0, 500, 1000, 1500])
    ax1.set_xlabel('somadistance (um)')

    ax2.plot(t_exc, c = 'r')
    ax2.plot(t_inh, c = 'grey')
    ax2.set_xticks(range(0, 85, 10))
    ax2.set_xticklabels(range(-80, 5, 10))
    ax2.set_xlabel('time (ms)')

    ax1.set_ylim(-0.4, 1.2)
    ax2.set_ylim(-1.2, 1.2)
    ax1.set_ylabel('contribution to spiking')
    ax2.set_ylabel('contribution to spiking')
    ax2.set_xlim(-5, 80)
    
    plt.tight_layout()
    sns.despine()
    plt.show()
    
def get_RM(morph,column,model_nr,mdb):
    mdb_model = mdb[morph][column]['model_{}'.format(model_nr)]
    filters = mdb_model['spatiotemporal_filters']
    nonlinearity = pd.Series(mdb_model['nonlinearity'])
    nonlinearity.index = nonlinearity.index.astype(int)
    nonlinearity = nonlinearity.sort_index() 
    penalty = pd.Series(mdb_model['ISI_penalty'])
    penalty.index = penalty.index.astype(int)
    penalty = penalty.sort_index()
    rm = ReducedModel(filters, nonlinearity, penalty)
    return rm
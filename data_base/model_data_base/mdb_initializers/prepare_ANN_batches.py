import Interface as I
import warnings


def get_binsize(length, binsize_goal=50):
    '''given a length of a branch, returns number of binsize and number of bins that results in binning closest to 
    the binsize goal'''
    n_bins = length / float(binsize_goal)
    n_bins_lower = I.np.floor(n_bins)
    n_bins_lower = I.np.max([n_bins_lower, 1])
    n_bins_upper = I.np.ceil(n_bins)
    binsize_lower = length / n_bins_lower
    binsize_upper = length / n_bins_upper
    if I.np.abs(binsize_goal - binsize_lower) < I.np.abs(binsize_goal -
                                                         binsize_upper):
        return binsize_lower, int(n_bins_lower)
    else:
        return binsize_upper, int(n_bins_upper)


def get_bin(value, bin_min, bin_max, n_bins, tolerance=0.1):
    bin_size = (bin_max - bin_min) / n_bins
    bins = [bin_min + n * bin_size for n in range(n_bins + 1)]
    bins[0] = bins[0] - tolerance
    bins[-1] = bins[-1] + tolerance
    if (I.np.max(value) >= bins[-1]) or (I.np.min(value) <= bins[0]):
        raise RuntimeError('value outside of bin_min and bin_max!')
    return I.np.digitize(value, bins)


def get_neuron_param_file(m):
    folder = m['parameterfiles_cell_folder']
    f = [f for f in folder.listdir() if not f.endswith('.pickle')]  #+.keys()
    if not len(f) == 1:
        warnings.warn(
            'found more than one neuron parameter file in the database. Make sure the database does not contain simulations with more than one morphology!'
        )
    return folder.join(f[0])


def get_section_distances_df(neuron_param_file, silent=True):
    neup = I.scp.NTParameterSet(neuron_param_file)
    if silent:
        with I.silence_stdout:
            cell = I.scp.create_cell(neup.neuron)
    sections_min_dist = [
        I.sca.synanalysis.compute_distance_to_soma(sec, 0)
        for sec in cell.sections
    ]
    sections_max_dist = [
        I.sca.synanalysis.compute_distance_to_soma(sec, 1)
        for sec in cell.sections
    ]
    binsize = [
        get_binsize(s_ma - s_mi)[0] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi,
                 s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    n_bins = [
        get_binsize(s_ma - s_mi)[1] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi,
                 s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    bin_borders = [
        I.np.linspace(s_mi, s_ma, num=n_bins) if
        not isinstance(n_bins, str) else 'Soma' for s_mi, s_ma, n_bins in zip(
            sections_min_dist, sections_max_dist, n_bins)
    ]
    section_distances_df = I.pd.DataFrame({
        'min_': sections_min_dist,
        'max_': sections_max_dist,
        'n_bins': n_bins,
        'binsize': binsize
    })
    return section_distances_df


def get_spatial_bin_names(section_distances_df):
    """Given a dataframe describing the distance to soma of all sections, as provided by :@function get_section_distances_df:,
    this method returns the names for all the spatial bins of the format section_id/bin_id. E.g.: 5/2 denotes the second bin of section 5.


    Args:
        section_distances_df (pd.DataFrame): the dataframe describing distance to soma for all sections, as provided by :@function get_section_distances_df:

    Returns:
        list: A list containing the bin ids in string format.
    """
    all_bins = []
    for index, row in section_distances_df.iterrows():
        n_bins = row['n_bins']
        if n_bins == 'Soma':
            all_bins.append(str(index) + '/' + str(0))
        else:
            for n in range(n_bins):
                all_bins.append(str(index) + '/' + str(n + 1))
    return all_bins


def get_bin_soma_distances_in_section(section_id, section_distances_df):
    """Given a section id, this method returns the distance to soma for all bins in this section

    Args:
        section_id (int): Id of the neuron section
        section_distances_df (pd.DataFrame): the dataframe describing distance to soma for all sections, as provided by :@function get_section_distances_df:

    Returns:
        list: A list containing the distance to soma for each bin in a section.
    """
    section = section_distances_df.iloc[int(section_id)]
    soma_d = []
    for i in range(section["n_bins"]):
        # centers of the bins
        soma_d.append(section["min_"] + int(i + 0.5) *
                      (section["max_"] - section["min_"]) / section["n_bins"])
    return soma_d


def get_bin_adjacency_map_in_section(cell, section_id, section_distances_df):
    """
    Creates an adjacency map with bin-specific resolution for a given section.
    
    Consecutive bins in the same section are trivially connected.
    This method also fetches other sections connected to the given section id, and checks at which bins they connect.
    Sections are defined by the neuron simulation, but bins are ad-hoc defined by data preparation for the ANN.

    This method exploits the tree structure of a neuron, i.e. a child section is always connected at the beginning
    This means that all child sections are connected to their parent section at bin number 1
    The goal is then to figure out at which bin in the parent section the child is connected to.
    Eeach section always has one or more bins.

    
    Args:
        cell (Cell): the Cell object
        section_id (int): index of the neuron section
        section_distances_df (pd.DataFrame): the dataframe describing distance to soma for all sections, as provided by :fun:get_section_distances_df

    Returns:
        neighboring_bins_dict (dict): a dictionary with bins as keys and a list of adjacent bins as values.
    """
    neighboring_bins = []
    neighbor_map = cell.get_section_adjacancy_map()

    # add adjacent bins from the current section
    for bin_n in range(section_distances_df.iloc[section_id]['n_bins'] - 1):
        # Each consecutive bin within the same section is connected.
        # They are added once here and will be inverted and duplicated later.
        neighboring_bins.append(("{}/{}".format(section_id, bin_n + 1 + 1),
                                 "{}/{}".format(section_id, bin_n + 1)))

    # add adjacent bins from parent section (if there is one)
    for parent_section in neighbor_map[int(section_id)]["parents"]:
        # section_id/1 is connected to some parent section, but at which parent bin?
        parent_bin_distances = get_bin_soma_distances_in_section(
            parent_section,
            section_distances_df)  # all bins in the parent section
        d_section_begin = get_bin_soma_distances_in_section(
            section_id, section_distances_df)[0]
        diff = [
            abs(parent_bin_d - d_section_begin)
            for parent_bin_d in parent_bin_distances
        ]
        closest_parent_bin = I.np.argmin(diff) + 1
        # the section is connected (section_id/1) to its parent at this bin (parent_id/closest_bin)
        neighboring_bins.append(
            ("{}/{}".format(section_id,
                            1), "{}/{}".format(parent_section,
                                               closest_parent_bin)))

        # check if parent section has a 3-way split (or more?)
        # check if parent bin is the last bin in the section
        if int(closest_parent_bin
              ) == section_distances_df.iloc[parent_section]['n_bins']:
            # fetch the children of the parent that are not equal to section_id, i.e. the siblings
            sibling_sections = [
                e for e in neighbor_map[parent_section]["children"]
                if e != section_id
            ]
            # if parent has other children, then these are siblings, i.e. 3-way splits (or more)
            for sibling_section in sibling_sections:
                neighboring_bins.append(
                    ("{}/{}".format(section_id,
                                    1), "{}/{}".format(sibling_section, 1)))

    # add adjacent bins from child sections (if there are any)
    for child in neighbor_map[int(section_id)]["children"]:
        # Each child bin (child_id/1) is connected to the section section_id, but at which bin?
        bin_distances = get_bin_soma_distances_in_section(
            section_id, section_distances_df)
        d_child_section_begin = get_bin_soma_distances_in_section(
            child, section_distances_df)[
                0]  # the bin of the child connected to the current section
        diff = [abs(d - d_child_section_begin) for d in bin_distances]
        closest_child_bin = I.np.argmin(diff) + 1
        # the section has a child (child_id/1) at this bin (section_id/closest_bin)
        neighboring_bins.append(
            ("{}/{}".format(child, 1), "{}/{}".format(section_id,
                                                      closest_child_bin)))

    # convert bin pairs to a dict,
    # and assure mutuality (a is connected to b AND b is connected to a)
    neighboring_bins_dict = {}
    for a, b in neighboring_bins:
        if not a in neighboring_bins_dict:
            neighboring_bins_dict[a] = []
        if not b in neighboring_bins_dict:
            neighboring_bins_dict[b] = []
        neighboring_bins_dict[a].append(b)
        # mutuality
        neighboring_bins_dict[b].append(a)

    return neighboring_bins_dict


def get_neighboring_spatial_bins(cell, bin_id, section_distances_df):
    """Given a bin id, this method returns all the neighboring bins

    Args:
        cell (cell): cell object
        neup (_type_): neuron parameter file
        bin_id (_type_): BIn id of format: section_id/bin_id

    Returns:
        list: list of all ids of bins that neighbor the given bin
    """
    section_id_, bin_id_ = map(int, bin_id.split('/'))
    n_bins = section_distances_df.iloc[int(section_id_)]['n_bins']
    assert 0 < int(
        bin_id_
    ) <= n_bins, "Bin does not exist. Section {} only has {} bins, but you asked for bin #{}".format(
        section_id_, n_bins, bin_id_)
    # check for adjacent sections
    bin_adj = get_bin_adjacency_map_in_section(cell, section_id_,
                                               section_distances_df)
    neighbors = bin_adj[bin_id]
    return neighbors


def augment_synapse_activation_df_with_branch_bin(sa_,
                                                  section_distances_df=None,
                                                  synaptic_weight_dict=None):
    """Given a DataFrame of synaptic activity, this method adds columns giving information on where on the branch this syaptic activity was present.
    This information is represented in a specific format: section_id/bin_within_section.
    For this, the sections have to be split up in spatial bins, which is represented in :@param section_distances_df:

    Args:
        sa_ (pd.DataFrame): The dataframe of synaptic activity
        section_distances_df (pd.DataFrame, optional): DataFrame representing each section's spatial bins and binsizes. Defaults to None.
        synaptic_weight_dict (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    out = []
    for secID, df in sa_.groupby('section_ID'):
        min_ = section_distances_df.loc[secID]['min_']
        max_ = section_distances_df.loc[secID]['max_']
        n_bins = section_distances_df.loc[secID]['n_bins']
        df = df.copy()
        if n_bins == 'Soma':
            df['branch_bin'] = 0
        else:
            df['branch_bin'] = get_bin(df.soma_distance, min_, max_, n_bins)
        out.append(df)
    sa_faster = I.pd.concat(out).sort_values(['synapse_type',
                                              'synapse_ID']).sort_index()
    sa_faster['section/branch_bin'] = sa_faster['section_ID'].astype(
        str) + '/' + sa_faster['branch_bin'].astype('str')
    sa_faster['celltype'] = sa_faster.synapse_type.str.split('_').str[0]
    sa_faster['EI'] = sa_faster['celltype'].isin(I.EXCITATORY).replace(
        True, 'EXC').replace(False, 'INH')
    if synaptic_weight_dict:
        sa_faster['syn_weight'] = sa_faster['synapse_type'].map(syn_weights)
    return sa_faster


@I.dask.delayed
def save_VT_batch(vt_batch,
                  batch_id,
                  outdir=None,
                  fname_template='batch_{}_VT_ALL.npy'):
    fname = fname_template.format(batch_id)
    outpath = I.os.path.join(outdir, fname)
    I.np.save(outpath, vt_batch)


@I.dask.delayed
def save_st_and_ISI(st,
                    batch_id,
                    chunk,
                    min_time,
                    max_time,
                    outdir,
                    suffix='SOMA'):
    current_st = st.loc[chunk]
    ISI_array = compute_ISI_array(current_st, min_time, max_time)
    AP_array = compute_AP_array(current_st, min_time, max_time)
    I.np.save(
        outdir.join('batch_{}_AP_{}.npy').format(batch_id, suffix), AP_array)
    I.np.save(
        outdir.join('batch_{}_ISI_{}.npy').format(batch_id, suffix), ISI_array)


def spike_times_to_onehot(spike_times, min_time=0, max_time=505, time_step=1):
    """This method resembles model_database.analyse.spike_detection.spike_in_interval, but more general.
    Given an array of spike times, this method one-hot encodes them to a list of size (max_time - min_time)//time_step,
    where each time step, a boolean represents if a spike was found in this time_step.
    """
    assert len(I.np.array(spike_times).shape
              ) == 1, "Please provide a 1-dimensional array as spike_times"
    assert all(
        [s >= 0 for s in spike_times]
    ), "Negative time values found. Are you sure you passed spike times as first argument?"
    if spike_times and (max(spike_times) > max_time):
        warnings.warn(
            "Spike times found larger than max_time. These will not be included in the one-hot encoding"
        )
    spike_times = [e for e in spike_times if min_time < e < max_time]
    time_steps = I.np.arange(min_time, max_time, time_step)
    n_time_steps = len(time_steps)
    one_hot = [False] * n_time_steps
    for st in spike_times:
        one_hot[int(st // time_step)] = True
    return one_hot


def compute_ISI_from_st_list(st, min_time=0, max_time=505, time_step=1):
    """Given an array of spike times, this method returns a list of size (:@param max_time: - :@param_min_time:)//:@param time_step:,
    where each time step gives the amount of time since the last spike in ms.
    Do not provide a pd.Series or pd.DataFrame here. For that, use :@function model_database.mdb_initialisers.prepare_ANN_batches.compute_ISI_from_st: instead.

    Args:
        st (array): _description_
        min_time (int, optional): Min time of time window in ms. Defaults to 0.
        max_time (int, optional): Max time of time window in ms. Defaults to 505.
        time_step (int, optional): Timestep in ms. Defaults to 1.

    Returns:
        _type_: _description_
    """
    assert type(st) not in (
        I.pd.DataFrame, I.pd.Series
    ), "This methods is for arrays or lists. When using a pandas Dataframe or Series, use model_database.mdb_initialisers.prepare_ANN_batches.compute_ISI_from_st instead."
    assert type(st) in (
        list, I.np.array), "Please provide a list or array as spike times."
    st = [e for e in st if min_time <= e <= max_time]
    ISI = []
    for timepoint in I.np.arange(min_time, max_time, time_step):
        st_ = [e for e in st if e < timepoint]
        if st_:
            max_spike_time_before_timepoint = max(st_)
            ISI.append(timepoint - max_spike_time_before_timepoint)
        else:
            ISI.append(timepoint)
    return ISI


def compute_ISI_from_st(st, timepoint, fillna=None):
    """Given a pandas DataFrame or pandas Series of spike times :@param st: and a timepoint, this method returns
    the time between :@param timepoint: and the most recent spike in ms.

    Args:
        st (pd.DataFrame | pd.Series): array of spike times
        timepoint (float/int): time point to compute last spike time from
        fillna (int, optional): Fill with NaN until the array has this length. Defaults to None (no NaN filling).

    Returns:
        float/array: The time between :@param timepoint: and the most recent spike in ms.
    """
    '''suggestion: use the temporal window width as fillna'''
    assert fillna is not None
    st = st.copy()
    st[st > timepoint] = I.np.NaN  # set all spike times beyond timepoint to NaN
    max_spike_time_before_timepoint = st.max(axis=1)
    ISI = timepoint - max_spike_time_before_timepoint
    if fillna is not None:
        ISI = ISI.fillna(fillna)
    return ISI


def compute_ISI_array(st, min_time, max_time, fillna=1000, step=1):
    """For each time point inbetween :@param min_time: and :@param max_time: (in steps of :@param step:),
    this method calculates where each element is the time since the last spike in ms.

    Args:
        st (array): array of spike times
        min_time (float/int): minimum time in ms
        max_time (float/int): maximum time in ms
        fillna (int, optional): Fill with NaN until the array has this length. Defaults to 1000.
        step (int/float, optional): Size of timestep in ms. Defaults to 1.

    Returns:
        array: An array of length (:@param max_time: - :@param min_time:)//:@param step:,
        where each element has as a value the time since the last spike in ms.
    """
    ISI = []
    for t in I.np.arange(min_time, max_time, step):
        ISI.append(compute_ISI_from_st(st, t, fillna).to_numpy().reshape(-1, 1))
    return I.np.concatenate(ISI, axis=1)


def compute_AP_array(st, min_time, max_time, fillna=1000, step=1):
    """Given a collection of spike times of a single trial, this method returns an array of length (max_time - min_time)//step,
    where, on each timestep of size :@param step:, a boolean represents if a spike is found in this interval.

    TODO: what is fillna?

    Args:
        st (array): Array of spike times
        min_time (float/int): Min time in ms
        max_time (float/int): Max time in ms
        fillna (int, optional, unused): Fill with NaN until the array has this length. Defaults to 1000. Added for congruence to compute_ISI_array?
        step (int, optional): Size of timesteps to consider. Defaults to 1 ms

    Returns:
        array: Array where each element is a boolean representing if an AP was present during this timestep.
    """
    AP = []
    for t in range(min_time, max_time, step):
        AP.append(
            I.spike_in_interval(st, t, t + step).to_numpy().reshape(-1, 1))
    return I.np.concatenate(AP, axis=1)


def load_syn_weights(m, client):
    folder_ = m['parameterfiles_network_folder']
    fnames = m['parameterfiles_network_folder'].listdir()
    fnames.pop(fnames.index('Loader.pickle'))
    param_df = m['parameterfiles']
    syn_weights_out = {}

    @I.dask.delayed
    def _helper(fname, stis):
        stis = I.cloudpickle.loads(stis)
        syn_weights = {}
        netp = I.scp.build_parameters(folder_.join(fname))
        for celltype in netp.network:
            if celltype.split('_')[0] in I.EXCITATORY:
                syn_weights[celltype] = netp.network[
                    celltype].synapses.receptors.glutamate_syn.weight[0]
            else:
                syn_weights[celltype] = netp.network[
                    celltype].synapses.receptors.gaba_syn.weight
        return {sti: syn_weights for sti in stis}

    stis_by_netp = {
        k: list(v.index) for k, v in param_df.groupby('hash_network')
    }
    delayeds = []
    for f in fnames:
        d = _helper(f, I.cloudpickle.dumps(stis_by_netp[f]))
        delayeds.append(d)

    result = client.gather(client.compute(delayeds))

    syn_weights_out = {}
    for r in result:
        syn_weights_out.update(r)

    return syn_weights_out


def temporal_binning_augmented_sa(sa_augmented,
                                  min_time,
                                  max_time,
                                  bin_size,
                                  use_weights=False):
    activation_times = sa_augmented[[
        c for c in sa_augmented.columns if I.utils.convertible_to_int(c)
    ]].values
    if use_weights:
        weights = (activation_times * 0 +
                   1) * sa_augmented.syn_weight.values.reshape(-1, 1)
        weights = weights[~I.np.isnan(activation_times)]
    activation_times = activation_times[~I.np.isnan(activation_times)]
    bin_borders = I.np.arange(min_time, max_time + bin_size, bin_size)
    if use_weights:
        return bin_borders, I.np.histogram(activation_times,
                                           bin_borders,
                                           weights=weights)[0]
    else:
        return bin_borders, I.np.histogram(activation_times, bin_borders)[0]


def get_synapse_activation_array_weighted(sa_,
                                          selected_stis=None,
                                          spatial_bin_names=None,
                                          min_time=0,
                                          max_time=600,
                                          bin_size=1,
                                          use_weights=False):
    fun = I.partial(temporal_binning_augmented_sa,
                    min_time=min_time,
                    max_time=max_time,
                    bin_size=1,
                    use_weights=use_weights)
    # sa_augmented = augment_synapse_activation_df_with_branch_bin(sa_, section_distances_df = section_distances_df)
    synapse_activation_binned = sa_.groupby(
        [sa_.index, 'EI', 'section/branch_bin']).apply(lambda x: fun(x)[1])
    synapse_activation_binned_dict = synapse_activation_binned.to_dict()
    n_time_bins = len(list(synapse_activation_binned_dict.values())[0])
    level_0_values = selected_stis
    level_1_values = ['EXC', 'INH']
    level_2_values = spatial_bin_names
    array = I.np.zeros((len(level_0_values), len(level_1_values),
                        len(level_2_values), n_time_bins))
    for i0, l0 in enumerate(level_0_values):
        for i1, l1 in enumerate(level_1_values):
            for i2, l2 in enumerate(level_2_values):
                if not (l0, l1, l2) in synapse_activation_binned_dict.keys():
                    continue
                arr = synapse_activation_binned_dict[(l0, l1, l2)]
                array[i0, i1, i2, :] = arr
    return array


@I.dask.delayed
def save_SA_batch(sa_,
                  selected_stis,
                  batch_id,
                  outdir=None,
                  section_distances_df=None,
                  spatial_bin_names=None,
                  min_time=0,
                  max_time=600,
                  bin_size=1,
                  synaptic_weight_dict=None):
    syn_weights = None
    if syn_weights:
        raise NotImplementedError()
        fname = 'batch_{}_SYNAPSE_ACTIVATION_WEIGHTED.npy'.format(batch_id)
    else:
        fname = 'batch_{}_SYNAPSE_ACTIVATION.npy'.format(batch_id)
    outpath = I.os.path.join(outdir, fname)
    sa_ = augment_synapse_activation_df_with_branch_bin(sa_,
                                                        section_distances_df,
                                                        syn_weights)
    array = get_synapse_activation_array_weighted(
        sa_,
        selected_stis,
        spatial_bin_names=spatial_bin_names,
        min_time=min_time,
        max_time=max_time,
        bin_size=bin_size,
        use_weights=syn_weights is not None)
    I.np.save(outpath, array)


# code to get the maximum depolarization per ms of a voltage traces dataframe
def get_time_groups(vt_pandas):
    time_groups = []
    for lv in range(len(vt_pandas.columns)):
        time_groups.append(lv // 40)
    return time_groups


def get_max_per_ms_on_pandas_dataframe(vt_pandas):
    time_groups = get_time_groups(vt_pandas)
    vt_max = vt_pandas.groupby(time_groups,
                               axis=1).apply(lambda x: x.max(axis=1))
    return vt_max


def get_max_depolarization_per_ms(vt_dask):
    meta_ = {t: 'float64' for t in get_time_groups(vt_dask.head())}
    vt_max_dask = vt_dask.map_partitions(get_max_per_ms_on_pandas_dataframe,
                                         meta=meta_)
    return vt_max_dask


# initializer class
class Init:

    def __init__(self,
                 mdb,
                 mdb_target=None,
                 min_time=None,
                 max_time=None,
                 bin_size=1,
                 batchsize=500,
                 client=None,
                 sti_selection=None,
                 sti_selection_name=None,
                 persist=False,
                 synaptic_weight=False,
                 dend_ap_suffix='_-30.0'):

        if sti_selection is not None:
            assert sti_selection_name is not None
        if mdb_target is None:
            mdb_target = mdb

        self.mdb = mdb
        self.mdb_target = mdb_target
        self.min_time = min_time
        self.max_time = max_time
        self.bin_size = bin_size
        self.batchsize = batchsize
        self.client = client
        self.sti_selection = sti_selection
        self.sti_selection_name = sti_selection_name
        self.persist = persist
        self.dend_ap_suffix = dend_ap_suffix

        # get selected trials - if none specified, select all
        if sti_selection is not None:
            sti_selection = list(sti_selection)
        else:
            st = mdb['spike_times']
            sti_selection = list(st.index)

        self.chunks = I.utils.chunkIt(sti_selection,
                                      len(sti_selection) / batchsize)

        # create directory to save batches
        if sti_selection_name:
            x = '{}_{}_{}_'.format(min_time, max_time,
                                   bin_size) + sti_selection_name
        else:
            x = '{}_{}_{}_'.format(min_time, max_time, bin_size) + 'all'
        self.outdir = mdb_target.create_managed_folder(
            ('ANN_batches', x, 'EI__section/branch_bin'), raise_=False)

        # setup spatial bins
        self._setup_spatial_bins()

        self._setup_synaptic_weights()

    def _setup_spatial_bins(self):
        self.neuron_param_file = get_neuron_param_file(self.mdb)
        self.section_distances_df = get_section_distances_df(
            self.neuron_param_file)
        self.spatial_bin_names = get_spatial_bin_names(
            self.section_distances_df)

    def _setup_synaptic_weights(self):
        self.synaptic_weight_dict = None
        # if synaptic_weight:
        #     synaptic_weight_dict = load_syn_weights(m,self.client)
        #     synaptic_weight_dict = self.client.persist(synaptic_weight_dict)
        # else:
        #     synaptic_weight_dict = None

    def init_all(self,
                 init_soma_vt=True,
                 init_dend_vt=True,
                 init_soma_AP_ISI=True,
                 init_dend_AP_ISI=True,
                 init_max_soma_vt=True,
                 init_max_dend_vt=True,
                 init_synapse_activation=True,
                 init_synapse_activation_weighted=True):
        pass

    def _get_distal_recording_site(self):
        keys = self.mdb['dendritic_recordings'].keys()
        dist_rec_site = sorted(keys, key=lambda x: float(x.split('_')[-1]))[1]
        return dist_rec_site

    def _save_vt(self, vt, fname_template=None):
        delayeds = []
        for batch_id, chunk in enumerate(self.chunks):
            selected_indices = chunk
            d = save_VT_batch(vt.loc[selected_indices],
                              batch_id,
                              outdir=self.outdir,
                              fname_template=fname_template)
            delayeds.append(d)
        return delayeds

    def init_soma_vt(self):
        vt = self.mdb['voltage_traces'].iloc[:, ::40].iloc[:,
                                                           self.min_time:self.
                                                           max_time]
        return self._save_vt(vt, fname_template='batch_{}_VT_SOMA.npy')

    def init_dend_vt(self):
        dist_rec_site = self._get_distal_recording_site()
        vt_dend = self.mdb['dendritic_recordings'][dist_rec_site]
        vt_dend = vt_dend.iloc[:, ::40].iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt_dend, fname_template='batch_{}_VT_DEND.npy')

    def _save_AP_ISI(self, st, suffix=None):
        delayeds = []
        # st = self.client.scatter(st)
        for batch_id, chunk in enumerate(self.chunks):
            d = save_st_and_ISI(st,
                                batch_id,
                                chunk,
                                self.min_time,
                                self.max_time,
                                self.outdir,
                                suffix=suffix)
            delayeds.append(d)
        return delayeds

    def init_soma_AP_ISI(self):
        st = self.client.scatter(self.mdb['spike_times'])
        return self._save_AP_ISI(st, suffix='SOMA')

    def init_dend_AP_ISI(self):
        dist_rec_site = self._get_distal_recording_site()
        st = self.client.scatter(
            self.mdb['dendritic_spike_times'][dist_rec_site +
                                              self.dend_ap_suffix])
        return self._save_AP_ISI(st, suffix='DEND')

    def init_max_soma_vt(self):
        vt = self.mdb['voltage_traces']
        vt = get_max_depolarization_per_ms(vt)
        vt = vt.iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt, fname_template='batch_{}_VT_SOMA_MAX.npy')

    def init_max_dend_vt(self):
        dist_rec_site = self._get_distal_recording_site()
        vt_dend = self.mdb['dendritic_recordings'][dist_rec_site]
        vt_dend = get_max_depolarization_per_ms(vt_dend)
        vt_dend = vt_dend.iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt_dend, fname_template='batch_{}_VT_DEND_MAX.npy')

    def init_synapse_activation(self, synaptic_weight=False):
        sa = self.mdb['synapse_activation']
        if self.persist:
            sa = self.client.persist(sa)

        delayeds = []
        print('Create delayed objects for synapse_activations')

        for batch_id, chunk in enumerate(self.chunks):
            selected_indices = chunk
            d = save_SA_batch(sa.loc[chunk],
                              chunk,
                              batch_id,
                              outdir=self.outdir,
                              section_distances_df=self.section_distances_df,
                              spatial_bin_names=self.spatial_bin_names,
                              min_time=self.min_time,
                              max_time=self.max_time,
                              bin_size=self.bin_size,
                              synaptic_weight_dict=self.synaptic_weight_dict)
            delayeds.append(d)
        return delayeds

    def init_synapse_activation_weighted(self):
        delayeds = []
        return delayeds


def init(
    mdb,
    mdb_target=None,
    min_time=None,
    max_time=None,
    bin_size=1,
    batchsize=500,
    client=None,
    sti_selection=None,
    sti_selection_name=None,
    persist=False,
    synaptic_weight=False,
    dend_ap_suffix='_-30.0',
):
    '''persist: whether the synapse activation dataframe should be loaded into memory 
                on the dask cluster. Speeds up the process if it fits in memory, otherwise leads to crash'''
    if mdb_target is None:
        mdb_target = mdb

    if sti_selection is not None:
        assert sti_selection_name is not None

    sa = mdb['synapse_activation']
    st = mdb['spike_times']
    if sti_selection is not None:
        sti_selection = list(sti_selection)
    else:
        sti_selection = list(st.index)

    chunks = I.utils.chunkIt(sti_selection, len(sti_selection) / batchsize)

    neuron_param_file = get_neuron_param_file(mdb)
    section_distances_df = get_section_distances_df(neuron_param_file)
    spatial_bin_names = get_spatial_bin_names(section_distances_df)
    if sti_selection_name:
        x = '{}_{}_{}_'.format(min_time, max_time,
                               bin_size) + sti_selection_name
    else:
        x = '{}_{}_{}_'.format(min_time, max_time, bin_size) + 'all'
    outdir = mdb_target.create_managed_folder(
        ('ANN_batches', x, 'EI__section/branch_bin'), raise_=False)

    if persist:
        sa = client.persist(sa)

    if synaptic_weight:
        synaptic_weight_dict = load_syn_weights(m, client)
        synaptic_weight_dict = client.persist(synaptic_weight_dict)
    else:
        synaptic_weight_dict = None

    delayeds = []
    print('Create delayed objects for synapse_activations')

    for batch_id, chunk in enumerate(chunks):
        selected_indices = chunk
        d = save_SA_batch(sa.loc[chunk],
                          chunk,
                          batch_id,
                          outdir=outdir,
                          section_distances_df=section_distances_df,
                          spatial_bin_names=spatial_bin_names,
                          min_time=min_time,
                          max_time=max_time,
                          bin_size=bin_size,
                          synaptic_weight_dict=synaptic_weight_dict)
        delayeds.append(d)

    print('Create delayed objects for somatic voltage traces')
    # somatic voltage traces
    vt = mdb['voltage_traces'].iloc[:, ::40].iloc[:, min_time:max_time]
    for batch_id, chunk in enumerate(chunks):
        selected_indices = chunk
        d = save_VT_batch(vt.loc[selected_indices], batch_id, outdir=outdir)
        delayeds.append(d)

    print('Create delayed objects for somatic APs and ISIs')
    # somatic AP and ISI
    st = client.scatter(mdb['spike_times'])
    for batch_id, chunk in enumerate(chunks):
        d = save_st_and_ISI(st, batch_id, chunk, min_time, max_time, outdir)
        delayeds.append(d)

    # dendritic voltage traces
    print('Create delayed objects for dendritic voltage traces')
    keys = mdb['dendritic_recordings'].keys()
    dist_rec_site = sorted(keys, key=lambda x: float(x.split('_')[-1]))[1]

    vt_dend = mdb['dendritic_recordings'][dist_rec_site]
    vt_dend = vt_dend.iloc[:, ::40].iloc[:, min_time:max_time]
    for batch_id, chunk in enumerate(chunks):
        selected_indices = chunk
        d = save_VT_batch(vt_dend.loc[selected_indices],
                          batch_id,
                          outdir=outdir,
                          fname_template='batch_{}_VT_DEND_ALL.npy')
        delayeds.append(d)

    # dend AP and ISI
    print('Create delayed objects for dendriticAPs and ISIs')
    st = client.scatter(mdb['dendritic_spike_times'][dist_rec_site +
                                                     dend_ap_suffix])
    for batch_id, chunk in enumerate(chunks):
        d = save_st_and_ISI(st,
                            batch_id,
                            chunk,
                            min_time,
                            max_time,
                            outdir,
                            suffix='DEND')
        delayeds.append(d)

    return delayeds


def run_delayeds_incrementally(client, delayeds):
    import time
    futures = []
    ncores = sum(client.ncores().values())
    for ds in I.utils.chunkIt(delayeds, len(delayeds) / ncores):
        f = client.compute(ds)
        futures.extend(f)
        while True:
            time.sleep(1)
            futures = [f for f in futures if not f.status == 'finished']
            for f in futures:
                if f.status == 'error':
                    f.result()
                    # raise RuntimeError()
            if len(futures) < ncores * 2:
                break
    I.distributed.wait(futures)
    return futures
"""Parse a simrun-initialized database for ANN batch preparation.

This module provides various methods to bin synapse actications, morphologies, and voltage traces.
This binned data can be used as input data for training an artificial neural network (ANN).
"""

import warnings, os, dask, distributed, cloudpickle
import numpy as np
from sumatra.parameters import NTParameterSet
from single_cell_parser import create_cell, build_parameters
from single_cell_parser.analyze import synanalysis
import pandas as pd
from data_base.utils import silence_stdout, convertible_to_int, chunkIt
from data_base.analyze.spike_detection import spike_in_interval
from functools import partial
from config.cell_types import EXCITATORY, INHIBITORY


def get_binsize(length, binsize_goal=50):
    """Calculate the bin size and number of bins closest to the desired bin size goal.

    Args:
        length (float): The length of a dendritic branch to bin.
        binsize_goal (float, optional): The desired bin size. Defaults to 50.

    Returns:
        tuple: A tuple containing the bin size (float) and the number of bins (int) that result in binning closest to the binsize goal.
    """
    n_bins = length / float(binsize_goal)
    n_bins_lower = np.floor(n_bins)
    n_bins_lower = np.max([n_bins_lower, 1])
    n_bins_upper = np.ceil(n_bins)
    binsize_lower = length / n_bins_lower
    binsize_upper = length / n_bins_upper
    if np.abs(binsize_goal - binsize_lower) < np.abs(binsize_goal - binsize_upper):
        return binsize_lower, int(n_bins_lower)
    else:
        return binsize_upper, int(n_bins_upper)


def get_bin(value, bin_min, bin_max, n_bins, tolerance=0.1):
    """Find the bin index of a given value.
    
    Args:
        value (float): The value to find the bin for.
        bin_min (float): Start of the first bin.
        bin_max (float): End of the last bin.
        n_bins (int): The number of bins.
        tolerance (float, optional): The tolerance for the outer ibn edges (for rounding errors). Defaults to 0.1.
        
    Returns:
        int: The bin the value belongs to.    
    """
    bin_size = (bin_max - bin_min) / n_bins
    bins = [bin_min + n * bin_size for n in range(n_bins + 1)]
    bins[0] = bins[0] - tolerance
    bins[-1] = bins[-1] + tolerance
    if (np.max(value) >= bins[-1]) or (np.min(value) <= bins[0]):
        raise RuntimeError('value outside of bin_min and bin_max!')
    return np.digitize(value, bins)


def get_neuron_param_file(db):
    """Get the path to the :ref:`cell_parameters_format` file from a simrun-initialized database.
    
    This method assumes the database has been simrun-initialized with
    :meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` and contains the key ``parameterfiles_cell_folder``.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The database object.
            
    Returns:
        str: The path to the neuron parameter file.    
    """
    folder = db['parameterfiles_cell_folder']
    f = [f for f in folder.listdir() if not f.endswith('.pickle')]  #+.keys()
    if not len(f) == 1:
        warnings.warn(
            'found more than one neuron parameter file in the database. Make sure the database does not contain simulations with more than one morphology!'
        )
    return folder.join(f[0])


def get_section_distances_df(neuron_param_file, silent=True):
    """Bin the morphology of a neuron from a :ref:`cell_parameters_format` file.
    
    This method reads the neuron parameter file and bins the morphology of the neuron into spatial bins.
    The amount of bins is inferred by :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.get_binsize`.
    
    Args:
        neuron_param_file (str): The path to the neuron parameter file.
        silent (bool, optional): If True, suppresses output. Defaults to True.
        
    Returns:
        pd.DataFrame: A dataframe containing the amount of bins, the bin size, and the min and max distance to the soma for each section.
    
    Example::
    
        >>> section_distances_df = get_section_distances_df(neuron_param_file)
            min_         max_       n_bins  binsize
        0     0.000000     0.000000   Soma     Soma
        1     0.000000    35.032795      1  35.0328
        2    35.032795   131.179980      2  48.0736
        3    35.032795    41.505115      1  6.47232
        4    41.505115   252.996874      4  52.8729
        ..         ...          ...    ...      ...
        165  95.220299   161.215314      1   65.995
        166  95.220299   158.805975      1  63.5857
        167   0.000000    20.000000      1       20
        168  20.000000    50.000000      1       30
        169  50.000000  1049.999969     20       50
    """
    neup = NTParameterSet(neuron_param_file)
    if silent:
        with silence_stdout:
            cell = create_cell(neup.neuron)
    else:
        cell = create_cell(neup.neuron)
    sections_min_dist = [
        synanalysis.compute_distance_to_soma(sec, 0)
        for sec in cell.sections
    ]
    sections_max_dist = [
        synanalysis.compute_distance_to_soma(sec, 1)
        for sec in cell.sections
    ]
    binsize = [
        get_binsize(s_ma - s_mi)[0] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi, s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    n_bins = [
        get_binsize(s_ma - s_mi)[1] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi,s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    bin_borders = [
        np.linspace(s_mi, s_ma, num=n_bins) if
        not isinstance(n_bins, str) else 'Soma' for s_mi, s_ma, n_bins in zip(
            sections_min_dist, sections_max_dist, n_bins)
    ]
    section_distances_df = pd.DataFrame({
        'min_': sections_min_dist,
        'max_': sections_max_dist,
        'n_bins': n_bins,
        'binsize': binsize
    })
    return section_distances_df


def get_spatial_bin_names(section_distances_df):
    """Get the bin names from a dataframe describing the distance to soma of all sections.
    
    Given a dataframe describing the distance to soma of all sections, as provided by 
    :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.get_section_distances_df`,
    this method returns the names for all the spatial bins of the format ``section_id/bin_id``. 
    E.g.: ``5/2`` denotes the second bin of section 5.

    Args:
        section_distances_df (pd.DataFrame): 
            The dataframe describing distance to soma for all sections.

    Returns:
        list: A list containing the bin ids in string format.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.get_section_distances_df`
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
    """Get the distance to the soma for all bins in this section.

    Args:
        section_id (int): Id of the neuron section
        section_distances_df (pd.DataFrame): The dataframe describing distance to soma for all sections, as provided by :@function get_section_distances_df:

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
    """Create an adjacency map with bin-specific resolution for a given section.
    
    Consecutive bins in the same section are trivially connected.
    This method also fetches other sections connected to the given section id, and checks at which bins they connect.
    Sections are defined by the neuron simulation, but bins are ad-hoc defined by data preparation for the ANN.

    This method exploits the tree structure of a neuron, i.e. a child section is always connected at the beginning.
    This means that all child sections are connected to their parent section at bin number 1
    The goal is then to figure out at which bin in the parent section the child is connected to.
    Eeach section always has one or more bins.
    
    Args:
        cell (Cell): the Cell object
        section_id (int): index of the neuron section
        section_distances_df (pd.DataFrame): the dataframe describing distance to soma for all sections, as provided by :meth:get_section_distances_df

    Returns:
        dict: a dictionary with bins as keys and a list of adjacent bins as values.
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
        closest_parent_bin = np.argmin(diff) + 1
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
        closest_child_bin = np.argmin(diff) + 1
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
    """Get all the neighboring bins from a :paramref:`bin_id`.

    Args:
        cell (cell): cell object
        bin_id (_type_): Bin id of format: ``"section_id/bin_id"``
        section_distances_df (pd.DataFrame): DataFrame representing each section's spatial bins and binsizes.

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
    bin_adj = get_bin_adjacency_map_in_section(
        cell, 
        section_id_,
        section_distances_df)
    neighbors = bin_adj[bin_id]
    return neighbors


def augment_synapse_activation_df_with_branch_bin(
    sa_,
    section_distances_df=None,
    synaptic_weight_dict=None,
    excitatory_celltypes=None
    ):
    """Augment a :ref:`syn_activation_format` dataframe with bin information.
    
    The :ref:`syn_activation_format` dataframe contains info of where along a dendrite some synapse impinged.
    This method infers to which bin that location belongs and adds it as an additional column.
    This information is represented in a specific format: section_id/bin_within_section.

    Args:
        sa_ (pd.DataFrame): 
            The dataframe of synaptic activity
        section_distances_df (pd.DataFrame): 
            DataFrame representing each section's spatial bins and binsizes. Defaults to None.
        synaptic_weight_dict (dict, optional): 
            A dictionary mapping the synapse type to a weight. 
            Defaults to None, in which case it is not added as an additional column.

    Returns:
        pd.DataFrame: The augmented dataframe with the additional columns 'section/branch_bin', 'celltype', 'EI', and 'syn_weight' (if synaptic_weight_dict is provided).
    """
    if excitatory_celltypes is None:
        excitatory_celltypes = EXCITATORY
    
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
    sa_faster = pd.concat(out).sort_values(['synapse_type','synapse_ID']).sort_index()
    sa_faster['section/branch_bin'] = sa_faster['section_ID'].astype(
        str) + '/' + sa_faster['branch_bin'].astype('str')
    sa_faster['celltype'] = sa_faster.synapse_type.str.split('_').str[0]
    sa_faster['EI'] = sa_faster['celltype'].isin(excitatory_celltypes).replace(True, 'EXC').replace(False, 'INH')
    if synaptic_weight_dict:
        sa_faster['syn_weight'] = sa_faster['synapse_type'].map(syn_weights)
    return sa_faster


@dask.delayed
def save_VT_batch(
    vt_batch,
    batch_id,
    outdir=None,
    fname_template=None):
    """Save a batch of voltage traces to a file.
    
    Convenience method wrapped as a dask delayed object.
    
    :skip-doc:
    """
    if fname_template is None:
        fname_template = 'batch_{}_VT_ALL.npy'
    fname = fname_template.format(batch_id)
    outpath = os.path.join(outdir, fname)
    np.save(outpath, vt_batch)


@dask.delayed
def save_st_and_ISI(
    st,
    batch_id,
    chunk,
    min_time,
    max_time,
    outdir,
    suffix='SOMA'):
    """Save spike times and inter-spike intervals to a file.
    
    Convenience method wrapped as a dask delayed object.
    
    :skip-doc:
    """
    current_st = st.loc[chunk]
    ISI_array = compute_ISI_array(current_st, min_time, max_time)
    AP_array = compute_AP_array(current_st, min_time, max_time)
    np.save(
        outdir.join('batch_{}_AP_{}.npy').format(batch_id, suffix), AP_array)
    np.save(
        outdir.join('batch_{}_ISI_{}.npy').format(batch_id, suffix), ISI_array)


def spike_times_to_onehot(spike_times, min_time=0, max_time=505, time_step=1):
    """One-hot encode spike times to a binned time vector.
    
    The time vector is created from :paramref:`min_time`, :paramref:`max_time` and :paramref:`time_step`
    and is of length ``(max_time - min_time)//time_step``.
    
    If a spike occured in a certain time interval, the corresponding entry in the one-hot vector is set to ``True``.
    
    Args:
        spike_times (array): Array of spike times
        min_time (int, optional): Min time in ms. Defaults to 0.
        max_time (int, optional): Max time in ms. Defaults to 505.
        time_step (int, optional): Timestep in ms. Defaults to 1.
        
    Returns:
        list: A list of booleans, where each element represents a time step and is True if a spike occured in this interval.
    """
    assert len(np.array(spike_times).shape
              ) == 1, "Please provide a 1-dimensional array as spike_times"
    assert all(
        [s >= 0 for s in spike_times]
    ), "Negative time values found. Are you sure you passed spike times as first argument?"
    if spike_times and (max(spike_times) > max_time):
        warnings.warn(
            "Spike times found larger than max_time. These will not be included in the one-hot encoding"
        )
    spike_times = [e for e in spike_times if min_time < e < max_time]
    time_steps = np.arange(min_time, max_time, time_step)
    n_time_steps = len(time_steps)
    one_hot = [False] * n_time_steps
    for st in spike_times:
        one_hot[int(st // time_step)] = True
    return one_hot


def compute_ISI_from_st_list(st, min_time=0, max_time=505, time_step=1):
    """Construct a time-binned list of inter-spike intervals from a list of spike times.
    
    Given a list of spike times, this method returns a list of size ``(max_time - min_time)//time_step``,
    where each time step gives the amount of time since the last spike in ms.

    Args:
        st (list): List of spike times
        min_time (int, optional): Min time of time window in ms. Defaults to 0.
        max_time (int, optional): Max time of time window in ms. Defaults to 505.
        time_step (int, optional): Timestep in ms. Defaults to 1.

    Returns:
        list: A list of inter-spike intervals in ms.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_from_st` for the pandas version.
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_array` for the array version.
    """
    assert type(st) not in (
        pd.DataFrame, pd.Series
    ), "This methods is for arrays or lists. When using a pandas Dataframe or Series, use model_database.db_initialisers.prepare_ANN_batches.compute_ISI_from_st instead."
    assert type(st) in (
        list, np.array), "Please provide a list or array as spike times."
    st = [e for e in st if min_time <= e <= max_time]
    ISI = []
    for timepoint in np.arange(min_time, max_time, time_step):
        st_ = [e for e in st if e < timepoint]
        if st_:
            max_spike_time_before_timepoint = max(st_)
            ISI.append(timepoint - max_spike_time_before_timepoint)
        else:
            ISI.append(timepoint)
    return ISI


def compute_ISI_from_st(st, timepoint, fillna=None):
    """Calculate the time since the last spike in ms for each element in a spike time pd.Series or pd.DataFrame.
    
    Given a pandas Series or DataFrame of spike times, this method returns a list of size ``(max_time - min_time)//time_step``,
    where each time step gives the amount of time since the last spike in ms.
    
    Args:
        st (pd.DataFrame | pd.Series): pandas DataFrame or Series of spike times
        timepoint (int): Time point in ms
        fillna (int, optional): Fill with NaN until the array has this length. Defaults to None.
        
    Returns:
        pd.Series: A pandas Series of inter-spike intervals in ms.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_from_st_list` for the list version.
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_array` for the array version.
    """
    '''suggestion: use the temporal window width as fillna'''
    assert fillna is not None
    st = st.copy()
    st[st > timepoint] = np.NaN  # set all spike times beyond timepoint to NaN
    max_spike_time_before_timepoint = st.max(axis=1)
    ISI = timepoint - max_spike_time_before_timepoint
    if fillna is not None:
        ISI = ISI.fillna(fillna)
    return ISI


def compute_ISI_array(st, min_time, max_time, fillna=1000, step=1):
    """Calculate the time since the last spike in ms for each element in a spike time Array.
    
    Given an array of spike times, this method returns a list of size ``(max_time - min_time)//time_step``,
    where each time step gives the amount of time since the last spike in ms.
    
    Args:
        st (pd.DataFrame | pd.Series): pandas DataFrame or Series of spike times
        timepoint (int): Time point in ms
        fillna (int, optional): Fill with NaN until the array has this length. Defaults to None.
        
    Returns:
        pd.Series: A pandas Series of inter-spike intervals in ms.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_from_st_list` for the list version.
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.compute_ISI_from_st` for the pandas version.
    """
    ISI = []
    for t in np.arange(min_time, max_time, step):
        ISI.append(compute_ISI_from_st(st, t, fillna).to_numpy().reshape(-1, 1))
    return np.concatenate(ISI, axis=1)


def compute_AP_array(st, min_time, max_time, fillna=1000, step=1):
    """One-hot encode spike times to a binned time vector.
    
    Given a collection of spike times of a single trial, this method returns an array of length ``(max_time - min_time)//step``,
    where a boolean represents if a spike is found in this interval.

    Args:
        st (array): Array of spike times
        min_time (float/int): Min time in ms
        max_time (float/int): Max time in ms
        step (int, optional): Size of timesteps to consider. Defaults to 1 ms

    Returns:
        array: Array where each element is a boolean representing if an AP was present during this timestep.
    """
    AP = []
    for t in range(min_time, max_time, step):
        AP.append(
            spike_in_interval(st, t, t + step).to_numpy().reshape(-1, 1))
    return np.concatenate(AP, axis=1)


def load_syn_weights(db, client, excitatory_celltypes=None):
    """Load synapse weights from a simrun-initialized database
    
    Fetches the :ref:`network_parameters_format` file from the
    ``parameterfiles_network_folder`` key in the database and extracts the synaptic weights.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database object.
        client (:py:class:`~dask.distributed.client.Client`):
            The dask client object.
            
    Returns:
        dict: A dictionary mapping the synapse type to a weight.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` for the database initialization.
    """
    if excitatory_celltypes is None:
        excitatory_celltypes = EXCITATORY
    folder_ = db['parameterfiles_network_folder']
    fnames = db['parameterfiles_network_folder'].listdir()
    fnames.pop(fnames.index('Loader.pickle'))
    param_df = db['parameterfiles']
    syn_weights_out = {}

    @dask.delayed
    def _helper(fname, stis):
        stis = cloudpickle.loads(stis)
        syn_weights = {}
        netp = build_parameters(folder_.join(fname))
        for celltype in netp.network:
            if celltype.split('_')[0] in excitatory_celltypes:
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
        d = _helper(f, cloudpickle.dumps(stis_by_netp[f]))
        delayeds.append(d)

    result = client.gather(client.compute(delayeds))

    syn_weights_out = {}
    for r in result:
        syn_weights_out.update(r)

    return syn_weights_out


def temporal_binning_augmented_sa(
    sa_augmented,
    min_time,
    max_time,
    bin_size,
    use_weights=False):
    """Bin synapse activation times into temporal bins.
    
    Args:
        sa_augmented (pd.DataFrame): Augmented synapse activation dataframe
        min_time (int): Min time in ms
        max_time (int): Max time in ms
        bin_size (int): Size of the time bins
        use_weights (bool, optional): 
            If True, weigh the synapse activation times with the corresponding synapse weights. 
            Defaults to False.
            
    Returns:
        tuple: A tuple containing the bin borders and the histogram of synapse activation times.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.prepare_ANN_batches.augment_synapse_activation_df_with_branch_bin`
    """
    activation_times = sa_augmented[[
        c for c in sa_augmented.columns if convertible_to_int(c)
    ]].values
    if use_weights:
        weights = (activation_times * 0 +
                   1) * sa_augmented.syn_weight.values.reshape(-1, 1)
        weights = weights[~np.isnan(activation_times)]
    activation_times = activation_times[~np.isnan(activation_times)]
    bin_borders = np.arange(min_time, max_time + bin_size, bin_size)
    if use_weights:
        return bin_borders, np.histogram(
            activation_times,
            bin_borders,
            weights=weights)[0]
    else:
        return bin_borders, np.histogram(
            activation_times, 
            bin_borders)[0]


def get_synapse_activation_array_weighted(
    sa_,
    selected_stis=None,
    spatial_bin_names=None,
    min_time=0,
    max_time=600,
    bin_size=1,
    use_weights=False):
    """Create a 4D array of synapse activation times.
    
    Create a 4D array of synaptic activation, where the axes are:
    
    - :paramref:`selected_stis`
    - EXC/INH
    - spatial bins
    - time bins
    
    The array is of shape ``(len(selected_stis), 2, len(spatial_bin_names), (max_time - min_time)//bin_size)``.
    
    Args:
        sa_ (pd.DataFrame): Augmented synapse activation dataframe
        selected_stis (list, optional): List of selected spike times. Defaults to None.
        spatial_bin_names (list, optional): List of spatial bin names. Defaults to None.
        min_time (int, optional): Min time in ms. Defaults to 0.
        max_time (int, optional): Max time in ms. Defaults to 600.
        use_weights (bool, optional): If True, weigh the synapse activation times with the corresponding synapse weights. Defaults to False.
        
    Returns:
        array: A 4D array of synapse activation times.
    """
    fun = partial(temporal_binning_augmented_sa,
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
    array = np.zeros((len(level_0_values), len(level_1_values),
                        len(level_2_values), n_time_bins))
    for i0, l0 in enumerate(level_0_values):
        for i1, l1 in enumerate(level_1_values):
            for i2, l2 in enumerate(level_2_values):
                if not (l0, l1, l2) in synapse_activation_binned_dict.keys():
                    continue
                arr = synapse_activation_binned_dict[(l0, l1, l2)]
                array[i0, i1, i2, :] = arr
    return array


@dask.delayed
def save_SA_batch(
    sa_,
    selected_stis,
    batch_id,
    outdir=None,
    section_distances_df=None,
    spatial_bin_names=None,
    min_time=0,
    max_time=600,
    bin_size=1,
    synaptic_weight_dict=None):
    """Save a batch of synapse activation times to a file.
    
    Args:
        sa_ (pd.DataFrame): Augmented synapse activation dataframe
        selected_stis (list): List of selected spike times
        batch_id (int): Batch id
        outdir (str): Output directory
        section_distances_df (pd.DataFrame, optional): DataFrame representing each section's spatial bins and binsizes. Defaults to None.
        spatial_bin_names (list, optional): List of spatial bin names. Defaults to None.
        min_time (int, optional): Min time in ms. Defaults to 0.
        max_time (int, optional): Max time in ms. Defaults to 600.
        bin_size (int, optional): Size of the time bins. Defaults to 1.
        
    Returns:
        dask.delayed: A dask delayed object. When computed, saves the synapse activation times to :paramref:`outdir`/batch_:paramref:`batch_id`_SYNAPSE_ACTIVATION.npy.
    """
    syn_weights = None
    if syn_weights:
        raise NotImplementedError()
        fname = 'batch_{}_SYNAPSE_ACTIVATION_WEIGHTED.npy'.format(batch_id)
    else:
        fname = 'batch_{}_SYNAPSE_ACTIVATION.npy'.format(batch_id)
    outpath = os.path.join(outdir, fname)
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
    np.save(outpath, array)


# code to get the maximum depolarization per ms of a voltage traces dataframe
def get_time_groups(vt_pandas):
    """Get the time groups for binning voltage traces.
    
    Group the voltage trace in 1 ms bins, assuming a time interval of 0.025 ms.
    
    Args:
        vt_pandas (pd.DataFrame): Voltage traces dataframe.
        
    Returns:
        list: A list of time groups.
        
    Attention:
        This method assumes a time interval of 0.025 ms.
    """
    time_groups = []
    for lv in range(len(vt_pandas.columns)):
        time_groups.append(lv // 40)  # 1 ms / 0.025 ms = 40
    return time_groups


def get_max_per_ms_on_pandas_dataframe(vt_pandas):
    """Subsample a voltage trace pandas dataframe to 1ms bins based on the maximum depolarization.
    
    Args:
        vt_pandas (pd.DataFrame): Voltage traces dataframe
        
    Returns:
        pd.Series: A pandas Series of the maximum depolarization per ms.
        
    Attention:
        This method assumes a voltage trace time interval of 0.025 ms.
    """
    time_groups = get_time_groups(vt_pandas)
    vt_max = vt_pandas.groupby(time_groups, axis=1).apply(lambda x: x.max(axis=1))
    return vt_max


def get_max_depolarization_per_ms(vt_dask):
    """Subsample a voltage trace dask dataframe to 1ms bins based on the maximum depolarization.
    
    Args:
        vt_dask (dask.dataframe): Voltage traces dask dataframe
        
    Returns:
        dask.dataframe: A dask dataframe of the maximum depolarization per ms.
        
    Attention:
        This method assumes a voltage trace time interval of 0.025 ms.
    """
    meta_ = {t: 'float64' for t in get_time_groups(vt_dask.head())}
    vt_max_dask = vt_dask.map_partitions(get_max_per_ms_on_pandas_dataframe, meta=meta_)
    return vt_max_dask


# initializer class
class Init:
    """Initializer class for preparing ANN batches.
    
    Parse a simrun-initialized database to binned voltage traces ready for ANN training.
    
    Attention:
        Still in development. See github issue #75.
    
    :skip-doc:    
    """
    def __init__(
        self,
        db,
        db_target=None,
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
        if db_target is None:
            db_target = db

        self.db = db
        self.db_target = db_target
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
            st = db['spike_times']
            sti_selection = list(st.index)

        self.chunks = chunkIt(sti_selection,
                                      len(sti_selection) / batchsize)

        # create directory to save batches
        if sti_selection_name:
            x = '{}_{}_{}_'.format(min_time, max_time,
                                   bin_size) + sti_selection_name
        else:
            x = '{}_{}_{}_'.format(min_time, max_time, bin_size) + 'all'
        self.outdir = db_target.create_managed_folder(
            ('ANN_batches', x, 'EI__section/branch_bin'), raise_=False)

        # setup spatial bins
        self._setup_spatial_bins()

        self._setup_synaptic_weights()

    def _setup_spatial_bins(self):
        self.neuron_param_file = get_neuron_param_file(self.db)
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

    def init_all(
        self,
        init_soma_vt=True,
        init_dend_vt=True,
        init_soma_AP_ISI=True,
        init_dend_AP_ISI=True,
        init_max_soma_vt=True,
        init_max_dend_vt=True,
        init_synapse_activation=True,
        init_synapse_activation_weighted=True):
        """:skip-doc:"""
        pass

    def _get_distal_recording_site(self):
        ":skip-doc:"
        keys = self.db['dendritic_recordings'].keys()
        dist_rec_site = sorted(keys, key=lambda x: float(x.split('_')[-1]))[1]
        return dist_rec_site

    def _save_vt(self, vt, fname_template=None):
        """:skip-doc:"""
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
        """:skip-doc:"""
        vt = self.db['voltage_traces'].iloc[:, ::40].iloc[:,self.min_time:self.max_time]
        return self._save_vt(vt, fname_template='batch_{}_VT_SOMA.npy')

    def init_dend_vt(self):
        """:skip-doc:"""
        dist_rec_site = self._get_distal_recording_site()
        vt_dend = self.db['dendritic_recordings'][dist_rec_site]
        vt_dend = vt_dend.iloc[:, ::40].iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt_dend, fname_template='batch_{}_VT_DEND.npy')

    def _save_AP_ISI(self, st, suffix=None):
        """:skip-doc:"""
        delayeds = []
        # st = self.client.scatter(st)
        for batch_id, chunk in enumerate(self.chunks):
            d = save_st_and_ISI(
                st,
                batch_id,
                chunk,
                self.min_time,
                self.max_time,
                self.outdir,
                suffix=suffix)
            delayeds.append(d)
        return delayeds

    def init_soma_AP_ISI(self):
        """:skip-doc:"""
        st = self.client.scatter(self.db['spike_times'])
        return self._save_AP_ISI(st, suffix='SOMA')

    def init_dend_AP_ISI(self):
        """:skip-doc:"""
        dist_rec_site = self._get_distal_recording_site()
        st = self.client.scatter(
            self.db['dendritic_spike_times'][dist_rec_site +
                                              self.dend_ap_suffix])
        return self._save_AP_ISI(st, suffix='DEND')

    def init_max_soma_vt(self):
        """:skip-doc:"""
        vt = self.db['voltage_traces']
        vt = get_max_depolarization_per_ms(vt)
        vt = vt.iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt, fname_template='batch_{}_VT_SOMA_MAX.npy')

    def init_max_dend_vt(self):
        """:skip-doc:"""
        dist_rec_site = self._get_distal_recording_site()
        vt_dend = self.db['dendritic_recordings'][dist_rec_site]
        vt_dend = get_max_depolarization_per_ms(vt_dend)
        vt_dend = vt_dend.iloc[:, self.min_time:self.max_time]
        return self._save_vt(vt_dend, fname_template='batch_{}_VT_DEND_MAX.npy')

    def init_synapse_activation(self, synaptic_weight=False):
        """:skip-doc:"""
        sa = self.db['synapse_activation']
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
        """:skip-doc:"""
        delayeds = []
        return delayeds


def init(
    db,
    db_target=None,
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
    '''Construct delayeds to parse a simrun-initialized database to binned voltage traces ready for ANN training.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The simrun-initialized database
        db_target (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The target database. Defaults to None, which initializes the ANN batches in the same database as :paramref:`db`.
    
    Attention:
        Still in development. See issue #75.
    
    persist: whether the synapse activation dataframe should be loaded into memory 
                on the dask cluster. Speeds up the process if it fits in memory, otherwise leads to crash
    :skip-doc:
    '''
    if db_target is None:
        db_target = db

    if sti_selection is not None:
        assert sti_selection_name is not None

    sa = db['synapse_activation']
    st = db['spike_times']
    if sti_selection is not None:
        sti_selection = list(sti_selection)
    else:
        sti_selection = list(st.index)

    chunks = chunkIt(sti_selection, len(sti_selection) / batchsize)

    neuron_param_file = get_neuron_param_file(db)
    section_distances_df = get_section_distances_df(neuron_param_file)
    spatial_bin_names = get_spatial_bin_names(section_distances_df)
    if sti_selection_name:
        x = '{}_{}_{}_'.format(min_time, max_time,
                               bin_size) + sti_selection_name
    else:
        x = '{}_{}_{}_'.format(min_time, max_time, bin_size) + 'all'
    outdir = db_target.create_managed_folder(
        ('ANN_batches', x, 'EI__section/branch_bin'), raise_=False)

    if persist:
        sa = client.persist(sa)

    if synaptic_weight:
        synaptic_weight_dict = load_syn_weights(db, client)
        synaptic_weight_dict = client.persist(synaptic_weight_dict)
    else:
        synaptic_weight_dict = None

    delayeds = []
    print('Create delayed objects for synapse_activations')

    for batch_id, chunk in enumerate(chunks):
        selected_indices = chunk
        d = save_SA_batch(
            sa.loc[chunk],
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
    vt = db['voltage_traces'].iloc[:, ::40].iloc[:, min_time:max_time]
    for batch_id, chunk in enumerate(chunks):
        selected_indices = chunk
        d = save_VT_batch(vt.loc[selected_indices], batch_id, outdir=outdir)
        delayeds.append(d)

    print('Create delayed objects for somatic APs and ISIs')
    # somatic AP and ISI
    st = client.scatter(db['spike_times'])
    for batch_id, chunk in enumerate(chunks):
        d = save_st_and_ISI(st, batch_id, chunk, min_time, max_time, outdir)
        delayeds.append(d)

    # dendritic voltage traces
    print('Create delayed objects for dendritic voltage traces')
    keys = db['dendritic_recordings'].keys()
    dist_rec_site = sorted(keys, key=lambda x: float(x.split('_')[-1]))[1]

    vt_dend = db['dendritic_recordings'][dist_rec_site]
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
    st = client.scatter(db['dendritic_spike_times'][dist_rec_site +
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
    """Convenience method to run a list of dask delayed objects incrementally.
    
    Run dask delayed objects incrementally in chunks.
    
    Args:
        client (:py:class:`~dask.distributed.client.Client`):
            The dask client object.
        delayeds (list): List of dask delayed objects.
        
    Returns:
        list: List of futures.
    """
    import time
    futures = []
    ncores = sum(client.ncores().values())
    for ds in chunkIt(delayeds, len(delayeds) / ncores):
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
    distributed.wait(futures)
    return futures
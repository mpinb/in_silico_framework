import dask
import numpy as np
import pandas as pd
import single_cell_parser.analyze as sca
import single_cell_parser as scp
from simrun2.rerun_mdb import synapse_activation_df_to_roberts_synapse_activation
import time
from model_data_base.mdb_initializers.prepare_ANN_batches import compute_AP_array, compute_ISI_array, spike_times_to_onehot, compute_ISI_from_st_list
from model_data_base.mdb_initializers.prepare_ANN_batches import get_synapse_activation_array_weighted, augment_synapse_activation_df_with_branch_bin, get_spatial_bin_names
from single_cell_parser.analyze.membrane_potential_analysis import simple_spike_detection
from project_specific_ipynb_code.hot_zone import get_main_bifurcation_section

from model_data_base.mdb_initializers.prepare_ANN_batches import get_binsize

import logging

log = logging.getLogger("ISF").getChild(__name__)


def get_section_distances_df_from_cell(cell, spatial_binsize_goal=50):
    """Given a Cell object, produce the section_distances_dataframe, i.e. a DataFrame with the following information:
    - Section indices as index
    - amount of bins per section
    - Size of the bins in this section
    - Min and max distance from soma

    Args:
        cell (Cell): The Cell object
        binsize_goal (int | float): The desired size of the spatial binning. Defaults to 50 microns.

    Returns:
        pd.DataFrame: The section distances dataframe describing size and location of the section, amount of bins and bin sizes
    """
    sections_min_dist = [
        sca.synanalysis.compute_distance_to_soma(sec, 0)
        for sec in cell.sections
    ]
    sections_max_dist = [
        sca.synanalysis.compute_distance_to_soma(sec, 1)
        for sec in cell.sections
    ]
    binsize = [
        get_binsize(length=s_ma - s_mi, binsize_goal=spatial_binsize_goal)[0] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi,
                 s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    n_bins = [
        get_binsize(length=s_ma - s_mi, binsize_goal=spatial_binsize_goal)[1] if
        (cell.sections[lv].label != 'Soma') else 'Soma'
        for lv, (s_mi,
                 s_ma) in enumerate(zip(sections_min_dist, sections_max_dist))
    ]
    # bin_borders = [I.np.linspace(s_mi, s_ma, num = n_bins) if not isinstance(n_bins, str) else 'Soma' for s_mi, s_ma, n_bins in
    #               zip(sections_min_dist, sections_max_dist, n_bins)]  # unused
    section_distances_df = pd.DataFrame({
        'min_': sections_min_dist,
        'max_': sections_max_dist,
        'n_bins': n_bins,
        'binsize': binsize
    })
    return section_distances_df


def bin_points_and_voltage(cell,
                           section_distances_df=None,
                           spatial_binsize_goal=50):
    """Given a cell object, this method calculates the binned spatial points and their corresponding voltage traces.

    Args:
        cell (Cell): The cell object

    Returns:
        (pd.Dataframe, np.array): the cell morphology as a pandas dataframe, and a nested numpy array of voltage traces, where axis0 is the spatial bin, and axis1 is time
    """
    section_distances_df = get_section_distances_df_from_cell(
        cell, spatial_binsize_goal=spatial_binsize_goal
    ) if section_distances_df is None else section_distances_df
    points = []
    vms = []
    for sec_n, sec in enumerate(cell.sections):
        if sec.label in ['AIS', 'Myelin']:
            continue
        pts = get_point_per_bin(sec, sec_n, section_distances_df)
        binned_vms = bin_voltages_in_section(
            section_distances_df=section_distances_df,
            section_id=sec_n,
            cell=cell)
        for i, pt in enumerate(pts):
            # Points within the same section
            x, y, z = pt
            d = sec.diamList[i]
            points.append([x, y, z, d, sec_n])
            vms.append(binned_vms[i])

    morphology = pd.DataFrame(points,
                              columns=['x', 'y', 'z', 'diameter', 'section'])
    return morphology, np.array(vms)


def get_synapse_activation_array_from_cell(cell,
                                           section_distances_df,
                                           min_time=None,
                                           max_time=None,
                                           bin_size=None,
                                           syn_weights=None):
    if not bin_size == 1:
        raise NotImplementedError()

    sa_ = cell.get_synapse_activation_dataframe()  ## added by arco
    sa_augmented = augment_synapse_activation_df_with_branch_bin(
        sa_, section_distances_df=section_distances_df)
    selected_stis = [
        0
    ]  # default index if synapse activation df is retrived by cell.get_synapse_activation_dataframe()
    #min_time = 0
    #max_time = 445+60
    #bin_size = 1
    spatial_bin_names = get_spatial_bin_names(section_distances_df)
    arr = get_synapse_activation_array_weighted(
        sa_augmented,
        selected_stis,
        spatial_bin_names=spatial_bin_names,
        min_time=min_time,
        max_time=max_time,
        bin_size=bin_size,
        use_weights=syn_weights is not None)
    sections_to_keep = [
        i for i, sec in enumerate(cell.sections)
        if sec.label in ['Soma', 'Dendrite', 'ApicalDendrite']
    ]
    spatial_bin_indices_to_keep = [
        i for i, sb in enumerate(spatial_bin_names)
        if int(sb.split('/')[0]) in sections_to_keep
    ]
    return arr[:, :, spatial_bin_indices_to_keep, min_time:max_time]


def assert_same_stepsize(t_array):
    dts = np.ediff1d(t_array)
    np.testing.assert_allclose(dts,
                               np.mean(dts),
                               err_msg="Stepsizes are not the same!")


def get_voltage_array_from_cell(cell,
                                section_distances_df,
                                min_time,
                                max_time,
                                temporal_resolution=1):
    """_summary_

    Args:
        cell (Cell): _description_
        section_distances_df (pd.DataFrame): _description_
        min_time (float/int): _description_
        max_time (float/int): _description_
        temporal_resolution (int, optional): Required resolution in ms. Defaults to 1 ms.
        spatial_binsize_goal (int | float): Desired size of the spatial bins in micrometer. Defaults to 50µm.

    Returns:
        np.array: 2D array
    """
    assert_same_stepsize(cell.t)
    dt = cell.t[1] - cell.t[0]  # most often 0.025
    every_other_index = int(temporal_resolution / dt)
    if max_time > cell.t[-1]:
        log.warning(
            "Specified max_time of {0} is larger than simulation time of {1}. Voltage traces can only be calcualted until {1} ms"
            .format(max_time, cell.t[-1]))
    # assert step size of 0.025
    # TODO: redundant if we test for equal stepsize and specify resolution. Test if this can be omitted.
    np.testing.assert_almost_equal(cell.t[1], 0.025)
    np.testing.assert_almost_equal(cell.t[40], 1)

    _, vms = bin_points_and_voltage(cell, section_distances_df)
    return vms[:, ::every_other_index][:, min_time:max_time]


def get_point_per_bin(section, section_id, section_distances_df):
    """Given a Cell.section object, this method returns one point per spatial bin in this section.
    Useful for plotting.

    Args:
        section (Cell.section): The Cell section
        section_id (int): Index of the section
        section_distances_df (pd.DataFrame): Dataframe describing the amount of spatial bins per section.

    Returns:
        _type_: _description_
    """
    all_points_in_section = section.pts
    n_bins = section_distances_df.iloc[section_id]['n_bins']
    n_bins = 1 if n_bins == "Soma" else n_bins
    jump = len(all_points_in_section) // n_bins
    pts_per_bin = [all_points_in_section[jump * i] for i in range(n_bins)]
    return pts_per_bin


def get_segments_in_section(cell, section_id):
    """Given a section number, this method returns the x value of each segment in this section"""
    xs = [segment.x for segment in cell.sections[section_id]]
    return xs


# if x coordinate of segment is between bin limits, it belongs to that bin


def get_bin_limits(section_id, section_distances_df):
    n_bins = section_distances_df.iloc[section_id]["n_bins"]
    n_bins = 1 if n_bins == 'Soma' else n_bins
    bin_limits = [i / n_bins for i in range(n_bins)]
    bin_limits.append(1)
    return bin_limits


def segments_to_bins(cell, section_id,
                     section_distances_df):  ## arco: added cell argument
    bins = []
    bin_limits = get_bin_limits(section_id, section_distances_df)
    segments = get_segments_in_section(cell, section_id)
    for segment in segments:
        for bin in range(len(bin_limits) - 1):
            if bin_limits[bin] < segment <= bin_limits[bin + 1]:
                bins.append(bin)
    return bins


def bin_voltages_in_section(cell, section_id,
                            section_distances_df):  ## arco: added cell argument
    binned_segments = segments_to_bins(
        cell, section_id, section_distances_df)  ## arco: added cell argument
    n_bins = binned_segments[-1] + 1
    section = cell.sections[section_id]
    binned_voltages = [None] * n_bins
    voltages = section.recVList
    n_time_points = len(cell.t)
    for bin in range(n_bins):
        segment_idxs = np.where([e == bin for e in binned_segments])[0]
        segment_voltage_traces = [voltages[i] for i in segment_idxs]
        max_voltages_in_bin = []
        for t in range(n_time_points):
            max_voltage_in_bin = max([
                segment_voltage_trace[t]
                for segment_voltage_trace in segment_voltage_traces
            ])
            max_voltages_in_bin.append(max_voltage_in_bin)
        binned_voltages[bin] = max_voltages_in_bin
    return np.array(binned_voltages)


def _evoked_activity(mdb,
                     stis,
                     outdir,
                     neuron_param_modify_functions=[],
                     network_param_modify_functions=[],
                     synapse_activation_modify_functions=[],
                     additional_network_params=[],
                     parameterfiles=None,
                     neuron_folder=None,
                     network_folder=None,
                     sa=None,
                     temporal_resolution=1,
                     min_time=0,
                     max_time=445 + 60):
    """This method runs simulations defined by the given arguments.
    For each entry in stis, a trial is run.
    The following data is then converted to a batch format with coarse resolution, optimised for ANN training:
    - Voltage traces at each spatial bin

    Args:
        mdb (_type_): _description_
        stis (_type_): _description_
        outdir (_type_): _description_
        neuron_param_modify_functions (list, optional): _description_. Defaults to [].
        network_param_modify_functions (list, optional): _description_. Defaults to [].
        synapse_activation_modify_functions (list, optional): _description_. Defaults to [].
        additional_network_params (list, optional): _description_. Defaults to [].
        parameterfiles (_type_, optional): _description_. Defaults to None.
        neuron_folder (_type_, optional): _description_. Defaults to None.
        network_folder (_type_, optional): _description_. Defaults to None.
        sa (_type_, optional): _description_. Defaults to None.
        temporal_resolution (int, optional): _description_. Defaults to 1.
        min_time (int, optional): _description_. Defaults to 0.
        max_time (_type_, optional): _description_. Defaults to 445+60.

    Raises:
        NotImplementedError: _description_
        NotImplementedError: _description_
    """
    log.info('saving to ', outdir)
    import neuron
    h = neuron.h
    sti_bases = [s[:s.rfind('/')] for s in stis]
    if not len(set(sti_bases)) == 1:
        raise NotImplementedError
    sti_base = sti_bases[0]
    sa = sa.content
    log.info('start loading synapse activations')
    sa = sa.loc[stis].compute(get=dask.get)
    log.info('done loading synapse activations')
    sa = {s: g for s, g in sa.groupby(sa.index)}

    #outdir_absolute = os.path.join(outdir, sti_base)
    #if not os.path.exists(outdir_absolute):
    #   os.makedirs(outdir_absolute)

    parameterfiles = parameterfiles.loc[stis]
    parameterfiles = parameterfiles.drop_duplicates()
    if not len(parameterfiles) == 1:
        raise NotImplementedError()

    neuron_name = parameterfiles.iloc[0].hash_neuron
    neuron_param = scp.build_parameters(neuron_folder.join(neuron_name))
    network_name = parameterfiles.iloc[0].hash_network
    network_param = scp.build_parameters(network_folder.join(network_name))
    additional_network_params = [
        scp.build_parameters(p) for p in additional_network_params
    ]
    for fun in network_param_modify_functions:
        network_param = fun(network_param)
    for fun in neuron_param_modify_functions:
        neuron_param = fun(neuron_param)

    scp.load_NMODL_parameters(neuron_param)
    scp.load_NMODL_parameters(network_param)
    cell = scp.create_cell(neuron_param.neuron, scaleFunc=None)

    bifur_sec = get_main_bifurcation_section(cell)
    #vTraces = []
    #tTraces = []
    #recordingSiteFiles = neuron_param.sim.recordingSites
    #recSiteManagers = []
    #for recFile in recordingSiteFiles:
    #    recSiteManagers.append(sca.RecordingSiteManager(recFile, cell))

    section_distances_df = get_section_distances_df_from_cell(cell)

    if max_time is not None:
        neuron_param.sim.tStop = max_time

    v_soma_list = []
    v_dend_list = []
    sa_arr_list = []
    VT = []
    for lv, sti in enumerate(stis):
        # Loop over stimulus trials.
        start_time = time.time()

        #-------------- Setup network --------------#
        ## Fetch synaptic input
        ## sti_number = int(sti[sti.rfind('/')+1:])  # unused
        syn_df = sa[sti]

        for fun in synapse_activation_modify_functions:  # adapt synaptic activation if specified
            syn_df = fun(syn_df)

        syn = synapse_activation_df_to_roberts_synapse_activation(syn_df)

        ## Calculate evoked activity in cell from synaptic activation.
        evokedNW = scp.NetworkMapper(cell, network_param.network,
                                     neuron_param.sim)
        evokedNW.reconnect_saved_synapses(syn)
        additional_evokedNWs = [
            scp.NetworkMapper(cell, p.network, neuron_param.sim)
            for p in additional_network_params
        ]
        for additional_evokedNW in additional_evokedNWs:
            additional_evokedNW.create_saved_network2()
        stopTime = time.time()
        setupdt = stopTime - start_time
        log.info('Network setup time: {:.2f} s'.format(setupdt))

        # synTypes = list(cell.synapses.keys())  # unused
        # synTypes.sort()  # unused

        #-------------- Run simulation --------------#
        log.info('Testing evoked response properties run {:d} of {:d}'.format(
            lv + 1, len(stis)))
        tVec = h.Vector()
        tVec.record(h._ref_t)
        start_time = time.time()
        scp.init_neuron_run(neuron_param.sim,
                            vardt=False)  #trigger the actual simulation
        stopTime = time.time()
        simdt = stopTime - start_time
        log.info('NEURON runtime: {:.2f} s'.format(simdt))

        # vmSoma = np.array(cell.soma.recVList[0])  # unused
        t = np.array(tVec)
        cell.t = t  # Extract time vector

        #-------------- Extract and save relevant data --------------#
        # - Voltage traces at each spatial bin
        # - Synaptic activation for this trial
        sa_arr = get_synapse_activation_array_from_cell(
            cell,
            section_distances_df,
            min_time=min_time,
            max_time=max_time,
            bin_size=temporal_resolution,
            syn_weights=None)
        vts = get_voltage_array_from_cell(
            cell,
            section_distances_df,
            min_time=min_time,
            max_time=max_time,
            temporal_resolution=temporal_resolution)
        v_dend = np.array(bifur_sec.recVList[-1])
        v_soma = np.array(cell.soma.recVList[0])
        # vts_dend.append(v_dist)
        # vts_soma.append(v_soma)
        v_soma_list.append(v_soma)
        v_dend_list.append(v_dend)
        sa_arr_list.append(sa_arr)
        VT.append(vts)
        #-------------- Re-initialise everything for next trial --------------#
        cell.re_init_cell()
        evokedNW.re_init_network()
        for additional_evokedNW in additional_evokedNWs:
            additional_evokedNW.re_init_network()

        log.info('-------------------------------')

    # WARNING: this is the dt of the cell that was last run. TODO: is this always the same dt in this loop?
    #-------------- Transform data to ANN batch format --------------#
    v_soma_df = pd.DataFrame(v_soma_list).T
    v_dend_df = pd.DataFrame(v_dend_list).T
    # collect spike times for all trials
    time_points = cell.t
    soma_AP_times = [
        simple_spike_detection(time_points,
                               v_soma_df[trial],
                               mode='regular',
                               threshold=0)
        for trial in range(v_soma_df.shape[1])
    ]
    dend_AP_times = [
        simple_spike_detection(time_points,
                               v_dend_df[trial],
                               mode='regular',
                               threshold=-30)
        for trial in range(v_dend_df.shape[1])
    ]
    # Transform to ISI lists and one-hot encoded AP
    AP_DEND = [
        spike_times_to_onehot(spike_times, min_time, max_time,
                              temporal_resolution)
        for spike_times in dend_AP_times
    ]
    ISI_DEND = [
        compute_ISI_from_st_list(spike_times, min_time, max_time,
                                 temporal_resolution)
        for spike_times in dend_AP_times
    ]
    AP_SOMA = [
        spike_times_to_onehot(spike_times, min_time, max_time,
                              temporal_resolution)
        for spike_times in soma_AP_times
    ]
    ISI_SOMA = [
        compute_ISI_from_st_list(spike_times, min_time, max_time,
                                 temporal_resolution)
        for spike_times in soma_AP_times
    ]
    SA = np.concatenate(sa_arr_list, axis=0)
    VT = VT
    #-------------- Save as .npy format --------------#
    np.savez(outdir_absolute,
             AP_DEND=I.np.array(AP_DEND, dtype='float16'),
             ISI_DEND=I.np.array(ISI_DEND, dtype='float16'),
             AP_SOMA=I.np.array(AP_SOMA, dtype='float16'),
             ISI_SOMA=I.np.array(ISI_SOMA, dtype='float16'),
             SA=I.np.array(SA, dtype='float16'),
             VT=I.np.array(VT, dtype='float16'))
    # np.save(os.path.join(outdir_absolute, "AP_DEND.npy"), AP_DEND) # arco: replace outdir with outdir_absolute
    # np.save(os.path.join(outdir_absolute, "ISI_DEND.npy"), ISI_DEND)
    # np.save(os.path.join(outdir_absolute, "AP_SOMA.npy"), AP_SOMA)
    # np.save(os.path.join(outdir_absolute, "ISI_SOMA.npy"), ISI_SOMA)
    # np.save(os.path.join(outdir_absolute, "SA.npy"), SA)
    # np.save(os.path.join(outdir_absolute, "VT.npy"), VT)


class Opaque:

    def __init__(self, content):
        self.content = content


from Interface import silence_stdout
from biophysics_fitting.utils import execute_in_child_process


def rerun_mdb(mdb,
              outdir,
              neuron_param_modify_functions=[],
              network_param_modify_functions=[],
              synapse_activation_modify_functions=[],
              stis=None,
              silent=False,
              additional_network_params=[],
              child_process=False,
              temporal_resolution=1,
              min_time=0,
              max_time=445 + 60):
    '''
    TODO: do we still need bin size? isn't this the same as temporal resolution?
    mdb: model data base initialized with I.mdb_init_simrun_general to be resimulated
    outdir: location where simulation files are supposed to be stored
    tStop: end of simulation
    neuron_param_modify_functions: list of functions which take a neuron param file and may return it changed
    network_param_modify_functions: list of functions which take a network param file and may return it changed
    synapse_activation_modify_functions: list of function, which take a synapse activation dataframe and may return it changed
    stis: sim_trial_indices which are to be resimulated. If None, the whole database is going to be resimulated.
    silent: suppress output to stdout
    child_process: run simulation in child process. This can help if dask workers time out during the simulation.'''
    parameterfiles = mdb['parameterfiles']
    neuron_folder = mdb['parameterfiles_cell_folder']
    network_folder = mdb['parameterfiles_network_folder']
    sa = mdb['synapse_activation']
    # without the opaque object, dask tries to load in the entire dataframe before passing it to _evoked_activity
    sa = Opaque(sa)
    if stis is not None:
        parameterfiles = parameterfiles.loc[stis]
    sim_trial_index_array = parameterfiles.groupby('path_neuron').apply(
        lambda x: list(x.index)).values
    delayeds = []

    myfun = _evoked_activity

    if silent:
        myfun = silence_stdout(myfun)

    if child_process:
        myfun = execute_in_child_process(myfun)

    myfun = dask.delayed(myfun)
    log.info('outdir is', outdir)
    for stis in sim_trial_index_array:
        d = myfun(mdb,
                  stis,
                  outdir,
                  neuron_param_modify_functions=neuron_param_modify_functions,
                  network_param_modify_functions=network_param_modify_functions,
                  synapse_activation_modify_functions=
                  synapse_activation_modify_functions,
                  parameterfiles=parameterfiles.loc[stis],
                  neuron_folder=neuron_folder,
                  network_folder=network_folder,
                  sa=sa,
                  additional_network_params=additional_network_params,
                  temporal_resolution=temporal_resolution,
                  min_time=min_time,
                  max_time=max_time)
        delayeds.append(d)
    return delayeds

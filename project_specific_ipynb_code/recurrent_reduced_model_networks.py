import Interface as I
from itertools import chain
import scipy as sp


def find_notebook_containing_model(mdb, model):
    for notebook in mdb.keys():
        if model in mdb[notebook]['biophysical_models'].keys():
            return notebook


def get_CDK_from_model(model):
    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    return find_notebook_containing_model(parameter_mdb, model).split('_')[4]


def syncon_by_CDK_and_position(mdb, CDK, position):
    '''
    mdb: ModelDataBase
    CDK: str
        e.g. "CDK89"
    position: str
        e.g. x_0_y_0, x_150_y_-150'''

    foldername = [
        f for f in I.os.listdir(mdb[CDK]['network_embedding'])
        if f.startswith(position) and not f.endswith('.hoc')
    ][0]
    folderpath = mdb[CDK]['network_embedding'].join(foldername)

    synfile = [f for f in I.os.listdir(folderpath) if f.endswith('.syn')][0]
    confile = [f for f in I.os.listdir(folderpath) if f.endswith('.con')][0]
    ncellsfile = 'NumberOfConnectedCells.csv'

    return folderpath.join(synfile), folderpath.join(confile), folderpath.join(
        ncellsfile)


########################
# functions to get and modify synapse activations
########################
@I.dask.delayed
def get_synapse_activation_dataframe(cell_param,
                                     network_param,
                                     sim_param,
                                     max_spikes=20,
                                     sim_trial_index=0):
    '''Returns a delayed synapse activation dataframe for one postsynaptic cell. Several of these can be combined into one dask dataframe using I.dask.dataframe.from_delayed(). 
    cell_param, network_param, sim_param: pickled dictionaries of parametersets
    max_spikes: int, optional
        preset value for maximum number of spikes at any given synapse, default 20
    sim_trial_index: int, optional
        will be used as the index for the dataframe, default 0'''
    with I.silence_stdout:

        cell_param = I.cloudpickle.loads(cell_param)
        network_param = I.cloudpickle.loads(network_param)
        sim_param = I.cloudpickle.loads(sim_param)

        cell_param = I.scp.NTParameterSet(cell_param)
        network_param = I.scp.NTParameterSet(network_param)
        sim_param = I.scp.NTParameterSet(sim_param)

        cell = I.scp.create_cell(cell_param.neuron)
        network_mapper = I.scp.network.NetworkMapper(cell,
                                                     network_param,
                                                     simParam=sim_param)
        network_mapper.create_saved_network2()

    cell = network_mapper.postCell
    syn_types = []
    syn_IDs = []
    spike_times = []
    sec_IDs = []
    pt_IDs = []
    dend_labels = []
    soma_distances = []
    for celltype in cell.synapses.keys():
        for syn in range(len(cell.synapses[celltype])):
            if cell.synapses[celltype][syn].is_active():
                ## get list of active synapses' types and IDs
                syn_types.append(celltype)
                syn_IDs.append(syn)
                ## get spike times
                st_temp = [
                    cell.synapses[celltype][syn].releaseSite.spikeTimes[:]
                ]
                st_temp.append([I.np.nan] * (max_spikes - len(st_temp[0])))
                st_temp = list(chain.from_iterable(st_temp))
                spike_times.append(st_temp)
                ## get info about synapse location
                secID = cell.synapses[celltype][syn].secID
                sec_IDs.append(secID)
                pt_IDs.append(cell.synapses[celltype][syn].ptID)
                dend_labels.append(cell.sections[secID].label)
                ## calculate synapse somadistances
                sec = cell.sections[secID]
                soma_distances.append(
                    I.sca.synanalysis.compute_syn_distance(
                        cell, cell.synapses[celltype][syn]))

    ## write synapse activation df
    columns = [
        'synapse_type', 'synapse_ID', 'soma_distance', 'section_ID',
        'section_pt_ID', 'dendrite_label'
    ]
    sa_pd = dict(
        zip(columns,
            [syn_types, syn_IDs, soma_distances, sec_IDs, pt_IDs, dend_labels]))
    sa_pd = I.pd.DataFrame(sa_pd)[columns]

    st_df = I.pd.DataFrame(columns=range(max_spikes),
                           data=I.np.asarray(spike_times))

    sa_pd = I.pd.concat([sa_pd, st_df], axis=1)

    sa_pd.index = [sim_trial_index] * len(sa_pd)

    assert sa_pd.iloc[:, -1].notnull().sum(
    ) == 0  # make sure no spikes got cut off by max_spikes by ensuring the last column is empty

    return sa_pd


def generate_spatiotemporally_binned_inputs(model,
                                            n_cells,
                                            timebins,
                                            out_mdb,
                                            client=None,
                                            evoked=False):
    assert client is not None
    best_positions = {
        '2019-01-11_9330_AgsniKR_1_51_552': 'x_-50_y_0',
        '2019-01-26_12752_uvEXhHc_1_47_301': 'x_0_y_-50',
        '2019-01-26_12752_uvEXhHc_4_113_409': 'x_-100_y_-50',
        '2019-02-11_9215_0Bx2rPx_5_171_390': 'x_-50_y_-50',
        '2019-02-22_35839_TG4IHEp_1_1_0': 'x_100_y_-100',
        '2019-02-23_7062_mvUlY5e_1_551_65': 'x_0_y_-50',
        '2019-03-05_20241_SZ3iYOZ_707527054352652_109_665': 'x_0_y_-100',
        '2019-05-10_15406_qBeBpVo_7712997831240842_108_441': 'x_-50_y_-100'
    }

    CDK = get_CDK_from_model(model)
    pos = best_positions[model]

    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    pmdb = parameter_mdb[find_notebook_containing_model(parameter_mdb, model)]

    cell_param = pmdb['biophysical_models'][model]['cell_param'].join(
        'cell.param')
    cell_param = I.scp.build_parameters(cell_param)
    cell_param.neuron.filename = I.os.path.join(
        sim_mdb[CDK]['network_embedding'], pos + '.hoc')

    sim_param = I.scp.NTParameterSet({'tStop': timebins})

    network_param = sim_mdb[CDK]['network_params']['C2'].join(pos + '.param')
    network_param = I.scp.build_parameters(network_param)

    synfile, confile, csv = syncon_by_CDK_and_position(sim_mdb, CDK, pos)

    for celltype in network_param.network.keys():
        network_param.network[celltype]['synapses'][
            'distributionFile'] = synfile
        network_param.network[celltype]['synapses']['connectionFile'] = confile
        if not evoked:
            try:
                network_param.network[celltype]['celltype']['pointcell'][
                    'offset'] = timebins + 100  #remove evoked
            except TypeError:  #not all celltypes have pointcell
                pass
    network_param = network_param.network

    cell_param_dict = I.cloudpickle.dumps(cell_param.as_dict())
    network_param_dict = I.cloudpickle.dumps(network_param.as_dict())
    sim_param_dict = I.cloudpickle.dumps(sim_param.as_dict())

    ds = []
    for i in range(n_cells):
        ds.append(get_synapse_activation_dataframe(cell_param_dict, network_param_dict, sim_param_dict,\
                                                   max_spikes = 200, sim_trial_index = i))

    meta_ = ds[0].compute(get=I.dask.get).head(1)
    ddf = I.dask.dataframe.from_delayed(ds, meta=meta_)

    out_mdb.create_sub_mdb('complete')
    out_mdb['complete']['synapse_activation'] = ddf
    I.mdb_init_synapse_activation_binning.init(out_mdb['complete'], groupby = ['EI', 'binned_somadist'], \
                                               maxtime = timebins, get = client.get)
    # remove L5 activations
    out_mdb.create_sub_mdb('no_L5C2')
    sa_df = out_mdb['complete']['synapse_activation'].compute()
    sa_df_no_L5 = sa_df[sa_df['synapse_type'] != 'L5tt_C2']
    out_mdb['no_L5C2']['synapse_activation'] = I.dask.dataframe.from_pandas(
        sa_df_no_L5, npartitions=40)
    I.mdb_init_synapse_activation_binning.init(out_mdb['no_L5C2'], groupby = ['EI', 'binned_somadist'], \
                                               maxtime = timebins, get = client.get)

    full_SAexc = _get_spatiotemporal_input(
        out_mdb['complete'],
        ('synapse_activation_binned', 't1', 'EI__binned_somadist'),
        ['EXC'])  # todo: compare with biophysical model

    full_SAinh = _get_spatiotemporal_input(
        out_mdb['complete'],
        ('synapse_activation_binned', 't1', 'EI__binned_somadist'), ['INH'])

    mod_SAexc = _get_spatiotemporal_input(
        out_mdb['no_L5C2'],
        ('synapse_activation_binned', 't1', 'EI__binned_somadist'),
        ['EXC'])  # todo: compare with biophysical model

    mod_SAinh = _get_spatiotemporal_input(
        out_mdb['no_L5C2'],
        ('synapse_activation_binned', 't1', 'EI__binned_somadist'), ['INH'])

    full_SAexc = I.np.asarray(full_SAexc)

    full_SAinh = I.np.asarray(full_SAinh)

    mod_SAexc = I.np.asarray(mod_SAexc)

    mod_SAinh = I.np.asarray(mod_SAinh)

    init_L5_SAexc = I.np.concatenate(
        (full_SAexc[:, 0:80, :], mod_SAexc[:, 80:, :]), axis=1)
    init_L5_SAinh = I.np.concatenate(
        (full_SAinh[:, 0:80, :], mod_SAinh[:, 80:, :]), axis=1)

    out_mdb.setitem('full_SAexc_10_best_position',
                    full_SAexc,
                    dumper=I.dumper_numpy_to_npy)
    out_mdb.setitem('full_SAinh_10_best_position',
                    full_SAinh,
                    dumper=I.dumper_numpy_to_npy)
    out_mdb.setitem('no_l5_SAexc_10_best_position',
                    mod_SAexc,
                    dumper=I.dumper_numpy_to_npy)
    out_mdb.setitem('no_l5_SAinh_10_best_position',
                    mod_SAinh,
                    dumper=I.dumper_numpy_to_npy)
    out_mdb.setitem('init_L5_SAexc_10_best_position',
                    init_L5_SAexc,
                    dumper=I.dumper_numpy_to_npy)
    out_mdb.setitem('init_L5_SAinh_10_best_position',
                    init_L5_SAinh,
                    dumper=I.dumper_numpy_to_npy)


def get_modular_L5_input(model,
                         timebins=10000,
                         n_cells=1086,
                         release_prob=0.6,
                         offset=80):
    '''Creates a dataframe containing information about release times at each synapse from L5 cells during ongoing activity. Returns: the dataframe containing synapse activation times, the connection matrix (pandas dataframe) and synapse location dataframe.
    model: str
    timebins: int
        number of 1 ms timebins you want to create synapse activations for
    n_cells: int, optional (default 1086)
    release_prob: float, optional
        release probability at synapses of this celltype. Default 0.6 (L5tt)
    offset: int, optional
        number of milliseconds to offset generated activations by. Used for adding activations only after a certain time.'''
    # build network param file to get the interval for ongoing spikes
    morph_lengths = {
        'CDK84': 30,
        'CDK85': 25,
        'CDK86': 32,
        'CDK89': 29,
        'CDK91': 26
    }
    morph = get_CDK_from_model(model)

    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    pmdb = parameter_mdb[find_notebook_containing_model(parameter_mdb, model)]

    loc = 'C2center'
    stim = 'C2'

    network_param = pmdb['network_embedding'][loc].join(stim + "_network.param")
    network_param = I.scp.build_parameters(network_param)

    celltype = 'L5tt_C2'
    try:
        interval = network_param.network[celltype]['celltype']['spiketrain'][
            'interval']
    except TypeError:
        interval = network_param.network[celltype]['interval']
    spike_intervals = I.np.random.exponential(size=(1086, 1000)) * interval
    spike_times = I.np.cumsum(spike_intervals, axis=1)

    assert (spike_times[:, -1]
            >= timebins).all()  # make sure no spike times got cut off

    # generate cell connectivity based on CIS

    # number of synapses per contact
    nsyns_v = I.np.array([0, 1, 2, 3, 4, 5])
    nsyns_p = I.np.array(
        [0., 0.74178254, 0.19662841, 0.04830702, 0.01066713, 0.0026149])
    # location of synapses
    syn_locs_v = I.np.array([
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
        20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33
    ])
    syn_locs_p = I.np.array([
        0.03650396, 0.07755782, 0.10978877, 0.12700056, 0.12413941, 0.11786334,
        0.09791762, 0.07843338, 0.05555168, 0.03857686, 0.02586259, 0.01598701,
        0.01258955, 0.00870567, 0.00649558, 0.00465966, 0.00370677, 0.00330017,
        0.00320538, 0.00377163, 0.00354713, 0.00334258, 0.00341741, 0.00303327,
        0.00345234, 0.00335006, 0.00338748, 0.00340993, 0.00426304, 0.00443017,
        0.00485921, 0.00446758, 0.0034224
    ])

    con_df = I.pd.DataFrame(generate_connection_matrix(
        n_cells, connected=True))  #are two cells connected?

    syn_df = I.pd.DataFrame(
        index=range(n_cells), columns=range(n_cells)
    )  #where are the synapses? - is filled even if 2 cells are not connected
    for cell in range(n_cells):
        syns = []
        for cell2 in range(n_cells):
            number_of_synapses = I.np.random.choice(
                nsyns_v, p=nsyns_p
            )  # random number of synapses based on CIS distribution
            assert number_of_synapses != 0
            syns.append(
                I.np.random.choice(
                    syn_locs_v[:morph_lengths[morph]],
                    p=syn_locs_p[:morph_lengths[morph]] *
                    (1. / sum(syn_locs_p[:morph_lengths[morph]])),
                    size=number_of_synapses)
            )  # somadistance distribution based on CIS
        syn_df.iloc[cell] = syns


#     syn_df = I.pd.DataFrame(index = range(n_cells), columns = range(n_cells)) #where are the synapses? - is filled even if 2 cells are not connected
#     for cell in range(n_cells):
#         syns = []
#         for cell2 in range(n_cells):
#             syns.append(I.np.random.randint(0, morph_lengths[morph], size = 5))
#         syn_df.iloc[cell] = syns

# get all synapse activation details for L5 cells
    modular_L5_df = I.pd.DataFrame(index=range(n_cells))
    connected_cells = []
    synapses = []
    activations = []
    for cell in range(n_cells):
        con_cells = con_df.loc[cell]
        con_cells = list(con_cells[
            con_cells > 0].index)  # which cells are postsynaptic to this cell?
        connected_cells.append(con_cells)

        synapses_from_one_cell = []
        activation_times_from_one_cell = []
        for con_cell in con_cells:
            syns = syn_df.loc[cell, con_cell]
            synapses_from_one_cell.append(syns)

            activation_times = []
            for syn in syns:
                st = spike_times[cell, :].copy()
                st += offset  #only need to start once L5 input is removed
                st = st[st < timebins]
                random = I.np.random.uniform(size=len(st))
                st = st[
                    random <
                    release_prob]  # drop synapse activations according to release probability
                activation_times.append(st)

            activation_times_from_one_cell.append(activation_times)

        synapses.append(synapses_from_one_cell)
        activations.append(activation_times_from_one_cell)

    modular_L5_df['connected_cells'] = connected_cells
    modular_L5_df['synapses'] = synapses
    modular_L5_df['activation_times'] = activations

    return modular_L5_df, con_df, syn_df


def test_get_modular_L5_input():
    l5, con, syn = get_modular_L5_input('2019-01-11_9330_AgsniKR_1_51_552',
                                        timebins=1080,
                                        n_cells=1086,
                                        release_prob=0.6,
                                        offset=80)

    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    pmdb = parameter_mdb[find_notebook_containing_model(parameter_mdb,
                                                        models[0])]

    loc = 'C2center'
    stim = 'C2'

    network_param = pmdb['network_embedding'][loc].join(stim + "_network.param")
    network_param = I.scp.build_parameters(network_param)

    celltype = 'L5tt_C2'

    interval = network_param.network[celltype]['celltype']['spiketrain'][
        'interval']

    theoretical_rate = (1000 / interval) * 0.6

    rates = []

    for cell in range(1086):
        n_spikes = []
        for post_cell in l5['activation_times'].iloc[cell]:
            for syn in post_cell:
                n_spikes.append(len(syn))

        rates.append(I.np.mean(n_spikes))

    effective_rate = I.np.mean(rates)

    assert 0.9 * theoretical_rate < effective_rate < 1.1 * theoretical_rate


def incomplete_network_activation(modular_L5_df,
                                  SAexc,
                                  SAinh,
                                  old_n_post_cells=1086,
                                  new_n_post_cells=150,
                                  cellIDs=None,
                                  target_pre_cells=None,
                                  con_df=None):
    '''uses a dataframe made by get_modular_L5_input() to randomly drop cells from n_cells until only new_n_post_cells 
    are left. The activation times of these dropped cells are added to the spatiotemporally binned activation 
    array (SAexc) according to their synapse somadistance and release time.
    modular_L5_df: pandas dataframe
    SAexc, SAinh: numpy arrays containing spatiotemporally binned synapse activation data
    new_n_post_cells: int
    n_cells: int, optional
        the number of cells originally contained in the network. Default 1086 from cortex in silico C2 barrel. 
        Should be the same as the one used for making the modular_L5_df.'''
    assert new_n_post_cells <= old_n_post_cells
    # choose random cells to drop, or take cellID if given:
    if cellIDs is not None:
        cells_to_keep = cellIDs
        cells_to_drop = [
            c for c in range(old_n_post_cells) if not c in cells_to_keep
        ]
    else:
        cells_to_drop = I.np.random.choice(range(old_n_post_cells),
                                           size=old_n_post_cells -
                                           new_n_post_cells,
                                           replace=False)
        cells_to_keep = [
            c for c in range(old_n_post_cells) if not c in cells_to_drop
        ]

    assert len(set(cells_to_drop)) + len(set(cells_to_keep)) == old_n_post_cells

    # for all cells that are not being simulated, add their spontaneous activity to the input for simulated cells
    for cell in cells_to_drop:
        for c, cell2 in enumerate(modular_L5_df.loc[cell, 'connected_cells']):
            if cell2 in cells_to_keep:  # if we are dropping it anyway, don't waste time
                syns = modular_L5_df.loc[cell, 'synapses'][c]
                for s, syn in enumerate(syns):  # somadistance bin
                    st = modular_L5_df.loc[cell, 'activation_times'][c][s]
                    for activation in st:  # timebin
                        SAexc[syn, cell2, I.np.floor(activation)] += 1

    # add more spontaneous activity to match embedding connection counts
    con_df = con_df.copy()
    con_df[con_df > 1] = 1
    if target_pre_cells is not None:
        for post_cell in cells_to_keep:
            if target_pre_cells - con_df[post_cell].sum() > 0:

                missing_cells = I.np.random.choice(cells_to_drop,
                                                   size=target_pre_cells -
                                                   con_df[post_cell].sum(),
                                                   replace=False)
                assert len(
                    missing_cells) + con_df[post_cell].sum() == target_pre_cells
                for pre_cell in missing_cells:
                    cell_index = I.np.random.randint(
                        len(modular_L5_df.loc[pre_cell, 'connected_cells'])
                    )  #choose a random post cell to take activation times from

                    syns = modular_L5_df.loc[pre_cell, 'synapses'][cell_index]

                    for s, syn in enumerate(syns):  # somadistance bin
                        st = modular_L5_df.loc[
                            pre_cell, 'activation_times'][cell_index][s]
                        for activation in st:  # timebin
                            SAexc[syn, post_cell, I.np.floor(activation)] += 1

    #SAexc_return = I.np.stack([SAexc[:, cell, :] for cell in cellIDs], axis = 2)
    #SAinh_return = I.np.stack([SAinh[:, cell, :] for cell in cellIDs], axis = 2)

    return SAexc, SAinh, cells_to_drop, cells_to_keep


def get_modular_evoked_L5_input(model,
                                syn_df,
                                con_df,
                                n_cells=1086,
                                release_prob=0.6):
    '''Creates a dataframe containing information about release times at each synapse from L5 cells during sensory evoked activity. Returns: the dataframe containing synapse activation times.
    model: str
    syn_df, con_df: pandas dataframes describing conecctions between cells
    n_cells: int, optional (default 1086)
    release_prob: float, optional
        release probability at synapses of this celltype. Default 0.6 (L5tt).'''

    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    pmdb = parameter_mdb[find_notebook_containing_model(parameter_mdb, model)]

    loc = 'C2center'
    stim = 'C2'

    network_param = pmdb['network_embedding'][loc].join(stim + "_network.param")
    network_param = I.scp.build_parameters(network_param)

    celltype = 'L5tt_C2'

    bins = network_param.network[celltype]['celltype']['pointcell']['intervals']
    probabilities = network_param.network[celltype]['celltype']['pointcell'][
        'probabilities']
    spike_times = I.np.empty((n_cells, len(bins)))
    spike_times.fill(I.np.nan)

    if len(bins) != len(probabilities):
        errstr = 'Time bins and probabilities of PSTH for cell type %s have unequal length! ' % preCellType
        errstr += 'len(bins) = %d - len(probabilities) = %d' % (
            len(bins), len(probabilities))
        raise RuntimeError(errstr)
    for i in range(len(bins)):  ##fill all cells bin after bin
        tBegin, tEnd = bins[i]
        assert tEnd - tBegin == 1  # make sure all bins are 1 ms wide so can ignore exact spike timing
        spikeProb = probabilities[i]
        active, = I.np.where(I.np.random.uniform(size=n_cells) < spikeProb)
        #     spikeTimes = offset + tBegin + (tEnd - tBegin)*np.random.uniform(size=len(active))
        spikeTimes = [tBegin] * len(
            active
        )  # don't care about spike time, just about number active per bin
        for j in active:
            #         self.cells[preCellType][active[j]].append(spikeTimes[j])
            spike_times[j, i] = tBegin

    # make dataframe
    evoked_L5_df = I.pd.DataFrame(index=range(n_cells))
    connected_cells = []
    synapses = []
    activations = []
    for cell in range(n_cells):
        #     print cell
        #     con_cells = [c for c in range(n_cells) if con_df.loc[cell, c] != 0]
        con_cells = con_df.loc[cell]
        con_cells = list(con_cells[
            con_cells > 0].index)  # which cells are postsynaptic to this cell?
        connected_cells.append(con_cells)

        synapses_from_one_cell = []
        activation_times_from_one_cell = []
        for con_cell in con_cells:
            syns = syn_df.loc[cell, con_cell]
            synapses_from_one_cell.append(syns)

            activation_times = []
            for syn in syns:
                st = spike_times[cell, :].copy()
                st = st[~I.np.isnan(st)]  # drop nan values
                random = I.np.random.uniform(size=len(st))
                st = st[
                    random <
                    release_prob]  # drop synapse activations according to release probability
                activation_times.append(st)

            activation_times_from_one_cell.append(activation_times)

        synapses.append(synapses_from_one_cell)
        activations.append(activation_times_from_one_cell)

    evoked_L5_df['connected_cells'] = connected_cells
    evoked_L5_df['synapses'] = synapses
    evoked_L5_df['activation_times'] = activations

    return evoked_L5_df


def test_get_modular_evoked_L5_input():
    # generate cell connectivity
    con_df = I.pd.DataFrame(generate_connection_matrix(
        n_cells, connected=True))  #are two cells connected?

    syn_df = I.pd.DataFrame(
        index=range(n_cells), columns=range(n_cells)
    )  #where are the synapses? - is filled even if 2 cells are not connected
    for cell in range(n_cells):
        syns = []
        for cell2 in range(n_cells):
            syns.append(I.np.random.randint(0, morph_lengths[morph], size=5))
        syn_df.iloc[cell] = syns

    evoked_l5_df = get_modular_evoked_L5_input(
        '2019-01-11_9330_AgsniKR_1_51_552',
        syn_df,
        con_df,
        n_cells=1086,
        release_prob=0.6)

    parameter_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200416_get_parameters_from_L6_simulations/'
    )
    pmdb = parameter_mdb[find_notebook_containing_model(
        parameter_mdb, '2019-01-11_9330_AgsniKR_1_51_552')]

    loc = 'C2center'
    stim = 'C2'

    network_param = pmdb['network_embedding'][loc].join(stim + "_network.param")
    network_param = I.scp.build_parameters(network_param)

    celltype = 'L5tt_C2'

    probabilities = network_param.network[celltype]['celltype']['pointcell'][
        'probabilities']

    theoretical_rate = sum(probabilities) * 0.6

    rates = []

    for cell in range(1086):
        n_spikes = []
        for post_cell in evoked_l5_df['activation_times'].iloc[cell]:
            for syn in post_cell:
                n_spikes.append(len(syn))

        rates.append(I.np.mean(n_spikes))

    effective_rate = I.np.mean(rates)

    assert 0.9 * theoretical_rate < effective_rate < 1.1 * theoretical_rate


def incomplete_evoked_network_activation(evoked_L5_df, SAexc, SAinh, n_cells = 1086, \
                                        cells_to_keep = None, cells_to_drop = None, offset = 245):

    assert len(set(cells_to_drop)) + len(set(cells_to_keep)) == n_cells

    for cell in cells_to_drop:
        for c, cell2 in enumerate(evoked_L5_df.loc[cell, 'connected_cells']):
            if cell2 in cells_to_keep:  # if we are dropping it anyway, don't waste time
                syns = evoked_L5_df.loc[cell, 'synapses'][c]
                for s, syn in enumerate(syns):
                    st = evoked_L5_df.loc[cell, 'activation_times'][c][s]
                    for activation in st:
                        SAexc[syn, cell2, I.np.floor(activation) + offset] += 1

    return SAexc, SAinh


# helper functions for getting spatiotemporal inputs from binned mdb
def get_spatial_bin_level(key):
    '''returns the index that relects the spatial dimension'''
    return key[-1].split('__').index('binned_somadist')


def get_sorted_keys_by_group(mdb, key, group):
    '''returns keys sorted such that the first key is the closest to the soma'''
    group = list(group)
    level = get_spatial_bin_level(key)
    keys = mdb[key].keys()
    keys = sorted(keys, key=lambda x: float(x[level].split('to')[0]))
    out = []
    for k in keys:
        k_copy = list(k[:])
        k_copy.pop(level)
        if k_copy == group:
            out.append(k)
    return out


def _get_spatiotemporal_input(mdb, key, group):
    '''returns spatiotemporal input in the following dimensions:
    (trial, time, space)'''
    keys = get_sorted_keys_by_group(mdb, key, group)
    out = [mdb[key][k] for k in keys]
    print(keys)
    return out


def get_spatiotemporal_inputs_from_biophysical_simulation(model, ntrials):
    '''fetches spatiotemporally binned inputs from biophysical simulations.
    model: str
    ntrials: int 
        number of trials per embedding position (between 0 and 1000)'''

    whiskers = ['B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'D3']

    sim_mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20200702_81grid_simulations_of_CDK_morphologies/'
    )
    st = sim_mdb[get_CDK_from_model(model)][model]['C2']['spike_times']
    positions = [st.index[n].split('/')[0][2:] for n in range(len(st.index))
                ]  # all 81 positions
    positions = sorted(list(set(positions)))

    SAexc = {}
    SAinh = {}

    for whisker in whiskers:
        sim_data = sim_mdb[get_CDK_from_model(model)][model][whisker]

        ## get all (separated) excitatory and inhibitory input, spatially binned
        with I.silence_stdout:
            full_SAexc = _get_spatiotemporal_input(
                sim_data,
                ('synapse_activation_binned', 't1', 'EI__binned_somadist'),
                ['EXC'])

            full_SAinh = _get_spatiotemporal_input(
                sim_data,
                ('synapse_activation_binned', 't1', 'EI__binned_somadist'),
                ['INH'])

        full_SAexc = I.np.asarray(full_SAexc)
        full_SAinh = I.np.asarray(full_SAinh)

        st = sim_mdb[get_CDK_from_model(model)][model][whisker]['spike_times']
        # get n trials from each position
        for loc in positions:
            b = [1 if ind.startswith(whisker + loc) else 0 for ind in st.index]
            start_index = I.np.nonzero(b)[0][0]

            SAexc[whisker + loc] = full_SAexc[:, start_index:start_index +
                                              ntrials, :]
            SAinh[whisker + loc] = full_SAinh[:, start_index:start_index +
                                              ntrials, :]

    return SAexc, SAinh


####################
# functions for setting up and running network simulations
#####################


def generate_connection_matrix(
        number_of_cells,
        connected=True,
        probs='hay'):  # 1 = unidirectional, 2 = bidirectional
    '''returns a pandas dataframe of size number_of_cells x number_of_cells, with 0 denoting no connection between two cells, 1 denoting a unidirectional connection and 2 denoting a bidirectional connection.
    number_of_cells: int
    connected: boolean, optional
        if False, returns a dataframe filled with zeroes to represent the unconnected state. Default True.
    probs: string, optional
        Connection probabilities between cells. Currently implemented: hay (Hay & Segev 2015), cis (cortex in silico network embedding). Default hay.'''

    cells = range(number_of_cells)  #number of cells in network

    connection_matrix = I.np.zeros((len(cells), len(cells)))
    done_cells = []
    if probs == 'hay':  # from Hay & Segev, 2015
        p1 = 0.065
        p2 = 0.13
        p3 = 0.19
    elif probs == 'cis':  # from cortex in silico embedding
        p1 = 0.098
        p2 = 0.196
        p3 = 0.265

    for cell1 in cells:
        done_cells.append(
            cell1
        )  #don't try to connect a cell to itself, don't try to connect 2 cells twice

        for cell2 in cells:
            if not cell2 in done_cells:
                if connected:
                    randn = I.np.random.uniform()

                    if randn < p1:
                        connection_matrix[cell1, cell2] = 1
                        connection_matrix[cell2, cell1] = 0
                    elif randn >= p1 and randn < p2:
                        connection_matrix[cell1, cell2] = 0
                        connection_matrix[cell2, cell1] = 1
                    elif randn >= p2 and randn < p3:
                        connection_matrix[cell1, cell2] = 2
                        connection_matrix[cell2, cell1] = 2
                else:
                    connection_matrix[cell1, cell2] = 0
                    connection_matrix[cell2, cell1] = 0

    return connection_matrix.astype(int)


def generate_synapse_location_matrix(n_cells, max_bin=30):
    syn_df = I.pd.DataFrame(
        index=range(n_cells), columns=range(n_cells)
    )  #where are the synapses? - is filled even if 2 cells are not connected
    for cell in range(n_cells):
        syns = []
        for cell2 in range(n_cells):
            syns.append(I.np.random.randint(0, max_bin, size=5))
        syn_df.iloc[cell] = syns
    return syn_df


@I.dask.delayed
def reduced_model_network(model,
                          out_mdb=None,
                          rm=None,
                          n_cells=150,
                          timebins=10000,
                          connected=True,
                          force=None,
                          biophys_input=False,
                          return_=False,
                          SAmdb=None,
                          cellIDs=None,
                          adjust_input=True):
    '''Runs a network of reduced model neurons. All neurons are the same reduced model.
    model: str
    out_mdb: ModelDataBase
    n_cells, timebins: int
    connected: boolean
        if True, cells are recurrently connected according to a generated connectivity matrix. If False, each cell is effectively a separate trial.
    force: int or None
        forces an output spike in all cells within 3 ms of this timebin to mimic a somatic current injection.
    biophys_input: False or str
        if str (format whisker_position), synaptic input will be taken from biophysical model simulations. Useful for direct output comparisons.
    return_: boolean
        if True, returns a concatenated spike_times and WNI_df dataframe instead of saving to a database. If 'spike_times', returns only the spike_times dataframe. If False, output is saved to out_mdb.'''
    selection = dict(
        zip([
            '2019-01-11_9330_AgsniKR_1_51_552',
            '2019-01-26_12752_uvEXhHc_1_47_301',
            '2019-01-26_12752_uvEXhHc_4_113_409',
            '2019-02-11_9215_0Bx2rPx_5_171_390',
            '2019-02-22_35839_TG4IHEp_1_1_0',
            '2019-02-23_7062_mvUlY5e_1_551_65',
            '2019-03-05_20241_SZ3iYOZ_707527054352652_109_665',
            '2019-05-10_15406_qBeBpVo_7712997831240842_108_441'
        ], [261, 262, 257, 261, 260, 260, 257, 257]))
    mdb = I.ModelDataBase(
        '/axon/scratch/abast/results/20201016_rieke_homogeneous_networks')
    assert n_cells <= 1086
    if not return_:  # you should either return the output or save it to mdb
        assert out_mdb is not None

    cells_to_keep = range(
        n_cells
    )  # unless this gets overwritten later, we just want to iterate through n_cells sequentially

    ## get all (separated) excitatory and inhibitory input, spatially binned
    #     morph = get_CDK_from_model(model)
    #     if connected and n_cells < 1086 and adjust_input: # in this condition, we need to modify synaptic inputs, as cells that would have provided recurrent input are not simulated
    #         SAexc = mdb[model]['synapse_activations']['no_l5_SAexc_10_best_position']
    #         SAinh = mdb[model]['synapse_activations']['no_l5_SAinh_10_best_position']
    #         print 'adjusting connected synaptic input for {} cells...'.format(n_cells)
    #         modular_L5_df, con_df, syn_df = get_modular_L5_input(model, timebins = timebins, n_cells = 1086, release_prob = 0.6, offset = 0)
    #         SAexc, SAinh, cells_to_drop, cells_to_keep = incomplete_network_activation(modular_L5_df, SAexc, SAinh, n_cells = 1086, new_n_cells = n_cells, cellIDs = cellIDs)
    #     elif connected and adjust_input:
    #         print 'getting synaptic input for full network...'
    #         SAexc = mdb[morph]['synapse_activations']['init_L5_SAexc_10']
    #         SAinh = mdb[morph]['synapse_activations']['init_L5_SAinh_10']
    #     elif connected and not adjust_input:
    #         SAexc = mdb[model]['synapse_activations']['full_SAexc_10_best_position']
    #         SAinh = mdb[model]['synapse_activations']['full_SAinh_10_best_position']
    #     elif biophys_input:
    #         print 'getting synaptic input from biophysical simulations'

    #         whisker = biophys_input[0:2]
    #         pos = biophys_input[3:]
    #         SAexc = SAmdb[whisker + pos +'_exc']
    #         SAinh = SAmdb[whisker + pos +'_inh']

    #     else:
    #         print 'adjusting unconnected synaptic input for {} cells...'.format(n_cells)
    #         SAexc = mdb[morph]['synapse_activations']['full_SAexc_10']
    #         SAinh = mdb[morph]['synapse_activations']['full_SAinh_10']
    #         SAexc = SAexc[:, :n_cells, :timebins]
    #         SAinh = SAinh[:, :n_cells, :timebins]

    SAexc = SAmdb[model]['synapse_activations']['full_SAexc_10_best_position']
    SAinh = SAmdb[model]['synapse_activations']['full_SAinh_10_best_position']
    SAexc = SAexc[:, :n_cells, :timebins]
    SAinh = SAinh[:, :n_cells, :timebins]

    # FETCH REDUCED MODEL
    if rm is None:
        rm_mdb = I.ModelDataBase(
            '/axon/scratch/abast/results/20200720_rieke_examining_reduced_model_81grid'
        )
        tmin = selection[model]
        trial = '50ISI' + str(tmin) + '_' + str(tmin + 1)
        selected_kernel_dict = rm_mdb[model][trial]['selected_kernel_dict']

        s_exc = selected_kernel_dict['s_exc']
        s_inh = selected_kernel_dict['s_inh']
        t_exc = selected_kernel_dict['t_exc']
        t_inh = selected_kernel_dict['t_inh']

        nonlinearities = rm_mdb['nonlinearities_variable_step'][model]
        LUT = nonlinearities[str(tmin)]

        WNI_boundary = rm_mdb[model][trial]['WNI_boundary']
        WNI_boundary -= min(WNI_boundary)

    else:
        kernel_dict = rm['kernel_dict']
        s_exc = kernel_dict['s_exc']
        s_inh = kernel_dict['s_inh']
        t_exc = kernel_dict['t_exc']
        t_inh = kernel_dict['t_inh']

        LUT = rm['LUT']

        WNI_boundary = rm['post_spike_penalty']
        WNI_boundary -= min(WNI_boundary)

    # APPLY THE REDUCED MODEL
    print('running reduced model network...')

    WNI_df = I.pd.DataFrame(index=range(n_cells), columns=range(
        timebins))  # dataframe for recording WNI values for later reference

    if connected and not adjust_input:
        con_df = I.pd.DataFrame(
            generate_connection_matrix(
                n_cells, connected=connected))  #are two cells connected?

        syn_df = I.pd.DataFrame(
            index=range(n_cells), columns=range(n_cells)
        )  #where are the synapses? - is filled even if 2 cells are not connected
        for cell in range(n_cells):
            syns = []
            for cell2 in range(n_cells):
                syns.append(I.np.random.randint(0, len(SAexc), size=5))
            syn_df.iloc[cell] = syns

    SAinh_cumulative = I.np.zeros(
        (n_cells, timebins)
    )  # need to store synapse activations so the temporal kernel can look back
    SAexc_cumulative = I.np.zeros((n_cells, timebins))

    spike_times_df = I.defaultdict(list)  # for recording output spikes

    for timebin in range(
            timebins
    ):  # iterate through one timebin at a time, so that recurrent inputs can be applied
        #         print timebin
        ## get excitatory and inhibitory input, spatially binned for the CURRENT timebin
        SAexc_timebin = I.np.ndarray((len(SAexc), n_cells, 1))
        for dist in range(len(SAexc)):
            for cell in range(n_cells):
                SAexc_timebin[dist, cell] = SAexc[dist][cell][timebin]

        SAinh_timebin = I.np.ndarray((len(SAinh), n_cells, 1))
        for dist in range(len(SAinh)):
            for cell in range(n_cells):
                SAinh_timebin[dist, cell] = SAinh[dist][cell][timebin]

        ## apply spatial kernel to the current timebin
        SAexc_timebin = sum([o * s for o, s in zip(SAexc_timebin, s_exc)])
        SAinh_timebin = sum([o * s for o, s in zip(SAinh_timebin, s_inh)])

        for cell in range(
                0, n_cells
        ):  # save the spatially filtered synapse activations for later
            SAinh_cumulative[cell, timebin] = SAinh_timebin[cell]
            SAexc_cumulative[cell, timebin] = SAexc_timebin[cell]

        ## apply temporal kernel
        spikes = []
        for c, cell in enumerate(cells_to_keep):
            if timebin - 80 >= 0:  # if we can't look back 80 ms, then look back as far as possible
                SAexc_window = SAexc_cumulative[c, timebin - 79:timebin + 1]
                SAinh_window = SAinh_cumulative[c, timebin - 79:timebin + 1]
            else:
                SAexc_window = SAexc_cumulative[c, 0:timebin + 1]
                SAinh_window = SAinh_cumulative[c, 0:timebin + 1]

            SAexc_window = sum([
                o * s for o, s in zip(SAexc_window, t_exc[-len(SAexc_window):])
            ])
            SAinh_window = sum([
                o * s for o, s in zip(SAinh_window, t_inh[-len(SAinh_window):])
            ])

            ## get weighted net input for each cell and record it
            WNI = SAexc_window + SAinh_window
            WNI_df.iloc[c, timebin] = WNI

            # check the last 80 timebins for a spike, apply WNI penalty if there was one
            if spike_times_df[cell]:  # if there have been spikes in the past
                last_spike_time = spike_times_df[cell][-1]
                last_spike_interval = timebin - last_spike_time
                if last_spike_interval < 80:
                    penalty = WNI_boundary[-last_spike_interval]
                    WNI -= penalty

            ## get spike probability from WNI
            if WNI > LUT.index.max():
                spiking_probability = LUT[LUT.index.max()]
            elif WNI < LUT.index.min():
                spiking_probability = LUT[LUT.index.min()]
            else:
                spiking_probability = LUT[I.np.round(WNI)]

            # force a spike (mimic soma current injection)
            if not force == None:
                if c % 3 == 0:  #get some jitter to forced spikes
                    target_bin = force
                elif c % 2 == 0:
                    target_bin = force + 1
                else:
                    target_bin = force + 2
            else:
                target_bin = None

            ## will the cell spike or not?
            if spiking_probability > I.np.random.uniform(
            ) or timebin == target_bin:  # cell can spike stochastically or because of a forced spike
                if timebin > 80:  # prevent recurrent spikes before full length of temporal kernel
                    spike_times_df[cell].append(
                        timebin
                    )  ## the cell spiked! now we might need to care about who it is connected to...
                    if connected:
                        for cell2, con in enumerate(
                                con_df.iloc[cell]
                        ):  # for all other cells in the network
                            assert type(cell2) == int
                            assert type(cells_to_keep[0]) == int
                            if con == 1 and cell2 in cells_to_keep:  # if the cells are connected and we are simulating cell2 as well
                                assert cell2 != cell  # make sure the cell isn't trying to feedback to itself
                                for syn in range(
                                        5
                                ):  # each connection consists of 5 synapses according to Hay
                                    if not timebin == timebins - 1:  #if we are already in the last timebin, we don't need to add to the next
                                        SAexc[syn_df.iloc[cell, cell2]
                                              [syn]][cell2][timebin + 1] += 1
                            elif con == 2 and cell2 in cells_to_keep:  #reciprocal connections are stronger as per Hay 2015
                                assert cell2 != cell
                                for syn in range(
                                        5
                                ):  # len(syn_df.iloc[cell, cell2]) for custom number of synapses
                                    if not timebin == timebins - 1:
                                        SAexc[syn_df.iloc[cell, cell2]
                                              [syn]][cell2][timebin + 1] += 1.5

    if return_ == 'spike_times' and biophys_input:
        spike_times_df.index = [biophys_input] * len(spike_times_df)
        WNI_df.index = [biophys_input] * len(WNI_df)

        if not whisker + pos in out_mdb[model].keys():
            out_mdb[model].create_sub_mdb(whisker + pos)
        out_mdb[model][whisker + pos]['spike_times'] = spike_times_df
        out_mdb[model][whisker + pos]['WNI'] = WNI_df

    elif return_:
        return I.pd.concat([
            spike_times_df, WNI_df
        ])  # you can make a dask.dataframe.from_delayed() out of this
    if biophys_input:
        mdb['troubleshooting'][model][str(n_cells) + 'list'] = spike_times_df
    else:
        with I.silence_stdout:
            #             if not model in mdb.keys():
            #                 mdb.create_sub_mdb(model)

            if not '{}_{}_{}_{}'.format(n_cells, timebins, connected,
                                        force) in out_mdb.keys():
                out_mdb.create_sub_mdb('{}_{}_{}_{}'.format(
                    n_cells, timebins, connected, force))

            out_mdb['{}_{}_{}_{}'.format(n_cells, timebins, connected,
                                         force)]['spike_times'] = spike_times_df

            out_mdb['{}_{}_{}_{}'.format(n_cells, timebins, connected,
                                         force)]['WNI'] = WNI_df

            if connected:
                out_mdb['{}_{}_{}_{}'.format(
                    n_cells, timebins, connected,
                    force)]['connection_matrix'] = con_df


####################
# functions for examining network simulations
#####################


def describe_rm_network(st, tmax=1000, plt=True):
    '''takes a spike times dataframe and calculates the mean spike rate, fraction of quiescent cells and mean coefficient of variation of ISI (as Landau)'''
    st[st >=
       tmax] = I.np.nan  # remove anything after + including tmax (eg. forced spike)
    ISIs = I.np.diff(st).astype(float)
    # coefficient of variation of ISIs
    CVs = []
    for i in ISIs:
        vals = i[~I.np.isnan(i)]
        CVs.append(sp.stats.variation(vals))
    CVs = I.np.asarray(CVs)

    mean_CV = I.np.mean(CVs[~I.np.isnan(CVs)])

    # fraction quiescent
    ncells = len(st)
    nquiet = (st.notnull().sum(axis=1) == 0).sum()
    frac = nquiet / float(ncells) * 100

    # mean spike rate
    rates = st.notnull().sum(axis=1)
    rates = rates / ((tmax - 80) / 1000.)
    if plt:
        I.plt.hist(rates)
        I.plt.show()
    meanrate = I.np.mean(rates)

    return meanrate, frac, mean_CV


@I.dask.delayed
def reformat_spike_times(spike_times_mdb, out_mdb):
    '''takes the output of a reduced model network simulation (dataframe size n_cells x timebins, filled with 0s and 1s) and converts it to the standard spike_times dataframe format, with size n_cells x max_spikes, where cells are filled with spike times.'''
    spike_times_df = spike_times_mdb['spike_times']
    st_reformat = I.pd.DataFrame(index=range(len(spike_times_df)),
                                 columns=range(max(spike_times_df.sum(axis=1))))
    for c, cell in enumerate(spike_times_df.index):
        nspikes = 0
        for timebin in spike_times_df.columns:
            if spike_times_df.iloc[c, int(timebin)] == 1:
                st_reformat.iloc[c, nspikes] = int(timebin)
                nspikes += 1

    out_mdb['st_reformat'] = st_reformat


###########################################
# heterogeneous cortex in silico networks #
###########################################

# assumes you have a network mapper object made with project_specific_ipynb_code/reduced_model_output_paper/Network


def lookup_postsyn_cells(con, syn, cellID):
    postsyn_cells = con.loc[cellID]
    recurrence_flag = [c for c in postsyn_cells if c > 0]
    postsyn_cells = list(postsyn_cells[postsyn_cells > 0].index)
    syn_distances = [
        list(syn.loc[cellID, post_cell]) for post_cell in postsyn_cells
    ]
    return postsyn_cells, syn_distances, recurrence_flag


# rm method - new
def run_recurrent_network(self,
                          SA_mdb=None,
                          SAexc=None,
                          SAinh=None,
                          save_WNI=False,
                          tStop=300,
                          connected=False,
                          cellIDs=None,
                          con_df=None,
                          syn_df=None,
                          out_mdb=None,
                          force=None,
                          force_jitter=0,
                          adaptation_current_dict=None):
    '''Apply the reduced model to synaptic input to get a list containing output spike times.
    self: ReducedModel object from project_specific_ipynb_code/reduced_model_output_paper/ReducedModel
    SAexc, SAinh: numpy arrays containing spatiotemporally binned synaptic inputs (format [somadistance_bin, timebin, cell_index]), future objects of these, or keys (str) in the SA_mdb where these are saved
    save_WNI: boolean
        True saves a dataframe containing WNI values at all timepoints. 
        False saves spike times list only.
    tStop: int'''

    cellIDs = list(cellIDs)
    # load SA arrays if given keys and mdb
    if type(SAexc) == str:
        assert SA_mdb is not None
        SAexc = SA_mdb[SAexc]
        SAinh = SA_mdb[SAinh]

        if SAexc.shape[2] > len(
                cellIDs
        ):  # then assume cellIDs can be used as indices, select them
            assert I.utils.convertible_to_int(cellIDs[0])
            assert max(cellIDs) <= SAexc.shape[2]
            SAexc = SAexc[:, :, cellIDs]
            SAinh = SAinh[:, :, cellIDs]

    else:  # it's likely being taken from a future object - these are immutable
        SAexc = SAexc.copy()
        SAinh = SAinh.copy()

    n_cells = len(cellIDs)

    s_exc = self.kernel_dict['s_exc']
    s_inh = self.kernel_dict['s_inh']
    t_exc = self.kernel_dict['t_exc']
    t_inh = self.kernel_dict['t_inh']

    if connected and con_df is None:
        con_df = I.pd.DataFrame(generate_connection_matrix(1086,
                                                           connected=True))
        syn_df = generate_synapse_location_matrix(1086, max_bin=SAexc.shape[0])

    if force is not None:
        cell_forced_spikes = {}
        for cellID in cellIDs:
            cell_forced_spikes[cellID] = force + I.np.random.choice(
                range(force_jitter + 1))
    else:
        cell_forced_spikes = {}
        for cellID in cellIDs:
            cell_forced_spikes[cellID] = None

    if adaptation_current_dict:
        decay_time = adaptation_current_dict['decay_time']
        penalty = adaptation_current_dict['penalty']
        l = I.np.log(0.5) / decay_time

        t = I.np.arange(0, 5000, 1)
        adaptation_current = penalty * I.np.exp(t * l)

        adaptation_current = I.pd.Series(index=range(5000),
                                         data=adaptation_current)
        adaptation_current[adaptation_current < 0] = 0

    LUT = self.LUT

    WNI_boundary = self.ISI_penalty

    SAinh_cumulative = I.np.zeros((n_cells, tStop))
    SAexc_cumulative = I.np.zeros((n_cells, tStop))

    wni_values = I.defaultdict(list)  # dict for recording wni values
    spike_times = I.defaultdict(list)  # dict for recording output spikes

    for timebin in range(tStop):  # iterate through one timebin at a time
        ## get excitatory and inhibitory input, spatially binned for the CURRENT timebin
        SAexc_timebin = SAexc[:,
                              timebin, :]  # shape: soma_distance-bin, timebin, cell
        SAinh_timebin = SAinh[:, timebin, :]

        ## apply spatial kernel to the current timebin
        SAexc_timebin = sum([o * s for o, s in zip(SAexc_timebin, s_exc)])

        # apply scaled inhibitory kernel for each cell
        SAinh_timebin = sum([o * s for o, s in zip(SAinh_timebin, s_inh)])

        for cell in range(n_cells):
            SAinh_cumulative[cell, timebin] = SAinh_timebin[cell]
            SAexc_cumulative[cell, timebin] = SAexc_timebin[cell]

        ## apply temporal kernel
        for cell, cellID in enumerate(cellIDs):
            if timebin - 79 >= 0:
                SAexc_window = SAexc_cumulative[cell][timebin - 79:timebin + 1]
                SAinh_window = SAinh_cumulative[cell][timebin - 79:timebin + 1]
            else:
                SAexc_window = SAexc_cumulative[cell][0:timebin + 1]
                SAinh_window = SAinh_cumulative[cell][0:timebin + 1]

            SAexc_window = sum([
                o * s for o, s in zip(SAexc_window, t_exc[-len(SAexc_window):])
            ])
            SAinh_window = sum([
                o * s for o, s in zip(SAinh_window, t_inh[-len(SAinh_window):])
            ])

            ## get weighted net input for each cell
            WNI = SAexc_window + SAinh_window
            wni_values[cellID].append(WNI)

            # apply ISI dependent WNI penalty
            if spike_times[cellID]:  # if there have been spikes in the past
                last_spike_time = spike_times[cellID][-1]
                last_spike_interval = timebin - last_spike_time
                if last_spike_interval < 80:
                    penalty = WNI_boundary[-last_spike_interval]
                    WNI -= penalty

            if adaptation_current_dict and spike_times[
                    cellID]:  # apply another penalty to the WNI with a longer time constant
                for s in spike_times[cellID]:
                    spike_interval = timebin - s
                    if spike_interval < 5000:
                        penalty = adaptation_current[spike_interval]
                        WNI -= penalty

            ## get spike probability from WNI
            if WNI > LUT.index.max():
                spiking_probability = LUT[LUT.index.max()]
            elif WNI < LUT.index.min():
                spiking_probability = LUT[LUT.index.min()]
            else:
                spiking_probability = LUT[I.np.round(WNI)]

            ## will the cell spike or not?
            if (spiking_probability > I.np.random.uniform() or
                    timebin == cell_forced_spikes[cellID]) and timebin > 80:
                spike_times[cellID].append(timebin)
                if connected:
                    if timebin == tStop - 1:  #if we are already in the last timebin, we don't need to add to the next
                        continue
                    for connected_cell, syns, flag in zip(
                            *lookup_postsyn_cells(con_df, syn_df, cellID)):
                        if flag == 1 and connected_cell in cellIDs:
                            for syn in syns:
                                SAexc[syn][timebin + 1][cellIDs.index(
                                    connected_cell)] += 1
                        elif flag == 2 and connected_cell in cellIDs:
                            for syn in syns:
                                SAexc[syn][timebin + 1][cellIDs.index(
                                    connected_cell)] += 1.5

    if isinstance(out_mdb, str):
        with open(out_mdb, 'w') as f:
            I.cloudpickle.dump(spike_times, f)
    else:
        out_mdb['spike_times'] = spike_times
        if save_WNI:
            out_mdb['WNI'] = wni_values
        if connected:
            out_mdb['con'] = con_df


from reduced_model_output_paper import generate_spiketimes


def _activate_pre_cells_and_remove_simulated(self,
                                             stim,
                                             tStop=300,
                                             simulated_cells=[],
                                             mdb=None):
    '''simulated_cells: list of cellIDs of cells that are simulated in the reduced model network. Their activations are removed from the precomputed background.'''
    nm = generate_spiketimes(stim, self.cell_counts, tStop=tStop, mdb=mdb)
    for celltype in nm.keys():
        for pre_cell, spike_times in zip(self.pre_cells[celltype],
                                         nm[celltype]):
            assert spike_times is not None
            del pre_cell.spike_times[:]
            pre_cell.spike_times.extend(spike_times)

    for cellID in simulated_cells:
        # del self.pre_cells_by_id[str(cellID)].spike_times[:]
        spike_times = self.pre_cells_by_id[str(cellID)].spike_times
        drop = [st for st in spike_times if st > 80]
        for st in drop:
            self.pre_cells_by_id[str(cellID)].spike_times.remove(st)


def _get_synapse_activations_for_one_postcell(post_cell, tStop=300):
    '''post_cell: PostCell object
    returns:
        input synapse activation arrays for the post_cell'''
    SAexc = post_cell._apply_release_probability_and_merge(
        post_cell._EXC_times, 0.6)
    SAinh = post_cell._apply_release_probability_and_merge(
        post_cell._INH_times, 0.25)
    SAexc = post_cell._get_SA_array(SAexc, tStop)
    SAinh = post_cell._get_SA_array(SAinh, tStop) * post_cell.inh_scale
    return SAexc, SAinh

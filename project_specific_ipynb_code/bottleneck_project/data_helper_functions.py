import Interface as I
from helper_functions import augment_synapse_activation_df_with_branch_bin, get_synapse_activation_array_weighted
import torch
from tqdm import tqdm


def register_databases(ip=""):
    assert ip is not "", "Please provide an ip for the distributed Client"
    # init mdb for which batches should be generated
    mdb = I.ModelDataBase(
        '/gpfs/soma_fs/scratch/abast/results/20220829_hot_zone_on_demand_simulations/'
    )
    mdb._register_this_database()
    mdb = mdb['mdbs']
    mdb._register_this_database()
    mdb = mdb[
        'example_in_distribution_simulation_1ms_INH_adapt_inh_v2.6_shift-3_offset_445_280000_trials']
    mdb._register_this_database()
    mdb_models = mdb['reduced_ANN_models5']
    mdb_models._register_this_database()
    # batches_dir = mdb[('synapse_activation_binned_v2', '365_505_1', 'EI__section/branch_bin')]
    mdb = I.ModelDataBase(
        '/gpfs/soma_fs/scratch/abast/results/20220829_hot_zone_on_demand_simulations/mdbs_qr8fqtte_/mdb'
    )
    mdb = mdb[
        'example_in_distribution_simulation_1ms_INH_adapt_inh_v2.6_shift-3_offset_445_280000_trials']


def load_data_helper_uncached(data_dir, batch):
    AP_DEND = torch.from_numpy(I.np.load(data_dir.join('batch_{}_AP_DEND.npy'.format(batch)))).half()  #.to(device)
    AP_SOMA = torch.from_numpy(I.np.load(data_dir.join('batch_{}_AP_SOMA.npy'.format(batch)))).half()  #.to(device)
    ISI_DEND = torch.from_numpy(I.np.load(data_dir.join('batch_{}_ISI_DEND.npy'.format(batch)))).half()  #.to(device)
    ISI_SOMA = torch.from_numpy(I.np.load(data_dir.join('batch_{}_ISI_SOMA.npy'.format(batch)))).half()  #.to(device)
    VT_SOMA = torch.from_numpy(I.np.load(data_dir.join('batch_{}_VT_ALL.npy'.format(batch)))).half()  #.to(device)
    VT_DEND = torch.from_numpy(I.np.load(data_dir.join('batch_{}_VT_DEND_ALL.npy'.format(batch)))).half()  #.to(device)
    SA = torch.from_numpy(I.np.load(data_dir.join('batch_{}_SYNAPSE_ACTIVATION.npy'.format(batch)))).half()  #.to(device)
    SA = torch.from_numpy(I.np.load(data_dir.join('batch_{}_SYNAPSE_ACTIVATION_WEIGHTED.npy'.format(batch)))).half()  #.to(device)

    #SA = SA.flatten().view(SA.shape[0],-1)
    return SA, ISI_SOMA, AP_SOMA, VT_SOMA, ISI_DEND, AP_DEND, VT_DEND


load_data_helper = I.utils.cache(load_data_helper_uncached)


def load_data_uncached(batches_dir, batch_range=10):
    """
    Loads simulation data from batches_dir
    """
    out = []
    for batch in tqdm(range(batch_range), desc="Loading batches"):
        out.append(load_data_helper(
            batches_dir, batch))  # why its not load_data_helper_uncached ???

    a1 = torch.cat([o[0] for o in out])  #.to(device)
    a2 = torch.cat([o[1] for o in out])  #.to(device)
    a3 = torch.cat([o[2] for o in out])  #.to(device)
    a4 = torch.cat([o[3] for o in out])  #.to(device)
    a5 = torch.cat([o[4] for o in out])  #.to(device)
    a6 = torch.cat([o[5] for o in out])  #.to(device)
    a7 = torch.cat([o[6] for o in out])  #.to(device)
    return a1, a2, a3, a4, a5, a6, a7


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
                  syn_weights=None):
    if syn_weights:
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


load_data = I.utils.cache(load_data_uncached)


def filter_models(models, keywords=None):
    """
    Given a list of models, filters through them to grep for some keywords
    Default keywods: ['loss_sAP', 'bn_2_', 'L2_0.001_', 'TV_0.001', 'min_max_80']
    
    Keywords meanings:
    # sAP: somatic AP
    # dAP: dendritic AP
    # bn: model.linear1.out_features
    # ISI: InterSpike Interval
    # width_min_max: synaptic_history; start and end times w.r.t. to onset of sensory stimulus defining the interval of simulation  data used to train the model
    # decoder: number of layers x width of layers
    # L2: l2 regularization on all weights as implemented by the ADAM optimizer
    # TV: total variation loss, penalizing the differences in weights in model.linear1 in adjacent timepoints

    TODO: improve keyword matching with just arguments like bottleneck_outputs: int, temporal window: int etc...
    """
    if keywords is None:
        keywords = ['loss_sAP', 'bn_2_', 'L2_0.001_', 'TV_0.001', 'min_max_80']
    for m in models.keys():
        for keyword in keywords:
            if not keyword in m:
                continue
        print(m)
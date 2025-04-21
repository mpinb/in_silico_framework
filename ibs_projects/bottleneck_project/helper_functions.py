import torch
import Interface as I
import torch.nn as nn

device = "cuda" if torch.cuda.is_available() else "cpu"


class Model(nn.Module):

    def __init__(self,
                 synaptic_input_size,
                 bottleneck_size=5,
                 output_size=1,
                 layer_width=40,
                 number_of_layers_after_bottleneck=5,
                 bottleneck_ISI_soma=True,
                 bottleneck_ISI_dend=True):

        super(Model, self).__init__()
        self.bottleneck_ISI_soma = bottleneck_ISI_soma
        self.bottleneck_ISI_dend = bottleneck_ISI_dend
        self.relu = nn.ReLU()
        self.linear1 = nn.Linear(in_features=synaptic_input_size,
                                 out_features=bottleneck_size,
                                 bias=False)  # bias was true
        self.bottleneck_layer = nn.Linear(
            in_features=bottleneck_size +
            sum([bottleneck_ISI_soma, bottleneck_ISI_dend]),
            out_features=layer_width,
            bias=True)
        self.layers_after_bottleneck = []
        for lv in range(number_of_layers_after_bottleneck):
            layer = nn.Linear(in_features=layer_width,
                              out_features=layer_width,
                              bias=True)
            setattr(self, 'layer_asd_{}'.format(lv), layer)
            self.layers_after_bottleneck.append(layer)
        self.output_layer = nn.Linear(in_features=layer_width,
                                      out_features=output_size,
                                      bias=True)

    def forward(self, X_ISI_MCM_list):
        '''
        X_ISI_list: a list containing two elements.
           First element is X, i.e. the same as in My_model_bottleneck
           Second element is ISI for each trial
        X is synaptic input history (80ms): n_trials x n_cell_types x n_spatial_bins x temporal window width
        ISI_SOMA: n_trials x 1 = time to previous soma spike
        ISI_DEND: n_trials x 1 = time to previous dendritic spike
        '''
        X, ISI_SOMA, ISI_DEND = X_ISI_MCM_list
        assert isinstance(X, torch.Tensor)
        out = self.linear1(X)
        list_ = [out]
        if self.bottleneck_ISI_soma:
            list_ = list_ + [ISI_SOMA]
        if self.bottleneck_ISI_dend:
            list_ = list_ + [ISI_DEND]
        out = torch.cat(list_, axis=1)
        out = self.bottleneck_layer(out)
        for layer in self.layers_after_bottleneck:
            out = self.relu(out)
            out = layer(out)
        out = self.output_layer(out)
        return out


def get_binsize(length, binsize_goal=50):
    '''given a length of a branch, returns number of binsize and number of bins that results in binning closest to 
    the binsize goal'''
    n_bins = length / float(binsize_goal)
    n_bins_lower = I.np.floor(
        n_bins
    )  # Return the floor of the input, element-wise round off the array always goes to the lower integer
    n_bins_lower = I.np.max([n_bins_lower, 1])
    n_bins_upper = I.np.ceil(
        n_bins
    )  # Return the ceiling of the input, element-wise. round off the array always goes to the higher integer
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
    return I.np.digitize(
        value, bins
    )  # Return the 'indices' of the bins to which each value in input array belongs 0.0 <= 0.2 < 1.0


def get_neuron_param_file(
    m
):  # this m should be the model data base which has the data like synaptic activation data
    folder = m['parameterfiles_cell_folder']
    f = [f for f in folder.listdir() if not f.endswith('.pickle')]  #+.keys()
    assert len(f) == 1
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
    all_bins = []
    for index, row in section_distances_df.iterrows():
        n_bins = row['n_bins']
        if n_bins == 'Soma':
            all_bins.append(str(index) + '/' + str(0))
        else:
            for n in range(n_bins):
                all_bins.append(str(index) + '/' + str(n + 1))
    return all_bins


def augment_synapse_activation_df_with_branch_bin(sa_,
                                                  section_distances_df=None,
                                                  syn_weights=None):
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
    sa_faster['EI'] = sa_faster['celltype'].isin(I.excitatory).replace(
        True, 'EXC').replace(False, 'INH')
    if syn_weights:
        sa_faster['syn_weight'] = sa_faster['synapse_type'].map(syn_weights)
    return sa_faster


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


def get_model_stats(mdb, model, best_epoch=None, bottleneck_node=0):
    with open(mdb[model].join('loss'), 'rb') as f:
        losses = I.cloudpickle.load(f)

    epochs = [l[1] for l in losses if l[0] == 'test_sAP_AUROC']
    AUCs = [l[-1] for l in losses if l[0] == 'test_sAP_AUROC']
    loss = [l[-1] for l in losses if l[0] == 'test_loss']

    if best_epoch == None:
        best_epoch = epochs[I.np.argmax(AUCs)] + 1

    with open(mdb[model].join('model__epoch_{}__batch_199'.format(best_epoch)),
              'rb') as f:
        model = I.cloudpickle.load(f)

    # print('max AUC:', max(AUCs), 'min loss:', min(loss), 'epoch:', epochs[best_epoch]+1)
    weights = model.linear1.weight[bottleneck_node].data.cpu().detach().numpy(
    ).reshape(
        2, 260, 80
    )  #- 1 *model.linear1.weight[1].data.cpu().detach().numpy().reshape(2,260,80)
    df = I.pd.DataFrame(losses, columns=['name', 'epoch', 'batch', 'value'])
    train_loss = df[df.name == 'train_loss'].groupby('epoch').value.mean()
    test_loss = df[df.name == 'test_loss'].groupby('epoch').value.mean()

    return epochs, best_epoch, AUCs, train_loss, test_loss, weights


def get_model(mdb, model_name, best_epoch=None):
    with open(mdb[model_name].join('loss'), 'rb') as f:
        losses = I.cloudpickle.load(f)
    epochs = [l[1] for l in losses if l[0] == 'test_sAP_AUROC']
    AUCs = [l[-1] for l in losses if l[0] == 'test_sAP_AUROC']

    if best_epoch == None:
        best_epoch = epochs[I.np.argmax(AUCs)] + 1
    with open(
            mdb[model_name].join(
                'model__epoch_{}__batch_199'.format(best_epoch)), 'rb') as f:
        model = I.cloudpickle.load(f)
    return model


def cartesian_product(*arrays):
    import numpy
    la = len(arrays)
    dtype = numpy.result_type(*arrays)
    arr = numpy.empty([len(a) for a in arrays] + [la], dtype=dtype)
    for i, a in enumerate(numpy.ix_(*arrays)):
        arr[..., i] = a
    return arr.reshape(-1, la)
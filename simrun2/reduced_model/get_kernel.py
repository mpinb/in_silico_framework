import os
import numpy as np
import pandas as pd
import dask
import matplotlib.pyplot as plt
import warnings
import collections
from model_data_base import utils as mdb_utils
from functools import partial


#############################################
# general methods
##############################################
def concatenate_return_boundaries(values, axis=0):
    X = np.concatenate(values, axis=axis)
    upper_bounds = np.cumsum([v.shape[axis] for v in values])
    lower_bounds = [0] + list(upper_bounds[:-1])
    boundaries = list(zip(lower_bounds, upper_bounds))
    return X, boundaries


def spike_in_interval(st, tmin, tmax):
    return ((st >= tmin) & (st < tmax)).any(axis=1)


def compare_lists_by_none_values(l1, l2):
    for x, y in zip(l1, l2):
        if x is None:
            if y is not None:
                return False
        if y is None:
            if x is not None:
                return False
    return True


##################################################
# methods for selecting synapse activation data out of a model_data_base instance
# and to convert it to a format suitable for scipy.linear_discriminant_analysis
#####################################################
def _kernel_preprocess_data(mdb_list, keys_to_synapse_activation_data, \
                            synapse_acivation_window_min, synapse_activation_window_max, \
                            output_window_min, output_window_max, aggfun = None):
    '''takes a dictionary containing synapse activation data. This data is then
    concatenated to one large matrix, which can be used for the lda estimator.
    
    data_dict has to have the following format:
        key: ModelDataBase - instance
        value: tuple containing keys to the synapse activation date
    
    Returns:
     - the large matrix
     - spike_times
     - a dictionary with the same keys as data_dict. Values are the respective columns
       in which this data can be found in the large matrix'''

    ys = []
    Xs = []
    spike_before = []
    sts = []
    for mdb in mdb_list:
        # get spike times for current mdb
        st = mdb['spike_times']
        y = np.array(spike_in_interval(st, output_window_min,
                                       output_window_max))
        # get values for current mdb
        mdb_values = {k: mdb[k][:, synapse_acivation_window_min:synapse_activation_window_max] \
                      for k in keys_to_synapse_activation_data}

        if aggfun is None:
            keys = keys_to_synapse_activation_data
            mdb_values_list = [mdb_values[k] for k in keys]
        else:
            keys, mdb_values_list = aggfun(mdb_values)

        X, boundaries = concatenate_return_boundaries(mdb_values_list, axis=1)

        ys.append(y)
        Xs.append(X)
        sts.append(st)

    y = np.concatenate(ys, axis=0)
    X = np.concatenate(Xs, axis=0)
    st = pd.concat(sts)
    return X, dict(list(zip(keys, boundaries))), y, st


import six


def _kernel_dict_from_clfs(clfs, boundaries):
    '''splits result of lda estimator based on boundaries'''
    kernel_dict = []
    for clf in clfs['classifier_']:
        out = dict()
        for key, b in six.iteritems(boundaries):
            out[key] = clf.coef_[0].squeeze()[b[0]:b[1]]
        kernel_dict.append(out)
    return kernel_dict


#################################
# methods specific for the task of building a reduced model
#################################


def interpolate_lookup_series(lookup_series):
    stepsize = 1
    diff = max(lookup_series.index) - min(lookup_series.index)
    #print 'lookup_series:', diff, len(lookup_series)
    index = np.arange(int(min(lookup_series.index) - 0.3 * diff), \
                                                   int(max(lookup_series.index) + 0.3 * diff), \
                                                   stepsize)
    s = pd.Series([np.NaN] * len(index), index=index)
    s.iloc[0] = 0
    s[lookup_series.index] = lookup_series
    return s.interpolate(method='linear')

def get_lookup_series_from_lda_values_spike_data(lda_values, spike, spike_before = None,\
                                                 lookup_series_stepsize = 3):
    '''
    
    lda_values: one-dimensional array containing lda_values of trail
    spike: one-dimensional array containing True / False
    mask: one-dimensional array containing True / False.
        If True: the respective trail will be ignored.
    '''
    pdf2 = pd.DataFrame(dict(lda_values=lda_values, spike=spike))
    if spike_before is not None:
        pdf = pdf2[~spike_before]
    else:
        pdf = pdf2
    groupby_ = (pdf.lda_values / lookup_series_stepsize).round().astype(int)
    groupby_ = groupby_ * lookup_series_stepsize
    lookup_series = pdf.groupby(groupby_).apply(
        lambda x: len(x[x.spike]) / float(len(x)))
    return interpolate_lookup_series(lookup_series)


##############################
# visualize reduced model
##############################
def get_plt_axis():
    fig = plt.figure(figsize=(15, 3), dpi=300)
    ax = fig.add_subplot(111)
    return fig, ax


def plot_kernel_dict(kernel_dict, ax=None):
    if ax is None:
        fig, ax = get_plt_axis()
    ax.set_title('kernel shape')
    ax.set_xlabel('# time bin')
    # plot kernel
    import six
    for lv in range(len(kernel_dict)):
        d = kernel_dict[lv]
        ax.set_prop_cycle(None)
        for k, v in six.iteritems(d):
            if lv == 0:
                ax.plot(v, label=k)
            else:
                ax.plot(v)
    plt.legend()


def plot_LUT(lookup_series, lda_values=None, min_items=None, ax=None):
    if ax is None:
        fig, ax = get_plt_axis()
    # plot data distribution and probability curve
    for lv in range(len(lookup_series)):
        if lda_values is not None:
            binned_lda_values = pd.Series(lda_values[lv]).round().astype(int).\
                                    value_counts().sort_index()
            binned_lda_values.plot(secondary_y=True, color='g')
        ls = lookup_series[lv]
        ls.plot(ax=ax, color='lightblue')
        if min_items:
            max_ = max(binned_lda_values[binned_lda_values > min_items].index)
            min_ = min(binned_lda_values[binned_lda_values > min_items].index)

            ls = ls[(ls.index <= max_) & (ls.index >= min_)]
        ls.plot(ax=ax, color='b')
        ax.set_ylabel('p_spike')
        ax.set_ylabel('# datapoints')
    ax.set_xlabel('lda_value')


##################################
# classes managing all the steps necessary to build a reduced model
##################################


class ReducedLdaModelResult():

    def __init__(self, RM, lda_dict, lda_values, p_spike):
        self.RM = RM
        self.lda_dict = lda_dict
        self.lda_values = lda_values
        self.p_spike = p_spike


class ReducedLdaModel():
    def __init__(self, \
                keys_to_synapse_activation_data, \
                synapse_activation_window_width = 80, \
                synapse_activation_window_min = None, \
                synapse_activation_window_max = None,\
                output_window_min = 255, output_window_max = 265, refractory_period = 0,\
                normalize_group_size = True, test_size = 0.4, verbosity = 2, \
                lookup_series_stepsize = 5, cache = True, aggfun = None):

        dummy = [
            synapse_activation_window_min, synapse_activation_window_max,
            synapse_activation_window_width
        ]
        if compare_lists_by_none_values(dummy, [1, 1, 1]):
            assert synapse_activation_window_width == synapse_activation_window_max - synapse_activation_window_min
        elif compare_lists_by_none_values(dummy, [None, None, 1]):
            synapse_activation_window_max = output_window_max
            synapse_activation_window_min = synapse_activation_window_max - synapse_activation_window_width
        elif compare_lists_by_none_values(dummy, [1, None, 1]):
            synapse_activation_window_max = synapse_activation_window_min + synapse_activation_window_width
        elif compare_lists_by_none_values(dummy, [1, 1, None]):
            pass
        else:
            raise ValueError(
                "synapse_activation_window not sufficiently defined.")

        self.keys_to_synapse_activation_data = keys_to_synapse_activation_data
        self.synapse_activation_window_min = synapse_activation_window_min
        self.synapse_activation_window_max = synapse_activation_window_max
        self.output_window_min = output_window_min
        self.output_window_max = output_window_max
        self.refractory_period = refractory_period
        self.normalize_group_size = normalize_group_size
        self.test_size = test_size
        self.verbosity = verbosity
        self.lookup_series_stepsize = lookup_series_stepsize
        self.aggfun = aggfun

        if cache:
            self.apply_rolling = mdb_utils.cache(self.apply_rolling)
            self.apply_static = mdb_utils.cache(self.apply_static)

    def fit(self, mdb_list, clfs=None):
        self.mdb_list = mdb_list
        X, boundaries, y, st = _kernel_preprocess_data(mdb_list, \
                                self.keys_to_synapse_activation_data, \
                                self.synapse_activation_window_min, \
                                self.synapse_activation_window_max, \
                                self.output_window_min, self.output_window_max, \
                                aggfun = self.aggfun)

        self.y = y
        self.st = st
        self.spike_before =  spike_in_interval(st, \
                                               self.output_window_min - self.refractory_period, \
                                               self.output_window_min).values

        import Interface as I
        if clfs is None:
            self.clfs = I.lda_prediction_rates(X[~self.spike_before], y[~self.spike_before], \
                                           verbosity = self.verbosity, return_ = 'all', \
                                           normalize_group_size = self.normalize_group_size, \
                                           test_size = self.test_size)
        else:
            self.clfs = clfs

        # added to keep the normalization that was present at the timepoint of development
        for lv, x in enumerate(self.clfs['classifier_']):
            norm = 7.260991424242837 / I.np.sqrt(sum([c**2 for c in x.coef_[0]
                                                     ]))
            x.coef_[0] = x.coef_[
                0] * norm  # normalization factor, as length of vector changes between python versions

        self.kernel_dict = _kernel_dict_from_clfs(self.clfs, boundaries)
        ## todo: kernel_dicts

        self.lda_value_dicts = []
        self.lookup_series = []
        self.lda_values = []
        for kernel_dict in self.kernel_dict:
            lda_values_dict = {}
            for k in list(boundaries.keys()):
                b = boundaries[k]
                lda_values_dict[k] = np.dot(X[:, b[0]:b[1]], kernel_dict[k])
            lda_values = sum(lda_values_dict.values())
            lookup_series = get_lookup_series_from_lda_values_spike_data(lda_values, y, \
                                         lookup_series_stepsize = self.lookup_series_stepsize, \
                                         spike_before = self.spike_before)
            self.lookup_series.append(lookup_series)
            self.lda_value_dicts.append(lda_values_dict)
            self.lda_values.append(lda_values)

    def get_lookup_series_for_different_refractory_period(
            self, refractory_period):
        spike_before =  spike_in_interval(self.st,\
                                          self.output_window_min - refractory_period, \
                                          self.output_window_min).values

        out = []
        for lv in range(len(self.kernel_dict)):
            dummy = get_lookup_series_from_lda_values_spike_data(
                self.lda_values[lv],
                self.y,
                lookup_series_stepsize=self.lookup_series_stepsize,
                spike_before=spike_before)
            out.append(dummy)
        return out

    def plot(self, return_fig=False, min_items=0):
        fig1, ax = get_plt_axis()
        plot_kernel_dict(self.kernel_dict, ax)
        fig2, ax = get_plt_axis()
        plot_LUT(self.lookup_series, self.lda_values, min_items, ax)
        ax.set_title('probability of spike in interval '\
                      + '[{output_window_min}:{output_window_max}] depending on lda_value, refractory_period = {ref}'
                      .format(output_window_min = self.output_window_min, \
                              output_window_max = self.output_window_max, \
                              ref = self.refractory_period))
        ax.set_xlabel('lda_value')
        if return_fig:
            return fig1, fig2

    def get_minimodel_static(self, model_number=0):
        '''returns partial, which can be called with keywords mdb or data_dict.
        
        The partial is constructed such that it can be serialized fast, allowing
        efficient multiprocessing. This is the recommended way of sending a reduced
        model through a network connection.'''
        return partial(_apply_static_helper, self.lookup_series[model_number], \
                                 self.synapse_activation_window_min, \
                                 self.synapse_activation_window_max, \
                                 self.kernel_dict[model_number])

    def apply_static(self, data, model_number=0):
        rm = self.get_minimodel_static(model_number)
        return rm(data)

    def get_minimodel_rolling(self, refractory_period=0, model_number=0):
        '''returns partial, which can be called with keywords mdb or data_dict.
        
        The partial is constructed such that it can be serialized fast, allowing
        efficient multiprocessing. This is the recommended way of sending a reduced
        model through a network connection.'''
        from . import spiking_output
        # nonlinearity_LUT has a different format in the spiking output format:
        # the key should be the refractory period, the value a single pd.Series object
        # containing the LUT
        nonlinearity_LUT = {refractory_period:  \
                            self.get_lookup_series_for_different_refractory_period(refractory_period)[model_number]}
        rm = spiking_output.get_reduced_model(self.kernel_dict[model_number], \
                                         nonlinearity_LUT, \
                                         refractory_period, \
                                         combine_fun = sum, \
                                         LUT_resolution = 1)

        return rm

    def apply_rolling(self):
        raise NotImplementedError()

    def apply_static_param(self):
        raise NotImplementedError()

    def apply_rolling_param(self):
        raise NotImplementedError()


def _apply_static_helper(lookup_series, min_index, max_index, kernel_dict,
                         data):
    '''optimized to require minimal datatransfer to allow efficient multiprocessing'''
    # preparing data
    lda_value_dict = {k: np.dot(data[k][:, min_index:max_index], \
                          kernel_dict[k]) for k in list(kernel_dict.keys())}
    lda_values = sum(lda_value_dict.values())
    indices = lda_values.round().astype(int)
    if max(indices) > max(lookup_series.index):
        warnings.warn(
            "lda values leave range of training data by more than 30%!")
        indices[indices > max(lookup_series.index)] = max(lookup_series.index)
    if min(indices) < min(lookup_series):
        warnings.warn(
            "lda values leave range of training data by more than 30%!")
        indices[indices < min(lookup_series.index)] = min(lookup_series.index)
    p_spike = lookup_series.loc[indices]
    return ReducedLdaModelResult(None, lda_value_dict, lda_values, p_spike)


###################################
# methods to get special kernels
###################################
def get_kernel_C2_grid(keys_to_synapse_activation_data = [
        ('synapse_activation', 'binned_t1', 'EI', 'proximal','EXC', 'prox'),
        ('synapse_activation', 'binned_t1', 'EI', 'proximal','INH', 'prox')], \
                synapse_activation_window_width = 80, \
                synapse_activation_window_min = None, \
                synapse_activation_window_max = None,\
                output_window_min = 255, output_window_max = 265, refractory_period = 0,\
                normalize_group_size = True, test_size = 0.4, verbosity = 2, \
                lookup_series_stepsize = 5, cache = True, mdbs = 'mdbs_inhrobert'):
    import Interface as I
    '''returns : clfs, lookup_series, pdf'''

    def spike_in_interval(st, tmin, tmax):
        return ((st >= tmin) & (st < tmax)).any(axis=1)

    def get_mdbs_inhrobert():
        basedir = '/nas1/Data_arco/results/20170222_SuW_stimulus_in_C2_grid/'
        stim = ['B1', 'B2', 'B3', 'C1', 'C3', 'D1', 'D2', 'D3']
        mdbs = {
            s: I.ModelDataBase(I.os.path.join(basedir, s, 'mdb')) for s in stim
        }
        mdbs['C2'] = I.ModelDataBase(
            '/nas1/Data_arco/results/20170214_use_cell_grid_with_soma_at_constant_depth_below_layer_4_to_evaluate_location_dependency_of_evoked_responses/mdb/'
        )
        return mdbs

    def get_mdbs_inh24():
        basedir = '/nas1/Data_arco/results/20170509_grid_with_tuned_INH_v2/mdbs/{stim}'
        stim = ['B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'D3']
        mdbs = {s: I.ModelDataBase(basedir.format(stim=s)) for s in stim}
        return mdbs

    if mdbs == 'mdbs_inhrobert':
        mdbs = get_mdbs_inhrobert()
    elif mdbs == 'mdbs_inh24':
        mdbs = get_mdbs_inh24()
    else:
        pass  # mdbs needs to be a dictionary

    #extract training values
    rm = ReducedLdaModel(keys_to_synapse_activation_data, \
                synapse_activation_window_width, \
                synapse_activation_window_min, \
                synapse_activation_window_max,\
                output_window_min, output_window_max, refractory_period,\
                normalize_group_size, test_size, verbosity, \
                lookup_series_stepsize, cache)

    rm.fit(list(mdbs.values()))
    return rm


get_kernel_C2_grid_cached = mdb_utils.cache(get_kernel_C2_grid)

# def C2_grid_10ms_to_20ms_poststim():
#     '''returns : clfs, lookup_series, pdf'''
#     warnings.warn(DeprecationWarning("Deprecated: Use get_kernel_C2_grid instead"))
#     return get_kernel_C2_grid(output_window_min = 255, output_window_max = 265)

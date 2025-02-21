import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings, six
from data_base import utils as db_utils
from functools import partial
from data_base.analyze.LDA import prediction_rates


#############################################
# general methods
##############################################
def concatenate_return_boundaries(values, axis=0):
    """Concatenate an array of numpy arrays and return the boundaries of the original arrays.
    
    Args:
        values (list): List of numpy arrays
        axis (int): Axis along which to concatenate the arrays
        
    Raises:
        ValueError: If the arrays do not have the same shape along the non-concatenating axes
        
    Example:
    
        >>> a = np.array([[1, 2], [3, 4]])
        >>> b = np.array([[5, 6], [7, 8], [9, 10]])
        >>> X, boundaries = concatenate_return_boundaries([a, b], axis=0)
        >>> X
        array([[ 1,  2],  # 0
               [ 3,  4],  # 1
               [ 5,  6],  # 2
               [ 7,  8],  # 3
               [ 9, 10]]  # 4
        )
        >>> boundaries
        [(0, 2), (2, 5)]

        
    Returns:
        tuple: 2D array of concatenated values and a list of tuples containing the boundaries of the original arrays
    """
    X = np.concatenate(values, axis=axis)
    upper_bounds = np.cumsum([v.shape[axis] for v in values])
    lower_bounds = [0] + list(upper_bounds[:-1])
    boundaries = list(zip(lower_bounds, upper_bounds))
    return X, boundaries


def spike_in_interval(st, tmin, tmax):
    return ((st >= tmin) & (st < tmax)).any(axis=1)


def compare_lists_by_none_values(l1, l2):
    """Compare two lists by their None values.
    
    Args:
        l1 (list): List of values
        l2 (list): List of values
        
    Returns:
        bool: True if the lists have ``None`` at the same positions, False otherwise
    """
    for x, y in zip(l1, l2):
        if x is None:
            if y is not None:
                return False
        if y is None:
            if x is not None:
                return False
    return True


##################################################
# methods for selecting synapse activation data out of a data_base instance
# and to convert it to a format suitable for scipy.linear_discriminant_analysis
#####################################################
def _kernel_preprocess_data(
    db_list, 
    keys_to_synapse_activation_data,
    synapse_acivation_window_min, 
    synapse_activation_window_max,
    output_window_min, 
    output_window_max, 
    aggfun = None):
    '''Extract synapse activations and spike times from a list of data_base instances.
    
    For each simrun-inited database, the synapse activations are extracted and concatenated
    to one large matrix of size ``(n_synapses, n_trials/simrun * n_simrun_databases). 
    The target variable (i.e. spike times) is also extracted, truncated to the desired time window, and concatenated to one large array.
    
    Args:
        db_list (list): List of data_base instances
        keys_to_synapse_activation_data (list): List of keys to the :ref:`syn_activation_format` data
        synapse_acivation_window_min (int): Start of the :ref:`syn_activation_format` data window
        synapse_activation_window_max (int): End of the :ref:`syn_activation_format` window
        output_window_min (int): Start of the output window
        output_window_max (int): End of the output window
        aggfun (function): Function to aggregate :ref:`syn_activation_format` data. If None, the data is concatenated.

    
    Returns:
        tuple: 4D tuple containing:
        
            - 2D matrix (synapse x time) of :ref:`syn_activation_format` data for all included databases.
            - Dictionary mapping synapse activation keys to the boundaries of the concatenated data
            - 1D array of spike times, truncated to the output window
            - 1D array of all spike times
    '''

    ys = []
    Xs = []
    spike_before = []
    sts = []
    for db in db_list:
        # Target variable y: get spike times for current db
        st = db['spike_times']
        y = np.array(spike_in_interval(st, output_window_min, output_window_max))
        
        # Input X: get values for current db
        db_values = {
            k: db[k][:, synapse_acivation_window_min:synapse_activation_window_max]
            for k in keys_to_synapse_activation_data
            }
        if aggfun is None:
            SA_locations = keys_to_synapse_activation_data
            db_values_list = [db_values[k] for k in SA_locations]
        else:
            SA_locations, db_values_list = aggfun(db_values)
        X, concat_db_divisions = concatenate_return_boundaries(db_values_list, axis=1)

        # Concatenate data
        ys.append(y)
        Xs.append(X)
        sts.append(st)

    y = np.concatenate(ys, axis=0)
    X = np.concatenate(Xs, axis=0)
    SA_location_db_division_map = dict(list(zip(SA_locations, concat_db_divisions)))
    st = pd.concat(sts)
    return X, SA_location_db_division_map, y, st


def _kernel_dict_from_clfs(clfs, boundaries):
    '''Split the result of :py:class:`~simrun.reduced_model.get_kernel.LDA` per data base
    
    
    
    '''
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
    index = np.arange(
        int(min(lookup_series.index) - 0.3 * diff),
        int(max(lookup_series.index) + 0.3 * diff),
        stepsize)
    s = pd.Series([np.NaN] * len(index), index=index)
    s.iloc[0] = 0
    s[lookup_series.index] = lookup_series
    return s.interpolate(method='linear')


def get_lookup_series_from_lda_values_spike_data(
        lda_values, 
        spike, 
        spike_before = None,
        lookup_series_stepsize = 3):
    '''
    
    lda_values: one-dimensional array containing lda_values of trial
    spike: one-dimensional array containing True / False
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
    """    
    As a function function of WNI what is the P of observing an AP?
    
    LUT is a mapping between WNI and P
    """
    if ax is None:
        fig, ax = get_plt_axis()
    # plot data distribution and probability curve
    for lv in range(len(lookup_series)):
        if lda_values is not None:
            binned_lda_values = pd.Series(
                lda_values[lv]).round().astype(int).value_counts().sort_index()
            binned_lda_values.plot(secondary_y=True, color='g', label="LUT")
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
    """Convenience dataclass to store the result of a :py:class:`ReducedLdaModel`.
    
    Used to minimize data transfer during parallel computing.
    """
    def __init__(self, RM, lda_dict, lda_values, p_spike):
        """
        Args:
            RM (ReducedLdaModel): The model that was used to compute the result
            lda_dict (dict): Dictionary 
        """
        self.RM = RM
        self.lda_dict = lda_dict
        self.lda_values = lda_values
        self.p_spike = p_spike

class ReducedLdaModel():
    """Fit the spike probability from synaptic input with LDA.
    
    Given a window of synaptic input data, this class fits an LDA model to predict the probability of a spike
    in a given output window. The model is then used to compute a lookup table (LUT) that maps the LDA value to the
    probability of a spike. The input synapse activation time window can, but does not ned to overlap with the output window.
    
    If you have the kernel and non-linearity, use this class as a model to compute AP timings
    from SA input.
    
    """
    def __init__(
        self,
        keys_to_synapse_activation_data,
        synapse_activation_window_width = 80,
        synapse_activation_window_min = None,
        synapse_activation_window_max = None,
        output_window_min = 255, 
        output_window_max = 265, 
        refractory_period = 0,
        normalize_group_size = True, 
        test_size = 0.4, 
        verbosity = 2,
        lookup_series_stepsize = 5, 
        cache = True, 
        aggfun = None
        ):
        """
        Args:
            keys_to_synapse_activation_data (list): 
                List of keys to the :ref:`syn_activation_format` data for each simrun-inited database that will be used to fit the model.
            synapse_activation_window_width (int): Width of the synapse activation window. Default is 80.
            synapse_activation_window_min (int): Start of the synapse activation window. Default is None.
            synapse_activation_window_max (int): End of the synapse activation window. Default is None.
            output_window_min (int): Start of the prediction time window. Default is 255.
            output_window_max (int): End of the prediction time window. Default is 265.
            refractory_period (int): 
                Period before the prediction start for which to omit input data. 
                Input data that has spikes between ``output_window_min - refractory_period`` and ``output_window_min`` 
                will be omitted from the fit & predict process. 
                Default is 0.
            normalize_group_size (bool): Subsample data so that both classes have the same number of samples. Default is True.
            test_size (float): Fraction of the data to use as test data. Default is 0.4.
            verbosity (int): Level of verbosity. Options are ``0``, ``1``, or ``2`` (default).
            lookup_series_stepsize (int): 
                Amount of bins for the lookup series. 
                Default is 5, i.e. the lookup series will be binned in ``[0, 0.2), [0.2, 0.4), ... [0.8, 1.)``
            
        """

        self.synapse_activation_window_width = synapse_activation_window_width
        self.synapse_activation_window_min = synapse_activation_window_min
        self.synapse_activation_window_max = synapse_activation_window_max
        self.output_window_min = output_window_min
        self.output_window_max = output_window_max
        self._check_time_window()
        
        self.keys_to_synapse_activation_data = keys_to_synapse_activation_data
        self.refractory_period = refractory_period
        self.normalize_group_size = normalize_group_size
        self.test_size = test_size
        self.verbosity = verbosity
        self.lookup_series_stepsize = lookup_series_stepsize
        self.aggfun = aggfun

        if cache:
            self.apply_rolling = db_utils.cache(self.apply_rolling)
            self.apply_static = db_utils.cache(self.apply_static)

    def _check_time_window(self):
        dummy = [
            self.synapse_activation_window_min, 
            self.synapse_activation_window_max,
            self.synapse_activation_window_width
        ]
        if compare_lists_by_none_values(dummy, [1, 1, 1]):
            assert self.synapse_activation_window_width == self.synapse_activation_window_max - self.synapse_activation_window_min
        elif compare_lists_by_none_values(dummy, [None, None, 1]):
            self.synapse_activation_window_max = self.output_window_max
            self.synapse_activation_window_min = self.synapse_activation_window_max - self.synapse_activation_window_width
        elif compare_lists_by_none_values(dummy, [1, None, 1]):
            self.synapse_activation_window_max = self.synapse_activation_window_min + self.synapse_activation_window_width
        elif compare_lists_by_none_values(dummy, [1, 1, None]):
            pass
        else:
            raise ValueError("synapse_activation_window not sufficiently defined.")
        
    
    def fit(self, db_list, clfs=None):
        """Fit an LDA model to synapse activations and save the prediction rates.
        
        This method iterates over all databases in :paramref:`db_list` and extracts the synapse activation data
        using the keys provided in :paramref:`keys_to_synapse_activation_data`. The data is then used to fit an LDA model.
        The predictions of the LDA model are saved in :paramref:`clfs`.
        
        Args:
            db_list (list): List of data_base instances
            clfs (dict): Dictionary describing a fitted LDA model. If None, a new fit is performed.
            
        See also:
            :py:meth:`data_base.analyze.LDA.prediction_rates` for the output format of :paramref:`clfs`,
            i.e. an LDA and its predictions.
        """
        self.db_list = db_list
        X, SA_key_to_db_division_map, y, st = _kernel_preprocess_data(
            self.db_list,
            self.keys_to_synapse_activation_data,
            self.synapse_activation_window_min,
            self.synapse_activation_window_max,
            self.output_window_min, self.output_window_max,
            aggfun = self.aggfun)

        self.y = y
        self.st = st
        self.spike_before =  spike_in_interval(
            st,
            self.output_window_min - self.refractory_period,
            self.output_window_min).values

        if clfs is None:  # fit new one
            self.clfs = prediction_rates(
                X[~self.spike_before], 
                y[~self.spike_before],
                verbosity = self.verbosity, 
                return_ = 'all',
                normalize_group_size = self.normalize_group_size,
                test_size = self.test_size)  # big dictionary, keys: score[all, 0, 1, rocauc, * ], classifier_, value_counts
        else:
            self.clfs = clfs

        # added to keep the normalization that was present at the timepoint of development
        for _, x in enumerate(self.clfs['classifier_']):
            norm = 7.260991424242837 / np.sqrt(sum([c**2 for c in x.coef_[0]]))
            x.coef_[0] = x.coef_[0] * norm  # normalization factor, as length of vector changes between python versions

        self.kernel_dict = _kernel_dict_from_clfs(self.clfs, SA_key_to_db_division_map)
        ## TODO: kernel_dicts

        self.lda_value_dicts = []
        self.lookup_series = []
        self.lda_values = []
        for kernel_dict in self.kernel_dict:
            lda_values_dict = {}
            for SA_key in list(SA_key_to_db_division_map.keys()):
                db_divisions = SA_key_to_db_division_map[SA_key]
                lda_spike_predictions = np.dot(X[:, db_divisions[0]:db_divisions[1]], kernel_dict[SA_key])
                lda_values_dict[SA_key] = lda_spike_predictions
            lda_values = sum(lda_values_dict.values())
            lookup_series = get_lookup_series_from_lda_values_spike_data(
                lda_values, y,
                lookup_series_stepsize = self.lookup_series_stepsize,
                spike_before = self.spike_before)
            self.lookup_series.append(lookup_series)
            self.lda_value_dicts.append(lda_values_dict)
            self.lda_values.append(lda_values)

    def get_lookup_series_for_different_refractory_period(
            self, 
            refractory_period):
        spikes_in_refract =  spike_in_interval(
            self.st,
            self.output_window_min - refractory_period,
            self.output_window_min
            ).values

        out = []
        for lv in range(len(self.kernel_dict)):
            dummy = get_lookup_series_from_lda_values_spike_data(
                self.lda_values[lv],
                self.y,
                lookup_series_stepsize=self.lookup_series_stepsize,
                spike_before=spikes_in_refract)
            out.append(dummy)
        return out

    def plot(self, return_fig=False, min_items=0):
        fig1, ax = get_plt_axis()
        plot_kernel_dict(self.kernel_dict, ax)
        fig2, ax = get_plt_axis()
        plot_LUT(self.lookup_series, self.lda_values, min_items, ax)
        ax.set_title(
            "probability of spike in interval [{output_window_min}:{output_window_max}] depending on lda_value\n" \
            "refractory_period = {ref}".format(
                output_window_min = self.output_window_min,
                output_window_max = self.output_window_max,
                ref = self.refractory_period))
        ax.set_xlabel('lda_value')
        if return_fig:
            return fig1, fig2

    def get_minimodel_static(self, model_number=0):
        '''returns partial, which can be called with keywords db or data_dict.
        
        The partial is constructed such that it can be serialized fast, allowing
        efficient multiprocessing. This is the recommended way of sending a reduced
        model through a network connection.'''
        return partial(
            _apply_static_helper, 
            self.lookup_series[model_number],
            self.synapse_activation_window_min,
            self.synapse_activation_window_max,
            self.kernel_dict[model_number])

    def apply_static(self, DATA_DICT, model_number=0):
        rm = self.get_minimodel_static(model_number)
        return rm(DATA_DICT)

    def get_minimodel_rolling(self, refractory_period=0, model_number=0):
        '''returns partial, which can be called with keywords db or data_dict.
        
        The partial is constructed such that it can be serialized fast, allowing
        efficient multiprocessing. This is the recommended way of sending a reduced
        model through a network connection.'''
        from . import spiking_output
        # nonlinearity_LUT has a different format in the spiking output format:
        # the key should be the refractory period, the value a single pd.Series object
        # containing the LUT
        nonlinearity_LUT = {
            refractory_period:  self.get_lookup_series_for_different_refractory_period(refractory_period)[model_number]
            }
        rm = spiking_output.get_reduced_model(
            self.kernel_dict[model_number],
            nonlinearity_LUT,
            refractory_period,
            combine_fun = sum,
            LUT_resolution = 1)

        return rm

    # TODO: implement convolution
    
    def apply_rolling(self):
        """For convolutional models.
        
        Roll over time-window of SA, and then you get a time-dependent WNI and spike P.
        You could then draw from that distribution to sample APs.
        As soon as a sample is taken, the refractory period is applied.
        
        :skip-doc:
        """
        raise NotImplementedError()

    def apply_static_param(self):
        """:skip-doc:"""
        raise NotImplementedError()

    def apply_rolling_param(self):
        """:skip-doc:"""
        raise NotImplementedError()


def _apply_static_helper(
    lookup_series, 
    min_index, 
    max_index, 
    kernel_dict,
    data):
    '''optimized to require minimal datatransfer to allow efficient multiprocessing'''
    # preparing data
    lda_value_dict = {
        k: np.dot(data[k][:, min_index:max_index], kernel_dict[k]) 
        for k in list(kernel_dict.keys())
        }
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



# def C2_grid_10ms_to_20ms_poststim():
#     '''returns : clfs, lookup_series, pdf'''
#     warnings.warn(DeprecationWarning("Deprecated: Use get_kernel_C2_grid instead"))
#     return get_kernel_C2_grid(output_window_min = 255, output_window_max = 265)

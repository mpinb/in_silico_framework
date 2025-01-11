"""
This module provides code to analyze the results of a random walk exploration through biophysical parameter space.
See :py:mod:`~biophysics_fitting.exploration_from_seedpoint.RW` for more information.
"""

import Interface as I
from pickle import UnpicklingError

def read_parameters(
    seed_folder,
    particle_id,
    normalized=False,
    only_in_space=False,
    only_return_parameters=True,
    param_names=None,
    param_ranges=None
    ):
    """
    Read the biophysical parameters that were explored during a RW exploration.
    To read the full results, use :py:meth:`~biophysics_fitting.exploration_from_seedpoint.RW_analysis.read_pickle` instead.
    See: :py:class:`~biophysics_fitting.exploration_from_seedpoint.RW.RW` for more info.
    
    Args:
        seed_folder (str): path to the folder that contains the RW exploration result for a particular seed.
        
    Returns:
        pd.DataFrame: a dataframe containing all biophysical parameters explored by a single particle.
    """
    df = read_pickle(seed_folder, particle_id)
    if only_in_space:
        df2 = df.dropna(subset=objectives_2BAC + objectives_step)
        df3 = df2[df2[objectives_2BAC].max(axis=1) < 3.2]
        df4 = df3[df3[objectives_step].max(axis=1) < 4.5]
        df = df4
    if only_return_parameters:
        df = df[param_names]
    else:
        assert normalized == False
    if normalized:
        df = (df - param_ranges['min']) / (param_ranges['max'] -
                                           param_ranges['min'])
    df['particle_id'] = particle_id
    return df


def robust_read_pickle(path):
    """
    Read a pickled dataframe. If it cannot be read, still return a dataframe, containing an error as content.
    Useful for when you don't want your code to error during some large-scale analysis.
    
    Args:
        path (str): path to the pickled dataframe
        
    Returns:
        pd.DataFrame | pd.Series: the pickled DataFrame if reading was succesful, a pd.Series otherwise. Both contain the key 'init_error', specifying whether or not the read was succesful.
    """
    try:
        df = I.pd.read_pickle(path) 
        df['init_error'] = ''
        return df
    # except (UnpicklingError, EOFError) as e:
    except:
        return I.pd.Series({"init_error":"Could not read {}".format(1)}).to_frame('init_error')
        
def read_pickle(seed_folder, particle_id):
    """
    Read the results of a single particle of a RW exploration.
    
    Args:
        seed_folder (str): the path of the directory corresponding to a seedpoint.
        particle_id (str): the particle id
        
    Returns:
        pd.DataFrame: The results of the RW exploration of a single particle.
    """
    path = I.os.path.join(seed_folder, str(particle_id))
    df_names = [p for p in I.os.listdir(path) if p.endswith('.pickle')]
    df_names = sorted(df_names, key=lambda x: int(x.split('.')[0]))
    dfs = [robust_read_pickle(I.os.path.join(path, p)) for p in df_names]
    if len(dfs) == 0:
        return 'empty'
    df = I.pd.concat(dfs).reset_index(drop=True)
    df['iteration'] = df.index
    df['particle_id'] = particle_id
    return df

def read_all(basedir, n_particles_start = 0, n_particles_end = 1000):
    """
    Read the results of all directories contained within some base directory, independent of which seepdoint or particle.
    """
    fun = I.dask.delayed(read_pickle)
    ds = [fun(basedir, i) for i in range(n_particles_start, n_particles_end)]
    return ds


class Load:
    """Class for efficiently loading exploration results
    
    Uses DASK to parallellize loading in large datasets."""

    def __init__(self, client, path, n_particles=1000):
        self.path = path
        self.n_particles = n_particles
        self.delayeds = read_all(path, n_particles_end=n_particles)
        self.futures = client.compute(self.delayeds)

        self.df = None

    def get_df(self):
        if self.df is None:
            self.df = I.dask.dataframe.from_delayed(self.futures)
        return self.df

    def get_futures(self):
        return self.futures


def get_inside_fraction(l):
    """Print the fraction of models that are inside the objective space.
    
    The exploration results contain a column "inside" that specifies whether or
    not a model is inside the objective space, i.e. below all thresholds for the objectives.
    
    Args:
        l (Load): the Load object containing the exploration results
        
    Returns:
        None. prints out the fraction of models that are inside the objective space."""
    df = l.get_df()
    n_models = df.shape[0].compute()
    n_inside = df[df.inside].shape[0].compute()
    frac = n_inside / n_models
    print('n_models: {}, n_inside: {}, frac: {}'.format(n_models, n_inside,
                                                        frac))
    
    
# analysis functions
def normalize(df, params):
    """Normalize a pd.DataFrame according to the values of specified parameters.
    
    Args:
        df (pd.DataFrame): the dataframe to normalize
        params (pd.DataFrame): a dataframe containing the min and max values for each parameter
        
    Returns:
        pd.DataFrame: the normalized dataframe"""
    return (df-params['min'])/(params['max'] - params['min'])

idx = I.pd.IndexSlice

def get_param_range_evolution_from_ddf(ddf, params, return_mi_ma = False):
    """Compute the range of parameters explored by a RW exploration, as a fraction of the total parameter range.
    
    Args:
        ddf (dask.dataframe): the exploration results
        params (pd.DataFrame): the parameter ranges
        return_mi_ma (bool): whether or not to return the min and max values of the parameter ranges separately, rather than a fraction.
        
    Returns:
        pd.DataFrame: the range of parameters explored by the RW exploration. If return_mi_ma is True, returns the min and max values of the parameter ranges."""
    assert(isinstance(params, I.pd.DataFrame))
    param_names = list(params.index)
    def _helper(df):
        return df[param_names + ['iteration']].groupby('iteration').agg(['max', 'min'])
    meta_ = ddf.get_partition(0).compute()
    meta_ = _helper(meta_).head(0)
    df_ranges = ddf.map_partitions(_helper, meta = meta_).compute()
    df_max = df_ranges.loc[:,idx[:,'max']]
    df_min = df_ranges.loc[:,idx[:,'max']]
    df_max.columns = param_names
    df_min.columns = param_names
    mi_ = df_min.groupby(df_max.index).min().cummin()
    ma_ = df_max.groupby(df_max.index).max().cummax()
    if return_mi_ma:
        return normalize(ma_, params), normalize(mi_, params)
    else:
        return normalize(ma_, params) - normalize(mi_, params)
    
def get_index(dataframe, channel):
    '''Compute the depolarization or hyperpolarization index.
    
    This index is how much the given channel contributed to depolarization (or hyperpolarization),
    relative to the total depolarization (or hyperpolarization) current.
    
    Args:
        dataframe (pd.DataFrame): the dataframe containing the biophysical parameters
        channel (str): the channel for which to compute the index
        
    Returns:
        pd.Series: the depolarization/hyperpolarization index for the given channel'''
    if channel in hyperpo_channels:
        norm = dataframe[hyperpo_channels].sum(axis = 1)
    elif channel in depo_channels:
        norm = dataframe[depo_channels].sum(axis = 1)
    return dataframe[channel] / norm

def get_depolarization_index(dataframe):
    """Compute the relative difference in depolarization contribution of Ca_LVA and Ca_HVA during the BAC stimulus.
    
    This index is defined as:
    
    .. math::
        \\frac{Ca_{LVA} - Ca_{HVA}}{Ca_{HVA} + Ca_{LVA}}
    
    Args:
        dataframe (pd.DataFrame): the dataframe containing the biophysical parameters
        
    Returns:
        pd.Series: the depolarization index for each model in the dataframe
        
    Note:
        This method is specific to L5PT neurons, or any cell with Ca_LVA and Ca_HVA channels."""
    CaHVA = get_index(dataframe, 'BAC_bifurcation_charges.Ca_HVA.ica')
    CaLVA = get_index(dataframe, 'BAC_bifurcation_charges.Ca_LVAst.ica')
    return (CaLVA-CaHVA)/(CaHVA+CaLVA)

def get_hyperpolarization_index(dataframe):
    """Compute the relative difference in hyperpolarization contribution of Im and SK during the BAC stimulus.
    
    This index is defined as:
    
    .. math::
        \\frac{I_{SK} - I_{m}}{I_{SK} + I_{m}}
        
    Returns:
        pd.Series: the hyperpolarization index for each model in the dataframe"""
    Im = get_index(dataframe, 'BAC_bifurcation_charges.Im.ik')
    Sk = get_index(dataframe, 'BAC_bifurcation_charges.SK_E2.ik')
    return (Sk-Im)/(Im+Sk)

def augment_ddf_with_PCA_space(ddf):
    """Augment a dask dataframe with the first two principal components of the hz current space.
    
    The hz current space is the space of current utilization during the BAC stimulus.
    The PCA space is the space spanned by the first two principal components of this space.
    
    Args:
        ddf (dask.dataframe): the dataframe to augment
        
    Returns:
        dask.dataframe: the augmented dataframe, containing the additional columns: 'pc0', 'pc1', 'depolarization_index', 'hyperpolarization_index'
    """
    def _helper(df):
        df['pc0'] = I.np.dot(df[hz_current_columns], pca_components[0])
        df['pc1'] = I.np.dot(df[hz_current_columns], pca_components[1])
        df['depolarization_index'] = get_depolarization_index(df)
        df['hyperpolarization_index'] = get_hyperpolarization_index(df)
        return df
    meta_ = _helper(ddf.head())
    ddf_augmented = ddf.map_partitions(_helper, meta = meta_)
    return ddf_augmented

def pandas_binby(df, c1, c2, binsize = 0.01):
    """Bin a pandas dataframe by two columns.
    
    Args:
        df (pd.DataFrame): the dataframe to bin
        c1 (str): the first column to bin by
        c2 (str): the second column to bin by
        binsize (float): the size of the bins
        
    Returns:
        pd.DataFrame: the binned dataframe"""
    return df.groupby([(df[c1]/binsize).round()*binsize, 
                (df[c2]/binsize).round()*binsize]).apply(lambda x: x.sample(1))

hz_current_columns = [
    'BAC_bifurcation_charges.Ca_HVA.ica',
    'BAC_bifurcation_charges.SK_E2.ik',
    'BAC_bifurcation_charges.Ca_LVAst.ica',
    'BAC_bifurcation_charges.NaTa_t.ina',
    'BAC_bifurcation_charges.Im.ik',
    'BAC_bifurcation_charges.SKv3_1.ik']

hz_current_columns_short = [k.split('.')[1] for k in hz_current_columns]

depo_channels = [
    'BAC_bifurcation_charges.Ca_HVA.ica',
    'BAC_bifurcation_charges.Ca_LVAst.ica',
    'BAC_bifurcation_charges.NaTa_t.ina']

hyperpo_channels = [
    'BAC_bifurcation_charges.SK_E2.ik',
    'BAC_bifurcation_charges.Im.ik',
    'BAC_bifurcation_charges.SKv3_1.ik']

pca_components = I.np.array([
    [ 7.63165639e-01,   6.29498003e-01,  -8.63749227e-02,
      2.74177180e-04,  -1.40787230e-02,   1.16839883e-01],
    [ 5.24587951e-01,  -5.64428021e-01,   5.25520353e-01,
     -1.39713239e-03,   3.57672349e-01,   4.61019458e-02]
    ])

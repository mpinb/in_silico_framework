# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This module provides routines to analyze the results of a random walk exploration through biophysical parameter space.

See also:
    :mod:`~biophysics_fitting.exploration_from_seedpoint.RW`
"""

import pandas as pd
import os
import dask
from pickle import UnpicklingError

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
        df = pd.read_pickle(path) 
        df['init_error'] = ''
        return df
    # except (UnpicklingError, EOFError) as e:
    except:
        return pd.Series({"init_error":"Could not read {}".format(1)}).to_frame('init_error')
        
def read_pickle(seed_folder, particle_id):
    """
    Read the results of a single particle of a RW exploration.
    
    Args:
        seed_folder (str): the path of the directory corresponding to a seedpoint.
        particle_id (str): the particle id
        
    Returns:
        pd.DataFrame: The results of the RW exploration of a single particle.
    """
    path = os.path.join(seed_folder, str(particle_id))
    df_names = [p for p in os.listdir(path) if p.endswith('.pickle')]
    df_names = sorted(df_names, key=lambda x: int(x.split('.')[0]))
    dfs = [robust_read_pickle(os.path.join(path, p)) for p in df_names]
    if len(dfs) == 0:
        return 'empty'
    df = pd.concat(dfs).reset_index(drop=True)
    df['iteration'] = df.index
    df['particle_id'] = particle_id
    return df

def read_all(basedir, n_particles_start = 0, n_particles_end = 1000):
    """
    Read the results of all directories contained within some base directory, independent of which seepdoint or particle.
    
    Args:
        basedir (str): the base directory containing the results of the RW exploration.
        n_particles_start (int): the first particle to read
        n_particles_end (int): the last particle to read
    """
    fun = dask.delayed(read_pickle)
    ds = [fun(basedir, i) for i in range(n_particles_start, n_particles_end)]
    return ds


class Load:
    """Class for efficiently loading exploration results
    
    Uses dask to parallellize loading in large datasets.
    """

    def __init__(self, client, path, n_particles=1000):
        self.path = path
        self.n_particles = n_particles
        self.delayeds = read_all(path, n_particles_end=n_particles)
        self.futures = client.compute(self.delayeds)

        self.df = None

    def get_df(self):
        """Get the exploration results as a pandas dataframe."""
        if self.df is None:
            self.df = dask.dataframe.from_delayed(self.futures)
        return self.df

    def get_futures(self):
        """Get the futures of the delayed computations.
        
        Useful to check the progress of distributed loading.
        """
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

idx = pd.IndexSlice

def get_param_range_evolution_from_df(df, params, iteration_group_size = 20, return_min_max = False):
    """Compute the cumulative range of each parameter explored by a RW exploration, as a fraction of its total range.

    Successful iterations differ between particles, so iterations are pooled into groups of
    ``iteration_group_size`` before taking the running min and max across all particles.

    Args:
        df (pd.DataFrame): the exploration results of successful iterations, containing the parameter columns and an ``iteration`` column.
        params (pd.DataFrame): the parameter ranges, with columns ``min`` and ``max`` and the parameter names as index.
        iteration_group_size (int): the number of consecutive iterations pooled into one group.
        return_min_max (bool): whether to return the normalized running max and min separately, rather than their difference.

    Returns:
        pd.DataFrame | (pd.DataFrame, pd.DataFrame): the explored range per parameter (columns) and iteration group (index).
        If ``return_min_max`` is True, the normalized running max and min instead."""
    param_names = list(params.index)
    df = df[param_names + ['iteration']].copy()
    df['iteration'] = (df.iteration // iteration_group_size) * iteration_group_size
    df_ranges = df.groupby('iteration').agg(['max', 'min'])
    df_min = normalize(df_ranges.loc[:, idx[:, 'min']].droplevel(1, axis=1).cummin(), params)
    df_max = normalize(df_ranges.loc[:, idx[:, 'max']].droplevel(1, axis=1).cummax(), params)
    if return_min_max:
        return df_max, df_min
    return df_max - df_min

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

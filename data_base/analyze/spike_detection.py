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
"""Detect spikes from :ref:`voltage_traces_format` dataframes.
"""
from functools import partial
import pandas as pd
import dask
from single_cell_parser.analyze.membrane_potential_analysis import simple_spike_detection


def spike_in_interval(st, tmin, tmax):
    """Check whether each trial contains at least one spike within the specified interval
    
    Args:
        st (:class:`~numpy.array`): 2D array of spike times (``n_trials x n_spikes``)
        tmin (float): Minimum time (inclusive).
        tmax (float): Maximum time (exclusive).
        
    Example::
    
        >>> st = np.array([[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.3, 0.4, 0.5]])
        >>> spike_in_interval(st, 0.4, 0.3)
        [False, True, True]
        
    Returns:
       :class:``~numpy.array``: 
        1D array of boolean values, indicating whether each trial contains at least one spike within the specified interval.
    """
    return ((st >= tmin) & (st < tmax)).any(axis=1)


def _helper(x, threshold=0):
    '''Parse a :ref:`voltage_traces_df_format` and return a :class:`pandas.Series` containing the spikes,
    
    Reads out a :ref:`voltage_traces_df_format`, so it can be fed into 
    :func:`~single_cell_parser.analyze.membrane_potential_analysis.simple_spike_detection`.
    The results are converted back to a :class:`pandas.Series`, so it can be concatenated 
    to a dask dataframe
    
    Args:
        x (:class:`~pandas.DataFrame`): A dataframe containing the voltage traces
        threshold (float): The threshold for spike detection
        
    Returns:
        :class:`~pandas.Series`: A series containing the spikes
        
    See also:
        :func:`~single_cell_parser.analyze.membrane_potential_analysis.simple_spike_detection`
    '''
    t = x.index.values.astype(float)
    values = x.values
    spikes = simple_spike_detection(
        t,
        values,
        mode='regular',
        threshold=threshold)
    #print(len(spikes))
    return pd.Series({lv: x for lv, x in enumerate(spikes)})


def spike_detection(ddf, scheduler=None, threshold=0):
    """Detect spikes in a dask :ref:`voltage_traces_df_format`.
    
    Args:
        ddf (:class:`~dask.dataframe.DataFrame`): A dask dataframe containing the voltage traces
        scheduler (str): The scheduler to use for computation
        threshold (float): The threshold for spike detection
        
    Returns:
        :class:`~pandas.DataFrame`: A pandas dataframe containing the spikes    
    """
    fun = partial(_helper, threshold=threshold)
    '''this method expects a dask dataframe and returns a pandas dataframe containing the spikes'''
    dummy = dask.compute(*list(
        map(
            dask.delayed(lambda x: x.apply(fun, axis=1)), 
            ddf.to_delayed())),
                         scheduler=scheduler)
    return pd.concat(dummy)

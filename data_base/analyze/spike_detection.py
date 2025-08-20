# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""Detect spikes from :ref:`voltage_traces_format` dataframes.
"""
from functools import partial
import pandas as pd
import dask
from single_cell_parser.analyze.membrane_potential_analysis import simple_spike_detection


def spike_in_interval(st, tmin, tmax):
    """Check whether each trial contains at least one spike within the specified interval
    
    Args:
        st (:py:class:`~numpy.array`): 2D array of spike times (``n_trials x n_spikes``)
        tmin (float): Minimum time (inclusive).
        tmax (float): Maximum time (exclusive).
        
    Example::
    
        >>> st = np.array([[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.3, 0.4, 0.5]])
        >>> spike_in_interval(st, 0.4, 0.3)
        [False, True, True]
        
    Returns:
       :py:class:``~numpy.array``: 
        1D array of boolean values, indicating whether each trial contains at least one spike within the specified interval.
    """
    return ((st >= tmin) & (st < tmax)).any(axis=1)


def _helper(x, threshold=0):
    '''Parse a :ref:`voltage_traces_df_format` and return a :py:class:`pandas.Series` containing the spikes,
    
    Reads out a :ref:`voltage_traces_df_format`, so it can be fed into 
    :py:meth:`~single_cell_parser.analyze.membrane_potential_analysis.simple_spike_detection`.
    The results are converted back to a :py:class:`pandas.Series`, so it can be concatenated 
    to a dask dataframe
    
    Args:
        x (:py:class:`~pandas.DataFrame`): A dataframe containing the voltage traces
        threshold (float): The threshold for spike detection
        
    Returns:
        :py:class:`~pandas.Series`: A series containing the spikes
        
    See also:
        :py:meth:`~single_cell_parser.analyze.membrane_potential_analysis.simple_spike_detection`
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
        ddf (:py:class:`~dask.dataframe.DataFrame`): A dask dataframe containing the voltage traces
        scheduler (str): The scheduler to use for computation
        threshold (float): The threshold for spike detection
        
    Returns:
        :py:class:`~pandas.DataFrame`: A pandas dataframe containing the spikes    
    """
    fun = partial(_helper, threshold=threshold)
    '''this method expects a dask dataframe and returns a pandas dataframe containing the spikes'''
    dummy = dask.compute(*list(
        map(
            dask.delayed(lambda x: x.apply(fun, axis=1)), 
            ddf.to_delayed())),
                         scheduler=scheduler)
    return pd.concat(dummy)
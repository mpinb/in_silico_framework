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
"""Bin :ref:`spike_times_format` or :ref:`syn_activation_format` dataframes by time and space.

See also:
    :py:mod:`data_base.db_initializers.synapse_activation_binning` for binning synapse activations
    by time, and a variety of other metrics (e.g. space, cell type ...)
"""

from __future__ import absolute_import
import pandas as pd
import numpy as np
import dask
import dask.dataframe as dd
from ._add_nparray_aligned import add_aligned
from ._helper_functions import time_list_from_pd, pd_to_array, map_return_to_series


def universal_pd(
    df, 
    distance_column, 
    spatial_distance_bins = 50, 
    min_time = 0,
    max_time = 300, 
    time_distance_bins = 1):
    '''Bin a pandas DataFrame by both distance and time.
    
    This is a speed-optimized binning code for 2d-binning of a :py:class:`pandas.DataFrame`.
    
    Args:
        df (:py:class:`pandas.DataFrame`): 
            DataFrame to bin. Must contain a column with the name :paramref:`distance_column` that contains the distance values.
        distance_column (str): 
            Column name of the distance values.
        spatial_distance_bins (int): 
            Size of the distance bins. Default is :math:`50\mu m`.
        min_time (int): 
            Minimum time value. Default is :math:`0 ms`.
        max_time (int): 
            Maximum time value. Default is :math:`300 ms`.
        time_distance_bins (int): 
            Size of the time bins. Default is :math:`1 ms`.
    
    Returns:
        :py:class:`~numpy.array`:
            A 2D array of the binned values.
    '''
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("expected pandas.DataFrame, got %s" % str(type(df)))

    df = df.assign(zbins = lambda x: np.floor(x[distance_column] / spatial_distance_bins).astype(int))
    t_bins = np.arange(min_time, max_time + time_distance_bins, time_distance_bins)

    fun = lambda row: np.histogram(row, t_bins)[0]
    x = df.groupby('zbins').apply(time_list_from_pd)
    # if z-bins are missing, fill them
    for lv in range(max(x.index.values) + 1):
        if not lv in x.index:
            x[lv] = []
    x = x.apply(fun)
    # sort index
    x = x.sort_index()
    return np.array(x.tolist())


def universal(
    df, 
    distance_column, 
    spatial_distance_bins = 50, 
    min_time = 0, 
    max_time = 300, 
    time_distance_bins = 1):
    '''Bin a pandas or dask DataFrame by both distance and time.
    
    Infers the type of the input DataFrame and calls the appropriate binning function.
    
    Args:
        df (:py:class:`~pandas.DataFrame` or :py:class:`~dask.dataframe.DataFrame`): 
            DataFrame to bin. Must contain a column with the name :paramref:`distance_column` that contains the distance values.
        distance_column (str): 
            Column name of the distance values.
        spatial_distance_bins (int): 
            Size of the spatial bins. Default is :math:`50\mu m`.
        min_time (int): 
            Minimum time value. Default is :math:`0 ms`.
        max_time (int): 
            Maximum time value. Default is :math:`300ms`.
        time_distance_bins (int): 
            Size of the time bins. Default is :math:`1ms`.
            
    Returns:
        :py:class:`~numpy.array`:
            A 2D array of the binned values.
    
    See also:
        :py:meth:`~data_base.analyze.spatial_binning.universal_pd`
    '''

    fun = lambda x: universal_pd(x, distance_column, spatial_distance_bins =  \
                                 spatial_distance_bins, min_time = min_time, \
              max_time = max_time, time_distance_bins = time_distance_bins)

    if isinstance(df, pd.DataFrame):
        return fun(df)
    elif isinstance(df, dd.DataFrame):
        #fun = map_return_to_series(fun)
        pixel_list = df.map_partitions(map_return_to_series(fun)).compute(scheduler="multiprocessing")
        pixel_list = list(pixel_list)
        #for x in pixel_list: print x
        #print add_aligned(*pixel_list)
        #fun_mapped = lambda x: map_return_to_series(fun, x)
        return add_aligned(*pixel_list)

    else:
        raise RuntimeError(
            "Expected pandas.DataFrame or dask.dataframe.DataFrame. Got %s." % str(type(df))
            )
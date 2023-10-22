from __future__ import absolute_import
import pandas as pd
import numpy as np
import dask
import dask.dataframe as dd
from ._add_nparray_aligned import add_aligned
from ._helper_functions import time_list_from_pd, pd_to_array, map_return_to_series


def universal_pd(df, distance_column, spacial_distance_bins = 50, min_time = 0, \
              max_time = 300, time_distance_bins = 1):
    '''speed-optimized binning code for 2d-binning of pandas.DataFrame.'''
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("expected pandas.DataFrame, got %s" % str(type(df)))

    df = df.assign(zbins = lambda x: np.floor(x[distance_column] / spacial_distance_bins)\
                   .astype(int))
    t_bins = np.arange(min_time, max_time + time_distance_bins,
                       time_distance_bins)

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

def universal(df, distance_column, spacial_distance_bins = 50, min_time = 0, \
              max_time = 300, time_distance_bins = 1):
    '''
    kwargs: 
    spacial_distance_bins = 50, 
    min_time = 0, \
    max_time = 300, time_distance_bins = 1
    '''

    fun = lambda x: universal_pd(x, distance_column, spacial_distance_bins =  \
                                 spacial_distance_bins, min_time = min_time, \
              max_time = max_time, time_distance_bins = time_distance_bins)

    if isinstance(df, pd.DataFrame):
        return fun(df)
    elif isinstance(df, dd.DataFrame):
        #fun = map_return_to_series(fun)
        pixel_list = df.map_partitions(map_return_to_series(fun))\
                        .compute(get = dask.multiprocessing.get)
        pixel_list = list(pixel_list)
        #for x in pixel_list: print x
        #print add_aligned(*pixel_list)
        #fun_mapped = lambda x: map_return_to_series(fun, x)
        return add_aligned(*pixel_list)

    else:
        raise RuntimeError("Expected pandas.DataFrame or dask.dataframe.DataFrame. Got %s." \
                           % str(type(df)))

from .spaciotemporal_binning import time_list_from_pd
import pandas as pd
import numpy as np
import dask.dataframe as dd
import dask
import compatibility

def temporal_binning_pd(df, bin_size = 1, min_time = None, max_time = None, normalize = True):
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("Expected pd.DataFrame, got %s" % str(type(df)))
    
    timelist = time_list_from_pd(df)
    
    #print timelist
    
    if min_time is None: min_time = min(timelist)
    if max_time is None: max_time = max(timelist)

    t_bins = np.arange(min_time, max_time + bin_size, bin_size)
    
    data = np.histogram(timelist, t_bins)[0]
    if normalize: 
        data = data / float(len(df))
        
    return t_bins, data

def temporal_binning_dask(ddf, bin_size = 1, min_time = None, max_time = None, normalize = True):

    if not isinstance (ddf, dd.DataFrame):
        raise RuntimeError("Expected dask.dataframe.Dataframe, got %s" % str(type(ddf)))
    
    if min_time is None or max_time is None: 
        raise RuntimeError("min_time and max_time have to be specified for parallel support")
    
    fun = lambda x: temporal_binning_pd(x, bin_size = bin_size, min_time = min_time, max_time = max_time, normalize = False)
    t_bins, silent = fun(ddf.head())
    
    fun2 = lambda x: pd.Series(dict(A = fun(x)[1]))    
    
    #bin each partition separately and sum to get result
#     meta = pd.Series(zip(*(t_bins,data)))
    out = ddf.map_partitions(fun2, meta = float).compute(get=compatibility.multiprocessing_scheduler).sum()
    
    if normalize: 
        out = out / float(len(ddf))
    return t_bins, out

def universal(*args, **kwargs):
    '''
    Binning of a pandas Dataframe, that contains timevalues in columns,
    whose name can be converted to int, like the usual spike_times dataframe.
    
    Parameters:
        bin_size
        min_time
        max_time
        normalize
    '''
    if isinstance(args[0], pd.DataFrame):
        return temporal_binning_pd(*args, **kwargs)
    elif isinstance(args[0], dd.DataFrame):
        return temporal_binning_dask(*args, **kwargs)
    else:
        raise ValueError("Expected pd.DataFrame or dask.dataframe.DataFrame, got %s" % type(args[0]))
    
    
    
        
    
    
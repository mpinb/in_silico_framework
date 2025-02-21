"""Bin :ref:`spike_times_format` and :ref:`syn_activation_format` dataframes by time.

This is used in :py:mod:`data_base.isf_data_base.db_initializers.synapse_activation_binning` to bin
synapse activations.
"""

from .spatiotemporal_binning import time_list_from_pd
import pandas as pd
import numpy as np
import dask.dataframe as dd
import dask
import compatibility


def temporal_binning_pd(
    df,
    bin_size=None,
    min_time=None,
    max_time=None,
    normalize=True,
    bin_borders=None,
    rate=False):
    """Bin timevalues in a pandas DataFrame.
    
    Given a dataframe containing time values in columns whose name can be converted to an integer, this function bins the values.
    It assumes that all columns whose names are integer-convertible contain time values.
    This is true for :ref:`spike_times_format` and :ref:`syn_activation_format` dataframes.
    
    Args:
        df (:py:class:`pandas.DataFrame`): DataFrame with containing time values in columns whose name are integer-convertible.
        bin_size (float, optional): Size of the bins. If not specified, :paramref:`bin_borders` have to be specified.
        min_time (float, optional): Minimum time to consider. If not specified, the minimum value in the DataFrame is used.
        max_time (float, optional): Maximum time to consider. If not specified, the maximum value in the DataFrame is used.
        bin_borders (list, optional): List of bin borders. If not specified, :paramref:`bin_size` has to be specified.
        normalize (bool, optional): If True, normalize the output to the total number of elements in the DataFrame.
        rate (bool, optional): If True, normalize the output to the bin size.
        
    Returns:
        tuple: Tuple containing the bin borders and the binned data.
    """
    
    
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("Expected pd.DataFrame, got %s" % str(type(df)))

    timelist = time_list_from_pd(df)

    if bin_borders is None:
        if min_time is None:
            min_time = min(timelist)
        if max_time is None:
            max_time = max(timelist)
        if bin_size is None:
            bin_size = 1
        bin_borders = np.arange(min_time, max_time + bin_size, bin_size)
    else:
        assert bin_size is None
        assert min_time is None
        assert max_time is None

    data = np.histogram(timelist, bin_borders)[0]
    if normalize:
        data = data / float(len(df))
    if rate:
        data = data / np.diff(bin_borders)

    return bin_borders, data


def temporal_binning_dask(
    ddf,
    bin_size=1,
    min_time=None,
    max_time=None,
    normalize=True,
    client=None):
    """Bin timevalues in a dask DataFrame.
    
    Given a dataframe containing time values in columns whose name can be converted to an integer, this function bins the values.
    It assumes that all columns whose names are integer-convertible contain time values.
    This is true for :ref:`spike_times_format` and :ref:`syn_activation_format` dataframes.
    
    Args:
        ddf (:py:class:`dask.dataframe.DataFrame`): DataFrame with containing time values in columns whose name are integer-convertible.
        bin_size (float, optional): Size of the bins. If not specified, :paramref:`bin_borders` have to be specified.
        min_time (float, optional): Minimum time to consider. If not specified, the minimum value in the DataFrame is used.
        max_time (float, optional): Maximum time to consider. If not specified, the maximum value in the DataFrame is used.
        normalize (bool, optional): If True, normalize the output to the total number of elements in the DataFrame.
        client (:py:class:`dask.distributed.Client`, optional): Dask client to use for parallel computation.
        
    Returns:
        tuple: Tuple containing the bin borders and the binned data.
    """
    if not isinstance(ddf, dd.DataFrame):
        raise RuntimeError("Expected dask.dataframe.Dataframe, got %s" %
                           str(type(ddf)))

    if min_time is None or max_time is None:
        raise RuntimeError(
            "min_time and max_time have to be specified for parallel support")

    fun = lambda x: temporal_binning_pd(
        x,
        bin_size=bin_size,
        min_time=min_time,
        max_time=max_time,
        normalize=False)
    t_bins, silent = fun(ddf.head())

    fun2 = lambda x: pd.Series(dict(A=fun(x)[1]))

    #bin each partition separately and sum to get result
    #     meta = pd.Series(zip(*(t_bins,data)))
    out = client.compute(ddf.map_partitions(fun2, meta=float)).result().sum()

    if normalize:
        out = out / float(len(ddf))
    return t_bins, out


def universal(*args, **kwargs):
    '''Bin spike times for dask or pandas dataframes.
    
    Infers the dataframe type and calls the appropriate binning function.
    
    Args:
        df | ddf (:py:class:`dask.dataframe.DataFrame`): DataFrame with containing time values in columns whose name are integer-convertible.
        bin_size (float, optional): Size of the bins. If not specified, :paramref:`bin_borders` have to be specified.
        min_time (float, optional): Minimum time to consider. If not specified, the minimum value in the DataFrame is used.
        max_time (float, optional): Maximum time to consider. If not specified, the maximum value in the DataFrame is used.
        normalize (bool, optional): If True, normalize the output to the total number of elements in the DataFrame.
        rate (bool, optional): If True, normalize the output to the bin size. Only valid if :paramref:`df` is a pandas DataFrame.
        client (:py:class:`dask.distributed.Client`, optional): Dask client to use for parallel computation. Only valid if :paramref:`ddf` is a dask DataFrame.
    
    See also:
        :py:meth:`~data_base.analyze.temporal_binning.temporal_binning_pd` and
        :py:meth:`~data_base.analyze.temporal_binning.temporal_binning_dask`
    '''
    if isinstance(args[0], pd.DataFrame):
        return temporal_binning_pd(*args, **kwargs)
    elif isinstance(args[0], dd.DataFrame):
        return temporal_binning_dask(*args, **kwargs)
    else:
        raise ValueError(
            "Expected pd.DataFrame or dask.dataframe.DataFrame, got %s" %
            type(args[0]))

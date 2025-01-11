"""Calculate the voltage as a density array.

This module provides methods to calculate the voltage as a histogram across many trials,
and bin them in timebins.
"""

import numpy as np
import pandas as pd
import dask.dataframe as dd
from ._helper_functions import is_int
from visualize._decorators import dask_to_pandas
from visualize._figure_array_converter import PixelObject


#@dask_to_pandas
def calculate_vdensity_array_pd(
    v,
    bin_size=0.05,
    ymin=-100,
    ymax=50,
    xmin=None,
    xmax=None):
    '''Bin a :ref:`voltage_traces_df_format` in timebins across trials.
    
    Args:
        v (:py:class:`~pandas.DataFrame`): 
            A voltage traces dataframe. Column indices float and reflect timepoints.
        bin_size (float): 
            The size of the bins.
        ymin (float): 
            The minimum voltage value.
        ymax (float): 
            The maximum voltage value.
     
    Warning:
        If dask dataframe is passed, it will be monolithically load into memory. 
        For large-scale simulations, this is likely not what you want.
        
    See also:
        :py:func:`~data_base.analyze.voltage_binning.calculate_vdensity_array_dask` for the dask version.
        
    '''
    bins = np.arange(ymin, ymax + bin_size, bin_size)
    voltagetrace_density_array = [np.histogram(v[time_in_ms].values, bins)[0] \
                                  for time_in_ms in v.columns if is_int(time_in_ms)]
    #voltagetrace_density_array = np.flipud(np.matrix.transpose(np.array(voltagetrace_density_array)))
    voltagetrace_density_array = np.matrix.transpose(
        np.array(voltagetrace_density_array))
    return voltagetrace_density_array


def get_bins(bin_size=None, min_=None, max_=None):
    """Construct bin edges from a sice and range.
    
    Args:
        bin_size (float): the size of the bins
        min_ (float): the minimum value
        max_ (float): the maximum value
        
    Return:
        np.array: the bin edges
    """
    bins = np.arange(min_, max_ + bin_size, bin_size)
    return bins


def calculate_vdensity_array_dask(
    v,
    bin_size=0.05,
    ymin=-100,
    ymax=50,
    xmin=None,
    xmax=None):
    '''Bin a :ref:`voltage_traces_df_format` in timebins across trials.
    
    Args:
        v (dask.DataFrame): A voltage traces dataframe. Column indices float and reflect timepoints
        bin_size (float): the size of the bins
        ymin (float): the minimum voltage value
        ymax (float): the maximum voltage value
        xmin (float): the minimum time value (unused)
        xmax (float): the maximum time value (unused)
    
    Returns:
        :py:class:`dask.dataframe.DataFrame`: the binned voltage traces dataframe
        
    See also:
        :py:func:`~data_base.analyze.voltage_binning.calculate_vdensity_array_pd` for the pandas version.
    '''

    def fun(x):
        out = calculate_vdensity_array_pd(
            x,
            bin_size=bin_size,
            ymin=ymin,
            ymax=ymax)
        return pd.Series({'A': out})

    out = v.map_partitions(fun, meta='object').sum()

    return out


def calculate_vdensity_array(*args, **kwargs):
    """Calculate the voltage density array.
    
    A voltage density is the time-binned voltage across trials.
    This method infers the type of dataframe passed and calls the appropriate method.
    
    Args:
        v (:py:class:`~pandas.DataFrame` | :py:class:`~dask.dataframe.DataFrame`): 
            A voltage traces dataframe. Column indices float and reflect timepoints
        bin_size (float): the size of the bins
        ymin (float): the minimum voltage value
        ymax (float): the maximum voltage value
        xmin (float): the minimum time value (unused)
        xmax (float): the maximum time value (unused)
    """
    if isinstance(args[0], pd.DataFrame):
        return calculate_vdensity_array_pd(*args, **kwargs)
    elif isinstance(args[0], dd.DataFrame):
        return calculate_vdensity_array_dask(*args, **kwargs)


def calculate_vdensity_array_pixelObject(*args, **kwargs):
    '''Calculate the voltage density array as a PixelObject.
    
    This method is identical to :py:meth:`~data_base.analyze.voltage_binning.calculate_vdensity_array`,
    but returns a :py:class:`~visualize._figure_array_converter.PixelObject` instead.
    
    Args:
        v (:py:class:`~pandas.DataFrame` | :py:class:`~dask.dataframe.DataFrame`): 
            A voltage traces dataframe. Column indices float and reflect timepoints
        bin_size (float): the size of the bins
        xmin (float): the minimum time value
        xmax (float): the maximum time value
        ymin (float): the minimum voltage value
        ymax (float): the maximum voltage value
        
    Returns:
        :py:class:`~visualize._figure_array_converter.PixelObject`: a PixelObject with the voltage density array
    '''
    array = calculate_vdensity_array(*args, **kwargs)
    extent = (kwargs['xmin'], kwargs['xmax'], kwargs['ymin'], kwargs['ymax'])
    return PixelObject(extent, array=array)

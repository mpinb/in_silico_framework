import numpy as np
import pandas as pd
import dask.dataframe as dd
from ._helper_functions import is_int
from visualize._decorators import dask_to_pandas
from visualize._figure_array_converter import PixelObject


#@dask_to_pandas
def calculate_vdensity_array_pd(v,
                                bin_size=0.05,
                                ymin=-100,
                                ymax=50,
                                xmin=None,
                                xmax=None):
    '''
    takes a pandas or dask dataframe v, that has to hasve the structure of a usual
    voltage_traces dataframe:
     - columns convertible to int / float resemble resemble timepoints
     - the values of these columns are of type float
     
     cave: currently only implemented for pandas. If dask dataframe is passed, it
     will be monolitically load into memory! 
     #Todo: try aproach with dask delayed
     
     xmin and xmax can be passed, but have no effect
     '''
    bins = np.arange(ymin, ymax + bin_size, bin_size)
    voltagetrace_density_array = [np.histogram(v[time_in_ms].values, bins)[0] \
                                  for time_in_ms in v.columns if is_int(time_in_ms)]
    #voltagetrace_density_array = np.flipud(np.matrix.transpose(np.array(voltagetrace_density_array)))
    voltagetrace_density_array = np.matrix.transpose(
        np.array(voltagetrace_density_array))
    return voltagetrace_density_array


def get_bins(bin_size=None, min_=None, max_=None):
    bins = np.arange(min_, max_ + bin_size, bin_size)
    return bins


def calculate_vdensity_array_dask(v,
                                  bin_size=0.05,
                                  ymin=-100,
                                  ymax=50,
                                  xmin=None,
                                  xmax=None):
    '''
    takes a pandas or dask dataframe v, that has to hasve the structure of a usual
    voltage_traces dataframe:
     - columns convertible to int / float resemble resemble timepoints
     - the values of these columns are of type float
     
     cave: currently only implemented for pandas. If dask dataframe is passed, it
     will be monolitically load into memory! 
     #Todo: try aproach with dask delayed
     
     xmin and xmax can be passed, but have no effect     
     '''

    def fun(x):
        out = calculate_vdensity_array_pd(x,
                                          bin_size=bin_size,
                                          ymin=ymin,
                                          ymax=ymax)
        return pd.Series({'A': out})

    out = v.map_partitions(fun, meta='object').sum()

    return out


def calculate_vdensity_array(*args, **kwargs):
    if isinstance(args[0], pd.DataFrame):
        return calculate_vdensity_array_pd(*args, **kwargs)
    elif isinstance(args[0], dd.DataFrame):
        return calculate_vdensity_array_dask(*args, **kwargs)


def calculate_vdensity_array_pixelObject(*args, **kwargs):
    '''like calculate_vdensity_array, but returns a PixelObject,
    which contains the array and the extent of the figure.
    
    Therefore, xmin, xmax, ymin and ymax have to be specified'''
    array = calculate_vdensity_array(*args, **kwargs)
    extent = (kwargs['xmin'], kwargs['xmax'], kwargs['ymin'], kwargs['ymax'])
    return PixelObject(extent, array=array)

from functools import partial
import pandas as pd
import dask
from single_cell_parser.analyze.membrane_potential_analysis import simple_spike_detection


def spike_in_interval(st, tmin, tmax):
    return ((st >= tmin) & (st < tmax)).any(axis=1)


def _helper(x, threshold=0):
    '''reads out a voltage trace, so it can be fed into simple_spike_detection()
    and converts the result back to pd.Series, so the result can be concatenated 
    to a dask dataframe'''
    t = x.index.values
    values = x.values
    spikes = simple_spike_detection(
        t,
        values,
        mode='regular',
        threshold=threshold)
    #print(len(spikes))
    return pd.Series({lv: x for lv, x in enumerate(spikes)})


def spike_detection(ddf, scheduler=None, threshold=0):
    fun = partial(_helper, threshold=threshold)
    '''this method expects a dask dataframe and returns a pandas dataframe containing the spikes'''
    dummy = dask.compute(*list(
        map(
            dask.delayed(lambda x: x.apply(fun, axis=1)), 
            ddf.to_delayed())),
                         scheduler=scheduler)
    return pd.concat(dummy)
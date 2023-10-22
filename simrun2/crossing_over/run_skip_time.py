import os
import pandas as pd
import dask
from .utils import filter_by_time, merge_synapse_activation, _convertible_to_int


def skip_time(df, t_skip_start, t_skip_end):
    '''accepts a synapse activation pandas data frame. Returns a dataframe, where
    synapse activation in the specified interval is skipped.'''
    df_pre_skip = filter_by_time(df, lambda x: x <= t_skip_start)
    df_post_skip = filter_by_time(df, lambda x: x > t_skip_end)
    data_columns = [c for c in df.columns if _convertible_to_int(c)]
    delta_t = t_skip_end - t_skip_start
    for c in data_columns:
        df_post_skip[c] = df_post_skip[c] - delta_t
    x = merge_synapse_activation(df_pre_skip.reset_index(),
                                 df_post_skip.reset_index())
    return x


from model_data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format


def _save_synapse_activation_to_folder(df, sim_trail_index, dirPrefix):
    path = os.path.join(dirPrefix, sim_trail_index + '_synapse_activation.csv')
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    write_pandas_synapse_activation_to_roberts_format(path, df)
    return path


def skip_time_and_save(df_db, sim_trail_index, t_skip_start, t_skip_end,
                       dirPrefix):
    df = df_db.loc[sim_trail_index].compute(get=dask.get)
    df = skip_time(df, t_skip_start, t_skip_end)
    return _save_synapse_activation_to_folder(df, sim_trail_index, dirPrefix)


def skip_time_and_save_parallel(synapse_activation_db, sim_trail_index_list,
                                t_skip_start, t_skip_end, dirPrefix):
    '''returns delayed object which on computation generates synapse activation files
    with skipped time interval'''
    myfun = lambda sim_trail_index: skip_time_and_save(synapse_activation_db, sim_trail_index, \
                                                    t_skip_start, t_skip_end, dirPrefix)
    d = [dask.delayed(myfun)(s) for s in sim_trail_index_list]
    paths = dask.delayed(lambda *args: args)(d)
    return paths
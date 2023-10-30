import os
# import cloudpickle
import compatibility
import pandas as pd
import dask
import json
from . import parent_classes
from model_data_base.utils import df_colnames_to_str

def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, dd.DataFrame)


@dask.delayed
def load_helper(savedir, n_partitions, partition, columns=None):
    return pd.read_parquet(os.path.join(
        savedir,
        'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)),
                           columns=columns)


@dask.delayed
def save_helper(savedir, delayed_df, n_partitions, partition):
    # save original columns and index name
    assert all([type(e) == str for e in delayed_df.columns]), "This method requires that all column names of the dataframe are strings, but they are {}".format([type(e) for e in delayed_df.columns])
    if delayed_df.index.name is not None:
        assert type(delayed_df.index.name) == str, "This method requires that the index name of the dataframe is a string, but it is {}".format(type(delayed_df.index.name))
    return delayed_df.to_parquet(
        os.path.join(
            savedir,
            'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)))

class Loader(parent_classes.Loader):

    def get(self, savedir, columns=None):
        fnames = os.listdir(savedir)
        fnames = [f for f in fnames if 'pandas_to_parquet' in f]
        n_partitions = int(fnames[0].split('.')[1])
        delayeds = [
            load_helper(savedir, n_partitions, partition, columns=columns)
            for partition in range(n_partitions)
        ]
        ddf = dask.dataframe.from_delayed(delayeds)
        if os.path.exists(os.path.join(savedir, 'divisions.json')):
            with open(os.path.join(savedir, 'divisions.json')) as f:
                divisions = json.load(f)
                if isinstance(divisions, list):
                    divisions = tuple(divisions)  # for py3.9
                ddf.divisions = divisions
                print('load dask dataframe with known divisions')
        return ddf


def dump(obj, savedir, schema=None, client=None):
    # fetch original column names
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name

    delayeds = obj.to_delayed()
    delayeds = [dask.delayed(df_colnames_to_str)(e) for e in delayeds]

    # save object
    delayeds = [
        save_helper(savedir, d, len(delayeds), lv)
        for lv, d in enumerate(delayeds)
    ]

    futures = client.compute(delayeds)
    client.gather(futures)
    
    if obj.divisions is not None:
        with open(os.path.join(savedir, 'divisions.json'), 'w') as f:
            json.dump(obj.divisions, f)
    #obj.to_parquet(os.path.join(savedir, 'pandas_to_parquet.parquet'), schema = schema)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

    # reset original colnames
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name

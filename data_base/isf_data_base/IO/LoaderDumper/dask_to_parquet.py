import os
# import cloudpickle
import compatibility
import pandas as pd
import dask
import json
from . import parent_classes
from data_base.utils import df_colnames_to_str, chunkIt
import json
from .utils import save_object_meta, set_object_meta, read_object_meta
import logging
logger = logging.getLogger("ISF").getChild(__name__)

def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, dask.dataframe)


@dask.delayed
def load_helper(savedir, n_partitions, partition, meta=None, columns=None):
    obj = pd.read_parquet(os.path.join(
        savedir, 
        'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)),
                           columns=columns)
    if meta is not None:
        set_object_meta(
            obj, 
            meta = meta)
    return obj


@dask.delayed
def save_helper(savedir, delayed_df, n_partitions, partition):
    # save original columns and index name
    assert all([type(e) == str for e in delayed_df.columns]), \
        "This method requires that all column names of the dataframe are strings, \
        but they are {}".format([type(e) for e in delayed_df.columns])
    if delayed_df.index.name is not None:
        assert type(delayed_df.index.name) == str, \
            "This method requires that the index name of the dataframe is a string, \
                but it is {}".format(type(delayed_df.index.name))
    return delayed_df.to_parquet(
        os.path.join(
            savedir,
            'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)
        ))

class Loader(parent_classes.Loader):
    def __init__(self, meta):
        self.meta = meta
        if self.meta is None: logger.warning(
            "No meta information provided. \
            Column names, index labels, and index name (if it exists) will be in string format.")
        
    def get(self, savedir, columns=None):
        fnames = os.listdir(savedir)
        fnames = [f for f in fnames if 'pandas_to_parquet' in f]
        n_partitions = int(fnames[0].split('.')[1])
        delayeds = [
            load_helper(savedir, n_partitions, partition, meta=self.meta, columns=columns)
            for partition in range(n_partitions)
        ]
        ddf = dask.dataframe.from_delayed(delayeds, meta=self.meta)
        if os.path.exists(os.path.join(savedir, 'divisions.json')):
            with open(os.path.join(savedir, 'divisions.json')) as f:
                divisions = json.load(f)
                if isinstance(divisions, list):
                    divisions = tuple(divisions)  # for py3.9
                ddf.divisions = divisions
                print('load dask dataframe with known divisions')
        
        return ddf


def dump(obj, savedir, schema=None, client=None, repartition = 10000):
    save_object_meta(obj, savedir)
    # fetch original column names
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name
    
    if repartition:
        if obj.npartitions >= repartition * 2:
            divisions_concat = [chunk[0] for chunk in chunkIt(obj.divisions[:-1], repartition)] + [obj.divisions[-1]]
            ddf_concat = dask.dataframe.from_delayed(divisions_concat)
            ddf_concat.divisions = divisions_concat
            obj = ddf_concat
    
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
    
    # partitions and n_partitions are saved in the filename
    # see load_helper and save_helper. Loader.get() does not need to be initialized with this information
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)


    # reset original colnames
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name
        

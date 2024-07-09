import os
# import cloudpickle
import compatibility
import pandas as pd
import dask
import json
from . import parent_classes
from data_base.utils import df_colnames_to_str, chunkIt
from .utils import save_object_meta, set_object_meta
import logging
logger = logging.getLogger("ISF")

def check(obj):
    '''checks whether obj can be saved with this dumper'''
    return isinstance(obj, dask.dataframe)


@dask.delayed
def load_helper(savedir, n_partitions, partition, columns=None):
    """
    Loads a single partition of a dask dataframe from a parquet file.
    Re-assigns the original column dtypes if a meta file is present.
    
    Args:
        savedir (str): The directory to load the partition from.
        n_partitions (int): The number of partitions the original dask dataframe was split into.
        partition (int): The partition number to load.
        columns: The columns to load.
        
    Returns:
        pd.DataFrame: The loaded partition.
    """
    obj = pd.read_parquet(
        os.path.join(
            savedir,
            'pandas_to_parquet.{}.{}.parquet'.format(
                n_partitions, partition)), 
        columns=columns)
    obj = set_object_meta(obj, savedir)
    return obj


@dask.delayed
def save_helper(savedir, delayed_df, n_partitions, partition):
    """
    Save a single partition of a dask dataframe to a parquet file.
    
    Args:
        savedir (str): The directory to save the partition in.
        delayed_df: The partition to save.
        n_partitions (int): The number of partitions the original dask dataframe was split into.
        partition (int): The current partition number to save.
        
    Returns:
        None. Saves the partition.
    """
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
        '''
        Read in all partitions of a saved dask dataframe.
        
        Args:
            savedir (str): The directory to load the dask dataframe from.
            columns: The columns to load.
                Default: None (all columns)
            
        Returns:
            dask.dataframe: The loaded dask dataframe.
        '''
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


def dump(obj, savedir, schema=None, client=None, repartition = 10000):
    """
    Dump an object using the parquet format.
    Saves the dtype of the original columns as meta, because parquet requires column types to be string.
    
    Args:
        obj: The object to save.
        savedir (str): The directory to save the object in.
        schema: The schema to save the object with (not implemented).
        client: The dask client to use for computation.
        repartition: The number of partitions to repartition the object into. See: https://docs.dask.org/en/latest/generated/dask.dataframe.DataFrame.partitions.html
        
    Returns:
        None. Saves the object.
    """
    save_object_meta(obj, savedir)
    
    # fetch original column names
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name
    
    if repartition:
        if obj.npartitions >= repartition * 2:
            ds = obj.to_delayed()
            concat_delayed_pandas_dfs = dask.delayed(pd.concat)
            ds_concat = [concat_delayed_pandas_dfs(chunk) for chunk in utils.chunkIt(ds, repartition)]
            divisions_concat = [chunk[0] for chunk in utils.chunkIt(sa.divisions[:-1], repartition)] + [sa.divisions[-1]]
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
    #obj.to_parquet(os.path.join(savedir, 'pandas_to_parquet.parquet'), schema = schema)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

    # reset original colnames
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name

# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""Save and load dask dataframes to and from Apache parquet format.

See also:
    https://parquet.apache.org/docs/overview
"""


import os
# import cloudpickle
import pandas as pd
import dask
import json
from . import parent_classes
from data_base.utils import df_colnames_to_str, chunkIt, convertible_to_int
import json
from .utils import save_object_meta, set_object_meta
import logging
logger = logging.getLogger("ISF").getChild(__name__)

ENGINE = "pyarrow"
COMPRESSION = 'snappy'

def check(obj):
    '''Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a dask.dataframe
    '''
    return isinstance(obj, dask.dataframe)


@dask.delayed
def load_helper(savedir, n_partitions, partition, meta=None, columns=None):
    """Load a single partition of a dask dataframe from a parquet file
    
    Args:
        savedir (str): Directory where the parquet files are stored
        n_partitions (int): Number of partitions
        partition (int): Partition number
        meta (pandas.DataFrame): Meta information for the dask dataframe
        columns (list): Columns to load
        
    Returns:
        dask.dataframe: Dask dataframe
    """
    obj = pd.read_parquet(
        os.path.join(savedir, 'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)),
        columns=columns)
    if meta is not None:
        set_object_meta(obj, meta = meta)
    return obj


@dask.delayed
def save_helper(savedir, delayed_df, n_partitions, partition):
    """Save a single partition of a dask dataframe to a parquet file
    
    Args:
        savedir (str): Directory where the parquet files are stored
        delayed_df (dask.dataframe): Dask dataframe
        n_partitions (int): Number of partitions
        partition (int): Partition number
        
    Returns:
        None
    """
    check_df_suitable_for_pq(delayed_df)
    return delayed_df.to_parquet(
        os.path.join(
            savedir,
            'pandas_to_parquet.{}.{}.parquet'.format(n_partitions, partition)),
        engine=ENGINE,
        compression=COMPRESSION)

@dask.delayed
def check_df_suitable_for_pq(delayed_df):
    assert all([type(e) == str for e in delayed_df.columns]), \
        "This method requires that all column names of the dataframe are strings, \
        but they are {}".format([type(e) for e in delayed_df.columns])
    if delayed_df.index.name is not None:
        assert type(delayed_df.index.name) == str, \
            "This method requires that the index name of the dataframe is a string, \
                but it is {}".format(type(delayed_df.index.name))

class Loader(parent_classes.Loader):
    """Load a dask dataframe from a parquet file
    
    Args:
        meta (pandas.DataFrame): Meta information for the dask dataframe
    """
    def __init__(self, meta):
        self.meta = meta
        if self.meta is None: logger.warning(
            "No meta information provided. \
            Column names, index labels, and index name (if it exists) will be inferred and in string format.")
        
    def get(self, savedir, columns=None):
        """Load a dask dataframe from one or more parquet files.
        
        Args:
            savedir (str): Directory where the parquet files are stored
            columns (list): Columns to load
            
        Returns:
            dask.dataframe: The loaded dask dataframe
            
        See also:
            Each individual partitoin is loaded using :py:meth:`~data_base.isf_data_base.IO.LoaderDumper.dask_to_parquet.load_helper`.
        """
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
                logger.info('Load dask dataframe with known divisions')
        
        return ddf


def dump(obj, savedir, schema=None, client=None, repartition = 10000):
    """Save a dask dataframe to one or more parquet files.
    
    One parquet file per partition is created.
    Each partition is written to a file named 'pandas_to_parquet.<n_partitions>.<partition>.parquet'.
    The writing of these files is parallelized using the dask client if one is provided.
    
    In addition to the dask dataframe itself, meta information is saved in the form of a JSON file.
    
    See also:
        :py:func:`~data_base.isf_data_base.IO.LoaderDumper.utils.save_object_meta` for saving meta information
    
    Args:
        obj (dask.dataframe): Dask dataframe to save
        savedir (str): Directory where the parquet files will be stored
        client (dask.distributed.Client): Dask client for parallellization.
        repartition (int): 
            If the original object has more than twice this amount of partitions, it will be repartitioned.
            Otherwise, the object is saved according to its original partitioning.
            
    Returns:
        None
        
    See also:
        Each individual partitoin is saved using :py:meth:`~data_base.isf_data_base.IO.LoaderDumper.dask_to_parquet.save_helper`.
    """
    # Save object meta information, e.g. dtypes of the columns and column names.
    save_object_meta(obj, savedir)
    
    # fetch original column names
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name
    
    # repartition the dataframe
    if repartition:
        if obj.npartitions >= repartition * 2:
            divisions_concat = [chunk[0] for chunk in chunkIt(obj.divisions[:-1], repartition)] + [obj.divisions[-1]]
            ddf_concat = dask.dataframe.from_delayed(divisions_concat)
            ddf_concat.divisions = divisions_concat
            obj = ddf_concat
    
    # construct delayeds to save the dataframe
    # Note: this converts the column names to string. These are reset to their original dtype at the end
    delayeds = obj.to_delayed()
    delayeds = [dask.delayed(df_colnames_to_str)(d) for d in delayeds]
    delayeds = [
        save_helper(savedir, d, len(delayeds), lv)
        for lv, d in enumerate(delayeds)
    ]

    # Execute the delayeds: save the df to parquet files
    futures = client.compute(delayeds)
    client.gather(futures)
    
    # Save the divisions
    if obj.divisions is not None:
        divisions_serializable = [int(e) if convertible_to_int(e) else e for e in obj.divisions]
        with open(os.path.join(savedir, 'divisions.json'), 'w') as f:
            json.dump(divisions_serializable, f)
    
    # partitions and n_partitions are saved in the filename
    # see load_helper and save_helper. Loader.get() does not need to be initialized with this information
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

    # reset original colnames
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name
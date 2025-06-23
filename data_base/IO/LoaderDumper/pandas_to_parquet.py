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
"""Read and write a pandas DataFrame to the parquet format.

See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.dask_to_parquet` for the correpsonding dask ``LoaderDumper``.
"""

import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
from data_base.utils import df_colnames_to_str
import json
from .utils import save_object_meta, set_object_meta, read_object_meta
import logging
logger = logging.getLogger("ISF").getChild(__name__)


def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a pandas DataFrame or Series.
    """
    return isinstance(
        obj, (pd.DataFrame, pd.Series))


class Loader(parent_classes.Loader):
    """Load for parquet files to pandas DataFrames
    
    Args:
        meta (dict, optional): Meta information to be saved with the object. Defaults to None.
        
    Attributes:
        meta (dict): Meta information to be saved with the object.
    """
    def __init__(self, meta=None):
        self.meta = meta
        if self.meta is None:
            logger.warning("No meta information provided. Column names, index labels, and index name (if it exists) will be string format.")

    def get(self, savedir):
        """Load the pandas DataFrame from the specified folder
        
        Args:
            savedir (str): Directory where the pandas DataFrame is stored.
            
        Returns:
            pd.DataFrame: The pandas DataFrame.
        """
        obj = pd.read_parquet(
            os.path.join(savedir, 'pandas_to_parquet.parquet'))
        if self.meta is not None:
            set_object_meta(
                obj,
                meta = self.meta)
        return obj
        


def dump(obj, savedir):
    """Save the pandas DataFrame in the specified directory.
    
    In addition to the pandas DataFrame itself,
    meta information is also saved in the form of a JSON file.
    
    See also:
        :py:func:`~data_base.isf_data_base.IO.LoaderDumper.utils.save_object_meta` for saving meta information
    
    Args:
        obj (pd.DataFrame): Pandas DataFrame to be saved.
        savedir (str): Directory where the pandas DataFrame should be stored.
    """
    save_object_meta(obj, savedir)
    # save original columns
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name
    # convert column names and index names to str
    # This overrides the original object, hence why we save the meta.
    obj = df_colnames_to_str(obj)
    # dump in parquet format
    obj.to_parquet(os.path.join(savedir, 'pandas_to_parquet.parquet'))
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
    # reset column names
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name

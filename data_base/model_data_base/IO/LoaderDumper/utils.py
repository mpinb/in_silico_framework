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
import os, json, six, yaml
import numpy as np
import pandas as pd
from dask.dataframe import DataFrame as ddf
import logging
logger = logging.getLogger("ISF").getChild(__name__)

def get_numpy_dtype_as_str(obj):
    """
    Get a string representation of the numpy dtype of an object.
    If the object is of type string, simply return 'str'.

    Python 2 has two types of strings: str and unicode. If left unspecified, numpy will default to unicode of unknown length, which is set to 0.
    reading this back in results in the loss of string-type column names. For this reason, we construct our own string representation of the numpy dtype of these columns.
    
    Args:
        obj: The object to get the numpy dtype of.
        
    Returns:
        str: The numpy dtype of the object.
    """
    if (isinstance(obj, six.text_type) or isinstance(obj, str)):
        if six.PY2:  # Check if obj is a string
            return '|S{}'.format(len(obj))
        else:
            return '<U{}'.format(len(obj))  # PY3: assure numpy has enough chars for string, given that the dtype is just 'str
    else:
        return str(np.dtype(type(obj)))
    
def save_object_meta(obj, savedir):
    """
    Construct a meta object to help out dask or parquet later on
    The original meta object is an empty dataframe with the correct column names
    We will save this in str format with parquet, as well as the original dtype for each column.
    
    Args:
        obj: The object to save the meta of.
        savedir: The directory to save the meta file in.
        
    Returns:
        None. Saves the meta object.
    """
    meta = obj._meta if isinstance(obj, ddf) else obj
    meta_json = {
        "columns": [str(c) for c in meta.columns],
        "column_name_dtypes" : [get_numpy_dtype_as_str(c) for c in meta.columns],
        "index_dtype": str(meta.index.dtype),
        "dtypes": [str(e) for e in meta.dtypes.values]
        }
    if meta.index.name is not None:
        meta_json.update({
            'index_name': str(meta.index.name),
            "index_name_dtype": get_numpy_dtype_as_str(meta.index.name)
        })
    with open(os.path.join(savedir, 'object_meta.json'), 'w') as f:
        json.dump(meta_json, f)
        
def get_meta_filename(savedir, raise_=True):
    """
    Get the filename of the meta file in the savedir.
    
    Args:
        savedir (str): The directory to look for the meta file.
        
    Raises:
        FileNotFoundError: If no meta file is found in the savedir.
        
    Returns:
        str: the name of the meta file.
    """
    if os.path.exists(os.path.join(savedir, 'dask_meta.json')):
        # Construct meta dataframe for dask
        meta_name = "dask_meta.json"
        raise DeprecationWarning("dask_meta.json has been renamed to object_meta.json, since both dask-related dumpers, as well as parquet in general needs this. Consider renaming these files, as dask_meta will be removed in the future.")
    elif os.path.exists(os.path.join(savedir, 'object_meta.json')):
        meta_name = "object_meta.json"
    else:
        if raise_:
            raise FileNotFoundError("No meta file found in {}.")
        else:
            logger.warning("No meta file found in {}".format(savedir))
            return None
    return meta_name
        
        
def read_object_meta(savedir, raise_=True):
    """
    Get the metadata associated with a saved object.
    Parquet dumpers convert column names to strings, which changes the dtype upon reading back in.
    Dask dumpers need a meta object to know the dtypes of the columns, including the values.
    
    Args:
        savedir (str): The directory where the meta file is stored.
        
    Returns:
        pd.DataFrame: The metadata of the saved object.
    """
    dtype_map = {'int64': int, 'float64': float, 'object': str, 'bool': bool}
    meta_name = get_meta_filename(savedir, raise_=raise_)
    with open(os.path.join(savedir, meta_name), 'r') as f:
        # use yaml instead of json to ensure loaded data is string (and not unicode) in Python 2
        # yaml is a subset of json, so this should always work, although it assumes the json is ASCII encoded, which should cover all our usecases.
        # See also: https://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-from-json
        meta_json = yaml.safe_load(f)  
    
    meta = pd.DataFrame({
        c: pd.Series([], dtype=t)
        for c, t in zip(meta_json['columns'], meta_json['dtypes'])
        }, 
        columns=meta_json['columns']  # ensure the order of the columns is fixed.
        )
    column_dtype_mapping = [
        (c, t)
        if not t.startswith('<U') else (c, '<U' + str(len(c)))  # PY3: assure numpy has enough chars for string, given that the dtype is just 'str'
        for c, t in zip(meta.columns.values, meta_json['column_name_dtypes'])
        ]
    meta.columns = tuple(np.array([tuple(meta.columns.values)], dtype=column_dtype_mapping)[0])
    meta.index = meta.index.astype(meta_json['index_dtype'])
    if meta_json.get('index_name'):
        # Cast to numpy array, set to correct dtype, extract from array again.
        meta.index.name = np.array([meta_json['index_name']]).astype(meta_json['index_name_dtype'])[0]
    else:
        logger.debug("No index name dtype found in meta file. Index name will be string format. Verify if the column is the desired dtype when resetting the index.")
    return meta

def set_object_meta(obj, savedir):
    """
    Reset the dtypes of the columns and index of an object to the original dtypes.
    Reads in the object meta from the same savedir and tries to assign the correct dtypes to columns and index.
    
    Args:
        obj: The object to reset the dtypes of.
        savedir: The directory where the meta file is stored.
        
    Returns:
        obj: The object with the correct dtypes.
    """
    try:
        meta = read_object_meta(savedir)
    except FileNotFoundError:
        logger.warning("No meta file found in {}. Skipping setting meta.".format(savedir))
        return obj
    
    # Reset object dtypes
    try:
        obj.index = obj.index.astype(meta.index.dtype)
        obj.index.name = meta.index.name
    except Exception as e:
        logger.warning(e)
        logger.warning("Could not set the dtype of the index. Index will be string format")
    try:
        obj.columns = meta.columns
    except Exception as e:
        logger.warning(e)
        logger.warning("Could not set the dtype of the columns. Columns will be string format")
    return obj
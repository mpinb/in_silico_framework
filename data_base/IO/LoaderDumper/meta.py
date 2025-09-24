"""Read and write dataframe meta.

The meta of a dataframe is an empty dataframe containing only the columns, column dtypes, index, index name, and index dtype.
These meta objects are used by dask and parquet to infer these properties during reading.
"""


import os, json, yaml
import numpy as np
import pandas as pd
from dask.dataframe import DataFrame as ddf
import logging
from config import get_meta_file_format
from isf_pandas_msgpack import to_msgpack, read_msgpack
from .utils import get_numpy_dtype_as_str

logger = logging.getLogger("ISF").getChild(__name__)


def _save_object_meta_json(obj, savedir):
    """Save the meta of an object in JSON format.

    JSON is human-readable, with the downside of being slow for dataframes with many columns.
    The dtypes of the columns and index are saved as string in numpy format.
    
    See also:
        :py:meth:`~data_base.IO.LoaderDumper.utils.get_numpy_dtype_as_str`
    
    Args:
        obj (dask.DataFrame | parquet.DataFrame): The object to save the meta of.
        savedir (str): The directory to save the meta file in.
        
    Returns:
        None: Saves the meta object.
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
            'index_name_dtype': get_numpy_dtype_as_str(meta.index.name)
        })
    with open(os.path.join(savedir, 'object_meta.json'), 'w') as f:
        json.dump(meta_json, f)


def _save_object_meta_msgpack(obj, savedir):
    """Save the meta of an object in msgpack format.
    
    Msgpack is fast, with the downside of not being human-readable.
    The dtypes of columns and indices are preserved automatically in msgpack.
    
    Args:
        obj (dask.DataFrame | parquet.DataFrame): The dataframe to save the meta of.
        savedir (str): The directory to save the meta file in.

    Returns:
        None: Writes result to disk.
    """
    meta = obj._meta if isinstance(obj, ddf) else obj
    to_msgpack(os.path.join(savedir, "object_meta.msgpack"), meta)


def save_object_meta(obj, savedir):
    """Save an object's meta in the file format configured in py:mod:`config`.
    
    Args:
        obj (dask.DataFrame | parquet.DataFrame): The dataframe to save the meta of.
        savedir (str): The directory to save the meta file in.

    Returns:
        None: Writes result to disk.
    """
    file_format = get_meta_file_format()
    if file_format == 'msgpack':
        _save_object_meta_msgpack(obj, savedir)
    elif file_format == 'json':
        _save_object_meta_json(obj, savedir)
    else:
        raise NotImplementedError("Invalid meta file format in database config: {}".format(file_format))
        

def get_meta_filename(savedir, raise_=True):
    """Get the filename of the meta file in the savedir.
    
    Args:
        savedir (str): The directory to look for the meta file.
        raise\_ (bool, optional): Whether to raise an error if no meta file is found. Defaults to True.
        
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
    elif os.path.exists(os.path.join(savedir, "object_meta.msgpack")):
        meta_name = "object_meta.msgpack"
    else:
        if raise_:
            raise FileNotFoundError("No meta file found in {}.")
        else:
            logger.warning("No meta file found in {}".format(savedir))
            return None
    return meta_name
        
        
def _read_object_meta_json(meta_fn):
    """Get the meta of a saved database key in JSON.
    
    Args:
        savedir (str): The directory where the meta file is stored.
        
    Returns:
        pd.DataFrame: The metadata of the saved object.
    """
    with open(os.path.join(meta_fn), 'r') as f:
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
        for c, t in zip(meta.columns, meta_json['column_name_dtypes'])
        ]
    meta.columns = tuple(np.array([tuple(meta.columns.values)], dtype=column_dtype_mapping)[0])
    meta.index = meta.index.astype(meta_json['index_dtype'])
    if meta_json.get('index_name'):
        # Cast to numpy array, set to correct dtype, extract from array again.
        meta.index.name = np.array([meta_json['index_name']]).astype(meta_json['index_name_dtype'])[0]
    else:
        logger.debug("No index name dtype found in meta file. Index name will be string format. Verify if the column is the desired dtype when resetting the index.")
    return meta


def read_object_meta(savedir, raise_=True):
    """Read the meta of a dask/parquet object.
    
    Assumes there is a meta file present in :py:param:`savedir` 
    (see :py:meth:`get_meta_filename` for allowed formats).
    
    Args:
        savedir (str): directory where the file partitions and object meta are saved. 
            This corresponds to the database key filepath.
        raise\_ (bool, optional): Whether to raise an errror if the meta object is not found on disk.

    Returns:
        pd.DataFrame: A pandas dataframe representing the object meta: column names, column dtypes, index name and index dtype.
    """
    meta_name = get_meta_filename(savedir, raise_=raise_)
    meta_fn = os.path.join(savedir, meta_name)
    if meta_name.endswith('json'):
        return _read_object_meta_json(meta_fn=meta_fn)
    elif meta_name.endswith('msgpack'):
        return read_msgpack(meta_fn)
    else:
        raise NotImplementedError("Invalid file format for object meta at {}: {}".format(savedir, meta_name))


def set_object_meta(obj, meta):
    """Set/reset the meta of a dataframe.
    
    Reads in the object meta from the same savedir and tries to assign the correct dtypes to columns and index, as well as the index name.
    
    Args:
        obj: The object to reset the dtypes of.
        meta (pd.DataFrame): metadata for the object, containing only column names and the index with correct dtypes.
        
    Returns:
        None. Adapts the original object.
        
    Raises:
        AssertionError: If the object is not a pandas DataFrame, pandas Series, or dask DataFrame.
        AssertionError: If no meta information is provided.
    """
    assert isinstance(obj, (pd.DataFrame, pd.Series, ddf)), "Object must be a pandas DataFrame, pandas Series, or dask DataFrame." 
    assert meta is not None, "No meta information provided. Cannot set the dtypes of the object."
    # Reset object dtypes
    try:
        obj.index = obj.index.astype(meta.index.dtype)
        obj.index.name = meta.index.name
    except Exception as e:
        logger.warning(e)
        logger.warning("Could not set the dtype of the index. Check if the index dtype is as expected.")
    try:
        obj.columns = meta.columns
    except Exception as e:
        logger.warning(e)
        logger.warning("Could not set the dtype of the columns. Check if the column dtypes are as expected.")

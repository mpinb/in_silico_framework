import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
from data_base.utils import df_colnames_to_str
from .utils import save_object_meta, set_object_meta
import logging
logger = logging.getLogger("ISF").getChild(__name__)


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))


class Loader(parent_classes.Loader):
    def get(self, savedir):
        """
        Load a pandas dataframe or series from a parquet file.
        Re-assign the original dtype of the columns if a meta file is present.
        
        Args:
            savedir (str): The directory to load the object from.
            
        Raises:
            FileNotFoundError: If no meta file is found in the savedir.
            
        Returns:
            pd.DataFrame or pd.Series: The loaded object.
        """
        obj = pd.read_parquet(
            os.path.join(savedir, 'pandas_to_parquet.parquet'))
        obj = set_object_meta(obj, savedir)
        return obj


def dump(obj, savedir):
    """
    Save a pandas dataframe or series to a parquet file.
    Save metadata alongside the original object containing the column names and their original dtypes.
    
    Args:
        obj: The object to save.
        savedir (str): The directory to save the object in.
        
    Returns:
        None. Saves the object.
    """
    save_object_meta(obj, savedir)
    # save original columns
    columns = obj.columns
    if obj.index.name is not None:
        index_name = obj.index.name
    # convert column names and index names to str
    obj = df_colnames_to_str(obj)  # overrides original object
    # dump in parquet format
    obj.to_parquet(os.path.join(savedir, 'pandas_to_parquet.parquet'))
    compatibility.cloudpickle_fun(
        Loader(),
        os.path.join(savedir, 'Loader.pickle'))
    # reset column names
    obj.columns = columns
    if obj.index.name is not None:
        obj.index.name = index_name

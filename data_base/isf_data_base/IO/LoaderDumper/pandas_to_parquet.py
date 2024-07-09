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
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame, pd.Series))


class Loader(parent_classes.Loader):
    def __init__(self, meta=None):
        self.meta = meta
        if self.meta is None:
            logger.warning("No meta information provided. Column names, index labels, and index name (if it exists) will be string format.")

    def get(self, savedir):
        obj = pd.read_parquet(
            os.path.join(savedir, 'pandas_to_parquet.parquet'))
        if self.meta is not None:
            set_object_meta(
                obj,
                meta = self.meta)
        return obj
        


def dump(obj, savedir):
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

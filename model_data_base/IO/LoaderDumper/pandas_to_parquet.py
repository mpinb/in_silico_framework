import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
from model_data_base.utils import df_colnames_to_str


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return pd.read_parquet(
            os.path.join(savedir, 'pandas_to_parquet.parquet'))


def dump(obj, savedir):
    # convert column names and index names to str
    obj = df_colnames_to_str(obj)  # overrides original object
    # dump in parquet format
    obj.to_parquet(os.path.join(savedir, 'pandas_to_parquet.parquet'))
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

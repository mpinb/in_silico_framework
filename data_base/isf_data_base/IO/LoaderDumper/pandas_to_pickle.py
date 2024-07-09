import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return pd.read_pickle(os.path.join(savedir, 'pandas_to_pickle.pickle'))


def dump(obj, savedir):
    obj.to_pickle(os.path.join(savedir, 'pandas_to_pickle.pickle'))

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

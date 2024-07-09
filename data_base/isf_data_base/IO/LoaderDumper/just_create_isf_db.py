import os
# import cloudpickle
from . import parent_classes
import json

def check(obj):
    '''checks whether obj can be saved with this dumper'''
    return obj is None  #isinstance(obj, np) #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return ISFDataBase(os.path.join(savedir, 'db'))


def dump(obj, savedir):
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

from data_base.isf_data_base.isf_data_base import ISFDataBase
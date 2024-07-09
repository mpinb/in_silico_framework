import os
# import cloudpickle
import compatibility
from . import parent_classes
from data_base.model_data_base.model_data_base import ModelDataBase


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return obj is None  #isinstance(obj, np) #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return ModelDataBase(os.path.join(savedir, 'mdb'))


def dump(obj, savedir):
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
    #         cloudpickle.dump(Loader(), file_)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

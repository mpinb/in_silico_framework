import os
# import cloudpickle
import compatibility
import numpy as np
from . import parent_classes


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, np)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return np.load(os.path.join(savedir, 'np.npz'))['arr_0']


def dump(obj, savedir):
    np.savez_compressed(os.path.join(savedir, 'np.npz'), arr_0=obj)
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
    #         cloudpickle.dump(Loader(), file_)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

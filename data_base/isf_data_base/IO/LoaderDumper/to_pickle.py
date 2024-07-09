import os
from . import parent_classes
import compatibility
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        #         with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
        #             return cPickle.load(file_)
        return compatibility.unpickle_fun(
            os.path.join(savedir, 'to_pickle_dump'))


def dump(obj, savedir):
    compatibility.pickle_fun(obj, os.path.join(savedir, 'to_pickle_dump'))
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
import os
import msgpack
from . import parent_classes
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
            return msgpack.load(file_)


def dump(obj, path):
    with open(os.path.join(path, 'to_pickle_dump'), 'wb') as file_:
        msgpack.dump(obj, file_)

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
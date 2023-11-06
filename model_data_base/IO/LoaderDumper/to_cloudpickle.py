import os
import compatibility
from . import parent_classes


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        #         with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
        #             return cloudpickle.load(file_, encoding = 'latin1')
        return compatibility.pandas_unpickle_fun(
            os.path.join(savedir, 'to_pickle_dump'))


def dump(obj, path):
    compatibility.cloudpickle_fun(obj, os.path.join(path, 'to_pickle_dump'))
    compatibility.cloudpickle_fun(Loader(), os.path.join(path, 'Loader.pickle'))


#     with open(os.path.join(path, 'to_pickle_dump'), 'wb') as file_:
#         cloudpickle.dump(obj, file_)

#     with open(os.path.join(path, 'Loader.pickle'), 'wb') as file_:
#         cloudpickle.dump(Loader(), file_)

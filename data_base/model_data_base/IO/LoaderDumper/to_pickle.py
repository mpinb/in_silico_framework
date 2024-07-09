import os
from . import parent_classes
import compatibility


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        #         with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
        #             return cPickle.load(file_)
        return compatibility.unpickle_fun(
            os.path.join(savedir, 'to_pickle_dump'))


def dump(obj, path):
    compatibility.pickle_fun(obj, os.path.join(path, 'to_pickle_dump'))
    compatibility.pickle_fun(Loader(), os.path.join(path, 'Loader.pickle'))


#     with open(os.path.join(path, 'to_pickle_dump'), 'wb') as file_:
#         cPickle.dump(obj, file_, protocol=cPickle.HIGHEST_PROTOCOL)

#     with open(os.path.join(path, 'Loader.pickle'), 'wb') as file_:
#         cPickle.dump(Loader(), file_)
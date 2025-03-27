"""Read and write numpy arrays to msgpack files

.. deprecated:: 0.2.0
   The msgpack format is deprecated and will be removed in a future version.
   Please consider using the Apache parquet, ``npz`` or ``npy`` formats.
   
:skip-doc:
"""


import os
# import cloudpickle
import compatibility
import pandas as pd
import numpy as np
from . import parent_classes
import isf_pandas_msgpack
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, np)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return isf_pandas_msgpack.read_msgpack(
            os.path.join(savedir, 'pandas_to_msgpack')).values


def dump(obj, savedir):
    obj = pd.DataFrame(obj)
    #     obj.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'), compress = 'blosc')
    isf_pandas_msgpack.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'),
                              obj,
                              compress='blosc')

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

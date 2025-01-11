"""Read and write a numpy array to the compressed ``.npz`` format.

See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.numpy_to_npy` for saving a single numpy array to a ``npy`` file.
"""


import os
# import cloudpickle
import compatibility
import numpy as np
from . import parent_classes
import json


def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a numpy object.
    """
    return isinstance(obj, np)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):
    """Loader for ``npz`` numpy arrays"""
    def get(self, savedir):
        return np.load(os.path.join(savedir, 'np.npz'))['arr_0']


def dump(obj, savedir):
    np.savez_compressed(os.path.join(savedir, 'np.npz'), arr_0=obj)
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

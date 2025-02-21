"""Read and write a numpy array to the ``zarr`` format.

See also:
    https://zarr.readthedocs.io/en/stable/api/zarr/storage/index.html#zarr.storage.LocalStore
"""


import os, json
# import cloudpickle
import numpy as np
from . import parent_classes
import zarr


def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a numpy object.
    """
    return isinstance(obj, np)


class Loader(parent_classes.Loader):
    """Loader for zarr objects"""
    def get(self, savedir):
        """Read in an object in ``.zarr`` format.
        
        Args:
            savedir (str): Directory where the ``.zarr`` object is saved.
        """
        return zarr.load(os.path.join(savedir, 'obj.zarr'))


def dump(obj, savedir):
    """Write out an object in .zarr format.
    
    Args:
        obj (object): Object to be saved
        savedir (str): Directory where the object is saved
    """
    zarr.save_array(os.path.join(savedir, 'obj.zarr'), obj)

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

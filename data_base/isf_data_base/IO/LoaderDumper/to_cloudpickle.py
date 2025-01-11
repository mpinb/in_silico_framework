"""Read and write an object to the cloudpickle format.

This is the default dumper for :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase` objects,
since they can save basically any Python object.
"""

import os
import compatibility
from . import parent_classes
import json


def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object can be saved with pickle (always True).
    """
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):
    """Loader for cloudpickle objects"""
    def get(self, savedir):
        """Load the object from the specified folder
        
        Args:
            savedir (str): Directory where the object is stored.
            
        Returns:
            object: The object.
        """
        return compatibility.pandas_unpickle_fun(
            os.path.join(savedir, 'to_pickle_dump'))


def dump(obj, savedir):
    """Save the object in the specified directory
    
    Args:
        obj (object): Object to be saved.
        savedir (str): Directory where the object should be stored.
    """
    compatibility.cloudpickle_fun(obj, os.path.join(savedir, 'to_pickle_dump'))
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)


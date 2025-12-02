# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
        """Read in an object in ``.npz`` format.
        
        Args:
            savedir (str): Directory where the ``.npz`` object is saved.
        """
        return np.load(os.path.join(savedir, 'np.npz'))['arr_0']


def dump(obj, savedir):
    """Write an object to a ``.npz`` file.
    
    Args:
        obj (object): Object to be saved.
        savedir (str): Directory where the object is saved.
    """
    np.savez_compressed(os.path.join(savedir, 'np.npz'), arr_0=obj)
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
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

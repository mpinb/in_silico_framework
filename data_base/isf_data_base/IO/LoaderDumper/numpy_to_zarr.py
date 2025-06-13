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

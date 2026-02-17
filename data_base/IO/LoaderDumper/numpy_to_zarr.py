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

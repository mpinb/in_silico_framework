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
"""Read and write an object to the cloudpickle format.

This is the default dumper for :class:`~data_base.DataBase` objects,
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


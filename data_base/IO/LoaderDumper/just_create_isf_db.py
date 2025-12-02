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
"""Create and load :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase` objects in a database.
"""

import os
# import cloudpickle
from . import parent_classes
import json

def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
    
    Returns:
        bool: Whether the object is None. This dumper requires no object to be saved.
    """
    return obj is None  #isinstance(obj, np) #basically everything can be saved with pickle


class Loader(parent_classes.Loader):
    """Loader for :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase` objects"""
    def get(self, savedir, **kwargs):
        """Load the database from the specified folder.
        
        Args:
            savedir (str): Directory where the database is stored.
            **kwargs: Additional keyword arguments. 
                These are passed to the :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase` constructor.
        """
        return ISFDataBase(os.path.join(savedir, 'db'), **kwargs)


def dump(obj, savedir):
    """Create a :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase` object in the specified :paramref:`savedir`
    
    Args:
        obj (None, optional): No object is required. If an object is passed, it is ignored.
        savedir (str): Directory where the database should be stored.
    """
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

from data_base.isf_data_base import ISFDataBase
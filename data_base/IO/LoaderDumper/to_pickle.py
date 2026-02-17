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
"""Read and write objects to the pickle format.

See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.to_cloudpickle` for saving to the cloudpickle format.
"""
import os
from . import parent_classes
import compatibility
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
    """Loader for pickle objects"""
    def get(self, savedir):
        """Load the object from the specified folder
        
        Args:
            savedir (str): Directory where the object is stored.
            
        Returns:
            object: The loaded object.
        """
        #         with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
        #             return cPickle.load(file_)
        return compatibility.unpickle_fun(
            os.path.join(savedir, 'to_pickle_dump'))


def dump(obj, savedir):
    """Save the object in the specified directory
    
    Args:
        obj (object): Object to be saved.
        savedir (str): Directory where the object should be stored.
    """
    compatibility.pickle_fun(obj, os.path.join(savedir, 'to_pickle_dump'))
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
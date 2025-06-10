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
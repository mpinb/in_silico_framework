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
"""Create and load :py:class:`~data_base.isf_data_base.isf-data_base.ISFDataBase` objects in a database.
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

from data_base.isf_data_base.isf_data_base import ISFDataBase
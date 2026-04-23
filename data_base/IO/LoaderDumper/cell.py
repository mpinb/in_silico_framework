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
"""Save and load :py:class:`~single_cell_parser.cell.Cell` objects to and from ``.pickle`` format.
"""

import os
import cloudpickle
import numpy as np
from . import parent_classes
from single_cell_parser.cell import Cell
from single_cell_parser.serialize_cell import save_cell_to_file
from single_cell_parser.serialize_cell import load_cell_from_file


def check(obj):
    '''Checks whether obj can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a :class:`single_cell_parser.cell.Cell` object
    '''
    return isinstance(obj, Cell)


class Loader(parent_classes.Loader):
    """Loader for :class:`~single_cell_parser.cell.Cell` objects
    
    See also:
        :func:`~single_cell_parser.serialize_cell.load_cell_from_file`
    """
    def get(self, savedir):
        """Loads a :class:`~single_cell_parser.cell.Cell` object from a directory
        """
        return load_cell_from_file(os.path.join(savedir, 'cell'))


def dump(obj, savedir):
    """Dumps a :class:`~single_cell_parser.cell.Cell` object to a directory
    
    Args:
        obj (:class:`~single_cell_parser.cell.Cell`): Object to be saved
        savedir (str): Directory to save the object to
        
    See also:
        :func:`~single_cell_parser.serialize_cell.save_cell_to_file`
    """
    save_cell_to_file(os.path.join(savedir, 'cell'), obj)

    with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
        cloudpickle.dump(Loader(), file_)

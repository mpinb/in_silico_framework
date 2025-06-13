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
import os
import cloudpickle
import compatibility
import numpy as np
from . import parent_classes
from single_cell_parser.cell import Cell
from single_cell_parser.serialize_cell import save_cell_to_file
from single_cell_parser.serialize_cell import load_cell_from_file


def check(obj):
    '''checks whether obj can be saved with this dumper'''
    return isinstance(obj, Cell)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return load_cell_from_file(os.path.join(savedir, 'cell'))


def dump(obj, savedir):
    save_cell_to_file(os.path.join(savedir, 'cell'), obj)

    with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
        cloudpickle.dump(Loader(), file_)
    #compatibility.cloudpickle_fun(Loader(), file_)
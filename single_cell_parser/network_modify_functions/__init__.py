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

'''Modify the cell and/or network after both have been initalized.

Such a function can for example be used to deactivate specific synapses at a soma distance.
'''
import importlib

__author__ = "Arco Bast"
__date__ = "2019-02-16"

def get(funname):
    '''Get the function with the given name.

    Network modify functions reside in a module of the same name.
    This method fetches them from said module.
    
    Args:
        funname (str): Name of the function to get.

    Returns:
        callable: The function with the given name.
    '''
    module = importlib.import_module(__name__ + '.' + funname)
    fun = getattr(module, funname)
    return fun

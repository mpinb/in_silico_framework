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

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
'''Read and write data in various formats.

This package provides IO modules that always contain three components:

1. A ``dump()`` function to write out the data, and its corresponding ``Loader`` object.
2. A ``Loader`` class that can load the data back into memory.
3. a ``check()`` method that checks whether the object can be saved with this dumper.

To save an object, the dump method is called::

    >>> import myDumper
    >>> myDumper.dump(obj, savedir)
 
This saves the object as specified in the respective ``dump()`` method.
In addition, a ``Loader.json`` is saved alongside the data. 
This file contains the specification of a ``Loader`` object, 
which can then be initialized and contains all the mechanisms to load the object back into memory.
'''

import os
# import cloudpickle
import compatibility, json, yaml
from .utils import read_object_meta
from data_base.exceptions import DataBaseException
from inspect import getmodule
import importlib
import pandas as pd
import numpy as np


def load(savedir, load_data=True, loader_kwargs={}):
    '''Standard interface to load data.
    
    Loads the data's respective ``Loader`` in the same directory as the data.
    Uses this ``Loader`` to load the data
    
    Args:
        savedir (str): Path to the data
        load_data (bool): Whether to load the data (default), or just the ``Loader`` object. Useful for debugging purposes.
        loader_kwargs (dict): Additional keyword arguments for the loader. Note that the ``Loader.json`` file should in principle contain all necessary information.
        
    Returns:
        object: The loaded object: either the data, or the ``Loader`` object.
    
    '''
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'rb') as file_:
    #         myloader = cloudpickle.load(file_, encoding = 'latin1')
    if os.path.exists(os.path.join(savedir, 'Loader.pickle')):
        raise DataBaseException("You're loading a .pickle file, which is the format used by data_base.model_data_base. However, I am the load() method from data_base.isf_data_base, not data_base.model_data_base.")
        myloader = compatibility.pandas_unpickle_fun(
            os.path.join(savedir, 'Loader.pickle'))
    else:
        with open(os.path.join(savedir, 'Loader.json'), 'r') as f:
            loader_init_kwargs = json.load(f)
        loader = loader_init_kwargs['Loader']
        del loader_init_kwargs['Loader']
        if os.path.exists(os.path.join(savedir, 'object_meta.json')):
            loader_init_kwargs['meta'] = read_object_meta(savedir)
        myloader = importlib.import_module(loader).Loader(**loader_init_kwargs)
    if load_data:
        return myloader.get(savedir, **loader_kwargs)
    else:
        return myloader


def get_dumper_string_by_dumper_module(dumper_module):
    """Convert a dumper submodule to a string.
    
    This is used to write the ``Loader.json`` specification file.

    Args:
        dumper_module: The module to check.
    
    Returns:
        The dumper string, relative to its parent ``LoaderDumper`` module.
        
    Example::
    
        >>> import data_base.isf_data_base.IO.LoaderDumper.my_dumper as dumper_module
        >>> get_dumper_string_by_dumper_module(dumper_module)
        'my_dumper'
    """
    name = dumper_module.__name__
    name = generic_to_specific_databases_module_name(name)
    prefix = 'data_base.isf_data_base.IO.LoaderDumper.'
    assert name.startswith(prefix), "Could not import dumper module {}, as it does not contain the prefix {} or".format(name, prefix)
    return name[len(prefix):]


def generic_to_specific_databases_module_name(module_name):
    """Convert a relative module path to an absolute one.
    
    Internally, ISF does not specify which database system to use,
    and simply tries to fetch any generic ``data_base.IO.LoaderDumper.my_dumper``.
    This function converts that relative module path to an absolute.
    
    Example::
    
        >>> dumper = 'data_base.IO.LoaderDumper.my_dumper'
        >>> generic_to_specific_database_module_name(dumper)
        'data_base.isf_data_base.IO.LoaderDumper.my_dumper
    
    Args:
        module_path (str): The relative module path.
    
    Returns:
        str: The absolute module path.
    """
    if not module_name.startswith('data_base.isf_data_base.') and module_name.startswith('data_base.'):
        # In case it is used as data_base.IO module
        module_name = module_name.split('.')
        module_name.insert(1, 'isf_data_base')
        module_name = '.'.join(module_name)
    return module_name


def get_dumper_string_by_savedir(savedir):
    """Get the dumper string from a filepath.
    
    This function reads the ``Loader.json`` file in the savedir and returns the dumper in string format.
    
    Args:
        savedir (str): The path to the saved data. Must contain a ``Loader.json`` file.
        
    Returns:
        str: The dumper string.
    """
    loader_kwargs = json.load(open(os.path.join(savedir, 'Loader.json')))
    loader_module = loader_kwargs['Loader']
    del loader_kwargs['Loader']
    dumper_module = importlib.import_module(loader_module)
    
    return get_dumper_string_by_dumper_module(dumper_module)


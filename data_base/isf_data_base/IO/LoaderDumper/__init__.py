'''Module implements a database concept, using two interfaces:
(1) the dump function
(2) the loader class

To save an object, the dump method is called, e.g:

..highlight:: python
..code-block:: python
    import myDumper
    myDumper.dump(obj, savedir)
 
This saves the object using a method specified in the respective dump method.
Additionally, a file Loader.pickle is created. This contains a Loader object,
which contains all the mechanisms to load the object. 

The Loader class provides a get-method, which returns the saved object. To allow
moving of the data, the path of the data is not saved within the Loader object
and has to be passed to the get function. This is wrapped in the following load function,
which is the intended way to reload arbitrary objects saved with a Dumper.
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
    '''Standard interface to load data, that was saved to savedir
    with an arbitrary dumper'''
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
    """
    Check if a dumper module starts with the correct prefix.
    The prefix can either be isf_data_base.something, 
    but also data_base.something, since isf_data_base is the default data_base system for the isf project.

    Args:
        dumper_module: The module to check.
    
    Returns:
        The dumper string.
    """
    name = dumper_module.__name__
    if not name.startswith('data_base.isf_data_base.') and name.startswith('data_base.'):
        # In case it is used as data_base.IO module
        name = name.split('.')
        name.insert(1, 'isf_data_base')
        name = '.'.join(name)
    prefix = 'data_base.isf_data_base.IO.LoaderDumper.'
    assert name.startswith(prefix), "Could not import dumper module {}, as it does not contain the prefix {} or".format(name, prefix)
    return name[len(prefix):]


def get_dumper_string_by_savedir(savedir):
    loader_kwargs = json.load(open(os.path.join(savedir, 'Loader.json')))
    loader_module = loader_kwargs['Loader']
    del loader_kwargs['Loader']
    dumper_module = importlib.import_module(loader_module)
    
    return get_dumper_string_by_dumper_module(dumper_module)


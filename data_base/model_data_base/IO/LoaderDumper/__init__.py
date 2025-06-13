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
# import cloudpickle
import compatibility
'''Module implements a database concept, using two interfaces:
(1) the dump function
(2) the loader class

To save an object, the dump method is called, e.g.
 > import myDumper
 > myDumper.dump(obj, savedir)
 
This saves the object using a method specified in the respective dump method.
Additionally, a file Loader.pickle is created. This contains a Loader object,
which contains all the mechanisms to load the object. 

The Loader class provides a get-method, which returns the saved object. To allow
moving of the data, the path of the data is not saved within the Loader object
and has to be passed to the get function. This is wrapped in the following load function,
which is the intended way to reload arbitrary objects saved with a Dumper.
'''
def _load_pickle(savedir):
    warnings.warn('Deprecated')
    pass

def _load_json(savedir):
    pass

def load(savedir, load_data=True, loader_kwargs={}):
    '''Standard interface to load data, that was saved to savedir
    with an arbitrary dumper'''
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'rb') as file_:
    #         myloader = cloudpickle.load(file_, encoding = 'latin1')
    myloader = compatibility.pandas_unpickle_fun(
        os.path.join(savedir, 'Loader.pickle'))
    if load_data:
        return myloader.get(savedir, **loader_kwargs)
    else:
        return myloader

def get_dumper_string_by_dumper_module(dumper_module):
    """
    Dumper modules can either be:
    - data_base.model_data_base.IO.LoaderDumper.some_module
    - model_data_base.IO.LoaderDumper.some_module (for backwards compatibility)
    - data_base.IO
    """
    name = dumper_module.__name__
    if name.startswith('data_base.model_data_base'):
        # For backwards compatibility: drop data_base. 
        name = '.'.join(name.split('.')[1:])
    elif name.startswith('data_base'):
        # This happens when ISF is used in Python 2: all IO subpackages are ISF-wide "data_base.IO"
        # save as model_data_base instead of data_base for backwards compatibility
        name = name.replace('data_base.', 'model_data_base.')
    prefix = 'model_data_base.IO.LoaderDumper.'
    assert name.startswith(prefix), "Could not import dumper {}, as it does not contain the prefix {}".format(name, prefix)
    return name[len(prefix):]

def get_dumper_string_by_savedir(savedir):
    import inspect
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'rb') as file_:
    #         myloader = cloudpickle.load(file_)
    myloader = compatibility.pandas_unpickle_fun(
        os.path.join(savedir, 'Loader.pickle'))
    dumper = inspect.getmodule(myloader)
    return get_dumper_string_by_dumper_module(dumper)

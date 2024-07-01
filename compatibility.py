'''
This module deals with API changes in 3rd party modules, and ensures backwards compatibility with older versions of ISF.
The following 3rd party modules are used: pandas, dask, distributed
'''

import six, yaml, cloudpickle, sys
import logging
import pkgutil
from importlib import import_module
logger = logging.getLogger("ISF").getChild(__name__)

# try: # new dask versions
#     synchronous_scheduler = dask.get
# except AttributeError: # old dask versions
#     synchronous_scheduler = dask.async.get_sync

# synchronous_scheduler = dask.get

#def mycompute(*args, **kwargs):
#    if six.PY3:
#        if 'get' in kwargs:
#            kwargs['scheduler'] = kwargs['get']
#            del kwargs['get']
#    return dask.compute(*args, **kwargs)

#dask.compute = mycompute


# --------------- compatibility with Python 2.7 vs Python 3.8/3.9
#  multiprocessing_scheduler = dask.multiprocessing.get
from six.moves import cPickle
if six.PY2:

    def pickle_fun(obj, file_path):
        with open(file_path, 'wb') as f:
            cPickle.dump(obj, f)

    def unpickle_fun(file_path):
        with open(file_path, 'rb') as f:
            return cPickle.load(f)

    def cloudpickle_fun(obj, file_path):
        with open(file_path, 'wb') as f:
            cloudpickle.dump(obj, f)

    def uncloudpickle_fun(file_path):
        with open(file_path, 'rb') as f:
            return cloudpickle.load(f)

    def pandas_unpickle_fun(file_path):
        return uncloudpickle_fun(file_path)

    YamlLoader = yaml.Loader

elif six.PY3:
    import types
    types.SliceType = slice

    def pickle_fun(obj, file_path):
        with open(file_path, 'wb') as f:
            cPickle.dump(obj, f, protocol=2)

    def unpickle_fun(file_path):
        with open(file_path, 'rb') as f:
            return cPickle.load(f, encoding='latin1')

    def cloudpickle_fun(obj, file_path):
        with open(file_path, 'wb') as f:
            cloudpickle.dump(obj, f, protocol=2)

    def uncloudpickle_fun(file_path):
        with open(file_path, 'rb') as f:
            return cloudpickle.load(f, encoding='latin1')

    def pandas_unpickle_fun(file_path):
        import pandas.compat.pickle_compat  #import Unpickler
        with open(file_path, 'rb') as f:
            return pandas.compat.pickle_compat.load(f)

    YamlLoader = yaml.FullLoader  # Better choice, but only exists in Py3

    import pandas.core.indexes
    sys.modules['pandas.indexes'] = pandas.core.indexes
        

# --------------- compatibility with old versions of ISF (only used by the Oberlaender lab in Bonn)
# For old pickled data. 
# This is to ensure backwards compatibility with the Oberlaender lab in MPINB, Bonn. Last adapted on 25/04/2024
# Previous versions of this codebase used pickle as a data format, pickle now tries to import modules that don't exist anymore upon loading
# For this reason, we save the renamed packages/modules under an additional name (i.e. their old name)

# simrun2 and simrun3 have been merged to simrun
import simrun
sys.modules['simrun3'] = simrun
sys.modules['simrun2'] = simrun

def register_module_or_pkg_old_name(module, replace_name, replace_with):
    additional_module_name = module.__name__.replace(replace_name, replace_with)
    logger.debug("Registering module \"{}\" under the name \"{}\"".format(module.__name__, additional_module_name))
    sys.modules[additional_module_name] = module


def register_package_under_additional_name(parent_package_name, replace_name, replace_with):
    parent_package = import_module(parent_package_name)
    register_module_or_pkg_old_name(parent_package, replace_name=replace_name, replace_with=replace_with)
    
    subpackages = []
    for loader, module_or_pkg_name, is_pkg in pkgutil.iter_modules(parent_package.__path__, parent_package.__name__+'.'):
        submodule = import_module(module_or_pkg_name)
        register_module_or_pkg_old_name(submodule, replace_name=replace_name, replace_with=replace_with)
        if is_pkg:
            subpackages.append(module_or_pkg_name)
    for pkg in subpackages:
        register_package_under_additional_name(pkg, replace_name, replace_with)

def init_mdb_backwards_compatibility():
    """
    Registers model_data_base as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. model_data_base has since been moved to :py:mod:`data_base.model_data_base`
    """
    register_package_under_additional_name(
        parent_package_name = "data_base.model_data_base", 
        replace_name="data_base.model_data_base", 
        replace_with="model_data_base"
    )
    
    import data_base, model_data_base.model_data_base
    model_data_base.model_data_base.get_mdb_by_unique_id = data_base.data_base.get_db_by_unique_id

def init_db_compatibility():
    """
    ISF has an update data_base_package, and imports it as :py:mod:`data_base` throughout the codebase.
    This new package has updated API calls, and should be used in all new code.
    For this reason, the old API of model_data_base needs to be updated.
    """
    import sys
    from data_base.isf_data_base import IO, db_initializers, dbopen
    sys.modules['data_base.IO'] = IO
    sys.modules['data_base.db_initializers'] = db_initializers 
    sys.modules['data_base.dbopen'] = dbopen
    
def init_data_base_compatibility():
    init_db_compatibility()
    init_mdb_backwards_compatibility()
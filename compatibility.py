'''
This module deals with API changes in 3rd party modules, and ensures backwards compatibility with older versions of ISF.
The following 3rd party modules are used: pandas, dask, distributed
'''

import six, yaml, cloudpickle, sys

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

import simrun
sys.modules['simrun3'] = simrun  # simrun used to be simrun2 and simrun3 (separate packages). Pickle still wants a simrun3 to exist.

def init_mdb_backwards_compatibility():
    """
    Registers model_data_base as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. model_data_base has since been moved to :py:mod:`data_base.model_data_base`
    """
    from data_base import model_data_base
    sys.modules['model_data_base'] = model_data_base

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
    init_mdb_backwards_compatibility()
    init_db_compatibility()

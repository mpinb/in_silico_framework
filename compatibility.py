'''
This module deals with API changes in 3rd party modules.
The following 3rd party modules are used: pandas, dask, distributed
'''

import six
import yaml
import cloudpickle

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
        # TODO: this is just the cloudpickle thing again. testing for compatibility reasons
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

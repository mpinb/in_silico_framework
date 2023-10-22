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
    name = dumper_module.__name__
    prefix = 'model_data_base.IO.LoaderDumper.'
    assert name.startswith(prefix)
    return name[len(prefix):]


def get_dumper_string_by_savedir(savedir):
    import inspect
    #     with open(os.path.join(savedir, 'Loader.pickle'), 'rb') as file_:
    #         myloader = cloudpickle.load(file_)
    myloader = compatibility.pandas_unpickle_fun(
        os.path.join(savedir, 'Loader.pickle'))
    dumper = inspect.getmodule(myloader)
    return get_dumper_string_by_dumper_module(dumper)

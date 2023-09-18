from . import dask_to_categorized_msgpack
import os


Loader = dask_to_categorized_msgpack.Loader
check = dask_to_categorized_msgpack.check

def dump(obj, savedir, repartition = False, get = None, client = None):
    import os
    if not "IS_TESTING" in os.environ:
        # Module was not called from within the test suite
        raise RuntimeError('pandas-msgpack is not supported anymore in the model_data_base')
    return dask_to_categorized_msgpack.dump(obj, savedir, repartition = repartition, get = get, categorize = False, client = client)

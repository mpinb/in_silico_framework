"""
.. deprecated:: 0.2.0
   The pandas-msgpack format is set to be deprecated in the future.
   Please consider using parquet instead.

:skip-doc:
"""


from . import dask_to_categorized_msgpack
import os

Loader = dask_to_categorized_msgpack.Loader
check = dask_to_categorized_msgpack.check


def dump(obj, savedir, repartition=False, scheduler=None, client=None):
    import os
    if not "ISF_IS_TESTING" in os.environ:
        # Module was not called from within the test suite
        raise RuntimeError(
            'pandas-msgpack is not supported anymore in the data_base')
    return dask_to_categorized_msgpack.dump(
        obj,
        savedir,
        repartition=repartition,
        scheduler=scheduler,
        categorize=False,
        client=client
        )

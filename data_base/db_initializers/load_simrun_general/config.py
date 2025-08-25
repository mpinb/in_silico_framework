"""Central configuration for simrun-initializing databases.

This config section contains configuration options for :py:func:`~data_base.db_initializers.load_simrun_general.init` beyond the keyword arguments.
This typically includes configuration options you would normally not change from one database initialization to the next, but rather on a user-based long-term level.
They are configured separately here to keep the options in :py:func:`~data_base.db_initializers.load_simrun_general.init` to a manageable level, 
and to avoid bombarding the user with config options they may not be interested in.
"""
from data_base.IO.LoaderDumper import (
    # dask_to_parquet,
    dask_to_msgpack,
    dask_to_categorized_msgpack,
    pandas_to_msgpack,
    # pandas_to_parquet,
    to_cloudpickle,
)

# Optimization config
DEFAULT_DUMPER = to_cloudpickle
"""The dumper to use when no specific dumper is configured for a data type."""
OPTIMIZED_PANDAS_DUMPER = pandas_to_msgpack
"""The dumper to use for pandas dataframes."""
OPTIMIZED_DASK_DUMPER = dask_to_msgpack
"""The dumper to use for dask dataframes."""
OPTIMIZED_CATEGORIZED_DASK_DUMPER = dask_to_categorized_msgpack
"""The dumper to use for categorized dask dataframes. 
Categorized dask dataframes are dask dataframes whose columns have many repeated values.
This is used for e.g. synapse and cell activations, where the cell types are often duplicated in a column."""

# Re-optimization config
DUMPERS_TO_REOPTIMIZE = ["pandas_to_parquet", "dask_to_parquet"]
"""List[str]: List of dumper names that will be re-optimized to the current optimized dumpers 
during :py:mod:`data_base.db_initializers.load_simrun_general.reoptimize.reoptimize_db`."""

# Dendritic voltage trace config
USE_RECSITE_SHORT_NAME = True
"""(bool): Whether to rename the dendritic voltage trace recsite labels to their short ID.
Dendritic voltage traces are saved in subfolders named after their associated recsite label.
If False (default), the dendritic voltage traces subfolders are named after the explicit recsite ID names, e.g. ``ID_001_sec_073_seg_008_x_0.944_somaDist_834.2``
If True, these subfolders are instead shortened to just their ID, e.g. ``001``. This is useful for simulations where the label may vary (e.g. due to morphology scaling), but the labels still reflect the same recsites.
"""

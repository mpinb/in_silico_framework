"""Central configuration for simrun-initializing databases.
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
DUMPERS_TO_REOPTIMIZE = ["pandas_to_parquet", "dask_to_parquet"]
"""List[str]: List of dumper names that will be re-optimized to the optimized dumpers."""

# Parameterfiles config
PARAM_FILE_COPY_METHOD = "remount"
"""(str): Strategy for copying over parameterfiles. 
"remount" subtracts the common ancestor of all paramfiles and copy the resulting paths (which may still include a directory structure) onto a new directory in the database. 
"hash_rename" renames the parameterfiles to a hash of their content. Identical parameterfiles will not be duplicated this way.
"remount" is recommended if your parameterfiles are structured in a specific way. 
"hash_rename" is recommended if your parameterfiles can come from very diverse locations on disk.
"""
NEUP_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for :ref:`cell_parameters_format` files."""
NETP_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for :ref:`network_parameters_format` files."""
HOC_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for :ref:`hoc_file_format` files."""
SYN_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for :ref:`syn_file_format` files."""
CON_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for :ref:`con_file_format` files."""
RECSITES_DIR = "parameterfiles_folder"
"""(str): Target directory in the database for recsites files."""

# Dendritic voltage trace config
USE_RECSITE_SHORT_NAME = True
"""(bool): Whether to rename the dendritic voltage trace recsite labels to their short ID.
Dendritic voltage traces are saved in subfolders named after their associated recsite label.
If False (default), the dendritic voltage traces subfolders are named after the explicit recsite ID names, e.g. ``ID_001_sec_073_seg_008_x_0.944_somaDist_834.2``
If True, these subfolders are instead shortened to just their ID, e.g. ``001``. This is useful for simulations where the label may vary (e.g. due to morphology scaling), but the labels still reflect the same recsites.
"""


# TODO:
# Raise error if RENAME_DEND_RECSITE is False and there are too many different recsite ID names
# Raise error if RENAME_DEND_RECSITE is True or False, but there are a different amount of dend vt files in each simresult dir
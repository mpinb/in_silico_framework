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
DUMPERS_TO_REOPTIMIZE = [
    "pandas_to_parquet",
    "dask_to_parquet"
]  
"""List of dumpers that will be re-optimized to the optimized dumpers."""

NEUP_DIR = "parameterfiles_folder"
"""Target directory in the database for :ref:`cell_parameters_format` files."""
NETP_DIR = "parameterfiles_folder"
"""Target directory in the database for :ref:`network_parameters_format` files."""
HOC_DIR = "parameterfiles_folder"
"""Target directory in the database for :ref:`hoc_file_format` files."""
SYN_DIR = "parameterfiles_folder"
"""Target directory in the database for :ref:`syn_file_format` files."""
CON_DIR = "parameterfiles_folder"
"""Target directory in the database for :ref:`con_file_format` files."""
RECSITES_DIR = "parameterfiles_folder"
"""Target directory in the database for recsites files."""
DEND_VT_SPLIT_PER_RECSITE_ID = False
"""(bool) whether or not to split the dendritic voltage traces per rec site ID.
Set to True if you expect the dendritic voltage traces to match the somatic voltage traces in a particular directory.
Set to False if the total amount of somatic voltage traces can mismatch dendritic recordings of the same ID.
"""
PARAM_FILE_COPY_METHOD = "remount"
"""(str): Strategy for copying over parameterfiles. 
"remount" subtracts the common ancestor of all paramfiles and copy the resulting paths (which may still include a directory structure) onto a new directory in the database. 
"hash_rename" renames the parameterfiles to a hash of their content. Identical parameterfiles will not be duplicated this way.
"remount" is recommended if your parameterfiles are structured in a specific way. 
"hash_rename" is recommended if your parameterfiles can come from very diverse locations on disk.
"""
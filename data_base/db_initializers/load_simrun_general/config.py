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

NEUP_DIR = "parameterfiles_cell_folder"
"""Target directory in the database for :ref:`cell_parameters_format` files."""
NETP_DIR = "parameterfiles_network_folder"
"""Target directory in the database for :ref:`network_parameters_format` files."""
HOC_DIR = "morphology"
"""Target directory in the database for :ref:`hoc_file_format` files."""
SYN_DIR = "syn_folder"
"""Target directory in the database for :ref:`syn_file_format` files."""
CON_DIR = "con_folder"
"""Target directory in the database for :ref:`con_file_format` files."""
RECSITES_DIR = "recsites_folder"
"""Target directory in the database for recsites files."""
"""
Efficient, reproducable and flexible database with dictionary-like API. 
This package provides efficient and scalable methods to store and access simulation results at a terrabyte scale.
Each data base entry contains metadata, indicating when the data was written, and the exact version of the source code that was used at this timepoint.
A wide variety of input data and output file formats are supported (see :py:mod:`data_base.IO.LoaderDumper`), including:

- 1D and ND numpy arrays
- pandas and dask dataframes
- :py:class:`~single_cell_parser.cell.Cell` objects
- :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel` objects

Simulation results from :py:mod:`single_cell_parser` and :py:mod:`simrun` can be imported and converted to a high performance binary format using the :py:mod:`data_base.db_initializers` subpackage.

Database backends can be easily swapped by changing the import statement in :py:mod:`data_base.data_base`.

1. Future support (or deprecation) for file formats and filesystems can be easily implemented by creating a ``new_database`` subpackage containing a ``IO.LoaderDumper`` subpackage.
2. Backwards compatibility to old data is guaranteed, as the previous database system is still available and automatically inferred by :py:class:`~data_base.data_base.DataBase`

The current database system is :py:mod:`~data_base.isf_data_base`, which uses the ``JSON`` format for metadata and IO information.

Example:

    ``Loader`` contains information on how to load the data. It contains which module to use (assuming it contains a ``Loader`` class)::
    
        {"Loader": "data_base.isf_data_base.IO.LoaderDumper.dask_to_parquet"}
        
    ``metadata`` contains the time, commit hash, module versions, creation date, file format, and whether or not the data was saved with uncommitted code (``dirty``).
    If the data was created within a Jupyter session, it also contains the code history that was used to produce this data::
    
        {
            "dumper": "dask_to_parquet", 
            "time": [2025, 2, 21, 15, 51, 23, 4, 52, -1], 
            "module_list": "...", 
            "module_versions": {
                "re": "2.2.1", 
                ...
                "pygments": "2.18.0", 
                "bluepyopt": "1.9.126"
                }, 
            "history": "import Interface as I ...", 
            "hostname": "localhost", 
            "metadata_creation_time": "together_with_new_key", 
            "version": "heads/master", 
            "full-revisionid": "9fd2c2a94cdc36ee806d4625e353cd289cd7ce16", 
            "dirty": false, 
            "error": null
        }
"""
import compatibility
compatibility.init_data_base_compatibility()
from .data_base import DataBase

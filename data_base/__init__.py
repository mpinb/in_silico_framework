"""
Efficient, reproducable and flexible database whose API mimics a python dictionary. 
This package provides efficient and scalable methods to store and access simulation results at a terrabyte scale.
Each data base entry contains metadata, indicating when the data was written, and the exact version of the source code that was used at this timepoint.
A wide variety of input data and output file formats are supported (see :py:mod:`data_base.IO.LoaderDumper`), including:

- 1D and ND numpy arrays
- pandas and dask dataframes
- :py:class:`~single_cell_parser.cell.Cell` and :py:class:`simrun.reduced_model.get_kernel.ReducedLdaModel`

Simulation results from :py:mod:`single_cell_parser` and :py:mod:`simrun` can be imported and converted to a high performance binary format. 

This package's ``IO`` and ``db_initializers`` subpackages can be adapted, changing the data base system. 
Which data base system to use is decided by :py:mod:`~data_base.data_base`.
This way:

1. Future support (or deprecation) for file formats can be easily implemented by creating a new ``IO.LoaderDumper`` submodule.
2. Backwards compatibility to old data or old formats is guaranteed, as the previous database system is still available.

Available data base systems:

1. :py:mod:`~data_base.isf_data_base`
2. :py:mod:`~data_base.model_data_base` (deprecated)
"""
import compatibility
compatibility.init_data_base_compatibility()
from .data_base import DataBase

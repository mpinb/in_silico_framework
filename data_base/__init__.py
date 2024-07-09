"""
This package provides an efficient, scalable, and flexible database whose API mimics a python dictionary. 
It provides efficient and scalable methods to store and access simulation results at a terrabyte scale. 
It also generates metadata, indicating when the data was put in the database and the exact version of the in_silico_framework that was used at this timepoint. 
Simulation results from the :py:mod:`single_cell_parser` module can be imported and converted to a high performance binary format. 
Afterwards the data is accessible using the pandas data analysis library and dask.

It contains two important subpackages:

    1. :py:mod:`model_data_base`: A legacy format, only used by the Oberlaender lab at In-Silico Brain Sciences, MPINB Bonn. This should never be used by anyone else.
    2. :py:mod:`isf_data_base`: An updated data_base package, using JSON as metadata format, and the newest file formats, such as parquet.

This package has "dynamic" IO and db_initializers subpackages, meaning that these can change in the future, and will be adapted here. 
As of now, data_base.isf_data_base provides an IO subpackage, that registers itself under the name data_base.IO as well.
This way:
1. future changes to file formats can be easily implemented by creating a new IO subpackage and having it register under the name data_base.IO.
2. Only one IO subpackage is active at a time.
3. Backwards compatibility to old data or old formats is guaranteed, as the previous IO subpackages are still available.

See also:
1. :py:mod:`data_base.data_base` to see how old data formats are automatically read in.
2. :py:mod:`model_data_base` to see how the old IO subpackage is registered under the original name `model_data_base.IO` to guarantee compatibility with `pickle` formats.

All methods in ISF should never import IO from the model_data_base or isf_data_base subpackages directly, but always use the data_base.IO module, which is set here to the correct IO subpackage.
"""
import compatibility
compatibility.init_data_base_compatibility()
from .data_base import DataBase
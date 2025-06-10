# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""
Efficient, reproducible and flexible database with dictionary-like API. 
This package provides efficient and scalable methods to store and access simulation results at a terrabyte scale.
Each data base entry contains metadata, indicating when the data was written, and the exact version of the source code that was used at this timepoint.
A wide variety of input data and output file formats are supported (see :py:mod:`data_base.IO.LoaderDumper`), including:

- 1D and ND numpy arrays
- pandas and dask dataframes
- :py:class:`~single_cell_parser.cell.Cell` objects
- :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel` objects

Simulation results from :py:mod:`single_cell_parser` and :py:mod:`simrun` can be imported and converted to a high performance binary format using the :py:mod:`data_base.db_initializers` subpackage.

Example:

    ``Loader`` contains information on how to load the data. It contains which module to use (assuming it contains a ``Loader`` class)::
    
        {"Loader": "data_base.IO.LoaderDumper.dask_to_parquet"}
        
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
import os
from . import data_base_register
from config import get_default_db

DataBase = get_default_db()


def _is_legacy_model_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.

    :skip-doc:
    """
    return os.path.exists(os.path.join(path, 'sqlitedict.db'))


def _is_isf_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.isf_data_base.ISFDataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.isf_data_base.ISFDataBase`.

    :skip-doc:
    """
    return os.path.exists(os.path.join(path, 'db_state.json'))


def is_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.data_base.DataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.data_base.DataBase`.
    """
    return _is_legacy_model_data_base(path) or _is_isf_data_base(path)


def _is_sub_isf_data_base(parent_db, key):
    """
    Check if a given key is a sub-database of the parent database.
    
    Args:
        parent_db (DataBase): The parent database.
        key (str): The key to check.
    
    Returns:
        bool: True if the key is a sub-database of the parent database.

    :skip-doc:
    """
    sub_db_key_path = parent_db._convert_key_to_path(key)
    sub_db_path = os.path.join(sub_db_key_path, "db")
    return os.path.exists(sub_db_path) and is_data_base(sub_db_path)

    
def _is_sub_model_data_base(parent_mdb, key):
    """
    Check if a given key is a sub-database of the parent database.
    
    Args:
        parent_db (DataBase): The parent database.
        key (str): The key to check.
    
    Returns:
        bool: True if the key is a sub-database of the parent database.

    :skip-doc:
    """
    sub_db_key_path = parent_mdb._get_path(key)
    sub_mdb_path = os.path.join(sub_db_key_path, "mdb")
    return os.path.exists(sub_mdb_path) and is_data_base(sub_mdb_path)


def is_sub_data_base(parent_db, key):
    """
    Check if a given key is a sub-database of the parent database.
    
    Args:
        parent_db (DataBase): The parent database.
        key (str): The key to check.
    
    Returns:
        bool: True if the key is a sub-database of the parent database.
    """
    if _is_legacy_model_data_base(parent_db.basedir):
        return _is_sub_model_data_base(parent_db, key)
    elif _is_isf_data_base(parent_db.basedir):
        return _is_sub_isf_data_base(parent_db, key)
    else:
        raise ValueError("Unknown database type. Cannot determine if the key is a sub-database.")


def get_db_by_unique_id(unique_id):
    """Get a DataBase by its unique ID, as registered in the data base register.
    
    Data base registers should be located at data_base/.data_base_register.db
    
    Args:
        unique_id (str): The data base's unique identifier
        
    Returns:
        :py:class:`data_base.data_base.DataBase`: The database associated with the :paramref:`unique_id`.
    """
    db_path = data_base_register._get_db_register().registry[unique_id]
    db = ISFDataBase(db_path, nocreate=True)
    assert db.get_id() == unique_id, "The unique_id of the database {} does not match the requested unique_id {}. Check for duplicates in your data base registry.".format(db.get_id(), unique_id)
    return db
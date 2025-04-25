"""
Modular data base system.

This module infers which data base system should be used based on the content of a given path.

Newly created databases automatically use the newest data base system. Only existing data bases in older formats are opened with the old data base system.
If the path points to a database that has been created with an older database system, this module returns the corresponding database object, with associated writers, readers, and file format readers.
"""

# Available data base systems:
# - :py:mod:`~data_base.isf_data_base`: The new data base system (default).
# - :py:mod:`~data_base.model_data_base`: The old data base system.

import logging
import os

from .data_base_register import _get_db_register
from .isf_data_base.isf_data_base import ISFDataBase
from .model_data_base.model_data_base import ModelDataBase

logger = logging.getLogger('ISF').getChild(__name__)
DEFAULT_DATA_BASE = ISFDataBase

class DataBase(object):
    """Wrapper class that initializes the correct data base class
    
    As this is a wrapper class, it has no class attributes itself. Its reponsibility is to return the correct DataBase object.

    Returns:
        :py:class:`~data_base.isf_datata_base.ISFDataBase` | :py:class:`~data_base.model_data_base.ModelDataBase`: The correct database object.
    """
    def __new__(cls, basedir, readonly=False, nocreate=False):
        """
        Args:
            basedir (str): The directory where the database is located.
            readonly (bool): If True, the database is read-only.
            nocreate (bool): If True, the database is not created if it does not exist.
        """
        if _is_legacy_model_data_base(basedir):
            logger.warning('Reading a legacy-format ModelDataBase.')
            logger.warning('Defining the following methods for compatibility with ISF syntax:\n(old) -> (new)\nmdb.getitem -> mdb.get\nmdb.setitem -> mdb.set\nmdb._get_path -> mdb._convert_key_to_path ')
            
            nocreate = not os.environ.get('ISF_IS_TESTING', False) # creating old format allowed during testing
            db = ModelDataBase(basedir, readonly=readonly, nocreate=nocreate)
            db.set = db.setitem
            db.get = db.getitem
            db._convert_key_to_path = db._get_path
            
            db.create_sub_db = db.create_sub_mdb
            return db
        
        else:
            return DEFAULT_DATA_BASE(basedir, readonly=readonly, nocreate=nocreate)

def get_db_by_unique_id(unique_id):
    """Get a DataBase by its unique ID, as registered in the data base register.
    
    Data base registers should be located at data_base/.data_base_register.db
    
    Args:
        unique_id (str): The data base's unique identifier
        
    Returns:
        :py:class:`data_base.data_base.DataBase`: The database associated with the :paramref:`unique_id`.
    """
    db_path = _get_db_register().registry[unique_id]
    db = DataBase(db_path, nocreate=True)
    assert db.get_id() == unique_id, "The unique_id of the database {} does not match the requested unique_id {}. Check for duplicates in your data base registry.".format(db.get_id(), unique_id)
    return db

def _is_legacy_model_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.
    """
    return os.path.exists(os.path.join(path, 'sqlitedict.db'))

def is_isf_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.isf_data_base.ISFDataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.isf_data_base.ISFDataBase`.
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
    return _is_legacy_model_data_base(path) or is_isf_data_base(path)


def is_sub_isf_data_base(parent_db, key):
    """
    Check if a given key is a sub-database of the parent database.
    
    Args:
        parent_db (DataBase): The parent database.
        key (str): The key to check.
    
    Returns:
        bool: True if the key is a sub-database of the parent database.
    """
    sub_db_key_path = parent_db._convert_key_to_path(key)
    sub_db_path = os.path.join(sub_db_key_path, "db")
    return os.path.exists(sub_db_path) and is_data_base(sub_db_path)

    
def is_sub_model_data_base(parent_mdb, key):
    """
    Check if a given key is a sub-database of the parent database.
    
    Args:
        parent_db (DataBase): The parent database.
        key (str): The key to check.
    
    Returns:
        bool: True if the key is a sub-database of the parent database.
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
        return is_sub_model_data_base(parent_db, key)
    elif is_isf_data_base(parent_db.basedir):
        return is_sub_isf_data_base(parent_db, key)
    else:
        raise ValueError("Unknown database type. Cannot determine if the key is a sub-database.")
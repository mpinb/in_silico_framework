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
        if is_model_data_base(basedir):
            logger.warning('Reading a legacy-format ModelDataBase. nocreate is set to {}'.format(nocreate))
            logger.warning('Overwriting mdb.set and mdb.get to be compatible with ISF syntax...')
            
            nocreate = not os.environ.get('ISF_IS_TESTING', False) # creating old format allowed during testing
            db = ModelDataBase(basedir, readonly=readonly, nocreate=nocreate)
            db.set = db.setitem
            db.get = db.getitem
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

def is_model_data_base(path):
    """
    Checks if a given path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.
    
    Args:
        path (str): The path to check.
        
    Returns:
        bool: True if the path contains a :py:class:`~data_base.model_data_base.ModelDataBase`.
    """
    return os.path.exists(os.path.join(path, 'sqlitedict.db'))

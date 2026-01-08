# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Registry of databases.

The data base registry keeps a ledger linking data base IDs to data base paths.
This is particularly useful to share databases, and moving databases to other file systems.

The registry should ideally be located in an obvious place. The default registry is ``.data_base_register.db`` in the :mod:`data_base` module itself.
Newly created data_bases are automatically added to the registry. Accessing someone elses database is possible if:

1. Its location is on the same filesystem and you have the absolute path. In this case, you can simply open the path and the db will register itself to your registry.
2. You know the unique ID of the database. In this case, you can use :func:`data_base.get_db_by_unique_id`.
3. Someone else has registered the database in a registry that you have access to. In this case, you can use :func:`assimilate_remote_register`.

See also:
    :func:`~data_base.DataBase.register_this_database`
"""

from __future__ import absolute_import
import os, json
from .utils import cache
from .exceptions import DataBaseException
from config import get_db_register_path
import logging
logger = logging.getLogger("ISF").getChild(__name__)

LOCAL_DATA_BASE_REGISTER_NAME = get_db_register_path()

class DataBaseRegister():
    """Two column registry mapping data bases to their locations.

    This registry keeps track of all :class:`DataBase` ``id`` tags and their locations on disk.
    This is useful when sharing data with other people, resolving relative database paths, and moving databases to other file systems.
    This registry implements an SQLite backend to store these locations and corresponding database IDs.
        
    You can explicitly walk through a directory and add all :class:`DataBase` it encounters to the registry with :func:`DataBaseRegister.search_dbs`.
    
    Attributes:
        registry_basedir (str): The location of the db registry
        registry (:class:`~data_base.sqlite_backend.sqlite_backend.SQLiteBackend`): The registry itself as an SQLite database.
    """
    def __init__(self, registry_basedir, search_dbs="on_first_init"):
        """        
        Args:
            registry_basedir (str): The location of the db registry
            search_dbs (str|bool, optional): Whether to look for data_bases in all subfolders of the registry's directory. Defaults to "on_first_init", which only does this if the registry is newly created.
        """
        self.registry_basedir = registry_basedir
        if not os.path.exists(self.registry_basedir):
            self._first_init = True
        else:
            self._first_init = False
        self.registry = SQLBackend(self.registry_basedir)
        if search_dbs == "on_first_init" and self._first_init:
            self.search_dbs(os.path.dirname(self.registry_basedir))
        elif search_dbs == True:
            self.search_dbs(os.path.dirname(self.registry_basedir))

    def search_dbs(self, directory=None):
        """Look for :class:`DataBase` in all subfolders of the registry's directory and add them to the registry.
        
        Args:
            directory (str, optional): The directory to search in. Defaults to None, in which case the directory of the registry is searched.
        """
        for dir_ in [x[0] for x in os.walk(directory)]:
            if dir_.endswith("data_base_register.db"):
                continue
            if os.path.exists(os.path.join(dir_, "metadata.json")):
                # it is an ISFDataBase
                try:
                    with open(os.path.join(dir_, "metadata.json"), 'r') as f:
                        metadata = json.load(f)
                    self.add_db(metadata["unique_id"], dir_)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except DataBaseException:  # if there is no database
                    continue
                except Exception as e:
                    self.registry['failed', dir_] = e
            elif os.path.exists(os.path.join(dir_, "dbcore.pickle")):
                # it is a ModelDataBase
                try:
                    metadata = pandas_unpickle_fun(os.path.join(dir_, "dbcore.pickle"))
                    self.add_db(metadata["_unique_id"], dir_)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except DataBaseException:  # if there is no database
                    continue
                except Exception as e:
                    self.mdb['failed', dir_] = e
            else:
                logger.warning(
                    "Could not find a metadata.json or dbcore.pickle file in {}. Are you sure the path points to a directory containing a DataBase?".format(dir_))
            
    def add_db(self, unique_id, db_basedir):
        """Add a database to the registry.
        
        Args:
            unique_id (str): The unique ID of the database.
            db_basedir (str): The location of the database
        """
        self.registry[unique_id] = os.path.abspath(str(db_basedir))

    def keys(self):
        """Get all keys in the registry.
        
        Each key is a unique ID of a database.
        
        Returns:
            list: All keys in the registry.
        """
        return self.registry.keys()

    def __delitem__(self, key):
        """Delete a database from the registry.
        
        Args:
            key (str): The unique ID of the database to delete.
        """
        del self.registry[key]


@cache
def _get_db_register():
    """Get the database register.
    
    Returns:
        :class:`~data_base.data_base_register.DataBaseRegister`: The database register.
    """
    dbr = DataBaseRegister(LOCAL_DATA_BASE_REGISTER_NAME)
    return dbr


def register_db(unique_id, db_basedir):
    """Register a database.
    
    Adds a database to the database register.
    
    Args:
        unique_id (str): The unique ID of the database.
        db_basedir (str): The location of the database.
    """
    dbr = _get_db_register()
    dbr.add_db(unique_id, db_basedir)

def deregister_db(unique_id):
    """Deregister a database.
    
    Removes this :class:`DataBase` from the registry.
    
    Args:
        unique_id (str): The unique ID of the database.
    """
    dbr = _get_db_register()
    del dbr.registry[unique_id]


def assimilate_remote_register(remote_path, local_path=None):
    """Assimilate a remote register.
    
    This method adds all databases from a remote register to the local register of the user.
    
    Args:
        remote_path (str): The path to the remote register.
        local_path (str, optional): The path to the local register. Defaults to None, in which case the default local register is used:
            ``.data_base_register.db`` in the same directory as this file.
    """
    if local_path is None:
        local_path = LOCAL_DATA_BASE_REGISTER_NAME
    from tqdm import tqdm
    dbr_remote = DataBaseRegister(remote_path)
    dbr_local = DataBaseRegister(local_path)
    # get all remote model ids
    whole_registry = {k: dbr_remote.registry[k] for k in dbr_remote.registry.keys()}
    logger.info("Filtering remote registry for non-existent paths...")
    whole_registry_filtered = {
        k: v for k, v in tqdm(whole_registry.items(), desc="Filtering remote registry...") if os.path.exists(v)
    }
    for k in tqdm(whole_registry_filtered.keys(), desc="Assimilating remote register"):
        dbr_local.registry[k] = whole_registry_filtered[k]

from .sqlite_backend.sqlite_backend import SQLiteBackend as SQLBackend
from compatibility import pandas_unpickle_fun

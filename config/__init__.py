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
"""Configuration for ISF

This package provides ISF-wide configuration settings, such as `dask` memory overflow, file locking server configuration, logging configuration, cell types etc.
In general, these settings may change when switching hardware or animal species, but are unlikely to be varied otherwise.
"""

import os, json, importlib

def _read_db_settings():
    """Read the database settings from the JSON file in the config directory.
    
    Returns:
        dict: The database settings.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'db_settings.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def isf_is_using_mdb():
    """Check if ISF is configured to use :py:mod:`data_base.model_data_base`
    
    The use of :py:mod:`data_base.model_data_base` is strongly discouraged, as the saved data is not robust under API changes.
    
    There are two reasons to use it anyways:
    
    - Reading in existing data that has already been saved with this database system (i.e. the IBS Oberlaender Lab), in which case one must also `from ibs_projects import compatibility`
    - Testing purposes
    
    Returns:
        bool: whether or not ISF needs to use :py:mod:`data_base.model_data_base` as a database backend.
    """
    return os.getenv("ISF_USE_MDB", 'False').lower() in ('true', '1', 't')

    
def get_default_db():
    """Get the default database settings.

    Returns:
        dict: The default database settings.
    """
    db_settings = _read_db_settings()
    db_fqn = db_settings.get('DEFAULT_DATA_BASE')['FQN']
    module = '.'.join(db_fqn.rsplit('.')[:-1])
    class_name = db_fqn.rsplit('.')[-1]
    db_class = getattr(importlib.import_module(module), class_name)
    return db_class

def get_db_register_path():
    """Get the path to the database register.

    Returns:
        str: The path to the database register.
    """
    db_settings = _read_db_settings()
    dbr_path = db_settings['DATA_BASE_REGISTER_PATH']['filepath']
    return os.path.abspath(dbr_path)

def get_default_db_dumper():
    """Get the default database dumper.

    Returns:
        str: The default database dumper.
    """
    db_settings = _read_db_settings()
    dumper_fqn = db_settings.get('DEFAULT_DUMPER')['FQN']
    dumper = importlib.import_module(dumper_fqn)
    return dumper
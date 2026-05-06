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
"""Configuration for ISF

This package provides ISF-wide configuration settings, such as `dask` memory overflow, file locking server configuration, logging configuration, cell types etc.
In general, these settings may change when switching hardware or animal species, but are unlikely to be varied otherwise.
"""

import os, json, importlib

AVAILABLE_SYNAPSE_MAPPING_METHODS = (
    "udvary2022",
    # no other methods have been implemented yet
)
"""Which methods ISF currently implements to infer synapse locations onto a poastsynaptic neuron morphology."""


def _read_db_settings():
    """Read the database settings from the JSON file in the config directory.
    
    Returns:
        dict: The database settings.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'db_settings.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def isf_is_using_legacy_mdb():
    """Check if ISF is configured to use :mod:`model_data_base`
    
    The use of :mod:`model_data_base` is strongly discouraged, as the saved data is not robust under API changes.
    
    There are two reasons to use it anyways:
    
    - Reading in existing data that has already been saved with this database system (i.e. the IBS Oberlaender Lab), in which case one must also `from ibs_projects import compatibility`
    - Testing purposes
    
    Returns:
        bool: whether or not ISF needs to use :mod:`model_data_base` as a database backend.
    """
    return os.getenv("ISF_USE_MDB", 'False').lower() in ('true', '1', 't')

    
def get_default_db():
    """Get the database class to be used by default throughout ISF.

    Returns:
        dict: The default database settings.
    """
    if isf_is_using_legacy_mdb():
        from model_data_base import ModelDataBase
        return ModelDataBase
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
    project_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dbr_path = db_settings['DATA_BASE_REGISTER_PATH']['filepath']
    dbr_path = os.path.join(project_src_dir, dbr_path)
    assert os.path.exists(os.path.dirname(dbr_path)), f"Parent directory of database register ({dbr_path}) does not exist. Please check your configuration."
    return dbr_path

def get_default_db_dumper():
    """Get the default database dumper.

    Returns:
        str: The default database dumper.
    """
    db_settings = _read_db_settings()
    dumper_basename = db_settings.get('DEFAULT_DUMPER')['base_name']
    dumper_fqn = "data_base.IO.LoaderDumper." + dumper_basename
    try:
        dumper = importlib.import_module(dumper_fqn)
    except ImportError as e:
        raise ImportError(f"Could not import dumper '{dumper_fqn}'. Make sure it is installed and available in the Python path.") from e
    return dumper


def get_meta_file_format():
    """Check which file format to use for saving data_base meta objects.

    This is either ``"msgpack"`` or ``"json"``.
    The actual format is defined in the database settings. This functions simply reads it to check which one should be used.

    Returns:
        str: The specified file format for meta objects.
    """
    allowed_formats = ("msgpack", "json")
    db_settings = _read_db_settings()
    meta_file_format = db_settings.get("OBJECT_META_FORMAT")['file_format']
    assert meta_file_format in allowed_formats, "Format for saving meta must be one of {}".format(allowed_formats)
    return meta_file_format

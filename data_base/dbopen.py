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
"""Open files directly in a database.

This module provides funtcionality to open files in a database directly.
This is generally not recommended, as the content of databases is usually written in a specific format,
which is automatically inferred by the database.

However, for development and testing purposes, it may be of use to explicitly open these files.
"""

from __future__ import absolute_import
import os
from data_base.data_base import DataBase, get_db_by_unique_id, is_data_base
from data_base.exceptions import DataBaseException
import cloudpickle
from six.moves import cPickle
import logging
logger = logging.getLogger("ISF").getChild(__name__)


def cache(function):
    """Cache the result of a function.
    
    Args:
        function (callable): The function to cache.
        
    Returns:
        callable: The cached function.
        
    Example:
    
        >>> cache(my_function)(*args, **kwargs)
    """
    import hashlib
    memo = {}
    def get_key(*args, **kwargs):
        try:
            hash = hashlib.md5(cPickle.dumps([args, kwargs])).hexdigest()
        except (TypeError, AttributeError):
            hash = hashlib.md5(cloudpickle.dumps([args, kwargs])).hexdigest()
        return hash
    
    def wrapper(*args, **kwargs):
        key = get_key(*args, **kwargs)
        if key in memo:
            return memo[key]
        else:
            rv = function(*args, **kwargs)
            memo[key] = rv
            return rv
    return wrapper


def resolve_reldb_path(path, db_basedir=None):
    """Resolve a relative database path
    
    Relative database paths are of the form ``reldb://...``.
    They are used for references to files that are known to be within the same database.
    Figuring out the absolute file location is then a matter of finding the shared parent database path.
    
    This method takes a relative path and a database, and returns the absolute path.
    
    Attention:
        Relative database paths always refer to the first parent database in the path.
        If the database is a sub-database, the path will be relative to the sub-database, not
        the parent database.
    Args:
        path (str): The relative path of the form ``reldb://...``.
        db (:py:class:`~data_base.data_base.DataBase`): The database.
        
    Returns:
        str: The resolved path.
    """
    if not path.startswith('reldb://'):
        return path
    
    assert db_basedir is not None, "If the path is in reldb:// format, a database object must be provided in order to resolve it."

    abs_path = os.path.join(db_basedir, *path.split('/')[2:])
    assert os.path.exists(abs_path), "The resolved path {} does not exist.".format(abs_path)
    return abs_path


def create_reldb_path(path):
    """Create a relative database path
    
    Relative database paths are of the form ``reldb://...``.
    They are used for references to files that are known to be within the same database.
    Figuring out the absolute file location is then a matter of finding the shared parent database path.
    
    This method takes an absolute path and a database, and returns the relative path.

    Attention:
        Relative database paths always refer to the first parent database in the path.
        If the database is a sub-database, the path will be relative to the sub-database, not
        the parent database.
    
    Args:
        path (str): The absolute path.
        db (:py:class:`~data_base.data_base.DataBase`): The database.
        
    Returns:
        str: The relative path of the form ``reldb://...``.
    """
    if path.startswith('reldb://'):
        logger.debug('Path {} already in reldb:// format'.format(path))
        return path
    
    parent_db_path = path
    while not is_data_base(parent_db_path):
        parent_db_path = os.path.dirname(parent_db_path)
        if parent_db_path == '/':
            raise DataBaseException(
                "The path {} does not seem to be within a DataBase!".format(path))

    relpath = os.path.relpath(path, parent_db_path)
    return os.path.join('reldb://', relpath)
    
    
def resolve_modular_db_path(path):
    """Resolve the path of a database.

    Modular database paths are filepaths of the form ``mdb://<unique_id>/...``.
    These are used to be independent of the location of the database on the hard drive.
    This has been useful for migrating data between different file systems.
    These relative paths are registered to an actual path in the data base registry upon creation.
    Migrating databases then consists of simply re-registering the database to the new location.
    
    This method checks the current registry for the absolute path of the database on the current filesystem.
    
    Args:
        path (str): The path to resolve.
        
    Returns:
        str: The resolved path.
    """
    if '/gpfs01/bethge/home/regger/data/' in path:
        logger.debug('found CIN cluster prefix')
        logger.debug('old path', path)
        path = path.replace(
            '/gpfs01/bethge/home/regger/data/',
            '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/')  # TODO: make this more general
        logger.debug('new path', path)
    
    if not path.startswith('mdb://'):
        return path

    path_splitted = path.split('//')[1].split('/')

    try:
        db = get_db_by_unique_id(path_splitted[0])
    except KeyError:
        raise IOError(
            "Trying to load {}. Did not find a DataBase with id {}".format(
                path, path_splitted[0]))
    try:
        managed_folder = db[path_splitted[1]]
    except KeyError:
        raise KeyError("Trying to load {}. The Database has been found at {}. ".format(path, db._basedir) + \
        "However, this Database does not contain the key {}".format(path_splitted[1]))
    return os.path.join(managed_folder, *path_splitted[2:])

@cache
def create_modular_db_path(path):
    """Create a database path from a given path.
    
    Modular database paths are of the form ``mdb://<unique_id>/...``.
    The point of these paths is to be independent of their location on the hard drive,
    and can thus be transferred to other file systems, and resolved afterwards using the database registry.
    
    Args:
        path (str): The path to be converted to a database path.
        
    Returns:
        str: The database path.
    """
    db_path = path
    if path.startswith('mdb://'):
        logger.debug('Path {} already in mdb:// format'.format(path))
        return path
    
    # Find mother database
    while True:
        if (os.path.isdir(db_path)) and (
            'dbcore.pickle' in os.listdir(db_path) or 'db_state.json' in os.listdir(db_path) or 'dbcore.pickle' in os.listdir(db_path)):
            break
        else:
            db_path = os.path.dirname(db_path)
        if db_path == '/':
            raise DataBaseException(
                "The path {} does not seem to be within a DataBase!".
                format(path))
    
    # Instantiate mother database
    db = DataBase(db_path, nocreate=True, readonly=True)

    #print path
    path_minus_db_basedir = os.path.relpath(path, db._basedir)

    # check to which key the given path belongs
    key = None
    for k in list(db.keys()):
        if k == path_minus_db_basedir.split('/')[0]:
            key = k
            break

    if key is None:
        raise KeyError(
            "Found a Database at {}. However, there is no key pointing to the subfolder {} in it.".format(
                db._basedir, path_minus_db_basedir.split('/')[0]))
    return os.path.join(
        'mdb://', 
        db.get_id(), 
        key,
        os.path.relpath(path, db[key]))


def resolve_db_path(path, db_basedir=None):
    """Resolve modular or relative database paths
    
    Args:
        path (str): The path to resolve.
        
    Returns:
        str: The resolved path.
    """
    if path.startswith('reldb://'):
        return resolve_reldb_path(path, db_basedir=db_basedir)
    elif path.startswith('mdb://'):
        return resolve_modular_db_path(path)
    else:
        return path


def resolve_neup_reldb_paths(neup, db_basedir):
    """Convert all relative database paths in a :ref:`cell_parameters_format` file to absolute paths.

    Args:
        neup (dict): Dictionary containing the neuron model parameters.
        db_basedir (str): Path to the database directory.

    Returns:
        :py:class:`~single_cell_parser.parameters.ParameterSet`: The modified neuron parameter set, with absolute paths.
    """
    neup["neuron"]["filename"] = resolve_reldb_path(
        neup["neuron"]["filename"], db_basedir
    )
    for i, recsite_fn in enumerate(neup["sim"]["recordingSites"]):
        neup["sim"]["recordingSites"][i] = resolve_reldb_path(recsite_fn, db_basedir)
    return neup


def resolve_netp_reldb_paths(netp, db_basedir):
    """Convert all relative database paths in a :ref:`network_parameters_format` file to absolute paths.

    Args:
        netp (dict): Dictionary containing the network model parameters.
        db_basedir (str): Path to the database directory.

    Returns:
        :py:class:`~single_cell_parser.parameters.ParameterSet`: The modified network parameter set, with absolute paths.
    """
    for cell_type in list(netp["network"].keys()):
        if not "synapses" in netp["network"][cell_type]:
            continue
        netp["network"][cell_type]["synapses"]["connectionFile"] = resolve_reldb_path(
            netp["network"][cell_type]["synapses"]["connectionFile"], db_basedir
        )
        netp["network"][cell_type]["synapses"]["distributionFile"] = resolve_reldb_path(
            netp["network"][cell_type]["synapses"]["distributionFile"], db_basedir
        )
    return netp


class dbopen:
    '''Context manager to open files in databases
    
    This explicitly calls Python's ``open()`` method on a file.
    This is generally not recommended, as the content of databases
    is usually written in a specific format, that is automatically inferred
    by the database.
    
    However, for development and testing purposes, it may be of use to explicitly open these files.
    
    Example:
    
        >>> with dbopen('db://my_db/my_key') as f:
        ...     print(f.read())
        # dumps the raw file content - not recommended for e.g. binary formats
        
    Attributes:
        path (str): The path to the file.
        mode (str): The mode in which the file is opened.
        exit_hooks (list): A list of functions to be called when the context manager is exited. Used to close ``.tar`` files
    '''
    def __init__(self, path, mode='r'):
        """
        Args:
            path (str): The path to the file.
            mode (str): The mode in which the file is opened. Default: 'r'
        """
        self.path = path
        self.mode = mode
        self.exit_hooks = []

    def __enter__(self, db=None):
        self.path = resolve_db_path(self.path, db_basedir=db)
        if '.tar/' in self.path:
            t = taropen(self.path, self.mode)
            self.f = t.open()
            self.exit_hooks.append(t.close)
        else:
            self.f = open(self.path, self.mode)
        return self.f

    def __exit__(self, *args, **kwargs):
        self.f.close()
        for h in self.exit_hooks:
            h()


class taropen:
    '''Context manager to open nested ``.tar`` hierarchies
    
    Args:
        path (str): The path to the file.
        mode (str): The mode in which the file is opened. Must be either ``'r'`` or ``'b'``. Default: ``'r'``
        
    Attributes:
        path (str): The path to the ``.tar`` file.
        mode (str): The mode in which the file is opened.
        tar_levels (list): A list of indices denoting the ``.tar`` hierarchy.
        open_files (list): A list of open files.
        
        
    Attention:
        This seems to be not fully implemented: the ``open()`` method has undefined attributes.
    
    :skip-doc:
    '''

    def __init__(self, path, mode='r'):
        if not mode in ['r', 'b']:
            raise NotImplementedError()
        self.path = path
        self.mode = mode
        psplit = path.split('/')
        self.tar_levels = [
            lv for lv, x in enumerate(psplit) if x.endswith('.tar')
        ]
        self.open_files = []

    def __enter__(self):
        # self.path = resolve_db_path(self.path)
        return self.open()

    def __exit__(self, *args, **kwargs):
        self.close()

    def open(self):
        open_files = self.open_files
        current_TarFS = None
        current_level = 0
        for lv, l in enumerate(tar_levels):
            path_ = '/'.join(psplit[current_level:l + 1])
            if current_TarFS is None:
                tar_fs = TarFS(path_)
                open_files.append(tar_fs)
                current_TarFS = tar_fs
            else:
                tar_fs = TarFS(current_TarFS.openbin(path_, 'r'))
                open_files.append(tar_fs)
                current_TarFS = tar_fs
            current_level = l + 1
        # location of file in last tar archive
        path_ = '/'.join(psplit[current_level:])
        if self.mode == 'r':
            final_file = current_TarFS.open(path_)
        elif self.mode == 'b':
            final_file = current_TarFS.openbin(path_)
        open_files.append(final_file)
        self.f = final_file
        return self.f

    def close(self):
        for f in reversed(open_files):
            f.close()
        self.open_files = []

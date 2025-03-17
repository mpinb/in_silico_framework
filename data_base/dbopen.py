"""Open files directly in a database.

This module provides funtcionality to open files in a database directly.
This is generally not recommended, as the content of databases is usually written in a specific format,
which is automatically inferred by the database.

However, for development and testing purposes, it may be of use to explicitly open these files.
"""

from __future__ import absolute_import
import os
from data_base.data_base import DataBase, get_db_by_unique_id, _is_legacy_model_data_base
from data_base.exceptions import DataBaseException
import cloudpickle
from six.moves import cPickle

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



def resolve_db_path(path):
    """Resolve the path of a database.
    
    Resolve a path of the form ``db://<unique_id>/<managed_folder>/<file>`` to
    the absolute path of the file on the current filesystem.
    
    Args:
        path (str): The path to resolve.
        
    Returns:
        str: The resolved path.
    """
    if '/gpfs01/bethge/home/regger/data/' in path:
        print('found CIN cluster prefix')
        print('old path', path)
        path = path.replace(
            '/gpfs01/bethge/home/regger/data/',
            '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/')  # TODO: make this more general
        print('new path', path)
    if not path.startswith('mdb://') and not path.startswith("db://"):
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
def create_db_path(path):
    """Create a database path from a given path.
    
    Database paths are of the form ``db://<unique_id>/<key>/<subfolder>``.
    The point of these paths is to be independent of their location on the hard drive,
    and can thus be transferred to other file systems, and resolved afterwards using the database registry.
    
    Args:
        path (str): The path to be converted to a database path.
        
    Returns:
        str: The database path.
    """
    db_path = path
    if path.startswith('mdb://'):
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
        'db://', 
        db.get_id(), 
        key,
        os.path.relpath(path, db[key]))


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

    def __enter__(self):
        self.path = resolve_db_path(self.path)
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

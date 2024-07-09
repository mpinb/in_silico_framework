from __future__ import absolute_import
import os
from data_base.data_base import DataBase, get_db_by_unique_id
from data_base.exceptions import DataBaseException
import cloudpickle
from six.moves import cPickle

def cache(function):
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


def resolve_mdb_path(path):
    # This has the purpose to map projects, that robert has run on the CIN cluster, to local paths
    if '/gpfs01/bethge/home/regger/data/' in path:
        print('found CIN cluster prefix')
        print('old path', path)
        path = path.replace('/gpfs01/bethge/home/regger/data/',
                            '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/')
        print('new path', path)
    if not path.startswith('db://'):
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
def create_mdb_path(path):
    db_path = path
    if path.startswith('db://'):
        return path
    while True:
        if (os.path.isdir(db_path)) and (
            'dbcore.pickle' in os.listdir(db_path) or 'db_state.json' in os.listdir(db_path)):
            break
        else:
            db_path = os.path.dirname(db_path)
        if db_path == '/':
            raise DataBaseException(
                "The path {} does not seem to be within a DataBase!".
                format(path))
    
    db = DataBase(db_path, nocreate=True)

    #print path
    path_minus_db_basedir = os.path.relpath(path, db._basedir)

    key = None
    for k in list(db.keys()):
        v = db._sql_backend[k] 
        try:
            if v.relpath == '':  #this means, we have a RegisteredFolder class
                key = k
                break
            if v.relpath == path_minus_db_basedir.split('/')[0]:
                key = k
                break
        except AttributeError:
            pass

    if key is None:
        raise KeyError("Found a Database at {}. ".format(db._basedir)+\
                       "However, there is no key pointing to the subfolder {} in it."\
                       .format(path_minus_db_basedir.split('/')[0]))
    return os.path.join('db://', db.get_id(), key,
                        os.path.relpath(path, db[key]))


class mdbopen:

    def __init__(self, path, mode='r'):
        self.path = path
        self.mode = mode
        self.exit_hooks = []

    def __enter__(self):
        self.path = resolve_mdb_path(self.path)
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
    '''context manager to open nested tar hierarchies'''

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

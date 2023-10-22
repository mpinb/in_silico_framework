from __future__ import absolute_import
import os
from .model_data_base import ModelDataBase, MdbException
from .model_data_base_register import get_mdb_by_unique_id
from .utils import cache


def resolve_mdb_path(path):
    # This has the purpose to map projects, that robert has run on the CIN cluster, to local paths
    if '/gpfs01/bethge/home/regger/data/' in path:
        print('found CIN cluster prefix')
        print('old path', path)
        path = path.replace('/gpfs01/bethge/home/regger/data/',
                            '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/')
        print('new path', path)
    if not path.startswith('mdb://'):
        return path

    path_splitted = path.split('//')[1].split('/')

    try:
        mdb = get_mdb_by_unique_id(path_splitted[0])
    except KeyError:
        raise IOError(
            "Trying to load {}. Did not find a ModelDataBase with id {}".format(
                path, path_splitted[0]))
    try:
        managed_folder = mdb[path_splitted[1]]
    except KeyError:
        raise KeyError("Trying to load {}. The Database has been found at {}. ".format(path, mdb.basedir) + \
        "However, this Database does not contain the key {}".format(path_splitted[1]))
    return os.path.join(managed_folder, *path_splitted[2:])


# def resolve_mdb_path(mdb, path):
#     path_splitted = path.split('::')
#     if not mdb.get_id() == path_splitted[0]:
#         try:
#             mdb = get_mdb_by_unique_id(mdb, path_splitted[0])
#         except KeyError:
#             raise IOError("Trying to load {}. Did not find a ModelDataBase with id {}".format(path, path_splitted[0]))
#     try:
#         managed_folder = mdb[path_splitted[1]]
#     except KeyError:
#         raise KeyError("Trying to load {}. The Database has been found at {}. ".format(path, mdb.basedir) + \
#         "However, this Database does not contain the key {}".format(path_splitted[1]))
#     return os.path.join(managed_folder,path_splitted[2])


@cache
def create_mdb_path(path):
    mdb_path = path
    if path.startswith('mdb://'):
        return path
    while True:
        if (os.path.isdir(mdb_path)) and ('dbcore.pickle'
                                          in os.listdir(mdb_path)):
            break
        else:
            mdb_path = os.path.dirname(mdb_path)
        if mdb_path == '/':
            raise MdbException(
                "The path {} does not seem to be within a ModelDatabase!".
                format(path))
    mdb = ModelDataBase(mdb_path, nocreate=True)

    #print path
    path_minus_mdb_basedir = os.path.relpath(path, mdb.basedir)

    key = None
    for k in list(mdb.keys()):
        v = mdb._sql_backend[k]
        try:
            if v.relpath == '':  #this means, we have a RegisteredFolder class
                key = k
                break
            if v.relpath == path_minus_mdb_basedir.split('/')[0]:
                key = k
                break
        except AttributeError:
            pass

    if key is None:
        raise KeyError("Found a Database at {}. ".format(mdb.basedir)+\
                       "However, there is no key pointing to the subfolder {} in it."\
                       .format(path_minus_mdb_basedir.split('/')[0]))
    return os.path.join('mdb://', mdb.get_id(), key,
                        os.path.relpath(path, mdb[key]))


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
        # self.path = resolve_mdb_path(self.path)
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

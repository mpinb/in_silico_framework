from __future__ import absolute_import
import os
from .sqlite_backend.sqlite_backend import SQLiteBackend as SQLBackend
from .utils import cache
from .settings import model_data_base_register_path

_foldername = '.model_data_base_register.db'


class ModelDataBaseRegister():

    def __init__(self, basedir, search_mdbs="on_first_init"):
        if not basedir.endswith(_foldername):
            basedir = os.path.join(basedir, _foldername)
        assert basedir.endswith(_foldername)
        self.basedir = basedir
        if not os.path.exists(self.basedir):
            self._first_init = True
        else:
            self._first_init = False
        self.mdb = SQLBackend(self.basedir)
        if search_mdbs == "on_first_init" and self._first_init:
            self.search_mdbs(os.path.dirname(self.basedir))
        elif search_mdbs == True:
            self.search_mdbs(os.path.dirname(self.basedir))

    def search_mdbs(self, directory=None):
        for dir_ in [x[0] for x in os.walk(directory)]:
            if dir_.endswith(_foldername):
                continue
            try:
                mdb = ModelDataBase(dir_, readonly=True)
                self.add_mdb(mdb)
            except (KeyboardInterrupt, SystemExit):
                raise
            except MdbException:  # if there is no database
                continue
            except Exception as e:
                self.mdb['failed', dir_] = e

        #print self.mdb.keys()

    def add_mdb(self, mdb):
        self.mdb[mdb._unique_id] = os.path.abspath(mdb.basedir)


@cache
def _get_mdb_register():

    mdbr = ModelDataBaseRegister(model_data_base_register_path)
    return mdbr


#def _set_mdb_register(dir_):
#    global mdbr
#    mdbr = ModelDataBaseRegister(dir_)

#     dir_ = os.path.abspath(dir_)
#     while True:
#         path = os.path.join(dir_, _foldername)
#         #print path
#         if os.path.exists(path):
#             return ModelDataBaseRegister(path)
#         dir_ = os.path.dirname(dir_)
#         if dir_ == '/':
#             raise MdbException("Did not find a ModelDataBaseRegister.")


def register_mdb(mdb):
    mdbr = _get_mdb_register()
    mdbr.add_mdb(mdb)


# def get_mdb_by_unique_id(parentdir_or_mdb, unique_id):
#     if isinstance(parentdir_or_mdb, ModelDataBase):
#         parentdir_or_mdb = parentdir_or_mdb.basedir
#     mdbr = _get_mdb_register(parentdir_or_mdb)
#     return ModelDataBase(mdbr.mdb[unique_id])


def get_mdb_by_unique_id(unique_id):
    mdb_path = _get_mdb_register().mdb[unique_id]
    mdb = ModelDataBase(mdb_path, nocreate=True)
    assert mdb.get_id() == unique_id
    return mdb


def assimilate_remote_register(remote_path, local_path=_foldername):
    mdbr_remote = ModelDataBaseRegister(remote_path)
    mdbr_local = ModelDataBaseRegister(local_path)
    # get all remote model ids
    whole_registry = {k: mdbr_remote.mdb[k] for k in mdbr_remote.mdb.keys()}
    whole_registry_filtered = {
        k: v for k, v in whole_registry.items() if os.path.exists(v)
    }
    for k in whole_registry_filtered.keys():
        mdbr_local.mdb[k] = whole_registry_filtered[k]


from .model_data_base import ModelDataBase, MdbException

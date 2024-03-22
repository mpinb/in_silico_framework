from __future__ import absolute_import
import os, json
from .sqlite_backend.sqlite_backend import SQLiteBackend as SQLBackend
from .utils import cache
from .exceptions import DataBaseException
from .settings import data_base_register_path
from compatibility import pandas_unpickle_fun

_foldername = '.data_base_register.db'

class DataBaseRegister():
    def __init__(self, registry_basedir, search_dbs="on_first_init"):
        """Class for the data_base registry. This registry keeps track of all data_bases.
        The registry should ideally be located in an obvious place, e.g. the data_base module itself.
        Newly created data_bases are automatically added to the registry.
        Accessing someone elses database is possible if:
        1. Its location is on the same filesystem and you have the absolute path. In this case, you can simply open the path and the db will register itself to your registry.
        2. You know the unique ID of the database. In this case, you can use :func data_base.get_db_by_unique_id:.
        3. Someone else has registered the database in a registry that you have access to. In this case, you can use :func data_base_register.assimilate_remote_register:.

        You can explicitly walk through a directory and add all data_bases to the registry with :func DataBaseRegister.search_dbs:.

        Args:
            registry_basedir (str): The location of the db registry
            search_dbs (str|bool, optional): Whether to look for data_bases in all subfolders of the registry's directory. Defaults to "on_first_init", which only does this if the registry is newly created.
        """
        if not registry_basedir.endswith(_foldername):
            registry_basedir = os.path.join(registry_basedir, _foldername)
        assert registry_basedir.endswith(_foldername)
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
        for dir_ in [x[0] for x in os.walk(directory)]:
            if dir_.endswith(_foldername):
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
                raise DataBaseException(
                    "Could not find a metadata.json or dbcore.pickle file in {}. \
                    Are you sure the path points to a ModelDataBase or ISFDataBase?".format(dir_))
            

    def add_db(self, unique_id, db_basedir):
        self.registry[unique_id] = os.path.abspath(db_basedir)

    def keys(self):
        return self.registry.keys()

    def __delitem__(self, key):
        del self.registry[key]


@cache
def _get_db_register():
    dbr = DataBaseRegister(data_base_register_path)
    return dbr


def register_db(unique_id, db_basedir):
    dbr = _get_db_register()
    dbr.add_db(unique_id, db_basedir)

def deregister_db(unique_id):
    dbr = _get_db_register()
    del dbr.registry[unique_id]


def assimilate_remote_register(remote_path, local_path=_foldername):
    dbr_remote = DataBaseRegister(remote_path)
    dbr_local = DataBaseRegister(local_path)
    # get all remote model ids
    whole_registry = {k: dbr_remote.registry[k] for k in dbr_remote.registry.keys()}
    whole_registry_filtered = {
        k: v for k, v in whole_registry.items() if os.path.exists(v)
    }
    for k in whole_registry_filtered.keys():
        dbr_local.registry[k] = whole_registry_filtered[k]
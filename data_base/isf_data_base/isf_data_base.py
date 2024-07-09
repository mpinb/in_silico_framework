"""
Created October 2023

@authors: Arco Bast, Bjorge Meulemeester
"""

import os, tempfile, string, json, threading, random, shutil, inspect, datetime, importlib, logging, errno, six
from pathlib import Path
from data_base import _module_versions, data_base_register
import data_base.exceptions as db_exceptions
from data_base.utils import colorize
VC = _module_versions.version_cached

logger = logging.getLogger("ISF").getChild(__name__)
class LoaderWrapper:
    '''This is a pointer to data, which is stored elsewhere.
    
    It is used by ModelDataBase, if data is stored in a subfolder of the 
    data_base.basedir folder. It is not used, if the data is stored directly
    in the sqlite database.
    
    The process of storing data in a subfolder is as follows, errno:
    1. The subfolder is generated using the mkdtemp method
    2. the respective dumper puts its data there
    3. the dumper also saves a Loader.pickle file there. This contains an object
       with a get method (call it to restore the data) and everything else
       necessary to recover the data
    4. A LoaderWrapper object pointing to the datafolder with a relative
        path (to allow moving of the database) is saved under the respective key
        in the data_base
        
    The process of loading in the data is as follows:
    1. the user request it: db['somekey']
    2. the LoaderWrapper object is loaded from the backend sql database
    3. the Loader.pickle file in the respective folder is loaded
    4. the get-methdod of the unpickled object is called with the
        absolute path to the folder.
    5. the returned object is returned to the user
    '''
    def __init__(self, relpath):
        self.relpath = relpath

class MetadataAccessor:
    """
    Access the metadata of some key
    It does not have a set method, as the metadata is set automatically when a key is set.
    Upon accidental metadata removal, the DataBase will try to estimate the metadata itself using :meth:DataBase._update_metadata_if_necessary.
    """
    def __init__(self, db):
        self.db = db
        
    def __getitem__(self, key):
        key = self.db._convert_key_to_path(key)
        if not Path.exists(key/'metadata.json'):
            logger.warning("No metadata found for key {}".format(key.name))
            return {
                'dumper': "unknown",
                'time': "unknown",
                'metadata_creation_time': 'post_hoc',
                'version': "unknown",
            }
        with open(str(key/'metadata.json')) as f:
            return json.load(f)

    def keys(self):
        return [ k for k in self.db.keys() if Path.exists(self.db._basedir/k/"Loader.[json][pickle]") ]
        
def _check_working_dir_clean_for_build(working_dir):
    '''Backend method that checks, wether working_dir is suitable
    to build a new database there'''
    if Path.exists(working_dir):
        try:
            if not os.listdir(str(working_dir)):
                return
            else:
                raise OSError()
        except OSError:
            raise db_exceptions.DataBaseException("Can't build database: " \
                               + "The specified working_dir is either not empty " \
                               + "or write permission is missing. The specified path is %s" % working_dir)
    else:
        try: 
            os.makedirs(str(working_dir))
            return
        except OSError:
            raise db_exceptions.DataBaseException("Can't build database: " \
                               + "Cannot create the directories specified in %s" % working_dir)
            
    self.metadata = MetadataAccessor(self)

def make_all_str(dict_):
    out = {}
    for k,v in dict_.items():
        k = str(k)
        if isinstance(v, dict):
            out[k] = make_all_str(v)
        elif isinstance(v, str):
            out[k] = v
        else:
            out[k] = str(v)
    return out

def get_dumper_from_folder(folder, return_ = 'module'):
    """Given a folder (i.e. key), return the dumper that was used to save the data in that folder/key.

    Args:
        folder (str): The folder in which the data is stored.
        return_ (str, optional): Whether to return the dumper as a string or the actual module. Defaults to 'module'.

    Returns:
        str | module: The dumper that was used to save the data in that folder/key.
    """
    with open(str(Path(folder)/"metadata.json")) as f:
        dumper_string = json.load(f)['dumper']
    if return_ == 'string':
        return dumper_string
    elif return_ == 'module':
        return importlib.import_module("data_base.IO.LoaderDumper.{}".format(dumper_string))

class ISFDataBase:
    def __init__(self, basedir, readonly = False, nocreate = False, suppress_errors=False):
        '''
        Class responsible for robustly storing and retrieving information.
        It is meant to be used as an interface to simulation results. 
        If the dask backends are used to save the data, it will be out of memory, 
        allowing larger than memory calculations.
        
        Saved elements can be accessed using dictionary syntax:
        
        Example::

            my_reloaded_element = db['my_new_element']
        
        All saved elements are stored in the ``basedir`` along with metadata 
        and a Loader.json object. The Loader.json object contains which 
        module should be used to load the data with, along with all the necessary 
        information to initialize the Loader. This is done because some data 
        loaders need additional arguments
        
        All saved elements have associated metadata:
        - 'dumper': Which data dumper was used to save this result. 
            It's corresponding Loader can always be found in the same file. 
            See :mod:data_base.data_base.IO.LoaderDumper for all dumpers and loaders.
        - 'time': Time at which this results was saved.
        - 'conda_list': A fill list of all modules installed in the conda environment 
            that was used to produce this result
        - 'module_versions': The versions of all modules in the conda environment 
            that was used to produce this result
        - 'history': The history of the code that was used to produce this result 
            in a Jupyter Notebook.
        - 'hostname': Name of the machine the code was run on.
        
        It is possible to use tuples of strings as keys to reflect an arbitrary hierarchy.
        Valid keys are tuples of str or str. "@" is not allowed.
        
        To read out all existing keys, use the keys() method.
        
        E.g. this class can be initialized in a way that after the initialization, 
        the data can be accessed in the following way::

            db['voltage_traces']
            db['synapse_activation']
            db['spike_times']
            db['metadata']
            db['cell_activation']
        
        Further more, it is possible to assign new elements to the database
        db['my_new_element'] = my_new_element

        Args:
            basedir (str): 
                The directory in which the database will be created, or read from.
            readonly (bool, optional): 
                If True, the database will be read only. Defaults to False.
            nocreate (bool, optional): 
                If True, a new database will not be created if it does not exist. 
                Defaults to False.
            suppress_errors (bool, optional):
                If True, errors will be suppressed and raised as warnings instead. Defaults to False. Use with caution.
        '''
        self.basedir = os.path.abspath(str(basedir))  # for public access: str. This is not a Path object for backwards compatibility.
        self._basedir = Path(self.basedir)  # for internal operations
        self.readonly = readonly
        self.nocreate = nocreate
        self.parent_db = None
        self._suppress_errors = suppress_errors

        # database state
        self._db_state_fn = "db_state.json"
        self._unique_id = None
        self._registeredDumpers = []
        self._registered_to_path = None
        self._is_legacy = False  # if loading in legacy ModelDataBase

        self._forbidden_keys = [
            "dbcore.pickle", "metadata.db", "sqlitedict.db", "Loader.json",  # for backwards compatibility
            "metadata.db.lock", "sqlitedict.db.lock",  # for backwards compatibility
            "Loader.json", "db_state.json"
        ]
        
        self.metadata = MetadataAccessor(self)
        if self._is_initialized():
            self.read_db_state()
        else:
            errstr = "Did not find a database in {path}. ".format(path = basedir) + \
            "A new empty database will not be created since "+\
            "{mode} is set to True."
            if nocreate:
                raise db_exceptions.DataBaseException(errstr.format(mode = 'nocreate'))
            if readonly:
                raise db_exceptions.DataBaseException(errstr.format(mode = 'readonly'))                
            self._initialize()
            
        if self.readonly == False:
            if self._unique_id is None:
                self._set_unique_id()
            if self._registered_to_path is None:
                self._register_this_database()
                self.save_db_state()
            self._infer_missing_metadata()  # In case some is missing

    def _infer_missing_metadata(self):
        '''
        Checks whether metadata is missing. Is so, it tries to estimate metadata, i.e. it sets the
        time based on the timestamp of the files. When metadata is created in that way,
        the field `metadata_creation_time` is set to `post_hoc`
        '''
        keys_in_db_without_metadata = set(self.keys()).difference(set(self.metadata.keys()))
        for key_str in keys_in_db_without_metadata:
            key = self._convert_key_to_path(key_str)
            logger.info("Updating metadata for key {key}".format(key = key.name))
            try:
                dumper = get_dumper_string_by_savedir(str(key))
            except EnvironmentError as e:
                dumper = "unknown"
            
            time = os.stat(str(key)).st_mtime
            time = datetime.datetime.utcfromtimestamp(time)
            time = tuple(time.timetuple())
            
            out = {
                'dumper': dumper, 
                'time': time,
                'metadata_creation_time': 'post_hoc',
                'version': 'unknown'
                }
            
            # Save metdata, only for the key that does not have any
            json.dump(out, open(str(key/'metadata.json'), 'w'))
            
    def _register_this_database(self):
        logger.info('registering database with unique id {} to the absolute path {}'.format(
            self._unique_id, self._basedir))
        try:
            data_base_register.register_db(self._unique_id, self._basedir)
            self._registered_to_path = self._basedir
        except db_exceptions.DataBaseException as e:
            if self._suppress_errors:
                logger.warning(str(e))
            else:
                raise e
  
    def _set_unique_id(self):
        """
        Sets a unique ID for the DataBase as class attribute. Does not save this ID as metadata (this is taken care of by :meth:_initialize)

        Raises:
            ValueError: If the unique ID is already set.
        """
        if self._unique_id is not None:
            raise ValueError("self._unique_id is already set!")
        # db_state.json may exist upon first init, but does not have a unique id yet. Create it and reset db_state
        time = os.stat(str(self._basedir/'db_state.json')).st_mtime
        time = datetime.datetime.utcfromtimestamp(time)
        time = time.strftime("%Y-%m-%d")
        random_string = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) 
                                for _ in range(7))
        self._unique_id = '_'.join([time, str(os.getpid()), random_string])
    
    def _is_initialized(self):
        if Path.exists(self._basedir/'dbcore.pickle'):
            self._is_legacy = True
        if Path.exists(self._basedir/'db_state.json'):
            # Converted legacy: has both .json and .pickle files.
            return True
        elif Path.exists(self._basedir/'dbcore.pickle'):
            # Just a legacy. No .json file.
            logger.warning('You are reading a legacy ModelDataBase using the new API. Beware that some functionality may not work (yet)')
            self._db_state_fn = 'dbcore.pickle'
            return True
        else:
            return False
    
    def _initialize(self):
        _check_working_dir_clean_for_build(self._basedir)   
        if not os.path.exists(str(self._basedir)):
            os.makedirs(str(self._basedir))
        # create empty state file. 
        with open(str(self._basedir/self._db_state_fn), 'w'):
            pass
        self._set_unique_id()
        self._registeredDumpers.append(DEFAULT_DUMPER)
        self._register_this_database()
        self.state = {
            '_registeredDumpers': self._registeredDumpers,
            '_unique_id': self._unique_id,
            '_registered_to_path': self._registered_to_path,
            }
        self.save_db_state()
           
    def _convert_key_to_path(self, key):
        self._check_key_format(key)
        if isinstance(key, str):
            return self._basedir/key
        elif isinstance(key, tuple):
            sub_db_path = ['db' if not self._is_legacy else 'mdb'] * (len(key) * 2 - 1)
            sub_db_path[0::2] = key
            return Path(self._basedir, *sub_db_path)
        else:
            assert isinstance(key, Path), "Key must be a string, tuple of strings, or Path. {} is type {}".format(key, type(key))
            return key
    
    def _check_key_format(self, key_str_tuple):
        """
        Checks the format of a key (string or tuple) and if it is valid for setting data (not for get).
        This is internal API and should never be called directly.
        This is the first line of checks when a user sets a key. For this reason, ``key`` is not Path, but a string or tuple.

        Args:
            key (str|tuple(str)): The key

        Raises:
            ValueError: If the key is over 100 characters long
            ValueError: If the key contains characters that are not allowed (only numeric or latin alphabetic characters, "-" and "_" are allowed)
        """
        assert isinstance(key_str_tuple, str) or isinstance(key_str_tuple, tuple), "Any key must be a string or tuple of strings. {} is type {}".format(key_str_tuple, type(key_str_tuple))
        if isinstance(key_str_tuple, str):
            key_str_tuple = key_str_tuple,  # convert to tuple
        assert all([isinstance(e, str) for e in key_str_tuple]), "Any key must be a string or tuple of strings. {} is type {}".format(key_str_tuple, type(key_str_tuple))

        # Check if individual characters are allowed
        for subkey in key_str_tuple:
            if len(subkey) > 100:
                raise ValueError('keys must be shorter than 100 characters')
            allowed_characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_.1234567890'
            for c in subkey:
                if not c in allowed_characters:
                    raise ValueError('Character {} is not allowed, but appears in key {}'.format(c, subkey))
        
    def _detect_dumper_string_of_existing_key(self, key):
        '''returns the dumper string of an existing key'''
        return get_dumper_from_folder(self._convert_key_to_path(key), return_ = 'string')
    
    def _find_dumper(self, item):
        '''
        Finds the dumper of a given item.
        Iterates all registered dumper and returns the first one that can save the item
        
        Args:
            item (object): The item to save

        Returns:
            module | None: The dumper module that can save the item, or None if there are no viable registered dumpers in the db.
        '''
        dumper = None
        for d in self._registeredDumpers:
            if d.check(item):
                dumper = d
                break
        return dumper
        
    def _write_metadata(self, dumper, dir_to_data):
        '''this is private API and should only
        be called from within DataBase.
        Can othervise be destructive!!!'''        
        if VC.get_git_version()['dirty']:
            logger.warning('The database source folder has uncommitted changes!')
        dumper_string = get_dumper_string_by_dumper_module(dumper)

        out = {'dumper': dumper_string,
               'time': tuple(datetime.datetime.utcnow().timetuple()), 
               'conda_list': VC.get_conda_list(),
               'module_versions': make_all_str(VC.get_module_versions()),
               'history': VC.get_history(),
               'hostname': VC.get_hostname(),
               'metadata_creation_time': "together_with_new_key"}

        out.update(VC.get_git_version())
            
        with open(str(dir_to_data/'metadata.json'), 'w') as f:
            json.dump(out, f)
    
    def _check_writing_privilege(self, key):
        '''raises DataBaseException, if we don't have permission to write to key '''
        if self.readonly is True:
            if self._suppress_errors:
                logger.warning("DB is in readonly mode. Blocked writing attempt to key %s" % key)
            else:
                raise db_exceptions.DataBaseException("DB is in readonly mode. Blocked writing attempt to key %s" % key)
        #this exists, so jupyter notebooks will not crash when they try to write something
        elif self.readonly == 'warning': 
            logger.warning("DB is in readonly mode. Blocked writing attempt to key %s" % key)
        elif self.readonly == False:
            pass
        else:
            raise db_exceptions.DataBaseException("Readonly attribute should be True, False or 'warning, but is: %s" % self.readonly)
    
    def _find_legacy_key(self, key):
        """Given a key, find the corresponding key in the legacy ModelDataBase.
        Legacy ModelDataBase keys have a random suffix wrapped in underscores, e.g. key_number_1_PGubxd_
        This method finds all legacy keys that match some key, and returns the first one.

        Args:
            key (_type_): _description_
        """
        matching_keys = [k for k in self.keys() if k.startswith(str(key))]
        if len(matching_keys) == 0:
            raise KeyError("Could not find key {} in legacy ModelDataBase".format(key))
        elif len(matching_keys) > 1:
            logger.warning("Found multiple keys that match {}. Returning the first one: {}. All matching keys: {}".format(key, matching_keys[0], matching_keys))
        return matching_keys[0]
    
    def check_if_key_exists(self, key):
        '''returns True, if key exists in a database, False otherwise'''
        return self._convert_key_to_path(key).exists()
    
    def get_id(self):
        return self._unique_id 
     
    def register_dumper(self, dumper_module):
        """
        Make sure to provide the module, not the class

        Args:
            dumper_module (module): A module from data_base.IO.LoaderDumper. Must contain a Loader class and a dump() method.
        
        """
        self._registered_dumpers.append(dumper_module)
    
    def save_db_state(self):
        '''saves the data which defines the state of this database to db_state.json'''
        ## things that define the state of this db and should be saved
        out = {'_registeredDumpers': [e.__name__ for e in self._registeredDumpers], \
               '_unique_id': self._unique_id,
               '_registered_to_path': str(self._registered_to_path)} 
        with open(str(self._basedir/self._db_state_fn), 'w') as f:
            if self._db_state_fn.endswith('.json'):
                json.dump(out, f)
            elif self._db_state_fn.endswith('.pickle'):
                import cloudpickle
                cloudpickle.dump(out, f)

    def read_db_state(self):
        '''sets the state of the database according to db_state.json/dbcore.pickle''' 
        if self._db_state_fn.endswith('.json'):
            with open(str(self._basedir/self._db_state_fn), 'r') as f:
                state = json.load(f)
        elif self._db_state_fn.endswith('.pickle'):
            state = pandas_unpickle_fun(str(self._basedir/self._db_state_fn))
            
        for name in state:
            if name == '_registeredDumpers':
                # from string to module
                for dumper_string in state[name]:
                    if dumper_string == 'self':
                        dumper_string = DEFAULT_DUMPER
                    else:
                        dumper = importlib.import_module(dumper_string)
                    self._registeredDumpers.append(dumper)
            else:
                setattr(self, name, state[name])

    def get_mkdtemp(self, prefix = '', suffix = ''):
        '''creates a directory in the data_base directory and 
        returns the path'''
        absolute_path = tempfile.mkdtemp(prefix = prefix + '_', suffix = '_' + suffix, dir=str(self._basedir))
        os.chmod(absolute_path, 0o755)
        relative_path = absolute_path.relative_to(str(self._basedir))
        return absolute_path, relative_path

    def create_managed_folder(self, key, raise_ = True):
        '''creates a folder in the db directory and saves the path in 'key'.
        You can delete the folder using del db[key]'''
        #todo: make sure that existing key will not be overwritten
        if key in list(self.keys()):
            if raise_:
                raise db_exceptions.DataBaseException("Key %s is already set. Please use del db[%s] first" % (key, key))
        else:           
            self.set(key, None, dumper = just_create_folder)
        return self[key]

    def create_shared_numpy_store(self, key, raise_ = True):
        if key in list(self.keys()):
            if raise_:
                raise db_exceptions.DataBaseException("Key %s is already set. Please use del db[%s] first" % (key, key))
        else:
            self.set(key, None, dumper = shared_numpy_store)        
        return self[key]
    
    def create_sub_db(self, key, register = 'as_parent', **kwargs):
        '''creates a DataBase within a DataBase. Example:
        db.create_sub_db('my_sub_database')
        db['my_sub_database']['some_key'] = ['some_value']
        Kwargs will be passed to the dumper.

        Args:
            key (str|tuple): The key of the sub_db
            register (str, optional): ? TODO. Defaults to 'as_parent'.
            raise_ (bool, optional): Whether to raise an error if the sub_db already exists. Defaults to True.

        Kwargs:
            overwrite (bool, optional): Whether to overwrite the sub_db if it already exists. Defaults to True.
            Other kwargs will be passed to the dumper, and may depend on which dumper you're using. Consult :mod:data_base.IO.LoaderDumper for more information on possible kwargs.

        Returns:
            DataBase: The newly created sub_db
        '''
        self._check_key_format(key)
        if isinstance(key, str):
            key = key,  # convert to tuple
        # go down the tree of pre-existing sub_dbs as long as the keys exist
        remaining_keys = key
        parent_db = self
        for i in range(len(key)):
            if key[i] not in parent_db.keys():
                # create sub_dbs from here on
                break
            if not parent_db[remaining_keys[0]].__class__.__name__ == "ISFDataBase":
                # The key exists and not an db, but we want to create one here
                raise db_exceptions.DataBaseException(
                    "You were trying to overwrite existing data at %s with a (sub)db by using key %s. Please use del db[%s] first" % (
                        parent_db._basedir/key[i], key, key[:i+1]
                        ))
            # go down the tree of sub_dbs
            parent_db = parent_db[remaining_keys[0]]
            remaining_keys = remaining_keys[1:]
        
        # If there are still unique keys remaining in the tuple, we have to create at least one sub_db
        for k in remaining_keys:
            parent_db.set(k, None, dumper = just_create_isf_db, **kwargs)
            # Note: registering this database happens upon initialization of the sub_db
            parent_db[k].parent_db = parent_db  # remember that it has a parent
            parent_db = parent_db[k]  # go down the tree of sub_dbs
        # Either ``raise_`` is false and there are no remaining keys 
        #   -> simply return the pre-existing sub_db
        # or we just created it 
        #   -> return newly created sub_db
        return parent_db

    def get(self, key, lock = None, **kwargs):
        """This is the main method to get data from a DataBase. :meth:getitem and :meth:__getitem__ call this method.
        :meth:getitem only exists to provide consistent API with dbv1.
        :meth:__getitem__ is the method that's being called when you use db[key].
        The advantage is that this allows to pass additional arguments to the loader, e.g.
        db.getitem('key', columns = [1,2,3]).

        Args:
            key (str): the key to get from db[key]
            lock (Lock, optional): If you use file locking, provide the lock that grants access. Defaults to None.

        Returns:
            object: The object saved under db[key]
        """
        # this looks into the metadata.json, gets the name of the dumper, and loads this module form IO.LoaderDumper
        if self._is_legacy:
            key = self._find_legacy_key(key)
        key = self._convert_key_to_path(key)
        if not Path.exists(key):
            raise KeyError("Key {} not found in keys of db. Keys found: {}".format(key.name, self.keys()))
        if lock:
            lock.acquire()
        try:
            return_ = LoaderDumper.load(str(key), **kwargs)
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                self.ls(all_files = True)
                raise db_exceptions.DataBaseException("Could not load key %s. The file %s does not exist." % (str(key), e.filename))
            else:
                raise e
        if lock:
            lock.release()
        return return_
    
    def rename(self, old_key, new_key):
        if not any([isinstance(e, str) or isinstance(e, Path) for e in [old_key, new_key]]):
            raise ValueError('old and new must be strings or Paths')
        old_key = Path(old_key)
        new_key = Path(new_key) 
        old_key.rename(new_key)

    def set(self, key, value, lock = None, dumper = None, **kwargs):
        """Main method to save data in a DataBase. :meth:set and :meth:__setitem__ call this method.
        :meth:set only exists to provide consistent API with dbv1.
        :meth:__setitem__ is the method that's being called when you use db[key] = value.
        The advantage of using this method is that you can specify a dumper and pass additional arguments to the dumper with **kwargs.
        This method is thread safe, if you provide a lock.
        # TODO: deprecate the dumper "self". "self" only makes sense with an sqlite backend. "default" would be better in this case.

        Args:
            key (str): _description_
            value (obj): _description_
            lock (Lock, optional): _description_. Defaults to None.
            dumper (module|str|None, optional): The dumper module to use when saving data. If None or "self" are passed, it will use the default dumper LoaderDumper.to_cloudpickle. Defaults to None.

        Raises:
            KeyError: _description_
        """
        # Find correct dumper to save data with
        if dumper is None:
            dumper = self._find_dumper(value)
        assert dumper is not None
        assert(inspect.ismodule(dumper))
        loaderdumper_module = dumper

        #check if we have writing privilege
        self._check_writing_privilege(key)
        self._check_key_format(key)

        # Use recursion to create sub_dbs in case a tuple key is passed
        # All elements except for the last one should become sub_dbs if they aren't already
        if isinstance(key, tuple) and len(key) > 1:
            sub_db = self.create_sub_db(key[0])  # create or fetch the sub_db
            # Recursion: set remaining subkeys in the sub_db
            sub_db.set(key[1:], value, lock = lock, dumper = dumper, **kwargs)
            return  # no further part of set() is needed for this subkey
        elif isinstance(key, tuple) and len(key) == 1:
            key = key[0]  # break recursion
        
        key = self._convert_key_to_path(key)

        # Key is Path and not a tuple if code made it here
        assert isinstance(key, Path)
        if Path.exists(key):  
            if is_db(key) or Path.exists(key/'db'):
                # Either the key is an db, or it's a key that contains a subdb
                # We are about to overwrite an db with data: that's a no-go (it's a me, Mario)
                raise db_exceptions.DataBaseException(
                    "You were trying to overwrite a sub_db at %s with data using the key %s. Please remove the sub_db first, or use a different key." % (
                        str(self._basedir), key.name
                        )
                )
            # check if we can overwrite
            overwrite = kwargs.get('overwrite', True)  # overwrite=True if unspecified
            if overwrite:
                logger.info('Key {} is already set in DataBase located at {}. Overwriting...'.format(key.name, str(self._basedir)))
                delete_in_background(key)
            else:
                raise KeyError(
                    'Key {} is already set and you passed overwrite=False in the kwargs: {}'.format(key.name, kwargs) + \
                    '\nEither use del db[key] first, set overwrite to True, or omit the overwrite keyword argument.')  
        
        # Either the path does not exist yet, or it's in the process of being deleted
        os.makedirs(str(key))
        
        if lock:
            lock.acquire()
        try:
            loaderdumper_module.dump(value, str(key), **kwargs)
            self._write_metadata(dumper, key)
        except Exception as e:
            logger.info("An error occured. Tidy up. Please do not interrupt.")
            try:
                shutil.rmtree(str(key))
            except:
                logger.info('could not delete folder {:s}'.format(key.name))
            raise
        if lock:
            lock.release()
    
    def maybe_calculate(self, key, fun, **kwargs):
        '''This function returns the corresponding value of key,
        if it is already in the database. If it is not in the database,
        it calculates the value by calling fun, adds this value to the
        database and returns the value.
        
        key: key on which the item can be accessed / should be accessible in the database
        fun: function expects no parameters (e.g. lambda: 'hello world') 
        force_calculation =: if set to True, the value will allways be recalculated
            If there is already an entry in the database with the same key, it will
            be overwritten
        **kwargs: attributes, that get passed to DataBase.set
        
        Example:
        #value is calculated, since it is the first call and not in the database
        db.maybe_calculate('knok_knok', lambda: 'whos there?', dumper = 'self')
        > 'whos there?'
        
        #value is taken from the database, since it is already stored
        db.maybe_calculate('knok_knok', lambda: 'whos there?', dumper = 'self')
        > 'whos there?'        
        '''
        
        if 'force_calculation' in kwargs:
            force_calculation = kwargs['force_calculation']
            del kwargs['force_calculation']
        else:
            force_calculation = False
        try:
            if force_calculation:
                raise ValueError
            return self[key]
        except KeyError:
            ret = fun()
            self.set(key, ret, **kwargs)
            return ret    
    
    def keys(self):
        '''returns the keys of the database as string objects'''
        all_keys = self._basedir.iterdir()
        keys_ =  tuple(
            e.name for e in all_keys 
            if e.name not in ("db_state.json", "metadata.json", "Loader.json")
            and e.name not in [
                "dbcore.pickle", "metadata.db", 
                "sqlitedict.db", "sqlitedict.db.lock",
                "metadata.db.lock"] # dbv1 compatibility
            and ".deleting." not in e.name
            )
        return keys_

    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __delitem__(self, key):
        """
        Items can be deleted using del my_data_base[key]
        Deleting an item will first rename the item to a random string and then delete it in the background.
        This way, your Python process is not interrupted when deleting large files, and you can immediately use the key again.
        
        """
        to_delete = self._convert_key_to_path(key)
        delete_in_background(to_delete)
    
    def __reduce__(self):
        return (self.__class__, (self._basedir, self.readonly, True), {})

    def __repr__(self):
        return self._get_str()  # print with default depth and max_lines

    def ls(self, depth=0, max_depth=2, max_lines=20, all_files=False, max_lines_per_key=3):
        """Prints out the content of the database in a tree structure.

        Args:
            max_depth (int, optional): How deep you want the filestructure to be. Defaults to 2.
            max_lines (int, optional): How long you want your filelist to be. Defaults to 20.
        """
        print(self._get_str(
            depth=depth, max_depth=max_depth, max_lines=max_lines, 
            all_files=all_files, max_lines_per_key=max_lines_per_key))
    
    def _get_str(self, depth=0, max_depth=2, max_lines=20, all_files=False, max_lines_per_key=3):
        """Fetches a string representation for this db in a tree structure.
        This is internal API and should never be called directly.
        
        Args:
            max_depth (int, optional): How deep you want the filestructure to be. Defaults to 2.
            max_lines (int, optional): How long you want your filelist to be. Defaults to 20.
            only_keys (bool, optional): Whether to only print keys only, or all files. Defaults to False.
            max_lines_per_key (int, optional): How many lines to print per key. Defaults to 4.

        Returns:
            str: A string representation of this db in a tree structure.

        """

        str_ = ['<{}.{} object at {}>'.format(self.__class__.__module__, self.__class__.__name__, hex(id(self)))]
        str_.append("Located at {}".format(self._basedir))
        str_.append("Located at {}".format(self._basedir))
        # str_.append("{1}DataBases{0} | {2}Directories{0} | {3}Keys{0}".format(
        #     bcolors.ENDC, bcolors.OKGREEN, bcolors.WARNING, bcolors.OKCYAN) )
        str_.append(colorize(self._basedir.name, bcolors.OKGREEN))
        lines = calc_recursive_filetree(
            self, Path(self._basedir), 
            depth=depth, max_depth=max_depth, max_lines_per_key=max_lines_per_key, all_files=all_files, max_lines=max_lines)
        for line in lines:
            str_.append(line)
        return "\n".join(str_)

    def remove(self):
        '''
        Deletes the database from disk in the background and de-registers itself from the register as soon as it is deleted.
        Note that this method is not a destructor, nor equivalent to __del__ or __delete__.
        IOW, this method does not get called during garbage collection, when the object goes out of scope, or when the program terminates.
        It should be explicitly called by the user when the user likes to delete a database.
        '''
        def delete_and_deregister_once_deleted(dir_to_data, unique_id):
            shutil.rmtree(dir_to_data)
            # this will delete in foreground of the thread, 
            # and thus wait until db is deleted and only then continue
            register = data_base_register._get_db_register()
            del register[unique_id]  # remove from the register

        # make sure folder is renamed before continuing python process
        dir_to_data_rename = rename_for_deletion(str(self._basedir))
        # start processes on one thread in background
        return threading.Thread(target = lambda : delete_and_deregister_once_deleted(dir_to_data_rename, self._unique_id)).start()


def get_isfdb_by_unique_id(unique_id):
    db_path = data_base_register._get_db_register().registry[unique_id]
    db = ISFDataBase(db_path, nocreate=True)
    assert db.get_id() == unique_id
    return db


from .IO import LoaderDumper
from .IO.LoaderDumper import to_cloudpickle, just_create_folder, just_create_isf_db, shared_numpy_store, get_dumper_string_by_savedir, get_dumper_string_by_dumper_module
from data_base.utils import calc_recursive_filetree, rename_for_deletion, delete_in_background, is_db, bcolors
from compatibility import pandas_unpickle_fun
DEFAULT_DUMPER = to_cloudpickle
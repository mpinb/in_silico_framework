'''
Created on Aug 15, 2016

@author: arco
'''
from __future__ import absolute_import
import os, random, string, threading
import contextlib
import shutil
import tempfile
import datetime
import cloudpickle as pickle
import yaml
from compatibility import YamlLoader


if 'ISF_MDB_CONFIG' in os.environ:
    config_path = os.environ['ISF_MDB_CONFIG']
    with open(os.environ['ISF_MDB_CONFIG'], 'r') as f:
        config = yaml.load(f, Loader=YamlLoader)
else:
    # config = dict(backend = dict(type = 'sqlite_remote', url = 'ip:port')) 
    config = dict(backend = dict(type = 'sqlite'))

if config['backend']['type'] == 'sqlite':
    from .sqlite_backend.sqlite_backend import SQLiteBackend as SQLBackend
elif config['backend']['type'] == 'sqlite_remote':
    print("Using remote sqlite backend with config {}".format(config))
    from .sqlite_backend.sqlite_remote_backend_client import SQLiteBackendRemote as SQLBackend
else:
    raise ValueError("backend must be sqlite or sqlite_remote")

from .sqlite_backend.sqlite_backend import InMemoryBackend

from collections import defaultdict
# import model_data_base_register ## moved to end of file since this is a circular import


import dask.diagnostics
import warnings
import re
import inspect
from ._version import get_versions
import six
import unicodedata

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    http://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
    a bit modified
    """
    value = six.text_type(value)
    value = unicodedata.normalize('NFKD', value)
    value = six.text_type(re.sub('[^\w\s-]', '', value).strip().lower())
    value = six.text_type(re.sub('[-\s]+', '-', value))
    value = six.text_type(value)
    if len(value) >= 50:
        value = value[:50]
    return value
    
class LoaderWrapper:
    '''This is a pointer to data, which is stored elsewhere.
    
    It is used by ModelDataBase, if data is stored in a subfolder of the 
    model_data_base.basedir folder. It is not used, if the data is stored directly
    in the sqlite database.
    
    The process of storing data in a subfolder is as follows:
    1. The subfolder is generated using the mkdtemp method
    2. the respective dumper puts its data there
    3. the dumper also saves a Loader.pickle file there. This contains an object
       with a get method (call it to restore the data) and everything else
       necessary to recover the data
    4. A LoaderWrapper object pointing to the datafolder with a relative
        path (to allow moving of the database) is saved under the respective key
        in the model_data_base
        
    The process of loading in the data is as follows:
    1. the user request it: mdb['somekey']
    2. the LoaderWrapper object is loaded from the backend sql database
    3. the Loader.pickle file in the respective folder is loaded
    4. the get-methdo of the unpickled object is called with the
        absolute path to the folder.
    5. the returned object is returned to the user
    '''
    def __init__(self, relpath):
        self.relpath = relpath
        
class FunctionWrapper:
    '''This class wraps arouand an object that cannot be saved directly (e.g. 
    using pickle) but needs an initialization function instead.
    
    To use it, 
    1. create a function, that does not expect any argument and returns the object
        you want to save    
    2. create an instance of this class and pass your function
    3. save it in the database with wathever dumper you want'''
    def __init__(self, fun):
        self.fun = fun
                
class MdbException(Exception):
    '''Typical mdb errors'''
    pass        

def _check_working_dir_clean_for_build(working_dir):
    '''Backend method that checks, wether working_dir is suitable
    to build a new database there'''
    #todo: try to make dirs
    if os.path.exists(working_dir):
        try:
            if not os.listdir(working_dir):
                return
            else:
                raise OSError()
        except OSError:
            raise MdbException("Can't build database: " \
                               + "The specified working_dir is either not empty " \
                               + "or write permission is missing. The specified path is %s" % working_dir)
    else:
        try: 
            os.makedirs(working_dir)
            return
        except OSError:
            raise MdbException("Can't build database: " \
                               + "Cannot create the directories specified in %s" % working_dir)

###methods to hide dask progress bar based on settings:
@contextlib.contextmanager
def empty_context_manager(*args, **kwargs):
    '''does nothing. is meant to replace ProgressBar, if no output is needed'''
    yield

def get_progress_bar_function():
    PB = empty_context_manager    
#     if settings.show_computation_progress:
#         PB = dask.diagnostics.ProgressBar
#     else:
#         PB = empty_context_manager
    return PB           

class SQLMetadataAccessor():
    def __init__(self, sql_backend):
        self.sql_backend = sql_backend
        
    def __getitem__(self, key):
        out = defaultdict(lambda: 'unknown')
        if key in list(self.sql_backend.keys()):
            out.update(self.sql_backend[key])
        return out
    
    def keys(self):
        return list(self.sql_backend.keys())

class ModelDataBase(object):
    def __init__(self, basedir, forceload = False, readonly = False, nocreate = False, 
                 forcecreate = False):
        '''
        Class responsible for storing information, meant to be used as an interface to simulation 
        results. If the dask backends are used to save the data, it will be out of memory,
        allowing larger than memory calculations.
        
        E.g. this class can be initialized in a way that after the initialization, 
        the data can be accessed in the following way:
        mdb['voltage_traces']
        mdb['synapse_activation']
        mdb['spike_times']
        mdb['metadata']
        mdb['cell_activation']
        
        Further more, it is possible to assign new elements to the database
        mdb['my_new_element'] = my_new_element
        These elements are stored together with the other data in the basedir.
        
        They can be read out of the database in the following way:
        my_reloaded_element = mdb['my_new_element']
        
        It is possible to use tuples of strings as keys to reflect an arbitrary hierarchy.
        Valid keys are tuples of str or str. "@" ist not allowed.
        
        To read out all existing keys, use the keys()-function.
        '''
        self.basedir = os.path.abspath(basedir)
        self.forceload = forceload
        self.readonly = readonly #possible values: False, True, 'warning'
        self._first_init = False
        self._unique_id = None
        self._registered_to_path = None
        
        try:
            self.read_db()
        except IOError:
            errstr = "Did not find a database in {path}. ".format(path = basedir) + \
                    "A new empty database will not be created since "+\
                    "{mode} is set to True."
            if nocreate:
                raise MdbException(errstr.format(mode = 'nocreate'))
            if readonly:
                raise MdbException(errstr.format(mode = 'readonly'))
            if not forcecreate:
                _check_working_dir_clean_for_build(basedir)
            self._first_init = True
            self._registeredDumpers = [to_cloudpickle]
            self.save_db()                        
            self._set_unique_id()
            self._register_this_database()
            self.save_db()
            
        
        self._sql_backend = SQLBackend(os.path.join(self.basedir, 'sqlitedict.db'))
        self._sql_metadata_backend = SQLBackend(os.path.join(self.basedir, 'metadata.db'))
        self.metadata = SQLMetadataAccessor(self._sql_metadata_backend)
        
        if self.readonly == False:
            if self._registered_to_path is None:
                self._register_this_database()
                self.save_db()
            #self._register_this_database()            
            self._update_metadata_if_necessary()
            #############################
            # the following code helps to smoothly transient databases of the old
            # format (does not implement _unique_id and metadata) to the new format.
            # Should be commented out soon.
            ##############################                    
            if self._unique_id is None:
                self._set_unique_id()

    def in_memory(self, keys = 'all', recursive = True):
        '''Load all data required for accessing data in memory. This can be helpful, if locking 
        is taking much time, but would not be required. If in_memory has been called, no changes to 
        the database are possible'''
        self._sql_backend = InMemoryBackend(self._sql_backend, keys = keys)
        self._sql_metadata_backend = InMemoryBackend(self._sql_metadata_backend, keys = keys)
        self.metadata.sql_backend = self._sql_metadata_backend # InMemoryBackend(self._sql_metadata_backend, keys = keys)
        self.readonly = True

        if recursive: 
            for k in list(self.keys()):
                if self.metadata[k]['dumper'] == 'just_create_mdb':
                    m = self[k]
                    m.in_memory(recursive = True)
                    self._sql_backend._db[k] = m

    def _register_this_database(self):
        print('registering database with unique_id {} to the absolute path {}'.format(
                        self._unique_id, self.basedir))
        try:
            model_data_base_register.register_mdb(self)
            self._registered_to_path = self.basedir
        except MdbException as e:
            warnings.warn(str(e))
            
    def _set_unique_id(self):
        if self._unique_id is not None:
            raise ValueError("self._unique_id is already set!")
        time = os.stat(os.path.join(self.basedir, 'dbcore.pickle')).st_mtime
        time = datetime.datetime.utcfromtimestamp(time)
        time = time.strftime("%Y-%m-%d")
        random_string = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) 
                                for _ in range(7))
        self._unique_id = '_'.join([time, str(os.getpid()), random_string])
        self.save_db()      
        
    def get_id(self):
        return self._unique_id 
        
    def registerDumper(self, dumperModule):
        '''caveat: make sure to provide the MODULE, not the class'''
        self._registeredDumpers.append(dumperModule)
    
    def read_db(self):
        '''sets the state of the database according to dbcore.pickle''' 
        with open(os.path.join(self.basedir, 'dbcore.pickle'), 'rb') as f:
            out = pickle.load(f)
            
        for name in out:
            setattr(self, name, out[name])            
            
    def save_db(self):
        '''saves the data which defines the state of this database to dbcore.pickle'''
        ## things that define the state of this mdb and should be saved
        out = {'_registeredDumpers': self._registeredDumpers, \
               '_unique_id': self._unique_id,
               '_registered_to_path': self._registered_to_path} 
        with open(os.path.join(self.basedir, 'dbcore.pickle'), 'wb') as f:
            pickle.dump(out, f)
        
    def itemexists(self, key):
        '''Checks, if item is already in the database'''
        return key in list(self.keys())
                
    def get_mkdtemp(self, prefix = '', suffix = ''):
        '''creates a directory in the model_data_base directory and 
        returns the path'''
        absolute_path = tempfile.mkdtemp(prefix = prefix + '_', suffix = '_' + suffix, dir = self.basedir) 
        os.chmod(absolute_path, 0o755)
        relative_path = os.path.relpath(absolute_path, self.basedir)
        return absolute_path, relative_path

    def create_managed_folder(self, key, raise_ = True):
        '''creates a folder in the mdb directory and saves the path in 'key'.
        You can delete the folder using del mdb[key]'''
        #todo: make sure that existing key will not be overwritten
        if key in list(self.keys()):
            if raise_:
                raise MdbException("Key %s is already set. Please use del mdb[%s] first" % (key, key))
        else:           
            self.setitem(key, None, dumper = just_create_folder)
        return self[key]
        
    def get_managed_folder(self, key):
        '''deprecated!
        
        Use create_managed_folder instead'''   
        warnings.warn("Get_managed_folder is deprecated.  Use create_managed_folder instead.") 
        return self.create_managed_folder(key)
    
    def create_shared_numpy_store(self, key, raise_ = True):
        if key in list(self.keys()):
            if raise_:
                raise MdbException("Key %s is already set. Please use del mdb[%s] first" % (key, key))
        else:
            self.setitem(key, None, dumper = shared_numpy_store)        
        return self[key]
            
    
    def create_sub_mdb(self, key, register = 'as_parent', raise_ = True):
        '''creates a ModelDataBase within a ModelDataBase. Example:
        mdb.create_sub_mdb('my_sub_database')
        mdb['my_sub_database']['sme_key'] = ['some_value']
        '''
        if register == 'as_parent':
            ##todo
            pass
        if key in list(self.keys()):
            if raise_:
                raise MdbException("Key %s is already set. Please use del mdb[%s] first" % (key, key))
        else:
            self.setitem(key, None, dumper = just_create_mdb)
        return self[key]
    
    def get_sub_mdb(self,key, register = 'as_parent'):
        '''deprecated!
        
        Use create_sub_mdb instead'''
        warnings.warn("get_sub_mdb is deprecated.  Use create_sub_mdb instead.")         
        return self.create_sub_mdb(key, register = register)
    
    def getitem(self, arg, **kwargs):
        '''instead of mdb['key'], you can use mdb.getitem('key'). The advantage
        is that this allows to pass additional arguments to the loader, e.g.
        mdb.getitem('key', columns = [1,2,3]).'''
        return self.__getitem__(arg, **kwargs)
        
    def _get_path(self, arg):
        dummy = self._sql_backend[arg]
        if isinstance(dummy, LoaderWrapper):
            return os.path.join(self.basedir, dummy.relpath)
        
    def _get_dumper_string(savedir, arg):
        path = self._get_path(arg)
        if path is None:
            return 'self'
        else:
            return IO.LoaderDumper.get_dumper_string_by_savedir(path)
        
    def __getitem__(self, arg, **kwargs):
        '''items can be retrieved from the ModelDataBase using this syntax:
        item = my_model_data_base[key]'''
        try:        
            # general case                
            dummy = self._sql_backend[arg]
            if isinstance(dummy, LoaderWrapper):
                dummy = LoaderDumper.load(os.path.join(self.basedir, dummy.relpath), loader_kwargs = kwargs) 
            if isinstance(dummy, FunctionWrapper):
                dummy = dummy.fun()
            return dummy   
        except KeyError:  
            # special case: if we have nested mdbs, allow accessing it with
            # mdb[key_in_parent_mdb, key_in_child_mdb] instead of forcing
            # mdb[key_in_parent_mdb][key_in_child_mdb]
            existing_keys = list(self.keys())
            
            def str_to_tuple(x):
                if isinstance(x, str):
                    return (x,)
                else:
                    return x
                
            existing_keys = list(map(str_to_tuple, existing_keys))            
            if isinstance(arg, tuple) and not arg in existing_keys:
                for lv in range(len(arg)):
                    if arg[:lv] in existing_keys:
                        return self[arg[:lv]][arg[lv:]]
            raise    
    
    def _check_writing_privilege(self, key):
        '''raises MdbException, if we don't have permission to write to key '''
        if self.readonly is True:
            raise MdbException("DB is in readonly mode. Blocked writing attempt to key %s" % key)
        #this exists, so jupyter notebooks will not crash when they try to write something
        elif self.readonly == 'warning': 
            warnings.warn("DB is in readonly mode. Blocked writing attempt to key %s" % key)
        elif self.readonly == False:
            pass
        else:
            raise MdbException("Readonly attribute should be True, False or 'warning, but is: %s" % self.readonly)
    
    def _find_dumper(self, item):
        '''finds the dumper of a given item.'''
        dumper = None
        for d in self._registeredDumpers:
            if d == 'self' or d.check(item):
                dumper = d
                break
        return dumper
    
    def _check_key_validity(self, key):
        '''raises an MdbException, if key is invalid'''
        if isinstance(key, str): 
            key = tuple([key])
        # make sure hierarchy mimics folder structure:
        # (parent, child) can only exist, if parent is not already set to
        # some value
        existing_keys = [tuple([k]) if isinstance(k, str) else k for k in list(self.keys())]
        # make sure, first elements of the key are not used already,
        # e.g. if we want to set ('A', '1'), we have to make sure that 
        # ('A') is not already set
        for current_key in [key[:lv] for lv in range(len(key))]:
            if current_key in existing_keys:
                raise MdbException("Cannot set {key1}. Conflicting key is {key2}"\
                                   .format(key1 = key, key2 = current_key))
        # do it vice versa
        for current_key in existing_keys:               
            if len(current_key) <= len(key): continue
            if key == current_key[:len(key)]:
                raise MdbException("Cannot set {key1}. Conflicting key is {key2}"\
                                   .format(key1 = key, key2 = current_key))
    
    def _get_savedir(self, key):
        '''returns directory in which the data is stored. Returns None if dumper is self.'''
        old_folder = None
        if self.check_if_key_exists(key):
            dummy = self._sql_backend[key]
            if isinstance(dummy, LoaderWrapper):
                old_folder = dummy.relpath
        return old_folder
    
    def check_if_key_exists(self, key):
        if isinstance(key, str): 
            key = tuple([key])        
            
        existing_keys = [tuple([k]) if isinstance(k, str) else k for k in list(self.keys())]

        if key in existing_keys:
            return True
        else:
            return False
        
    def _setitem_no_metadata(self, key, item, dumper, **kwargs):
        '''private API! Used for storing data. Writing metadata needs to be done
        in addition!'''
        #if dumper is 'self': store in this DB
        if dumper == 'self':
            self._sql_backend[key] = item
                
        #if dumper is something else: 
        #generate temp directory, save the object in that directory using dump()
        #wrap the relative path to an LoaderWrapper object and save it to the 
        #internal database
        else:
            basedir_absolute, basedir_relative = self.get_mkdtemp(prefix = slugify(key))
            try:
                dumper.dump(item, basedir_absolute, **kwargs)
            except Exception as e:
                print("An error occured. Tidy up. Please do not interrupt.")
                try:
                    shutil.rmtree(basedir_absolute)
                except:
                    print('could not delete folder {:s}'.format(basedir_absolute))
                raise
            self._sql_backend[key] = LoaderWrapper(basedir_relative)
            
    
    def setitem(self, key, item, **kwargs):
        '''Allows to set items. Compared to the mdb['some_keys'] = my_item syntax,
        this method allows more control over how the item is stored in the database.
        
        key: key
        item: item that should be saved
        dumper= dumper module to use, e.g. model_data_base.IO.LoaderDumper.numpy_to_npy
            If dumper is not set, the default dumper is used
        **kwargs: other keyword arguments that should be passed to the dumper
        '''
        if isinstance(key, str): key = tuple([key])
        
        #make sure, key is valid and not conflicting with other keys
        self._check_key_validity(key)
        
        #extract dumper from kwargs
        if not 'dumper' in kwargs:
            dumper = None
        else:
            dumper = kwargs['dumper']
            del kwargs['dumper']
                    
        #check if we have writing privilege
        self._check_writing_privilege(key)
        
        # check if there is already a subdirectory assigned to this key. 
        # If so: store folder to delete it after new item is set.
        old_folder = self._get_savedir(key)
                                
        #find dumper
        if dumper is None:
            dumper = self._find_dumper(item)
        assert dumper is not None
        
        #write data
        self._setitem_no_metadata(key, item, dumper, **kwargs)
        
        #delete old data directory        
        if old_folder is not None:
            self._robust_rmtree(key, os.path.join(self.basedir, old_folder))
            
        #write metadata
        self._write_metadata_for_new_key(key, dumper)
    
    def _write_metadata_for_new_key(self, key, dumper):
        '''this is private API and should only
        be called from within ModelDataBase.
        Can othervise be destructive!!!'''        
        if inspect.ismodule(dumper):
            dumper = LoaderDumper.get_dumper_string_by_dumper_module(dumper)
        elif isinstance(dumper, str):
            pass
        else:
            raise ValueError
        
        out = {'dumper': dumper,
               'time': tuple(datetime.datetime.utcnow().timetuple()), 
               'metadata_creation_time': 'together_with_new_key', 
               'conda_list': VC.get_conda_list(),
               'module_versions': VC.get_module_versions(),
               'history': VC.get_history(),
               'hostname': VC.get_hostname()}

        out.update(VC.get_git_version())

        if VC.get_git_version()['dirty']:
            warnings.warn('The database source folder has uncommitted changes!')
        
        self._sql_metadata_backend[key] = out

    def _delete_metadata(self, key):
        '''this is private API and should only
        be called from within ModelDataBase.
        Can othervise be destructive!!!'''        
        del self._sql_metadata_backend[key]    

    def _detect_dumper_string_of_existing_key(self, key):
        dumper = self._sql_backend[key]
        if isinstance(dumper, LoaderWrapper):
            dumper = LoaderDumper.get_dumper_string_by_savedir(os.path.join(self.basedir, dumper.relpath))
        else:
            dumper = 'self'
        return dumper

    def _get_dumper_folder(self, key):
        dumper = self._sql_backend[key]
        if isinstance(dumper, LoaderWrapper):
            return os.path.join(self.basedir, dumper.relpath)
        else:
            return None        

    def _write_metadata_for_existing_key(self, key):
            '''this is private API and should only
            be called from within ModelDataBase.
            Can othervise be destructive as it overwrites metadata!!!'''
            dumper = self._detect_dumper_string_of_existing_key(key)
            
            if dumper == 'self':
                time = 'unknown'
            else:
                time = os.stat(self._get_dumper_folder(key)).st_mtime
                time = datetime.datetime.utcfromtimestamp(time)
                time = tuple(time.timetuple())
            
            out = {'dumper': dumper, \
                   'time': time, \
                   'metadata_creation_time': 'post_hoc'}
            
            if VC.get_git_version()['dirty']:
                warnings.warn('The database source folder has uncommitted changes!')
            
            self._sql_metadata_backend[key] = out
    
    def _update_metadata_if_necessary(self):
        '''ckecks, wehter metadata is missing. Is so, it tries to estimate metadata, i.e. it sets the
        time based on the timestamp of the files. When metadata is created in that way,
        the field `metadata_creation_time` is set to `post_hoc`'''
        keys_in_mdb_without_metadata = set(self.keys()).difference(set(self.metadata.keys()))
        for key in keys_in_mdb_without_metadata:
            print("Updating metadata for key {key}".format(key = str(key)))
            self._write_metadata_for_existing_key(key)
               
    def __setitem__(self, key, item):
        '''items can be set using my_model_data_base[key] = item
        This saves the data with the default dumper.
        
        A more elaborate version of this function, which allows more 
        control on how the data is stored in the database is 
        ModelDataBase.setitem.'''
                
        self.setitem(key, item, dumper = None)

    def _robust_rmtree(self, key, path):
        try:
            print('start deleting {}'.format(path))
            shutil.rmtree(path)
        except OSError:
            print(('The folder ' + path + ' was registered as belonging to ' + \
                  str(key) + '. I tried to delete this folder, because the corresponding key was overwritten. ' + \
                  'Could not delete anything, because folder did not exist in the first place. I just carry on ...'))
        print('done deleting {}'.format(path))

            
    def __delitem__(self, key):
        '''items can be deleted using del my_model_data_base[key]'''
        dummy = self._sql_backend[key]
        if isinstance(dummy, LoaderWrapper):
            threading.Thread(target = lambda : self._robust_rmtree(key, os.path.join(self.basedir,dummy.relpath))).start()
        del self._sql_backend[key]
        self._delete_metadata(key)
    
    def _write_metadata_for_new_dumper(self, key, new_dumper):
        #update metadata
        if inspect.ismodule(new_dumper):
            dumper = LoaderDumper.get_dumper_string_by_dumper_module(new_dumper)
        elif isinstance(dumper, str):
            pass
                
        metadata = self.metadata[key]
        if not 'dumper_updates' in metadata:
            metadata['dumper_update'] = [{k: metadata[k] for k in ['dumper', 'time', 'module_versions']}]
        new_dumper = LoaderDumper.get_dumper_string_by_dumper_module(new_dumper)
        dumper_update = {'dumper': new_dumper,
               'time': tuple(datetime.datetime.utcnow().timetuple()),
               'conda_list': VC.get_conda_list(),
               'module_versions': VC.get_module_versions(),
               'history': VC.get_history(),
               'hostname': VC.get_hostname()}
        dumper_update.update(VC.get_git_version())

        metadata['dumper_update'].append(dumper_update)
        metadata['dumper'] = new_dumper
        
        self._sql_metadata_backend[key] = metadata
        
    def change_dumper(self, key, new_dumper, **kwargs):
        if VC.get_git_version()['dirty']:
            warnings.warn('The database source folder has uncommitted changes!')
                    
        if new_dumper == 'self':
            raise NotImplementedError()
        
        old_folder = self._get_savedir(key)
        item = self[key]
        self._setitem_no_metadata(key, item, new_dumper, **kwargs)
        if old_folder is not None:
            self._robust_rmtree(key, os.path.join(self.basedir, old_folder))
        
        #update metadata
        self._write_metadata_for_new_dumper(key, new_dumper)
        
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
        **kwargs: attributes, that get passed to ModelDataBase.setitem
        
        Example:
        #value is calculated, since it is the first call and not in the database
        mdb.maybe_calculate('knok_knok', lambda: 'whos there?', dumper = 'self')
        > 'whos there?'
        
        #value is taken from the database, since it is already stored
        mdb.maybe_calculate('knok_knok', lambda: 'whos there?', dumper = 'self')
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
            with get_progress_bar_function()():
                ret = fun()
                self.setitem(key, ret, **kwargs)
            return ret    
        
    def keys(self):
        '''returns the keys of the database'''
        return list(self._sql_backend.keys()) ###
    
    def get_readonly(self):
        '''returns a new ModelDataBase, which is readonly.
        
        Usecase: If you want to use the database for distributed computations, which only require
        loading in data, a readonoly database can speed things up as some checks can be ommitted'''
        return ModelDataBase(self.basedir, forceload = False, readonly = True, nocreate = True, forcecreate = False)

    def __reduce__(self):
        if isinstance(self._sql_backend, InMemoryBackend):
            self._sql_metadata_backend
            dict_ = {'_sql_backend':self._sql_backend, 
                     '_sql_metadata_backend': self._sql_metadata_backend, 
                     'metadata': self.metadata}
            return (self.__class__, (self.basedir, self.forceload, self.readonly, True), dict_)
        else:
            return (self.__class__, (self.basedir, self.forceload, self.readonly, True), {})
    
class RegisteredFolder(ModelDataBase):
    def __init__(self, path):
        ModelDataBase.__init__(self, path, forcecreate = True)
        self.setitem('self', None, dumper = just_create_folder)
        dumper = just_create_folder
        dumper.dump(None, path)
        self._sql_backend['self'] = LoaderWrapper('')
        self.setitem = None
        
    

from . import mdbopen
from . import _module_versions
from .IO import LoaderDumper

from .IO.LoaderDumper import just_create_folder
from .IO.LoaderDumper import just_create_mdb
from .IO.LoaderDumper import to_pickle
from .IO.LoaderDumper import to_cloudpickle
if six.PY3:
    from .IO.LoaderDumper import shared_numpy_store
                      
VC = _module_versions.version_cached

from . import model_data_base_register
# get_versions_cache = get_versions()
# module_versions_cache = _module_versions.get_module_versions()

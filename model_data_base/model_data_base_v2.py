import os
import string
import warnings
import json
import threading
import random
import shutil
import inspect
import datetime
import importlib
from .IO import LoaderDumper
from . import _module_versions
VC = _module_versions.version_cached

class MdbException(Exception):
    '''Typical mdb errors'''
    pass 

class MetadataAccessor:
    def __init__(self, mdb):
        self.mdb = mdb
        
    def __getitem__(self, key):
        dir_to_data = mdb._get_dir_to_data(key, check_exists = True)
        with open(os.path.join(dir_to_data, 'metadata.json')) as f:
            return json.load(f)
        
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
    with open('/gpfs/soma_fs/scratch/abast/testmdbv2/1/metadata.json') as f:
        dumper_string = json.load(f)['dumper']
    if return_ == 'string':
        return dumper_string
    elif return_ == 'module':
        return importlib.import_module("model_data_base.IO.LoaderDumper.{}".format(dumper_string))

class ModelDataBase:
    def __init__(self, basedir, readonly = False, nocreate = False):
        self.basedir = os.path.abspath(basedir)
        self.readonly = readonly
        self.nocreate = nocreate
        
        if not self._is_initialized():
            errstr = "Did not find a database in {path}. ".format(path = basedir) + \
                    "A new empty database will not be created since "+\
                    "{mode} is set to True."
            if nocreate:
                raise MdbException(errstr.format(mode = 'nocreate'))
            if readonly:
                raise MdbException(errstr.format(mode = 'readonly'))                
            self._initialize()
            
    def _is_initialized(self):
        return os.path.exists(os.path.join(self.basedir, 'mdb.json'))
    
    def _initialize(self):
        _check_working_dir_clean_for_build(self.basedir)
        os.makedirs(self.basedir, exist_ok = True)
        with open(os.path.join(self.basedir, 'mdb.json'), 'w'):
            pass
        
    def _check_key_format(self, key):
        assert(key != 'mdb.json')
    
        if len(key) > 50:
            raise ValueError('keys must be shorter than 50 characters')
        allowed_characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_1234567890'
        for c in key:
            if not c in allowed_characters:
                raise ValueError('Character {} is not allowed'.format(c))        
        
    def _get_dir_to_data(self, key, check_exists = False):
        self._check_key_format(key)
        dir_to_data = os.path.join(self.basedir, key)
        if check_exists:
            if not os.path.exists(dir_to_data):
                raise KeyError('Key {} is not set.'.format(key))
        return dir_to_data
    
    
    def get(self, key, lock = None, **kwargs):
        dir_to_data = self._get_dir_to_data(key, check_exists = True)
        # this looks into the metadat.json, gets the name of the dumper, and loads this module form IO.LoaderDumper
        loaderdumper_module = get_dumper_from_folder(dir_to_data)
        loader = loaderdumper_module.Loader()
        if lock:
            lock.acquire()
        return_ = loader.get(dir_to_data, **kwargs)
        if lock:
            lock.release()
        return return_
    
    def rename(self, old, new):
        dir_to_data_old = self._get_dir_to_data(old, check_exists = True)
        dir_to_data_new = self._get_dir_to_data(new)
        os.rename(old, new)

    def set(self, key, value, lock = None, dumper = None, **kwargs):
        assert(inspect.ismodule(dumper))
        dir_to_data = self._get_dir_to_data(key)
        if os.path.exists(dir_to_data):
            raise KeyError('Key {} is already set. Use del mdb[key] first.'.format(key))  
        else:
            os.makedirs(dir_to_data)
        loaderdumper_module = dumper
        if lock:
            lock.acquire()
        try:
            loaderdumper_module.dump(value, dir_to_data, **kwargs)
            self._write_metadata(dumper, dir_to_data, key)
        except Exception as e:
            print("An error occured. Tidy up. Please do not interrupt.")
            try:
                shutil.rmtree(dir_to_data)
            except:
                print('could not delete folder {:s}'.format(basedir_absolute))
            raise
        if lock:
            lock.release()
        
    def _write_metadata(self, dumper, dir_to_data, key):
        '''this is private API and should only
        be called from within ModelDataBase.
        Can othervise be destructive!!!'''        
        dumper_string = LoaderDumper.get_dumper_string_by_dumper_module(dumper)

        out = {'dumper': dumper_string,
               'time': tuple(datetime.datetime.utcnow().timetuple()), 
               'conda_list': VC.get_conda_list(),
               'module_versions': make_all_str(VC.get_module_versions()),
               'history': VC.get_history(),
               'hostname': VC.get_hostname()}

        out.update(VC.get_git_version())

        if VC.get_git_version()['dirty']:
            warnings.warn('The database source folder has uncommitted changes!')
            
        with open(os.path.join(dir_to_data, 'metadata.json'), 'w') as f:
            json.dump(out, f)
            
    def setitem(self, key, value, dumper = None, **kwargs):
        warnings.warn('setitem is deprecated. it exist to provide a consistent API with model_data_base version 1. use set instead.')
        self.set(key, value, dumper = dumper, **kwargs)
    
    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __delitem__(self, key):
        '''items can be deleted using del my_model_data_base[key]'''
        dir_to_data = self._get_dir_to_data(key, check_exists = True) 
        # rename folder to random folder
        N = 5
        while True:
            random_string = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))
            dir_to_data_rename = dir_to_data + '.deleting.' + random_string
            if not os.path.exists(dir_to_data_rename):
                break
        os.rename(dir_to_data, dir_to_data_rename)
        threading.Thread(target = lambda : shutil.rmtree(dir_to_data_rename)).start()
    
    def __reduce__(self):
        return (self.__class__, (self.basedir, self.readonly, True), {})
import os
import hashlib
import numpy as np
import logging
log = logging.getLogger(__name__)
import six
if six.PY3:
    from multiprocessing import shared_memory
else:
    log.warning("multiprocessing.shared_memory can not be imported in Python 2 (available in >=Py3.8)")
#from . import shared_memory_bugfixed as shared_memory
import tempfile
import shutil
import compatibility
import signal
import blosc

    
def shared_array_from_numpy(arr, name = None):
    '''takes an array in memory and puts it into shared memory'''    
    shm = shared_memory.SharedMemory(create=True, size=arr.nbytes, name = name)
    shm_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
    np.copyto(shm_arr, arr)
    return shm, shm_arr

def shared_array_from_disk(path, shape = None, dtype = None, name = None):
    '''loads an array saved to disk and puts it into shared memory'''
    shm = shared_memory.SharedMemory(create=True, size=np.prod(shape) * np.dtype(dtype).itemsize, name = name)
    shm_arr = np.ndarray(shape, dtype=dtype, buffer=shm.buf)    
    with open(path, 'rb') as f:
        f.readinto(shm.buf)
    return shm, shm_arr

def shared_array_from_shared_mem_name(fname, shape = None, dtype = None):
    '''loads an already shared array by its name'''
    shm = shared_memory.SharedMemory(name=fname)
    #unregister(fname, 'shared_memory')
    shm_arr = np.ndarray(shape, dtype, buffer=shm.buf)
    return shm, shm_arr

class Uninterruptible:
    def __enter__(self):
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        self.original_sigterm_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        signal.signal(signal.SIGINT, self.original_sigint_handler)
        signal.signal(signal.SIGTERM, self.original_sigterm_handler)

class SharedNumpyStore:
    def __init__(self, working_dir):
        """
        This class helps storing numpy arrays on disk and sharing them between processes.
        
        Warning: this doesn't have ways to reload data if it has changed on disk.
        
        Args:
            working_dir (str): The path of the working directory to store numpy arrays.
        """
        self.working_dir = working_dir
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        assert(not working_dir.endswith('/')) # ambiguity that would confuse the hash            
        self._suffix = hashlib.md5(working_dir.encode('utf-8')).hexdigest()[:8]
        self._shared_memory_buffers = {} # contains all already loaded buffers and arrays
        self._pending_renames = {}
        self.update()
    
    def update(self):
        """Update the list of files in the working directory."""
        self._files = {f.split('__')[0]: f for f in os.listdir(self.working_dir)}
    
    @staticmethod
    def _get_metadata_from_fname(fname):
        """
        returns name, shape, and dtype from a filename that follows the convention of NumpyStore
        """
        name  = fname.split('__')[0]
        shape = tuple(map(int, fname.split('__')[1].split('_')))
        dtype = fname.split('__')[2]
        return name, shape, dtype
    
    def _get_metadata_from_name(self, name):
        """
        returns fname, shape, and dtype from an array with 'name' saved in this instance of NumpyStore
        """ 
        if not name in self._files:
            self.update()
            if not name in self._files:
                raise ValueError("Array with name {} not found in the store.".format(name))

        _, shape, dtype = SharedNumpyStore._get_metadata_from_fname(self._files[name])
        return self._files[name], shape, dtype
    
    def get_expected_file_length(self, name):
        """
        Returns the expected length in bytes of a file given its metadata (shape and dtype).
        """
        _, shape, dtype = self._get_metadata_from_name(name)
        total_elements = np.prod(shape)
        element_size = np.dtype(dtype).itemsize
        file_length = total_elements * element_size
        return file_length
    
    def _get_fname_from_metadata(self, name, shape, dtype):
        '''
        for a given name, shape, and dtype, create a filename that follows the convention of NumpyStore
        '''
        fname = name + '__' + '_'.join(map(str, shape)) + '__' + str(dtype)
        return fname    
            
    def _get_fname(self, arr, name):
        '''
        for a given array and its name, create a filename that follows the convention of NumpyStore
        '''
        return self._get_fname_from_metadata(name, arr.shape, arr.dtype)
    
    def save(self, arr, name):
        """
        Save a numpy array to disk at the working_dir of this instance of NumpyStore.
        """
        assert(not '__' in name)
        fname = self._get_fname(arr, name)
        self._files[name] = fname        
        full_path = os.path.join(self.working_dir, fname)
        arr.tofile(full_path + '.saving')
        os.rename(full_path + '.saving', full_path)
            
    def flush(self):
        with Uninterruptible():       
            keys = list(self._pending_renames.keys())
            for fname in keys:
                name, new_fname = self._pending_renames[fname]
                print(fname, new_fname)
                os.rename( os.path.join(self.working_dir, fname), os.path.join(self.working_dir, new_fname))
                self._files[name] = new_fname                
                del self._pending_renames[fname]
                
    def close(self):
        """
        Close all shared memory objects and remove them from the dictionary.
        """
        for _, (shm, _) in self._shared_memory_buffers.items():
            shm.close()
            shm.unlink()
        self._shared_memory_buffers.clear()                

    def append_save(self, arr, name, autoflush = True):
        """
        Appends the given numpy array 'arr' to an existing array with the specified 'name'.
        """
        # created together with chatgpt
        
        # Check if the array with the given name exists in the store
        if not name in self._files:
            self.update()
            if not name in self._files:
                self.save(arr,name)
                
        # Get metadata (filename, shape, dtype) of the existing array
        fname, shape, dtype = self._get_metadata_from_name(name)
        existing_file_path = os.path.join(self.working_dir, fname)
        
        # Check if the dimensions are compatible for appending
        if len(shape) != len(arr.shape) or shape[1:] != arr.shape[1:]:
            raise ValueError("Incompatible dimensions for appending arrays.")
            
        # Compute the new shape for the combined array
        new_shape = (shape[0] + arr.shape[0],) + shape[1:]

        # Create a new filename for the combined array
        new_fname = self._get_fname_from_metadata(name, new_shape, dtype)

        # Compute the last byte written to the file
        last_byte_written = self.get_expected_file_length(name)    
        print('last_byte_written', last_byte_written)
        # Open the existing file in append mode and write the new array data
        assert(fname not in self._pending_renames)
        
        with open(existing_file_path, 'r+b') as f:
            f.seek(last_byte_written)
            arr.tofile(f)            
 
        # Update the filename with the new shape
        self._pending_renames[fname] = name, new_fname        
        if autoflush:
            self.flush()

    def load(self, name, load_from_disk = False):
        # if already loaded, return:
        if name in self._shared_memory_buffers:
            return self._shared_memory_buffers[name]
        # raises ValueError if array isn't stored here. If it is, get metadata
        fname, shape, dtype = self._get_metadata_from_name(name) 
        full_path = os.path.join(self.working_dir, fname)   
        try: # already put in shared mem by other process?
            self._shared_memory_buffers[name] = shared_array_from_shared_mem_name(fname + '__' + self._suffix, shape, dtype)
        except FileNotFoundError:  # no --> load it!
            if load_from_disk:
                self._shared_memory_buffers[name] = shared_array_from_disk(full_path, shape, dtype, fname + '__' + self._suffix)
            else:
                raise ValueError("The array exists, but is not loaded into shared memory yet. Set load_from_disk=True if you want to load it here.")
            
        return self._shared_memory_buffers[name]

from . import parent_classes

def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, None) 

class Loader(parent_classes.Loader):
    def get(self, savedir):
        return SharedNumpyStore(savedir)
    
def dump(obj, savedir):
    compatibility.cloudpickle_fun(Loader(), os.path.join(savedir, 'Loader.pickle'))

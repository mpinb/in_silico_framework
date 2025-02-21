"""Read and write numpy arrays to and from shared memory.

Shared memory is a memory space that is shared between multiple processes. 

Note:
    This module is speicalized for use with SLURM HPC systems.
    To use with other systems, set the JOB_SHMTMPDIR environment variable to a directory in shared memory.
"""

import os
import hashlib
import numpy as np
import logging

logger = logging.getLogger("ISF").getChild(__name__)
import tempfile
import shutil
import compatibility
import signal

import tempfile
import shutil
import compatibility
import signal

import six
if six.PY3:
    import _posixshmem
    import mmap
    _O_CREX = os.O_CREAT | os.O_EXCL
    _USE_POSIX = True

    class SharedMemory:
        """
        Modified from multiprocessing.shared_memory to work with SLURM HPC systems:
        
        - created in the shared memory SLURM directory specified in the ``JOB_SHMTMPDIR`` environment variable    
        - Adresses bug in https://bugs.python.org/issue39959 by not registering the shared memory object
        - Only supports named shared memory
        - and cleanup is left to slurm
        
        Only supports POSIX, not windows.

        Creates a new shared memory block or attaches to an existing
        shared memory block.

        Every shared memory block is assigned a unique name.  This enables
        one process to create a shared memory block with a particular name
        so that a different process can attach to that same shared memory
        block using that same name.

        As a resource for sharing data across processes, shared memory blocks
        may outlive the original process that created them.  When one process
        no longer needs access to a shared memory block that might still be
        needed by other processes, the close() method should be called.
        When a shared memory block is no longer needed by any process, the
        unlink() method should be called to ensure proper cleanup.
        
        
        Attributes:
            _buf (memoryview): A memoryview of the contents of the shared memory block.
            _name (str): Unique name that identifies the shared memory block.
            _size (int): Size in bytes of the shared memory block.
            _path (str): Path to the shared memory block on the disk.
            _fd (int): File descriptor of the shared memory block.
        """

        # Defaults; enables close() and unlink() to run without errors.
        _name = None
        _fd = -1
        _mmap = None
        _buf = None
        _flags = os.O_RDWR
        _mode = 0o600
        _prepend_leading_slash = True  # if _USE_POSIX else False

        def __init__(
            self,
            name=None,
            create=False,
            size=0,
            track_resource=False):
            """
            Args:
                name (str): Path to the shared memory block on the disk.
                create (bool): If True, create a new shared memory block. If False, attach to an existing shared memory block.
                size (int): Size in bytes of the shared memory block.
                track_resource (bool): If True, register the shared memory block with the resource tracker. If False, do not register the shared memory block with the resource tracker.
            """
            assert name is not None
            if not name[0] == '/':
                name = '/' + name

            if 'JOB_SHMTMPDIR' in os.environ:
                SHMDIR = os.environ['JOB_SHMTMPDIR']
                logging.log(500, SHMDIR)

                if not SHMDIR.startswith('/dev/shm'):
                    raise NotImplementedError()
                SHMDIR = SHMDIR[9:]
            else:
                raise RuntimeError(
                    'Shared memory not available. Set JOB_SHMTMPDIR environment variable'
                )

            if not size >= 0:
                raise ValueError("'size' must be a positive integer")
            if create:
                self._flags = _O_CREX | os.O_RDWR

            self._name = name
            self._path = name = SHMDIR + '/' + name  # if self._prepend_leading_slash else name
            self._fd = _posixshmem.shm_open(self._name,
                                            self._flags,
                                            mode=self._mode)
            try:
                if create and size:
                    os.ftruncate(self._fd, size)
                stats = os.fstat(self._fd)
                size = stats.st_size
                self._mmap = mmap.mmap(self._fd, size)
            except OSError:
                self.unlink()
                raise

            if track_resource:
                raise NotImplementedError()
            # from .resource_tracker import register
            # if create:
            #     register(self._name, "shared_memory")

            self._size = size
            self._buf = memoryview(self._mmap)

        def __del__(self):
            try:
                self.close()
            except OSError:
                pass

        def __reduce__(self):
            return (
                self.__class__,
                (
                    self.name,
                    False,
                    self.size,
                ),
            )

        def __repr__(self):
            return '{class_name}({name!r}, size={size})'.format(
                class_name=self.__class__.__name__,
                name=self.name,
                size=self.size)

        @property
        def buf(self):
            "A memoryview of contents of the shared memory block."
            return self._buf

        @property
        def name(self):
            "Unique name that identifies the shared memory block."
            reported_name = self._name
            if _USE_POSIX and self._prepend_leading_slash:
                if self._name.startswith("/"):
                    reported_name = self._name[1:]
            return reported_name

        @property
        def size(self):
            "Size in bytes."
            return self._size

        def close(self):
            """Closes access to the shared memory from this instance but does
            not destroy the shared memory block."""
            if self._buf is not None:
                self._buf.release()
                self._buf = None
            if self._mmap is not None:
                self._mmap.close()
                self._mmap = None
            if _USE_POSIX and self._fd >= 0:
                os.close(self._fd)
                self._fd = -1

        def unlink(self):
            """Requests that the underlying shared memory block be destroyed.

            In order to ensure proper cleanup of resources, unlink should be
            called once (and only once) across all processes which have access
            to the shared memory block."""
            # if _USE_POSIX and self._name:
            #from .resource_tracker import unregister
            _posixshmem.shm_unlink(self._path)
            #unregister(self._name, "shared_memory")
else:
    logger.warning(
        "multiprocessing.shared_memory can not be imported in Python 2 (available in >=Py3.8)"
    )
#from . import shared_memory_bugfixed as shared_memory


def shared_array_from_numpy(arr, name=None):
    '''Takes an array in memory and puts it into shared memory
    
    Args:
        arr (np.ndarray): The array to be put into shared memory.
        name (str, optional): The name of the shared memory block. Default: None.
        
    Returns:
        tuple: 
            A tuple containing the :py:class:`~data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedMemory`
            object and the shared memory array.
    '''
    shm = SharedMemory(create=True, size=arr.nbytes, name=name)
    shm_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
    np.copyto(shm_arr, arr)
    return shm, shm_arr


def _get_offset_and_size_in_bytes(start_row, end_row, shape, dtype):
    """Get the offset and size in bytes for a given ``start_row`` and ``end_row``.
    
    Rows here refer to the first dimension of a multi-dimensional array.
    
    Args:
        start_row (int): The starting row of the array.
        end_row (int): The ending row of the array.
        shape (tuple): The shape of the array. ``shape[0]`` is the number of rows.
        dtype (str): The data type of the array. Used to infer the size in bytes.
        
    Returns:
        tuple: A tuple containing the ``start_row``, ``end_row``, ``bytes_offset``, ``bytes_size``, and ``final_shape``.
    """
    if start_row is None:
        start_row = 0
    if end_row is None:
        end_row = shape[0]
    assert start_row <= end_row
    assert start_row >= 0
    assert end_row <= shape[0]
    final_shape = tuple([end_row - start_row] + list(shape[1:]))
    bytes_size = np.prod(final_shape) * np.dtype(dtype).itemsize
    bytes_offset = np.prod([start_row] + list(shape[1:])) * np.dtype(dtype).itemsize
    return start_row, end_row, bytes_offset, bytes_size, final_shape


def _check_filesize_matches_shape(path, shape, dtype):
    """Check whether the file size matches the expected size based on the shape and dtype.
    
    Args:
        path (str): Path to the file.
        shape (tuple): Shape of the array.
        dtype (str): Data type of the array.
        
    Raises:
        ValueError: If the file size does not match the expected size.
    """
    bytes_file = os.path.getsize(path)
    bytes_expected = np.prod(shape) * np.dtype(dtype).itemsize
    if bytes_file != bytes_expected:
        raise ValueError("File size doesn't match expected size")


def shared_array_from_disk(
    path,
    shape=None,
    dtype=None,
    name=None,
    start_row=None,
    end_row=None):
    '''Loads a numpy array from disk and puts it into shared memory
    
    Args:
        path (str): Path to the file on disk.
        shape (tuple, optional): Shape of the array.
        dtype (str, optional): Data type of the array.
        name (str, optional): 
            Name of the shared memory block. 
            To be passed to :py:class:`~data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedMemory` 
            Default: None.
        start_row (int, optional): The starting row of the array. Default: None.
        end_row (int, optional): The ending row of the array. Default: None.
        
    Returns:
        tuple: The :py:class:`~data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedMemory` object and the shared memory array.
    '''
    #_check_filesize_matches_shape(path, shape, dtype)
    start_row, end_row, bytes_offset, bytes_size, final_shape = _get_offset_and_size_in_bytes(
        start_row, end_row, shape, dtype)
    shm = SharedMemory(create=True, size=bytes_size, name=name)
    shm_arr = np.ndarray(final_shape, dtype=dtype, buffer=shm.buf)
    with open(path, 'rb') as f:
        f.seek(bytes_offset)
        # in principle nice, but does it work if the file is larger than the buffer, e.g. if end_row is somewhere in the middle of the file?
        # I tested and it works, but I didn't find anything in the docs that guarantees that behavior
        f.readinto(shm.buf)

        # alternative method, reads in the file in chunks and moves it to shared memory, much slower
        # chunk_size = 1_000_000_000  # or some other reasonable size, e.g., 1GB
        # offset = 0
        # while offset < len(shm.buf):
        #     read_size = min(chunk_size, len(shm.buf) - offset)
        #     chunk = f.read(read_size)
        #     shm.buf[offset:offset+read_size] = chunk
        #     offset += read_size
    return shm, shm_arr


def memmap_from_disk(
    path,
    shape=None,
    dtype=None,
    name=None,
    start_row=None,
    end_row=None):
    """Memory map a numpy array on disk.
    
    Create a numpy memory map from a file on disk. This allows for the array to be accessed without loading the entire array into memory.
    
    Args:
        path (str): Path to the file on disk.
        shape (tuple, optional): Shape of the array.
        dtype (str, optional): Data type of the array.
        name (str, optional): Name of the shared memory block. Default: None.
        start_row (int, optional): The starting row of the array. Default: None.
        end_row (int, optional): The ending row of the array. Default: None.
        
    Returns:
        np.memmap: A numpy memory map object.
        
    See also:
        https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
    """
    _check_filesize_matches_shape(path, shape, dtype)
    start_row, end_row, bytes_offset, bytes_size, final_shape = _get_offset_and_size_in_bytes(
        start_row, end_row, shape, dtype)
    arr = np.memmap(full_path,
                    dtype=np.dtype(dtype),
                    mode='r',
                    offset=bytes_offset,
                    shape=final_shape,
                    order='C')
    return arr


def shared_array_from_shared_mem_name(fname, shape=None, dtype=None):
    '''Loads an existing shared array by its name
    
    Args:
        fname (str): Name of the shared memory block.
        shape (tuple, optional): Shape of the array. Default: None.
        dtype (str, optional): Data type of the array. Default: None.
        
    Returns:
        tuple: The :py:class:`~data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedMemory` object and the shared memory array.
    '''
    shm = SharedMemory(name=fname)
    shm_arr = np.ndarray(shape, dtype, buffer=shm.buf)
    return shm, shm_arr


class Uninterruptible:
    """Context manager to create an uninterruptible section of code.
    
    This context manager temporarily ignores ``SIGINT`` and ``SIGTERM`` signals.
    
    Warning:
        This context manager should be used with caution, as it can lead to unresponsive code (by design).
    """
    def __enter__(self):
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        self.original_sigterm_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        signal.signal(signal.SIGINT, self.original_sigint_handler)
        signal.signal(signal.SIGTERM, self.original_sigterm_handler)


###############################################
# SharedNumpyStore objects are added to this list. Without it, the kernel dies if the shared memory object moves out of scope
# TODO: find a better way to handle this
sns_list = []
#################################################


class SharedNumpyStore:
    """Store numpy arrays on disk and share them between processes.
    
    This class is used to store numpy arrays on disk and share them between processes using shared memory.
    
    Warning:
        This class provides no way to reload data if it has changed on disk.
        

        
    Attributes:
        working_dir (str): The path of the working directory to store numpy arrays.
        _suffix (str): A unique suffix for the working directory.
        _shared_memory_buffers (dict): A dictionary containing all already loaded buffers and arrays.
        _pending_renames (dict): A dictionary containing all pending renames for files.
        _files (dict): A dictionary mapping array names to filepaths in shared memory.
    """
    def __init__(self, working_dir):
        """
        Args:
            working_dir (str): The path of the working directory to store numpy arrays.
        """
        self.working_dir = working_dir
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        assert not working_dir.endswith(
            '/')  # ambiguity that would confuse the hash
        self._suffix = hashlib.md5(working_dir.encode('utf-8')).hexdigest()[:8]
        self._shared_memory_buffers = {
        }  # contains all already loaded buffers and arrays
        self._pending_renames = {}
        self.update()
        sns_list.append(self)

    def update(self):
        """Update the list of files in the working directory."""
        self._files = {
            f.split('__')[0]: f for f in os.listdir(self.working_dir)
        }
        if 'Loader.pickle' in self._files:
            del self._files['Loader.pickle']

    @staticmethod
    def _get_metadata_from_fname(fname):
        """Get metadata from a filename that follows the convention of NumpyStore.
        
        Returns:
            tuple: the name, shape, and dtype from a filename that follows the convention of NumpyStore
        """
        name = fname.split('__')[0]
        shape = tuple(map(int, fname.split('__')[1].split('_')))
        dtype = fname.split('__')[2]
        return name, shape, dtype

    def _get_metadata_from_name(self, name):
        """Get metadata from a name that follows the convention of NumpyStore.
        
        Returns:
            tuple: the filename, shape, and dtype from an array with 'name' saved in this instance of NumpyStore
        """
        if not name in self._files:
            self.update()
            if not name in self._files:
                raise ValueError(
                    "Array with name {} not found in the store.".format(name))

        _, shape, dtype = SharedNumpyStore._get_metadata_from_fname(
            self._files[name])
        return self._files[name], shape, dtype

    def get_expected_file_length(self, name):
        """Get the expected length in bytes of a file given its metadata (shape and dtype).
        
        Args:
            name (str): The name of the array.
        
        Returns:
            int: the expected length in bytes of a file given its metadata (shape and dtype).
        """
        _, shape, dtype = self._get_metadata_from_name(name)
        total_elements = np.prod(shape)
        element_size = np.dtype(dtype).itemsize
        file_length = total_elements * element_size
        return file_length

    def _get_fname_from_metadata(self, name, shape, dtype):
        '''Get the filename from metadata.
        
        For a given name, shape, and dtype, create a filename that follows the convention of NumpyStore
        
        Args:
            name (str): the name of the array
            shape (tuple): the shape of the array
            dtype (str): the data type of the array
        
        Returns:
            str: the filename that follows the convention of NumpyStore
        '''
        fname = name + '__' + '_'.join(map(str, shape)) + '__' + str(dtype)
        return fname

    def _get_fname(self, arr, name):
        '''Get the filename of an array.
        
        For a given array and its name, create a filename that follows the convention of NumpyStore
        
        Args:
            arr (np.ndarray): the array
            name (str): the name of the array
        
        Returns:
            str: the filename that follows the convention of NumpyStore
        '''
        return self._get_fname_from_metadata(name, arr.shape, arr.dtype)

    def save(self, arr, name):
        """Save a numpy array to disk at the working_dir of this instance of NumpyStore.
        
        Args:
            arr (np.ndarray): The array to be saved.
            name (str): The name of the array.
            
        Warning:
            This method does not check if the array already exists in the store. If it does, it will be overwritten.
            
        Raises:
            AssertionError: If the name is reserved for a Database ``Loader``.
            AssertionError: If the name contains double underscores, which would throw off the NumpyStore convention.
        """
        assert name != 'Loader.pickle'  # reserved to model data base
        assert name != 'Loader.json'  # reserved to isf data base
        assert not '__' in name
        fname = self._get_fname(arr, name)
        self._files[name] = fname
        full_path = os.path.join(self.working_dir, fname)
        arr.tofile(full_path + '.saving')
        os.rename(full_path + '.saving', full_path)

    def flush(self):
        """Rename all files according to the new names in :paramref:`_pending_renames`.
        
        Deletes the old files and updates the :paramref:`_files` dictionary.
        """
        with Uninterruptible():
            keys = list(self._pending_renames.keys())
            for fname in keys:
                name, new_fname = self._pending_renames[fname]
                print(fname, new_fname)
                os.rename(os.path.join(self.working_dir, fname),
                          os.path.join(self.working_dir, new_fname))
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

    def append_save(self, arr, name, autoflush=True):
        """
        Appends the given numpy array :paramref:`arr` to an existing array with the specified :paramref:`name`.
        """
        assert name != 'Loader.pickle'  # reserved to model data base
        assert not '__' in name
        # created together with chatgpt

        # Check if the array with the given name exists in the store
        if not name in self._files:
            self.update()
            if not name in self._files:
                self.save(arr, name)
                return

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
        assert fname not in self._pending_renames

        with open(existing_file_path, 'r+b') as f:
            f.seek(last_byte_written)
            arr.tofile(f)

        # Update the filename with the new shape
        self._pending_renames[fname] = name, new_fname
        if autoflush:
            self.flush()

    def _update_name_to_account_for_start_row_end_row(
        self,
        name,
        start_row=None,
        end_row=None):
        """:skip-doc:"""
        return name
        # return name + '{}_{}'.format(start_row, end_row)

    def load(
        self,
        name,
        mode='shared_memory',
        start_row=None,
        end_row=None,
        allow_create_shm=False):
        '''Load an array from shared memory.
        
        Args:
            mode (str): 
                'memmap': memory map the file and return a numpy memmap object.
                'memory': load file into (not shared) memory and return a numpy array
                'shared_memory': access file in shared memory and return numpy array. 
            allow_create_shm (bool): only relevant in mode shared_memory. 
                If True, if the file on disk is not yet loaded into shared memory, load it.
                If False, requires that file already exists in shared memory. Use this e.g. in child processes 
                in which you want to be sure they don't create a new shared memory file. 
            start_row (int): first row from the array to load
            end_row (int): last row of the array to load
            
            Note: in shared_memory mode, for each call with different start_row or end_row parameters, a new independent 
                file is created.
        
        Returns:
            np.ndarray: the array
            
        Raises:
            ValueError: if mode is not one of 'memmap', 'memory', or 'shared_memory'
            
        Raises:
            AssertionError: if the file is not in shared memory yet and allow_create_shm is False
        '''

        fname, shape, dtype = self._get_metadata_from_name(name)
        start_row, end_row, bytes_offset, bytes_size, final_shape = _get_offset_and_size_in_bytes(
            start_row, end_row, shape, dtype)

        full_path = os.path.join(self.working_dir, fname)
        if mode == 'memmap':
            return np.memmap(full_path,
                             dtype=np.dtype(dtype),
                             mode='r',
                             offset=bytes_offset,
                             shape=final_shape,
                             order='C')
        elif mode == 'memory':
            assert bytes_size % np.dtype(dtype).itemsize == 0
            return np.fromfile(full_path,
                               offset=bytes_offset,
                               count=bytes_size // np.dtype(dtype).itemsize,
                               dtype=dtype).reshape(final_shape)
        elif 'shared_memory':
            # if already loaded, return:
            if name in self._shared_memory_buffers:
                return self._shared_memory_buffers[
                    name + '{}_{}'.format(start_row, end_row)][1]
            # if not, check if another process put it into shared memory already
            shared_mem_fname = fname + '__' + '{}_{}'.format(
                start_row, end_row
            ) + '__' + self._suffix  # the shared memory file known by the OS
            shared_mem_name = name + '__{}_{}'.format(
                start_row, end_row
            )  # the key used in the internal dictionaries to refer to the shared memory
            try:  # did another process put it into shared memory already?
                self._shared_memory_buffers[
                    shared_mem_name] = shared_array_from_shared_mem_name(
                        shared_mem_name, final_shape, dtype)
                return self._shared_memory_buffers[shared_mem_name][1]
            except FileNotFoundError as e:  # no
                if allow_create_shm:
                    self._shared_memory_buffers[
                        shared_mem_name] = shared_array_from_disk(
                            full_path,
                            shape,
                            dtype,
                            shared_mem_name,
                            start_row=start_row,
                            end_row=end_row)
                    return self._shared_memory_buffers[shared_mem_name][1]
                else:
                    raise ValueError(
                        "The array is not in shared memory yet. Set allow_create_shm to True to load the array into shared memory."
                    )
        else:
            raise ValueError("mode must be one of (memmap, memory, shared_memory)")


###############################
# model data base stuff
###############################

from . import parent_classes


def check(obj):
    """Check whether the object can be saved with this dumper.
    
    Args:
        obj (object): Object to be saved.
        
    Returns:
        bool: Whether the object is None. This dumper requires no object to be saved.
    """
    return isinstance(obj, None)


class Loader(parent_classes.Loader):
    """Loader for :py:class:`~data_base.isf_data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedNumpyStore` objects.
    """
    def get(self, savedir):
        """Load the shared numpy store from the specified folder."""
        return SharedNumpyStore(savedir)


def dump(obj, savedir):
    """Dump the shared numpy store in the specified directory.
    
    Args:
        obj (None, optional): No object is required. If an object is passed, it is ignored.
        savedir (str): Directory where the shared numpy store should be stored.
    
    Note:
        This method does not require the numpy arrays themselves.
        Rather, it saves a :py:class:`~data_base.isf_data_base.IO.LoaderDumper.shared_numpy_store.SharedNumpyStore` object,
        which can further be used to save and load numpy arrays to and from shared memory.
        
    See also:
        :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.numpy.npy` and :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.numpy.npz`
        for directly saving numpy arrays to disk (non-shared memory).
    """
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

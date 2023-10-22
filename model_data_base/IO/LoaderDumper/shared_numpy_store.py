import os
import hashlib
import numpy as np
import logging

log = logging.getLogger("ISF").getChild(__name__)
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
        Modified from multiprocessing/shared_memory.py
        - is by  created in the shared memory SLURM directory specified in the JOB_SHMTMPDIR environment variable    
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
        unlink() method should be called to ensure proper cleanup."""

        # Defaults; enables close() and unlink() to run without errors.
        _name = None
        _fd = -1
        _mmap = None
        _buf = None
        _flags = os.O_RDWR
        _mode = 0o600
        _prepend_leading_slash = True  # if _USE_POSIX else False

        def __init__(self,
                     name=None,
                     create=False,
                     size=0,
                     track_resource=False):
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
    log.warning(
        "multiprocessing.shared_memory can not be imported in Python 2 (available in >=Py3.8)"
    )
#from . import shared_memory_bugfixed as shared_memory


def shared_array_from_numpy(arr, name=None):
    '''takes an array in memory and puts it into shared memory'''
    shm = SharedMemory(create=True, size=arr.nbytes, name=name)
    shm_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
    np.copyto(shm_arr, arr)
    return shm, shm_arr


def _get_offset_and_size_in_bytes(start_row, end_row, shape, dtype):
    if start_row is None:
        start_row = 0
    if end_row is None:
        end_row = shape[0]
    assert start_row <= end_row
    assert start_row >= 0
    assert end_row <= shape[0]
    final_shape = tuple([end_row - start_row] + list(shape[1:]))
    bytes_size = np.prod(final_shape) * np.dtype(dtype).itemsize
    bytes_offset = np.prod([start_row] +
                           list(shape[1:])) * np.dtype(dtype).itemsize
    return start_row, end_row, bytes_offset, bytes_size, final_shape


def _check_filesize_matches_shape(path, shape, dtype):
    bytes_file = os.path.getsize(path)
    bytes_expected = np.prod(shape) * np.dtype(dtype).itemsize
    if bytes_file != bytes_expected:
        raise ValueError("File size doesn't match expected size")


def shared_array_from_disk(path,
                           shape=None,
                           dtype=None,
                           name=None,
                           start_row=None,
                           end_row=None):
    '''loads an array saved to disk and puts it into shared memory'''
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


def memmap_from_disk(path,
                     shape=None,
                     dtype=None,
                     name=None,
                     start_row=None,
                     end_row=None):
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
    '''loads an already shared array by its name'''
    shm = SharedMemory(name=fname)
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


###############################################
# SharedNumpyStore objects are added to this list. Without it, the kernel dies if the shared memory object moves out of scope
# TODO: find a better way to handle this
sns_list = []
#################################################


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
        """
        returns name, shape, and dtype from a filename that follows the convention of NumpyStore
        """
        name = fname.split('__')[0]
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
                raise ValueError(
                    "Array with name {} not found in the store.".format(name))

        _, shape, dtype = SharedNumpyStore._get_metadata_from_fname(
            self._files[name])
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
        assert name != 'Loader.pickle'  # reserved to model data base
        assert not '__' in name
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
        Appends the given numpy array 'arr' to an existing array with the specified 'name'.
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

    def _update_name_to_account_for_start_row_end_row(self,
                                                      name,
                                                      start_row=None,
                                                      end_row=None):
        return name
        # return name + '{}_{}'.format(start_row, end_row)

    def load(self,
             name,
             mode='shared_memory',
             start_row=None,
             end_row=None,
             allow_create_shm=False):
        '''Load array.
            mode: memmap: memory map the file and return a numpy memmap object.
                  memory: load file into (not shared) memory and return a numpy array
                  shared_memory: access file in shared memory and return numpy array. 
            allow_create_shm: only relevant in mode shared_memory. 
                If True, if the file on disk is not yet loaded into shared memory, load it.
                If False, requires that file already exists in shared memory. Use this e.g. in child processes 
                in which you want to be sure they don't create a new shared memory file. 
            start_row: first row from the array to load
            end_row: last row of the array to load
            
            Note: in shared_memory mode, for each call with different start_row or end_row parameters, a new independent 
                file is created.
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
            raise ValueError('mode must be')


###############################
# model data base stuff
###############################

from . import parent_classes


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, None)


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return SharedNumpyStore(savedir)


def dump(obj, savedir):
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))

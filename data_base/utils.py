# -*- coding: utf-8 -*-
# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""Database utility and convenience functions.
"""
import sys, os, time, random, string, warnings, six, cloudpickle, \
    contextlib, io, dask, distributed, tempfile, shutil, \
    signal, logging, threading, hashlib, collections, inspect, \
    json, functools
from six.moves.cPickle import PicklingError # this import format has potential issues (see six documentation) -rieke
from pathlib import Path
from copy import deepcopy
from six.moves import cPickle
import dask.dataframe as dd
import numpy as np
from collections import defaultdict
import pandas as pd
logger = logging.getLogger("ISF").getChild(__name__)


def chunkIt(seq, num):
    '''Splits :paramref:`seq` in :paramref:`num` lists, with approximately equal size.
    
    Args:
        seq (array): array to be split
        num (int): number of chunks
    
    See also:
        https://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    '''
    avg = len(seq) / float(num)
    out = []
    last = 0.0
    
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    
    return [o for o in out if o] #filter out empty lists

class silence_stdout():
    '''Silence stdout
    
    Can be used as context manager and decorator.
    
    See also:
        https://stackoverflow.com/a/2829036/5082048
    '''
    
    def __init__(self, fun = None):
        self.save_stdout = sys.stdout
        if fun is not None:
            return self(fun)
        
    def __enter__(self):
        logging.disable(logging.CRITICAL)
        sys.stdout = six.StringIO()
        
    def __exit__(self, *args, **kwargs):
        logging.disable(logging.NOTSET)
        sys.stdout = self.save_stdout
        
    def __call__(self, func):
        def wrapper(*args, **kwds):
            with self:
                return func(*args, **kwds)
        return wrapper
    
silence_stdout = silence_stdout()

class mkdtemp():
    '''Context manager for creating temporary directories
    
    Example:

        >>> with mkdtemp() as tempdir:
        ...     print(tempdir)
        ...     print(os.path.exists(tempdir))
        /pat/to/tmpdir
        True
        >>> os.path.exists(tempdir)
        False

    '''
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        return self.tempdir
    
    def __exit__(self, *args, **kwargs):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

def convertible_to_int(x):
    """Returns True if x can be converted to an integer, False otherwise
    
    Args:
        x (any): the object to be tested
        
    Returns:
        bool: True if x can be converted to an integer, False otherwise
    """
    try:
        int(x)
        return True
    except:
        return False
        
def split_file_to_buffers(f, split_str = '#'):
    '''Reads a file f and splits it wherever :paramref:`split_str` is found.
    
    Args:
        f (file): file to be split
        split_str (str): string to split the file. Default is '#'
    
    Returns:
        list: list of :py:class:`StringIO` Buffers.
    
    See also:
        adapted from http://stackoverflow.com/a/33346758/5082048'''
    stringios = [] 
    stringio = None
    for line in f:
        if line.startswith(split_str):
            if stringio is not None:
                stringio.seek(0)
                stringios.append(stringio)
            stringio = six.StringIO()
        stringio.write(line)
        stringio.write("\n")
    stringio.seek(0)
    stringios.append(stringio)
    return stringios

def first_line_to_key(stringios):
    '''Convert a list of StringIO objects to a dictionary.
    
    Takes a list io StringIO objects. Each should contain one table.
    It returns a dictionary conatining the first line as key (assuming it is the name of the table)
    and the rest of it as value
    
    Args:
        stringios (list): list of StringIO objects
        
    Returns:
        dict: dictionary with the first line as key and the rest as value
    '''
    out = {}
    value = None
    for s in stringios:
        for lv, line in enumerate(s):
            if lv == 0:
                name = line.strip()
                value = six.StringIO()
            else:
                value.write(line)
                value.write("\n")
        value.seek(0)
        out[name] = value
    return out

def pandas_to_array(pdf, x_component_fun, y_component_fun, value_fun):
    '''Convert a pandas dataframe, in which information is stored linearly to a 2D presentation.
    
    Args:
        pdf (pd.DataFrame): dataframe to be converted
        x_component_fun (function): function to extract the x component
        y_component_fun (function): function to extract the y component
        value_fun (function): function to extract the value
        
    Returns:
        pd.DataFrame: 2D representation of the data
    
    Example:
    
        >>> df
                'bla'
        x_1_y_1    10
        x_2_y_1    15
        x_3_y_1     7
        x_1_y_2     2
        x_2_y_2     0
        x_3_y_2    -1
    
        >>> pandas_to_array(
        ...    pdf, 
        ...    lambda index, values: index.split('_')[1],
        ...    lambda index, values: index.split('_')[-1],
        ...    lambda index, values: values.bla)
            1    2    3
        1    10   15    7
        2     2    0   -1
    '''
    out_dict = defaultdict(lambda: {})
    if isinstance(pdf, pd.DataFrame):
        iterator = pdf.iterrows()
    elif isinstance(pdf, pd.Series):
        iterator = pdf.iteritems()
    elif isinstance(pdf, dict):
        iterator = pd.Series(pdf).iteritems()
    for index, values in iterator:
        x = x_component_fun(index, values)
        y = y_component_fun(index, values)
        dummy = out_dict[x]
        assert y not in dummy
        dummy[y] = value_fun(index, values)
    
    return pd.DataFrame.from_dict(out_dict)

def select(df, **kwargs):
    """Selects rows from a dataframe based on the values of the columns
    
    Args:
        df (pd.DataFrame): the dataframe
        **kwargs: the columns and values to be selected
    
    Returns:
        pd.DataFrame: the dataframe with the selected rows
    """
    for kwarg in kwargs:
        df = df[df[kwarg] == kwargs[kwarg]]
    return df

def pooled_std(m, s, n):
    '''Calculates the pooled standard deviation out of samples.
    
    Args:
        m (array): means
        s (array): unbiased standard deviation (normalized by N-1)
        n (array): number of samples per group
        
    Returns:
        tuple: pooled mean and pooled standard deviation
    '''
    assert len(m) == len(s) == len(n) > 0
    M = np.dot(m,n) / float(sum(n))#[mm*nn / float(sum(n)) for mm, nn in zip(m,n)]
    # take carre of n = 0
    dummy = [(ss,mm,nn) for ss,mm,nn in zip(s,m,n) if nn >= 1]
    s,m,n = list(zip(*dummy)) 
    assert len(m) == len(s) == len(n) > 0
    #calculate SD
    s = [ss * np.sqrt((nn-1)/float(nn)) for ss,nn in zip(s,n)] # convert to biased estimator  
    var_tmp = np.dot(n, [ss**2 + mm**2 for ss, mm in zip(s,m)]) / np.array(n).sum() - (np.dot(m, n) / float(sum(n)))**2 # calculate variance
    SD = np.sqrt(var_tmp) * np.sqrt(sum(n) /float(sum(n)-1)) #convert to unbiased estimator 
    return M,SD

def skit(*funcs, **kwargs):
    '''Splits kwargs up to supply different functions with the right subset.
    
    Args:
        *funcs (function): functions to be supplied with the right subset of kwargs
        **kwargs: keyword arguments to be split up
    
    See also:
        Adapted from http://stackoverflow.com/a/23430335/5082048
    '''
    out = []
    for fun in funcs:
        out.append({key: value for key, value in six.iteritems(kwargs) 
                if key in fun.__code__.co_varnames})
        if 'kwargs' in fun.__code__.co_varnames:
            out[-1].update(kwargs)
        
    return tuple(out)

def unique(list_):
    """Get the unique elements of a list
    
    Args:
        list_ (list): the list
        
    Returns:
        list: the unique elements of the list
    """
    return list(pd.Series(list_).drop_duplicates())

def cache(function):
    """Decorator to cache the result of a function
    
    Args:
        function (function): the function to be cached
        
    Returns:
        function: the cached function
    """
    import hashlib
    memo = {}
    def get_key(*args, **kwargs):
        try:
            hash = hashlib.md5(cPickle.dumps([args, kwargs])).hexdigest()
        except (TypeError, AttributeError):
            hash = hashlib.md5(cloudpickle.dumps([args, kwargs])).hexdigest()
        return hash
    
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        key = get_key(*args, **kwargs)
        if key in memo:
            return memo[key]
        else:
            rv = function(*args, **kwargs)
            memo[key] = rv
            return rv
    return wrapper

def fancy_dict_compare(dict_1, dict_2, dict_1_name = 'd1', dict_2_name = 'd2', path=""):
    """Compare two dictionaries recursively to find non-matching elements

    Args:
        dict_1 (dict): dictionary 1
        dict_2 (dict): dictionary 2

    Returns:
        str: a string containing the differences
    """
    # https://stackoverflow.com/a/35065035/5082048
    err = ''
    key_err = ''
    value_err = ''
    old_path = path
    for k in list(dict_1.keys()):
        path = old_path + "[%s]" % k
        if k not in dict_2:
            key_err += "Key %s%s not in %s\n" % (dict_2_name, path, dict_2_name)
        else:
            if isinstance(dict_1[k], dict) and isinstance(dict_2[k], dict):
                err += fancy_dict_compare(dict_1[k],dict_2[k],'d1','d2', path)
            else:
                if dict_1[k] != dict_2[k]:
                    value_err += "Value of %s%s (%s) not same as %s%s (%s)\n"\
                        % (dict_1_name, path, dict_1[k], dict_2_name, path, dict_2[k])

    for k in list(dict_2.keys()):
        path = old_path + "[%s]" % k
        if k not in dict_1:
            key_err += "Key %s%s not in %s\n" % (dict_2_name, path, dict_1_name)

    return key_err + value_err + err

def wait_until_key_removed(db, key, delay = 5):
    """Wait until a key is removed from a database.
    
    This function checks every :paramref:`delay` seconds if the key is still in the database.
    Useful for waiting until a process has finished.
    
    Args:
        db (sqlitedict): the database
        key (str): the key
        delay (int): the delay between checks
        
    Returns:
        None
    """
    already_printed = False
    while True:
        if key in list(db.keys()):
            if not already_printed:
                print(("waiting till key {} is removed from the database. I will check every {} seconds.".format(key, delay)))
                already_printed = True				
            time.sleep(5)
        else:
            if already_printed:
                print(("Key {} has been removed. Continuing.".format(key)))
            return
        
def get_file_or_folder_that_startswith(path, startswith):
    """Get the file or folder in a directory that starts with a certain string
    
    Args:
        path (str): the path
        startswith (str): the string
        
    Returns:
        str: the file or folder
    """
    paths = [p for p in os.listdir(path) if p.startswith(startswith)]
    assert len(paths) == 1
    return os.path.join(path,paths[0])

def get_file_or_folder_that_endswith(path, endswith):
    """Get the file or folder in a directory that ends with a certain string
    
    Args:
        path (str): the path
        endswith (str): the string
        
    Returns:
        str: the file or folder
    """
    paths = [p for p in os.listdir(path) if p.endswith(endswith)]
    assert len(paths) == 1
    return os.path.join(path,paths[0])


class DelayedKeyboardInterrupt(object):
    '''Context manager that allows to delay a KeyboardInterrupt such that it also works in subthreads.
    
    If a KeyboardInterrupt is received while code is still running within this context manager, 
    the KeyboardInterrupt is intercepted by this class and delayed until the context manager is exited.
    
    The usecase is to allow for subthreads to finish their work before the KeyboardInterrupt is raised.
    
    Example:
    
        >>> with DelayedKeyboardInterrupt():
        ...     time.sleep(10)   # press Ctrl+C here, after <10s
        ...     print("I am finished after 10 seconds")
        I am finished after 10 seconds
    
    See also:
        https://stackoverflow.com/questions/842557/how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py
    '''
    def __enter__(self):
        self.signal_received = False
        self.we_are_in_main_thread = True
        try:
            self.old_handler = signal.signal(signal.SIGINT, self.handler)
        except ValueError:
            self.we_are_in_main_thread = False

    def handler(self, sig, frame):
        """Handle KeyboardInterrupt signals and delay them
        """
        self.signal_received = (sig, frame)
        logging.debug('SIGINT received. Delaying KeyboardInterrupt.')

    def __exit__(self, type, value, traceback):
        if self.we_are_in_main_thread:
            signal.signal(signal.SIGINT, self.old_handler)
            if self.signal_received:
                self.old_handler(*self.signal_received)

def flatten(l):
    '''Flatten a nested list
    
    Args:
        l (list): the list
        
    Yields:
        any: the elements of the list
    
    See also:
        https://stackoverflow.com/a/2158532/5082048'''
    import collections
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, six.string_types): # not sure about syntax here - rieke
            for sub in flatten(el):
                yield sub
        else:
            yield el
            
###########################
# this version does not leave behind a file but serialization takes a long time
##########################

#@dask.delayed
#def _synchronous_ddf_concat(ddf_delayeds, meta): 
#    with warnings.catch_warnings():
#        warnings.filterwarnings('ignore')
#        ddf_delayeds = cloudpickle.loads(ddf_delayeds)
#        ddf = dd.from_delayed(ddf_delayeds, meta = meta)
#        dask_options = dask.context._globals
#        pdf = ddf.compute(scheduler="synchronous")
#        dask.context._globals = dask_options
#        return pdf


#def myrepartition(ddf, n, path = None):
#    '''This repartitions without generating more tasks'''
#    divisions = ddf.divisions
#    meta = ddf._meta
#    delayeds = ddf.to_delayed()
#    divisions_unknown = any(d is None for d in ddf.divisions)
#    if divisions_unknown:
#        chunks_delayeds = chunkIt(delayeds, n)
#        delayeds = [_synchronous_ddf_concat(cloudpickle.dumps(c), meta) for lv, c in enumerate(chunks_delayeds)]
#        return dd.from_delayed(delayeds, meta = meta)
#    else:
#        assert len(divisions) - 1 == len(delayeds)
#        chunks_divisions = chunkIt(divisions[:-1], n)
#        chunks_delayeds = chunkIt(delayeds, n)
#        divisions = [c[0] for c in chunks_divisions] + [chunks_divisions[-1][-1]]
#        delayeds = [_synchronous_ddf_concat(cloudpickle.dumps(c), meta) for lv, c in enumerate(chunks_delayeds)]
#        assert len(divisions) - 1 == len(delayeds)
#        return dd.from_delayed(delayeds, meta = meta, divisions = divisions)


###############################
# this version is not nice ... it leaves behind a file
# but it showed by far the best performance for dataframes with hundreds of thousands of partitions
################################

@dask.delayed
def synchronous_ddf_concat(ddf_path, meta, N, n, scheduler=None):
    """Concatenate a pickles dask dataframe to a pandas dataframe.
    
    Args:
        ddf_path (str): path to the dask dataframe
        meta (pd.DataFrame): the metadata for the dask dataframe.
        N (int): number of chunks
        n (int): the chunk to be concatenated
        scheduler (str): the scheduler to be used
        
    Returns:
        pd.DataFrame: the concatenated dataframe
    """
    with open(ddf_path, 'rb') as f:
        ddf = cloudpickle.load(f)
    delayeds = ddf.to_delayed()
    chunks_delayeds = chunkIt(delayeds, N)
    chunk = chunks_delayeds[n]
    ddf = dd.from_delayed(chunk, meta = meta)
    dask_options = dask.context._globals
    pdf = ddf.compute(scheduler="synchronous")
    dask.context._globals = dask_options
    return pdf

def myrepartition(ddf, N):
    '''Repartition a dask dataframe without generating more tasks.
    
    Args:
        ddf (dask.DataFrame): the dataframe to be repartitioned
        N (int): the number of partitions
        
    Returns:
        dask.DataFrame: the repartitioned dataframe
    '''
    folder = tempfile.mkdtemp()
    ddf_path = os.path.join(folder, 'ddf.cloudpickle.dump')
    with open(ddf_path, 'wb') as f:
        cloudpickle.dump(ddf, f)

    divisions = ddf.divisions
    meta = ddf._meta
    delayeds = ddf.to_delayed()
    divisions_unknown = any(d is None for d in ddf.divisions)

    if divisions_unknown:
        chunks_delayeds = chunkIt(delayeds, N)
        delayeds = [synchronous_ddf_concat(ddf_path, meta, N, n) for n in range(N)]
        return dd.from_delayed(delayeds, meta = meta)
    else:
        assert len(divisions) - 1 == len(delayeds)
        chunks_divisions = chunkIt(divisions[:-1], N)
        divisions = [c[0] for c in chunks_divisions] + [chunks_divisions[-1][-1]]
        delayeds = [synchronous_ddf_concat(ddf_path, meta, N, n) for n in range(N)]
        assert len(divisions) - 1 == len(delayeds)
        return dd.from_delayed(delayeds, meta = meta, divisions = divisions)
    
def df_colnames_to_str(df):
    """Convert the column names and index names of a dataframe to string.
    
    Useful for dumping using the pandas_to_parquet dumper, or dask_to_parquet dumper.
    Warning: This overwrites the original object. This is preferred over the overhead of creating a copy on every write.

    Args:
        df (pd.DataFrame | dask.DataFrame): a DataFrame

    Returns:
        df (pd.DataFrame | dask.DataFrame): the same dataframe, but with string type column and index names.
    """
    if not all([type(e) == str for e in df.columns]):
        logger.warning("Converting the following column names to string for saving with parquet: {}".format(df.columns))
        df.columns = df.columns.astype(str)
    if df.index.name is not None:
        if not type(df.index.name) == str:
            logger.warning("Converting the following index name to string for saving with parquet: {}".format(df.index.name))
            df.index.name = str(df.index.name)
    return df

def colorize_key(key):
    """Colorizes a key based on its type.
    
    The key is colorized green if it is a database, blue if it is a subdatabase, and black otherwise.
    
    Args:
        key (pathlib.Path): the key
        
    Returns:
        str: the colorized key
        
    See also:
        :py:meth:`data_base.utils.colorize`
    """
    if is_db(key.absolute()):
        c = bcolors.OKGREEN
    elif any([Path.exists(key/e) for e in ('Loader.json', 'Loader.pickle')]):
        c = bcolors.OKBLUE
    else:
        c = ""
    return c + key.name + bcolors.ENDC

def colorize_str(key, bcolor):
    """Colorize a string with a terminal color.
    
    Simply concatenates the string with escape sequences that colroize the text in a terminal.
    
    Args:
        key (str): the string
        bcolor (str): the color
        
    Returns:
        str: the colorized string
    
    See also:
        :py:class:`data_base.utils.bcolors` For color escape sequences.
    """
    return bcolor + key + bcolors.ENDC
        

def calc_recursive_filetree(
    db, root_dir_path, max_lines=30,
    depth=0, max_depth=2, max_lines_per_key=3,
    lines=None, indent=None, all_files=False, colorize=True):
    """
    Fetches the contents of an db and formats them as a string representing a tree structure

    Args:
        db (data_base.data_base.DataNase): The database to be visualized
        root_dir_path (str): The path to the root directory
        max_depth (int): Maximum depth to recurse into the directory tree
        max_lines (int): Maximum number of lines to print. Default is 30.
        max_lines_per_key (int): Maximum number of lines per key. Default is 3.
        lines (list): List of strings to append to during recursion. Default is ``None``.
        all_files (bool): If True, all files are shown (including e.g. /db subfolders). If False, only files that are keys in the database are shown. Default is ``False``.
        colorize (bool): If True, colorizes the keys. Default is ``True``.
        
    Returns:
        list: The formatted tree structure as a list of strings.
    """
    recursion_kwargs = locals()
    
    if colorize == False:
        _colorize_key = lambda x: x.name
    else:
        _colorize_key = colorize_key
    
    if colorize == False:
        _colorize_key = lambda x: x.name
    else:
        _colorize_key = colorize_key
    lines = [] if lines is None else lines
    indent = "" if indent is None else indent
    tee = '├── '
    last = '└── '
    listd = [e for e in root_dir_path.iterdir()]
    if not all_files:
        listd = [e for e in listd if e.name in db.keys() or e.name == "db"]

    for i, element in enumerate(listd):
        # stop iteration if max lines per key is reached
        if i == max_lines_per_key and depth:
            lines = lines[:-1]
            lines.append(indent + '... ({} more)'.format(len(listd)-max_lines_per_key+1))
            return lines
        # stop iteration if max lines is reached
        if len(lines) >= max_lines:
            lines.append(indent + '... ({} more)'.format(len(listd)-i))
            return lines
        
        # format the strings
        prefix = indent + last if i == len(listd)-1 else indent + tee

        if not element.is_dir():  # not a directory: just add the file
            lines.append(prefix + _colorize_key(element))
        elif depth >= max_depth:
            # directory at max depth: add, but don't recurse deeper
            colored_key = _colorize_key(element)
            colored_key = str(colored_key + os.sep + '...') if Path.exists(element/'db') else element.name
            lines.append(prefix + colored_key)
        else:
            # Directory: recurse deeper
            recursion_kwargs_next_iter = recursion_kwargs  # adapt kwargs for recursion
            lines.append(prefix + _colorize_key(element))
            recursion_kwargs_next_iter['depth'] += 1  # Recursion index
            recursion_kwargs_next_iter['indent'] = indent + '    ' if i == len(listd)-1 else indent + '│   '
            recursion_kwargs_next_iter['root_dir_path'] = element
            recursion_kwargs_next_iter['lines'] = lines
            if Path.exists(element/'db') and not all_files:
                # subdb: recurse deeper without adding 'db' as key
                # (only add 'db' if all_files=True)
                recursion_kwargs_next_iter['db'] = db.get(element.name, readonly=True)
                recursion_kwargs_next_iter['root_dir_path'] = Path(recursion_kwargs_next_iter['db'].basedir)
            lines = calc_recursive_filetree(**recursion_kwargs_next_iter)
            
    return lines

class bcolors:
    """
    List of colors for terminal output in bash.
    
    Attributes:
        HEADER (str): Header color
        OKBLUE (str): Blue color
        OKCYAN (str): Cyan color
        OKGREEN (str): Green color
        WARNING (str): Warning color
        FAIL (str): Fail color
        ENDC (str): End color (reset)
        BOLD (str): Bold
        UNDERLINE (str): Underline
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def rename_for_deletion(key):
    """Renames some key to indicate it's in the process of being deleted.

    Args:
        key (pathlib.Path): The key

    Returns:
        pathlib.Path: The renamed key
    """
    N = 5
    while True:
        random_string = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))
        key_to_delete = Path(str(key) + '.deleting.' + random_string)
        if not key_to_delete.exists():
            break
    Path(key).rename(key_to_delete)
    return key_to_delete

def delete_in_background(key):
    """Starts a background process that deletes a key

    Args:
        key (pathlib.Path): The key to be deleted

    Returns:
        threading.Thread: The process that takes care of deletion
    """
    if not key.exists():
        logging.warning("Cannot delete key {}. Path {} does not exist".format(key.name, key))
        return None
    key_to_delete = rename_for_deletion(key)
    p = threading.Thread(target = lambda : shutil.rmtree(str(key_to_delete))).start()
    return p

def is_db(dir_to_data):
    '''Check if a path is a :py:class:`~data_base.data_base.DataBase`.
    
    Args:
        dir_to_data (pathlib.Path): The path to the directory
    
    Returns:
        bool: ``True`` if :paramref:`dir_to_data` is a (sub)db, ``False`` otherwise.
    '''
    can_exist = [
        'db_state.json', 
        'db',
        'sqlitedict.db',  # for backwards compatibility
        ]
    return any([Path.exists(dir_to_data/e) for e in can_exist]) or \
         any([Path.exists(dir_to_data/'db'/e) for e in can_exist]) or \
            any([Path.exists(dir_to_data/'mdb'/e) for e in can_exist])

import sys, os, time
import warnings
import six
from six.moves.cPickle import PicklingError # this import format has potential issues (see six documentation) -rieke
import cloudpickle
import contextlib
import io
import dask.dataframe as dd
import dask
import pandas as pd
import numpy as np
import distributed
import six
from six.moves import cPickle


def chunkIt(seq, num):
    '''splits seq in num lists, which have approximately equal size.
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
    '''Silences stdout. Can be used as context manager and decorator.
    https://stackoverflow.com/a/2829036/5082048
    '''
    
    def __init__(self, fun = None):
        self.save_stdout = sys.stdout
        if fun is not None:
            return self(fun)
        
    def __enter__(self):
        sys.stdout = six.StringIO()
        
    def __exit__(self, *args, **kwargs):
        sys.stdout = self.save_stdout
        
    def __call__(self, func):
        def wrapper(*args, **kwds):
            with self:
                return func(*args, **kwds)
        return wrapper
    
silence_stdout = silence_stdout()


import tempfile
import shutil

class mkdtemp():
    '''context manager creating a temporary folder'''
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        return self.tempdir
    
    def __exit__(self, *args, **kwargs):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

def convertible_to_int(x):
        try:
            int(x)
            return True
        except:
            return False
        
def split_file_to_buffers(f, split_str = '#'):
    '''reads a file f and splits it, whenever "split_str" is found.
    Returns a list of StringIO Buffers.
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
    '''takes a list io StringIO objects. Each should contain one table.
    It returns a dictionary conatining the first line as key (assuming it is the name of the table)
    and the rest of it as value'''
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

from collections import defaultdict
import pandas as pd

def pandas_to_array(pdf, x_component_fun, y_component_fun, value_fun):
    '''this can convert a pandas dataframe, in which information
    is stored linearly to a 2D presentation.
    
    Example: you have a dataframe like:
               'bla'
    
    x_1_y_1    10
    x_2_y_1    15
    x_3_y_1    7
    x_1_y_2    2
    x_2_y_2    0
    x_3_y_2   -1
    
    Ans it should be converted to:
           1    2    3
    
    1      10   15   7
    2      2    0    -1
    3
    
    You can use:
    pandas_to_array(pdf, lambda index, values: index.split('_')[1], \
                         lambda index, values: index.split('_')[-1], \
                         lambda index, values: values.bla)
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
        assert(y not in dummy)
        dummy[y] = value_fun(index, values)
    
    return pd.DataFrame.from_dict(out_dict)

def select(df, **kwargs):
    for kwarg in kwargs:
        df = df[df[kwarg] == kwargs[kwarg]]
    return df

import numpy as np
def pooled_std(m, s, n):
    '''calculates the pooled standard deviation out of samples.
    
    m: means
    s: unbiased standarddeviation (normalized by N-1)
    n: number of samples per group
    
    returns: pooled mean, pooled std
    '''
    assert(len(m) == len(s) == len(n) > 0)
    M = np.dot(m,n) / float(sum(n))#[mm*nn / float(sum(n)) for mm, nn in zip(m,n)]
    # take carre of n = 0
    dummy = [(ss,mm,nn) for ss,mm,nn in zip(s,m,n) if nn >= 1]
    s,m,n = list(zip(*dummy)) 
    assert(len(m) == len(s) == len(n) > 0)
    #calculate SD
    s = [ss * np.sqrt((nn-1)/float(nn)) for ss,nn in zip(s,n)] # convert to biased estimator  
    var_tmp = np.dot(n, [ss**2 + mm**2 for ss, mm in zip(s,m)]) / np.array(n).sum() - (np.dot(m, n) / float(sum(n)))**2 # calculate variance
    SD = np.sqrt(var_tmp) * np.sqrt(sum(n) /float(sum(n)-1)) #convert to unbiased estimator 
    return M,SD

def skit(*funcs, **kwargs):
    '''splits kwargs up to supply different functions with the right subset
    adapted from http://stackoverflow.com/a/23430335/5082048
    '''
    out = []
    for fun in funcs:
        out.append({key: value for key, value in six.iteritems(kwargs) 
                if key in fun.__code__.co_varnames})
        if 'kwargs' in fun.__code__.co_varnames:
            out[-1].update(kwargs)
        
    return tuple(out)

def unique(list_):
    return list(pd.Series(list_).drop_duplicates())

def cache(function):
    import hashlib
    memo = {}
    def get_key(*args, **kwargs):
        try:
            hash = hashlib.md5(cPickle.dumps([args, kwargs])).hexdigest()
        except (TypeError, AttributeError):
            hash = hashlib.md5(cloudpickle.dumps([args, kwargs])).hexdigest()
        return hash
    
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
    """Compare two dictionaries recursively to find non mathcing elements

    Args:
        dict_1: dictionary 1
        dict_2: dictionary 2

    Returns:

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

def wait_until_key_removed(mdb, key, delay = 5):
    already_printed = False
    while True:
        if key in list(mdb.keys()):
            if not already_printed:
                print(("waiting till key {} is removed from the database. I will check every {} seconds.".format(key, delay)))
                already_printed = True				
            time.sleep(5)
        else:
            if already_printed:
                print(("Key {} has been removed. Continuing.".format(key)))
            return
        
def get_file_or_folder_that_startswith(path, startswith):
    paths = [p for p in os.listdir(path) if p.startswith(startswith)]
    assert len(paths) == 1
    return os.path.join(path,paths[0])

def get_file_or_folder_that_endswith(path, endswith):
    paths = [p for p in os.listdir(path) if p.endswith(endswith)]
    assert len(paths) == 1
    return os.path.join(path,paths[0])

import signal
import logging

# see https://stackoverflow.com/questions/842557/how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py
class DelayedKeyboardInterrupt(object):
    '''context manager, that allows to delay a KeyboardInterrupt
    extended, such that it also works in subthreads.'''
    def __enter__(self):
        self.signal_received = False
        self.we_are_in_main_thread = True
        try:
            self.old_handler = signal.signal(signal.SIGINT, self.handler)
        except ValueError:
            self.we_are_in_main_thread = False

    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        logging.debug('SIGINT received. Delaying KeyboardInterrupt.')

    def __exit__(self, type, value, traceback):
        if self.we_are_in_main_thread:
            signal.signal(signal.SIGINT, self.old_handler)
            if self.signal_received:
                self.old_handler(*self.signal_received)

def flatten(l):
    '''https://stackoverflow.com/a/2158532/5082048'''
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
#        pdf = ddf.compute(get = dask.get)
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
#        assert(len(divisions) - 1 == len(delayeds))
#        chunks_divisions = chunkIt(divisions[:-1], n)
#        chunks_delayeds = chunkIt(delayeds, n)
#        divisions = [c[0] for c in chunks_divisions] + [chunks_divisions[-1][-1]]
#        delayeds = [_synchronous_ddf_concat(cloudpickle.dumps(c), meta) for lv, c in enumerate(chunks_delayeds)]
#        assert(len(divisions) - 1 == len(delayeds))
#        return dd.from_delayed(delayeds, meta = meta, divisions = divisions)


###############################
# this version is not nice ... it leaves behind a file
# but it showed by far the best performance for dataframes with hundreds of thousands of partitions
################################

@dask.delayed
def synchronous_ddf_concat(ddf_path, meta, N, n):    
    with open(ddf_path, 'rb') as f:
        ddf = cloudpickle.load(f)
    delayeds = ddf.to_delayed()
    chunks_delayeds = chunkIt(delayeds, N)
    chunk = chunks_delayeds[n]
    ddf = dd.from_delayed(chunk, meta = meta)
    dask_options = dask.context._globals
    pdf = ddf.compute(get = dask.get)
    dask.context._globals = dask_options
    return pdf

def myrepartition(ddf, N):
    '''This repartitions without generating more tasks'''
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
        assert(len(divisions) - 1 == len(delayeds))
        chunks_divisions = chunkIt(divisions[:-1], N)
        divisions = [c[0] for c in chunks_divisions] + [chunks_divisions[-1][-1]]
        delayeds = [synchronous_ddf_concat(ddf_path, meta, N, n) for n in range(N)]
        assert(len(divisions) - 1 == len(delayeds))
        return dd.from_delayed(delayeds, meta = meta, divisions = divisions)
    


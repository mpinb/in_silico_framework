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
r"""Save and load dask dataframes to msgpack with categorical columns.

This dumper is designed for dataframes with the following properties:

- The index is str
- The columns have a lot of repetitive values, so they can be grouped.
 
If the number of partitions is very large (>10000), it will repartition the 
dataframe to 5000 partitions. 
Loading such a dataframe is normaly possible within 1 second.

Before saving, all str-columns will be converted to ``pd.Categorical``s
In each respective partition, if the part of unique values in the respective column is <= 20%. The original datatype
will be restored if the dataframe is loaded. 
This therefore only serves as optimization to increase loading speed and reduce network traffic for suitable dataframes. 
Suitable dataframes are for example the :ref:`syn_activation_format` dataframe.

This uses a fork of the original `pandas_to_msgpack` package, `available on PyPI <https://pypi.org/project/isf-pandas-msgpack/>`_
"""

import os, yaml
import cloudpickle
import dask.dataframe as dd
import dask.delayed
import dask
import pandas as pd
from . import parent_classes
import glob
from data_base.utils import chunkIt, myrepartition, convertible_to_int 
import six
import numpy as np
from isf_pandas_msgpack import to_msgpack, read_msgpack
import json
from .utils import save_object_meta

####
# if you want to use this as template to implement another dask dumper:
# lines that most likely need to be changed are marked with ###
####
############################
# custom methods to categorize and entcategorize a dataframe:
############################
def str_to_category(pdf):
    '''careful: changes pdf!'''
    for c in pdf.columns:
        if pdf[c].dtype == 'object':
            pdf[c] = pdf[c].astype('category')
    if pdf.index.dtype == 'object':
        index_name = pdf.index.name
        pdf.index = pd.Categorical(pdf.index, ordered=False)
        pdf.index.name = index_name


def category_to_str(pdf):
    '''careful: changes pdf!'''
    if six.PY3: # when loading data saved in py2 within py3
        columns = [c.decode('utf-8') if isinstance(c, bytes) else c for c in pdf.columns]
        index = [i.decode('utf-8') if isinstance(i, bytes) else i for i in pdf.index]
        index_names = [i.decode('utf-8') if isinstance(i, bytes) else i for i in pdf.index.names]
        pdf.index = index
        pdf.columns = columns
        pdf.index.names = index_names
        for name, value in pdf.iloc[0].iteritems():
            if isinstance(value, bytes):
                pdf[name] = pdf[name].str.decode('utf-8')
    for c in pdf.select_dtypes(include=['category']).columns:
        pdf[c] = pdf[c].astype('object')  #map(str)#astype('object')
    if str(pdf.index.dtype) == 'category':
        pdf.index = pdf.index.astype('object')  #map(str)
    return pdf


####################################################
# custom to_csv method, because the one of dask does eat all the memory
# this method has to the aim to be as simple as possible
#####################################################
def get_writer_function(categorize):
    '''returns function, that stores pandas dataframe'''

    def ddf_save_chunks(pdf, path, number, digits):
        if categorize:
            str_to_category(pdf)
        #  pdf.to_msgpack(path.replace('*', str(number).zfill(digits)), compress = 'blosc') ###
        to_msgpack(
            path.replace('*', str(number).zfill(digits)),
            pdf, 
            compress='blosc')
    return ddf_save_chunks


@dask.delayed()
def bundle_delayeds(*args):
    '''bundeling delayeds provided a huge speedup.
    this issue was adressed here:
    https://github.com/dask/dask/issues/1884
    '''
    pass


############################################
# original version. bad performance in case of complex dask dataframes
#############################################
# def my_dask_writer(ddf, path, optimize_graph = False, get = settings.multiprocessing_scheduler):
#     ''' Very simple method to store a dask dataframe to a bunch of files.
#     The reason for it's creation is a lot of frustration with the respective
#     dask method, which has some weired hard-to-reproduce issues, e.g. it sometimes
#     takes all the ram (512GB!) or takes a very long time to "optimize" / merge the graph.
#
#     Update: this issue was addressed here:
#     https://github.com/dask/dask/issues/1888
#     '''
#
#     ddf_save_chunks = get_writer_function()
#     ddf = ddf.to_delayed()
#     l = len(ddf)
#     digits = len(str(l))
#     print 'generating arguments for delayed function'
#     save_delayeds = zip(ddf, [path]*l, list(range(l)), [digits]*l) #put all data together
#     print 'call writer function with arguments'
#     save_delayeds = map(dask.delayed(lambda x: ddf_save_chunks(*x), traverse = False), save_delayeds) #call save function with it
#     #save_delayeds = bundle_delayeds(*save_delayeds) #bundle everything, so dask does not merge the graphs, which takes ages
#     #dask.compute(save_delayeds, optimize_graph = optimize_graph, get = get)
#     print 'call compute'
#     dask.delayed(save_delayeds).compute(optimize_graph = True, get = get)
#     #save_delayeds.compute(optimize_graph = False, get = get)

##############################################
# best performance, but needs to write files and is complex
# (where should the files be written? best would probably be
# to write in os.path.dirname(path), but to make it robust,
# you need to take care of name conflicts and so on ...
###############################################
# import tempfile, shutil
# import isf_data_base
# from data_base.utils import chunkIt
# def my_dask_writer(ddf, path, optimize_graph = False, get = settings.multiprocessing_scheduler):
#     ''' Very simple method to store a dask dataframe to a bunch of files.
#     The reason for it's creation is a lot of frustration with the respective
#     dask method, which has some weired hard-to-reproduce issues, e.g. it sometimes
#     takes all the ram (512GB!) or takes a very long time to "optimize" / merge the graph.
#
#     Update: this issue was addressed here:
#     https://github.com/dask/dask/issues/1888
#     '''
#     l = len(ddf.to_delayed())
#     print 123
#     try:
#         f = tempfile.mkdtemp()
#         print f
#         db = isf_data_base.DataBase(f)
#         db['fun'] = get_writer_function()
#         db['ndigits'] = len(str(l))
#         db['path'] = path
#         db['ddf'] = ddf
#         print 'db successful'
#
#         @dask.delayed(traverse = False)
#         def save_chunk(db, numbers):
#             fun = db['fun']
#             ndigits = db['ndigits']
#             path = db['path']
#             ddf = db['ddf']
#
#             for number in numbers:
#                 pdf = ddf.get_partition(number).compute(scheduler=dask.async.get_sync)
#                 fun(pdf, path, number, ndigits)
#
#         print 'execute!'
#         delayeds = [save_chunk(db, chunk) for chunk in chunkIt(range(ddf.npartitions), 100)]
#         dask.delayed(delayeds).compute(scheduler=get)
#     except:
#         print 'reraise exception'
#         raise
#     finally:
#         shutil.rmtree(f)
#     return

######################################################
# reasonable performance: just do the serialization yourself
######################################################
from data_base.utils import chunkIt
import cloudpickle


def my_dask_writer(
        ddf,
        path,
        optimize_graph=False,
        categorize=True,
        client=None):
    ''' Very simple method to store a dask dataframe to a bunch of files.
    There was a lot of frustration with the respective dask method, which has some weired hard-to-reproduce issues, e.g. it sometimes 
    takes all the ram (512GB!) or takes a very long time to "optimize" / merge the graph.
     
    Update: this issue was addressed here:
    https://github.com/dask/dask/issues/1888
    '''
    fun = get_writer_function(categorize)
    ndigits = len(str(ddf.npartitions))

    @dask.delayed()
    def save_chunk(s, numbers):
        ddf = cloudpickle.loads(s)
        dask_options = dask.context._globals
        dask.config.set(callbacks=set())  #disable progress bars etc.
        for number in numbers:
            pdf = ddf.get_partition(number).compute(scheduler="synchronous")
            fun(pdf, path, number, ndigits)
        dask.context._globals = dask_options

    ddf_scattered = client.scatter(cloudpickle.dumps(ddf))
    #folder = tempfile.mkdtemp()
    #path = os.path.join(folder, 'dump')
    #print path
    #with open(path, 'w') as f:
    #    f.write(cloudpickle.dumps(ddf))

    delayeds = [
        save_chunk(ddf_scattered, chunk)
        for chunk in chunkIt(list(range(ddf.npartitions)), 10000)
    ]  #max 5000 tasks writing at the same time
    futures = client.compute(delayeds)  #dask.delayed(delayeds).compute(scheduler=get)
    client.gather(futures)  # throw an error if there was an error


########################################################
# actual dumper
########################################################
fileglob = 'dask_to_msgpack.*.csv'  ###


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, dd.DataFrame)  # and (obj.index.dtype == 'object')

def get_numpy_dtype_as_str(obj):
    """
    Get a string representation of the numpy dtype of an object.
    If the object is of type string, simply return 'str'.

    Python 2 has two types of strings: str and unicode. If left unspecified, numpy will default to unicode of unknown length, which is set to 0.
    reading this back in results in the loss of string-type column names. For this reason, we construct our own string representation of the numpy dtype of these columns.
    """
    if (isinstance(obj, six.text_type) or isinstance(obj, str)) and six.PY2:  # Check if obj is a string
            return '|S{}'.format(len(obj))
    else:
        return str(np.dtype(type(obj)))

def read_object_meta(savedir):
    if os.path.exists(os.path.join(savedir, 'dask_meta.json')):
        # Construct meta dataframe for dask
        with open(os.path.join(savedir, 'dask_meta.json'), 'r') as f:
            # use yaml instead of json to ensure loaded data is string (and not unicode) in Python 2
            # yaml is a subset of json, so this should always work, although it assumes the json is ASCII encoded, which should cover all our usecases.
            # See also: https://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-from-json
            meta_json = yaml.safe_load(f)  
        meta = pd.DataFrame({
            c: pd.Series([], dtype=t)
            for c, t in zip(meta_json['columns'], meta_json['dtypes'])
            }, 
            columns=meta_json['columns']  # ensure the order of the columns is fixed.
            )
        column_dtype_mapping = [
            (c, t)
            if not t.startswith('<U') else (c, '<U' + str(len(c)))  # PY3: assure numpy has enough chars for string, given that the dtype is just 'str'
            for c, t in zip(meta.columns.values, meta_json['column_name_dtypes'])
            ]
        meta.columns = tuple(np.array([tuple(meta.columns.values)], dtype=column_dtype_mapping)[0])
        return meta
    return None
    

class Loader(parent_classes.Loader):

    def __init__(self, meta, index_name=None, divisions=None):
        self.index_name = index_name
        self.meta = meta
        self.divisions = divisions

    def get(self, savedir, verbose=False):
        # if dtypes is not defined (old db_versions) set it to None
        try:
            self.dtypes
        except AttributeError:
            self.dtypes = None
            
        # my_reader = lambda x: category_to_str(pd.read_msgpack(x))  ###
        my_reader = lambda x: category_to_str(read_msgpack(x))

        if self.divisions:
            if verbose:
                print('loaded dask dataframe with known divisions')
            #it does not seem to be a good idea to pass the long index list through the delayed interface
            #therefore the list is contained in this function enclosure
            ddf = [dask.delayed(my_reader, traverse = False)(fname) \
                   for fname in sorted(glob.glob(os.path.join(savedir, fileglob)))]
            ddf = dd.from_delayed(ddf, divisions=self.divisions, meta=self.meta)
        else:
            if verbose:
                print('loaded dask dataframe without known divisions')
            ddf = [dask.delayed(my_reader, traverse = False)(fname) \
                   for fname in sorted(glob.glob(os.path.join(savedir, fileglob)))]
            ddf = dd.from_delayed(ddf, meta=self.meta)
        ddf.index.name = self.index_name
        return ddf


def dump(
        obj,
        savedir,
        repartition=False,
        scheduler=None,
        categorize=True,
        client=None):
    """
    Save an object to a file in a DataBase in the pandas-msgpack format.
    Has been deprecated since 2023-09-01. Please use another dumper.
    This is only still available for testing purposes in support of backwards compatibility.

    Args:
        obj (_type_): The object to be saved
        savedir (str or Path): Output directory to save the file in.
        repartition (bool, optional): Whether or not to repartition.. Defaults to False.
        get (_type_, optional): A getter method, e.g. dask.get. Defaults to None.
        categorize (bool, optional): Defaults to True.
        client (distributed.Client, optional): distributed.Client for parallellization. Defaults to None.
        test (bool, optional): Whether or not the dumper is called from within a test method. Defaults to False.

    Raises:
        RuntimeError: _description_
    """
    import os
    if client is None:
        assert get is not None
        client = get
    if repartition:
        if obj.npartitions > 10000:
            obj = myrepartition(obj, 10000)

    my_dask_writer(
        obj,
        os.path.join(savedir, fileglob),
        categorize=categorize,
        client=client)

    index_name = obj.index.name
    if obj.known_divisions:
        assert obj.npartitions + 1 == len(obj.divisions)
        divisions = obj.divisions
    else:
        divisions = None


    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        divisions_serializable = [int(e) if convertible_to_int(e) else e for e in obj.divisions]
        json.dump({
            'Loader': __name__,
            'index_name': index_name,
            'divisions': divisions_serializable},
            f)
    
    save_object_meta(obj, savedir)

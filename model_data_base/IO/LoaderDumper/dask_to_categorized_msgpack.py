'''This dumper is designed for dataframes with the following properties:
 - index is str
 - str columns have a lot of repetitive values.
 
 How will it save the dataframe?
  1. If the number of partitions is very big (>10000), it will repartition the 
        dataframe to 5000 partitions. Loading such a dataframe is normaly possible
        within 1 second.
  2. 
      


stores an arbitrary dask dataframe to msgpack. Before saving, all str-columns will be converted to categoricals, in
each respective partition, if the part of unique values in the respective column is <= 20%. The original datatype
will be restored if the dataframe is loaded. This therefore only serves as optimization to increase loading speed and
reduce network traffic for suitable dataframes. Suitable dataframes are for example the synapse_activation dataframe.

Limitations: This is not tested to work well with dataframes that natively contain categoricals'''

import os
import cloudpickle
import tempfile
import dask.dataframe as dd
import dask.delayed
import dask
import pandas as pd
from . import parent_classes
import glob
import compatibility
import time
from model_data_base.utils import chunkIt, myrepartition, mkdtemp
import distributed
# import pandas_msgpack # do not import this; it will break pickle in loaded dataframes
from pandas_msgpack import to_msgpack, read_msgpack


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


#         pdf.to_msgpack(path.replace('*', str(number).zfill(digits)), compress = 'blosc') ###
        to_msgpack(path.replace('*',
                                str(number).zfill(digits)),
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
# import model_data_base
# from model_data_base.utils import chunkIt
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
#         mdb = model_data_base.ModelDataBase(f)
#         mdb['fun'] = get_writer_function()
#         mdb['ndigits'] = len(str(l))
#         mdb['path'] = path
#         mdb['ddf'] = ddf
#         print 'db successful'
#
#         @dask.delayed(traverse = False)
#         def save_chunk(mdb, numbers):
#             fun = mdb['fun']
#             ndigits = mdb['ndigits']
#             path = mdb['path']
#             ddf = mdb['ddf']
#
#             for number in numbers:
#                 pdf = ddf.get_partition(number).compute(get = dask.async.get_sync)
#                 fun(pdf, path, number, ndigits)
#
#         print 'execute!'
#         delayeds = [save_chunk(mdb, chunk) for chunk in chunkIt(range(ddf.npartitions), 100)]
#         dask.delayed(delayeds).compute(get=get)
#     except:
#         print 'reraise exception'
#         raise
#     finally:
#         shutil.rmtree(f)
#     return

######################################################
# reasonable performance: just do the serialization yourself
######################################################
from model_data_base.utils import chunkIt
import cloudpickle


def my_dask_writer(
        ddf,
        path,
        optimize_graph=False,
        categorize=True,
        client=None):  #get = compatibility.multiprocessing_scheduler,
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
            pdf = ddf.get_partition(number).compute(
                get=dask.get)  #get = compatibility.synchronous_scheduler
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
    futures = client.compute(delayeds)  #dask.delayed(delayeds).compute(get=get)
    client.gather(futures)  # throw an error if there was an error


########################################################
# actual dumper
########################################################
fileglob = 'dask_to_msgpack.*.csv'  ###


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, dd.DataFrame)  # and (obj.index.dtype == 'object')


class Loader(parent_classes.Loader):

    def __init__(self, meta, index_name=None, divisions=None):
        self.index_name = index_name
        self.meta = meta
        self.divisions = divisions

    def get(self, savedir, verbose=False):
        #if dtypes is not defined (old mdb_versions) set it to None
        try:
            self.dtypes
        except AttributeError:
            self.dtypes = None


#         my_reader = lambda x: category_to_str(pd.read_msgpack(x))  ###
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


def dump(obj,
         savedir,
         repartition=False,
         get=None,
         categorize=True,
         client=None):
    """
    Save an object to a file in a ModelDataBase in the pandas-msgpack format.
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
    if not "ISF_IS_TESTING" in os.environ:
        # Module was not called from within the test suite
        raise RuntimeError(
            'pandas-msgpack is not supported anymore in the model_data_base')
    if client is None:
        assert get is not None
        client = get
    if repartition:
        if obj.npartitions > 10000:
            obj = myrepartition(obj, 10000)

    my_dask_writer(obj,
                   os.path.join(savedir, fileglob),
                   categorize=categorize,
                   client=client)
    meta = obj._meta
    index_name = obj.index.name
    if obj.known_divisions:
        assert obj.npartitions + 1 == len(obj.divisions)
        divisions = obj.divisions
    else:
        divisions = None


#     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
#         cloudpickle.dump(Loader(meta, index_name = index_name, divisions = divisions), file_)
    compatibility.cloudpickle_fun(
        Loader(meta, index_name=index_name, divisions=divisions),
        os.path.join(savedir, 'Loader.pickle'))

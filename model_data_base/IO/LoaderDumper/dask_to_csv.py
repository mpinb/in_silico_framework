import os
import cloudpickle
import dask.dataframe as dd
import dask.delayed
import pandas as pd
from . import parent_classes
import glob
import compatibility


####################################################
# custom to_csv method, because the one of dask does eat all the memory
# this method has to the aim to be as simple as possible
#####################################################
def get_to_csv_function(index=None):
    '''returns function, that stores pandas dataframe'''

    def ddf_save_chunks(pdf, path, number, digits):
        pdf.to_csv(path.replace('*', str(number).zfill(digits)), index=index)

    return ddf_save_chunks


def chunkIt(seq, num):
    '''makes approx. equal size chunks out of seq'''
    avg = len(seq) / float(num)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


@dask.delayed
def bundle_delayeds(*args):
    '''bundeling delayeds provided a huge speedup.
    this issue was adressed here:
    https://github.com/dask/dask/issues/1884
    '''
    pass


def my_to_csv(ddf,
              path,
              optimize_graph=False,
              index=None,
              client=None):  #get = compatibility.multiprocessing_scheduler):
    ''' Very simple method to store a dask dataframe to a bunch of csv files.
    The reason for it's creation is a lot of frustration with the respective 
    dask method, which has some weired hard-to-reproduce issues, e.g. it sometimes 
    takes all the ram (512GB!) or takes a very long time to "optimize" / merge the graph.
    
    Update: this issue was addressed here:
    https://github.com/dask/dask/issues/1888
    '''

    ddf_save_chunks = get_to_csv_function(index=index)
    ddf = ddf.to_delayed()
    l = len(ddf)
    digits = len(str(l))
    save_delayeds = list(zip(ddf, [path] * l, list(range(l)),
                             [digits] * l))  #put all data together
    save_delayeds = list(
        map(dask.delayed(lambda x: ddf_save_chunks(*x)),
            save_delayeds))  #call save function with it
    save_delayeds = bundle_delayeds(
        *save_delayeds
    )  #bundle everything, so dask does not merge the graphs, which takes ages
    save_delayeds.compute(optimize_graph=optimize_graph, scheduler=client)
    #dask.compute(save_delayeds, optimize_graph = optimize_graph, get = get)


########################################################
# actual dumper
########################################################
fileglob = 'dask_to_csv.*.csv'


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, dd.DataFrame)


class Loader(parent_classes.Loader):

    def __init__(self, meta, index_name=None, divisions=None):
        self.index_name = index_name
        self.meta = meta
        self.divisions = divisions

    def get(self, savedir, verbose=True):
        #if dtypes is not defined (old mdb_versions) set it to None
        try:
            self.dtypes
        except AttributeError:
            self.dtypes = None


        my_read_csv = lambda x: pd.read_csv(x, index_col = self.index_name, skiprows = 1, \
                                                names = [self.index_name] + list(self.meta.columns), \
                                                dtype = self.meta.dtypes.append(pd.Series({self.meta.index.name: self.meta.index.dtype})).to_dict())
        if self.index_name is None:
            if verbose:
                print('loaded dask dataframe without index')
            ddf = dd.read_csv(os.path.join(savedir, fileglob),
                              dtype=self.meta.dtypes.to_dict(),
                              names=list(self.meta.columns),
                              skiprows=1)
        elif self.index_name is not None and self.divisions:
            if verbose:
                print('loaded dask dataframe with index and known divisions')
            #it does not seem to be a good idea to pass the long index list through the delayed interface
            #therefore the list is contained in this function enclosure
            ddf = [dask.delayed(my_read_csv)(fname) \
                   for fname in sorted(glob.glob(os.path.join(savedir, fileglob)))]
            ddf = dd.from_delayed(ddf, divisions=self.divisions, meta=self.meta)
        elif self.index_name is not None and not self.divisions:
            if verbose:
                print(
                    'loaded dask dataframe with index but without known divisions'
                )
            ddf = [dask.delayed(my_read_csv)(fname) \
                   for fname in sorted(glob.glob(os.path.join(savedir, fileglob)))]
            ddf = dd.from_delayed(ddf, meta=self.meta)
        ddf.index.name = self.index_name
        return ddf


def dump(obj, savedir, repartition=False, get=None):
    if repartition:
        if obj.npartitions > 10000:
            obj = obj.repartition(npartitions=5000)

#     get = compatibility.multiprocessing_scheduler if get is None else get
    index_flag = obj.index.name is not None
    my_to_csv(obj,
              os.path.join(savedir, fileglob),
              client=get,
              index=index_flag)
    #obj.to_csv(os.path.join(savedir, fileglob), get = settings.multiprocessing_scheduler, index = index_flag)
    meta = obj._meta
    index_name = obj.index.name
    if obj.known_divisions:
        divisions = obj.divisions
    else:
        divisions = None


#     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
#         cloudpickle.dump(Loader(meta, index_name = index_name, divisions = divisions), file_)
    compatibility.cloudpickle_fun(
        Loader(meta, index_name=index_name, divisions=divisions),
        os.path.join(savedir, 'Loader.pickle'))

'''
Methods for fast binning of synapse activation dask dataframe.

Exemplary use:

    groupby  = ['EI']
    values = synapse_activation_postprocess_dask(mdb['synapse_activation'], groupby = groupby, prefun = prefun, applyfun = applyfun, postfun = postfun)
    values = values.compute(scheduler=c.get)
    print 'save'
    save_groupby(mdb, values, groupby)
'''

from __future__ import absolute_import
from collections import defaultdict
from functools import partial
import numpy as np
import dask
from data_base.analyze.temporal_binning import universal as temporal_binning
from ..IO.LoaderDumper import numpy_to_msgpack
import logging
from config.cell_types import EXCITATORY
logger = logging.getLogger("ISF").getChild(__name__)


def prefun(df):
    dummy = df.synapse_type.str.split('_')
    df['celltype'] = dummy.str[0]
    df['presynaptic_column'] = dummy.str[1]
    df['proximal'] = (df.soma_distance
                      < 500).replace(True, 'prox').replace(False, 'dist')
    df['EI'] = df['celltype'].isin(EXCITATORY).replace(True, 'EXC').replace(
        False, 'INH')
    bs = 50
    df['binned_somadist'] = df.soma_distance.div(bs).map(np.floor).astype(
        int).map(lambda x: '{}to{}'.format(x * bs, x * bs + bs))
    return df


def postfun(s, maxtime=None):
    # default_value_size = s.dropna().iloc[0].shape
    default_value_size = (maxtime,)
    defaultvalue = np.zeros(default_value_size)
    s_old = s
    # s = s.map(lambda x: defaultvalue if( isinstance(x, float) and np.isnan(x)) else x)
    s = s.map(lambda x: defaultvalue
              if ((isinstance(x, float) and np.isnan(x)) or (x is None)) else x)
    return np.vstack(s.values)


def applyfun(pdf, maxtime=None):
    return temporal_binning(pdf,
                            min_time=0,
                            max_time=maxtime,
                            bin_size=1,
                            normalize=False)[1]



def synapse_activation_postprocess_pandas(pdf, groupby = '', \
                                          prefun = None,
                                          applyfun = None,
                                          postfun = None):
    '''see docstring of synapse_activation_postprocess_dask'''

    if not isinstance(groupby, list):
        groupby = [groupby]
    pdf = prefun(pdf)
    groups = pdf.groupby([pdf.index] + groupby).apply(applyfun)

    for lv in range(len(groupby)):
        groups = groups.unstack(1)
    keys = list(groups.columns)
    out = {key: postfun(groups[key]) for key in keys}
    return out


@dask.delayed
def merge_results_together(dicts):
    out = defaultdict(lambda: [])
    all_keys = set([x for d in dicts for x in list(d.keys())])
    for d in dicts:
        for key in all_keys:  #d.keys():
            if key in d:
                out[key].append(d[key])
            else:
                out[key].append(np.zeros(d[list(
                    d.keys())[0]].shape))  #fill with zeros

    for key in list(out.keys()):
        out[key] = np.vstack(out[key])
    return out


def tree_reduction(delayeds, aggregate_fun, length=7):
    if len(delayeds) > length:
        chunks = [
            delayeds[i:i + length] for i in range(0, len(delayeds), length)
        ]
        delayeds = [aggregate_fun(chunk) for chunk in chunks]
        return tree_reduction(delayeds, aggregate_fun, length)
    else:
        return aggregate_fun(delayeds)


def synapse_activation_postprocess_dask(ddf, **kwargs):
    '''
    Calculates bins of synapse activation dask dataframe per trail.
    #Todo: make this method out of core
    
    args:
        ddf: synapse activation dask dataframe
    kwargs:
        groupby: (default: ''): species for which subgroups the bins should be 
            calculated. Available values include: 
                'celltype', 
                'presynaptic_column', 
                'proximal', (soma distance < 500 ym)
                'EI' (Lumping the EXC / INH celltypes together)
                'binned_somadist' synapse counts for all 50 microns
            It can also be any column in the specified dataframe.
            Can be a list, if "sub-subgroups" should be calculated.
        mdb: if specified, the result will be computed immediately and 
                saved in the database immediately.
        get: only has an effect if 'mdb' kwarg is provided. In this case,
                it allows to specify a dask scheduler for the computation
        (prefun: function to apply on each partition before binning)
        (applyfun: actual binning function)
        (postfun: function to merge results together for one partition)
        
    
    returns: 
        dask.delayed object. If computed, this will return a dictionary 
        containing numpy arrays. rows: sim trails, columns: bins
    '''
    fun = dask.delayed(synapse_activation_postprocess_pandas)
    ds = ddf.to_delayed()

    #special case: if mdb is defined: isolate that keyword
    #for later use
    if 'mdb' in kwargs:
        mdb = kwargs['mdb']
        del kwargs['mdb']
    else:
        mdb = None
    if 'get' in kwargs:
        get = kwargs['get']
        del kwargs['get']
    if "scheduler" in kwargs:
        scheduler = kwargs["scheduler"]
        del kwargs["scheduler"]
    else:
        get = None
        scheduler=None

    ds = [fun(d, **kwargs) for d in ds]
    ret = tree_reduction(ds, merge_results_together)

    if mdb is not None:
        assert 'groupby' in kwargs
        save_groupby_delayed = dask.delayed(save_groupby)
        ret_saved = save_groupby_delayed(mdb, ret, kwargs['groupby'])
        ret_saved.compute(scheduler=scheduler)
        # data = ret.compute(scheduler=get)
        # save_groupby(mdb, data, kwargs['groupby'])
    else:
        return ret


@dask.delayed
def save_groupby(mdb, result, groupby):
    '''saves the result of synapse_activation_postprocess_dask to a model data base.
    
    A new model data base within mdb is created and the numpy arrays are stored there.'''
    if not isinstance(groupby, list):
        groupby = [groupby]
    identifier = tuple(['synapse_activation_binned', 't1'] +
                       ['__'.join(groupby)])
    try:
        del mdb[identifier]
    except:
        pass
    sub_mdb = mdb.create_sub_mdb(identifier)
    for key in result:
        sub_mdb.setitem(key, result[key], dumper=numpy_to_msgpack)


def init(mdb,
         groupby='',
         scheduler=None,
         prefun=prefun,
         applyfun=applyfun,
         postfun=postfun,
         maxtime=400):
    '''
    Binning synapse activations.
    
    mdb: ModelDataBase object, which is already initalized, such that 
         the key mdb['synapse_activation'] exists.
    
    groupby: (default: ''): species for which subgroups the bins should be 
            calculated. Available values include: 
                'celltype', 
                'presynaptic_column', 
                'proximal', (soma distance < 500 ym)
                'EI' (Lumping the EXC / INH celltypes together)
                'binned_somadist', 50 micron bins on soma distance
            It can also be any column in the specified dataframe.
            Can be a list, if "sub-subgroups" should be calculated.

    get: allows to specify a dask scheduler for the computation
    
    Not implemented yet:
        (prefun: function to apply on each partition before binning)
        (applyfun: actual binning function)
        (postfun: function to merge results together for one partition)
        
    
    returns: None. The binned synapse activation data will be stored in mdb.
    '''
    applyfun = partial(applyfun, maxtime=maxtime)
    postfun = partial(postfun, maxtime=maxtime)
    synapse_activation_postprocess_dask(mdb['synapse_activation'], \
                                        groupby = groupby, mdb = mdb, \
                                        scheduler = scheduler, \
                                        prefun = prefun, \
                                        applyfun = applyfun, \
                                        postfun = postfun)

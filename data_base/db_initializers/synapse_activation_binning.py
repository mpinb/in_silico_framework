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
'''Methods for fast binning of :ref:`syn_activation_format` dataframes.

Example:

    >>> groupby  = ['EI']  # excitatory or inhibitory
    >>> values = synapse_activation_postprocess_dask(
    ...    ddf = db['synapse_activation'], 
    ...    groupby = groupby, 
    ...    prefun = prefun, 
    ...    applyfun = applyfun, 
    ...    postfun = postfun)
    >>> values = values.compute(scheduler=c.get)
    >>> save_groupby(db, values, groupby)
'''

from __future__ import absolute_import
from collections import defaultdict
from functools import partial
import numpy as np
import dask
from data_base.analyze.temporal_binning import universal as temporal_binning
from config.cell_types import EXCITATORY
import logging
logger = logging.getLogger("ISF").getChild(__name__)

from data_base.IO.LoaderDumper import numpy_to_msgpack
numpy_dumper = numpy_to_msgpack


def prefun(df):
    """Augment a :ref:`syn_activation_format` dataframe with additional columns.
    
    Adds the following columns:
    
    - ``celltype``: The celltype of the synapse.
    - ``presynaptic_column``: The presynaptic column of the synapse.
    - ``proximal``: Whether the synapse is proximal (soma distance < 500 um).
    - ``EI``: Whether the synapse is excitatory or inhibitory.
    - ``binned_somadist``: The soma distance binned in 50 microns.
    
    This method is used by default during the binning of synapse activations.
    
    Args:
        df (:py:class:`pandas.DataFrame`): synapse activation dataframe
        
    Returns:
        :py:class:`pandas.DataFrame`: The modified dataframe with additional columns.
        
    See also:
        :py:meth:`~data_base.db_initializers.init`
    """
    dummy = df.synapse_type.str.split('_')
    df['celltype'] = dummy.str[0]
    df['presynaptic_column'] = dummy.str[1]
    df['proximal'] = (df.soma_distance < 500).replace(True, 'prox').replace(False, 'dist')
    df['EI'] = df['celltype'].isin(EXCITATORY).replace(True, 'EXC').replace(
        False, 'INH')
    bs = 50
    df['binned_somadist'] = df.soma_distance.div(bs).map(np.floor).astype(
        int).map(lambda x: '{}to{}'.format(x * bs, x * bs + bs))
    return df


def postfun(s, maxtime=None):
    """Postprocess a column of the binned synapse activations.
    
    This method fills ``None`` and ``np.nan`` values with zeroes instead.
    It is used by default during the binning of synapse activations.
    
    Args:
        s (:py:class:`pandas.Series`): A column of the binned synapse activations.
        maxtime (int): The maximum time of the synapse activations.
        
    Returns:
        numpy.array: The processed column of synapse activations.
        
    See also:
        :py:meth:`~data_base.db_initializers.init`
    """
    # default_value_size = s.dropna().iloc[0].shape
    default_value_size = (maxtime,)
    defaultvalue = np.zeros(default_value_size)
    s_old = s
    # s = s.map(lambda x: defaultvalue if( isinstance(x, float) and np.isnan(x)) else x)
    s = s.map(lambda x: defaultvalue if ((isinstance(x, float) and np.isnan(x)) or (x is None)) else x)
    return np.vstack(s.values)


def applyfun(pdf, maxtime=None):
    """Bin the synapse activations using :py:meth:`~data_base.analyze.temporal_binning.universal`.
    
    This is used by default during the binning of synapse activations.
    
    Args:
        pdf (:py:class:`pandas.DataFrame`): synapse activation dataframe
        maxtime (int): The maximum time of the synapse activations.
        
    Returns:
        numpy.array: The binned synapse activations.
    
    See also:
        :py:meth:`~data_base.db_initializers.init`
    """
    return temporal_binning(
        pdf,
        min_time=0,
        max_time=maxtime,
        bin_size=1,
        normalize=False)[1]


def synapse_activation_postprocess_pandas(
    pdf, 
    groupby = '',
    prefun = None,
    applyfun = None,
    postfun = None):
    '''Calculates bins of synapse activation per trial from a pandas dataframe.
    
    Args:
        pdf (:py:class:`pandas.DataFrame`): synapse activation dask dataframe
        groupby (str): species for which subgroups the bins should be calculated. Available values include:
        
          - ``celltype``
          - ``presynaptic_column``
          - ``proximal`` (soma distance < 500 um)
          - ``EI`` (Lumping the EXC / INH celltypes together)
          - ``binned_somadist``: synapse counts for all 50 microns
          - any column in the specified dataframe.
        
        db (DataBase): if specified, the result will be computed immediately and saved in the database immediately.
        get (dask scheduler): Specify a dask scheduler for the computation (e.g. :py:func:`dask.distributed.Client.get`)
        prefun (callable):
            A function to preprocess the synapse activation dataframe before binning.
            The function should take a pandas dataframe and return a pandas dataframe.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.prefun`
        applyfun (callable):
            A function to bin the synapse activations.
            The function should take a pandas dataframe and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.applyfun`
        postfun (callable):
            A function to postprocess the binned synapse activations.
            The function should take a pandas series and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.postfun`
    
    Returns: 
        dict: Dictionary containing numpy arrays, whose rows are sim trials, and columns are time bins. The dictionary keys are defined by :paramref:`groupby`.
        
    See also:
        :py:meth:`~data_base.db_initializers.synapse_activation_postprocess_dask` for the delayed version of this method.
    '''
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
    """Aggregate many dictionaries with the same keys.
    
    If a key is not present in some dictionary, it is filled with zeros instead.
    This method is evaluated delayed on the results of the synapse activation binning to merge them in one dictionary.
    
    Args:
        dicts (array): 
            list of dictionaries with the same keys.
            
    Returns:
        dict: The aggregated dictionary.
    
    Example::
    
        >>> dicts = [
        ...     {'a': np.array([1, 2]), 'b': np.array([3, 4])},
        ...     {'a': np.array([5, 6]), 'c': np.array([7, 8])}
        ...     ]
        >>> merge_results_together(dicts)
        {'a': array([[1, 2], [5, 6]]), 'b': array([[3, 4], [0, 0]), 'c': array([[0, 0], [7, 8]])} 
    """
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
    """Recursively aggregate the results of a list of delayed objects.
    
    This is used in :py:meth:`~data_base.db_initializers.synapse_activation_postprocess_dask`
    and :py:meth:`~data_base.db_initializers.synapse_activation_postprocess_pandas` to aggregate
    the resulting synapse binning (which is in dictionary format) to a single dictionary.
    
    Args:
        delayeds (array): 
            list of :py:class:`~dask.delayed` objects
        aggregate_fun (:py:class:`~dask.delayed`): 
            Function to aggregate the results with (e.g. :py:func:`~data_base.db_initializers.merge_results_together`)
        length (int): chunk size for aggregation
        
    Note:
        Once the delayed objects are evaluated, :paramref:`aggregate_fun` is applied to the results of :paramref:`delayeds`, 
        and thus :paramref:`aggregate_fun` should be able to handle the results of :paramref:`delayeds`.
        
    Returns:
        :py:class:`dask.delayed`: The aggregated result.
    """
    if len(delayeds) > length:
        chunks = [
            delayeds[i:i + length] for i in range(0, len(delayeds), length)
        ]
        delayeds = [aggregate_fun(chunk) for chunk in chunks]
        return tree_reduction(delayeds, aggregate_fun, length)
    else:
        return aggregate_fun(delayeds)


def synapse_activation_postprocess_dask(
    ddf, 
    **kwargs
    ):
    '''Calculates bins of synapse activation per trial from a dask dataframe.
    
    Args:
        ddf (dask.dataframe): synapse activation dask dataframe
        groupby (str): species for which subgroups the bins should be calculated. Available values include:
          - ``celltype``
          - ``presynaptic_column``
          - ``proximal`` (soma distance < 500 um)
          - ``EI`` (Lumping the EXC / INH celltypes together)
          - ``binned_somadist``: synapse counts for all 50 microns
          - any column in the specified dataframe.
        db (DataBase): if specified, the result will be computed immediately and saved in the database immediately.
        get (dask scheduler): only has an effect if 'db' kwarg is provided. In this case, it allows to specify a dask scheduler for the computation.
        scheduler (dask scheduler): 
            Specify a dask scheduler for the computation (e.g. :py:func:`dask.distributed.Client.get`)
        prefun (callable):
            A function to preprocess the synapse activation dataframe before binning.
            The function should take a pandas dataframe and return a pandas dataframe.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.prefun`
        applyfun (callable):
            A function to bin the synapse activations.
            The function should take a pandas dataframe and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.applyfun`
        postfun (callable):
            A function to postprocess the binned synapse activations.
            The function should take a pandas series and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.postfun`
    
    Returns: 
        :py:class:`dask.delayed`: 
            If computed, this will return a dictionary containing numpy arrays, whose rows are sim trials, and columns are time bins.
            The dictionary keys are defined by :paramref:`groupby`.
            
    See also:
        :py:meth:`~data_base.db_initializers.synapse_activation_postprocess_pandas` for the non-delayed
        version of this method.
    '''
    # TODO: make this method out of core
    fun = dask.delayed(synapse_activation_postprocess_pandas)
    ds = ddf.to_delayed()

    # special case: if db is defined: isolate that keyword for later use
    if 'db' in kwargs:
        db = kwargs['db']
        del kwargs['db']
    else:
        db = None
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

    if db is not None:
        assert 'groupby' in kwargs
        save_groupby_delayed = dask.delayed(save_groupby)
        ret_saved = save_groupby_delayed(db, ret, kwargs['groupby'])
        ret_saved.compute(scheduler=scheduler)
        # data = ret.compute(scheduler=get)
        # save_groupby(db, data, kwargs['groupby'])
    else:
        return ret


@dask.delayed
def save_groupby(db, result, groupby):
    '''Save the result of synapse_activation_postprocess_dask to a database.
    
    A new model data base within :paramref:`db` is created and the numpy arrays are stored there.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The simrun-initialized database object.
        result (dict): The result of the synapse activation binning.
        groupby (str): The groupby key for the synapse activation bins.
        
    Returns:
        None.
        
    See also:
        :py:meth:`~data_base.db_initializers.load_simrun_general.init` for how to simrun-initialize a database.
    '''
    if not isinstance(groupby, list):
        groupby = [groupby]
    identifier = tuple(['synapse_activation_binned', 't1'] +
                       ['__'.join(groupby)])
    try:
        del db[identifier]
    except:
        pass
    sub_db = db.create_sub_db(identifier)
    for key in result:
        sub_db.set(key, result[key], dumper=numpy_dumper)


def init(
    db,
    groupby='',
    scheduler=None,
    prefun=prefun,
    applyfun=applyfun,
    postfun=postfun,
    maxtime=400):
    '''Main pipeline to bin synapse activations from a :ref:`syn_activation_format` dataframe.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The simrun-initialized database object.
            Must contain the key ``synapse_activation``.
        groupby (str):
            Aggregation key for the synapse activation bins. Available values include:
            
            - ``celltype``
            - ``presynaptic_column``
            - ``proximal`` (soma distance < 500 um)
            - ``EI`` (Lumping the EXC / INH celltypes together)
            - ``binned_somadist``: synapse counts for all 50 microns
            - any column in the specified dataframe.
            - Can be a list, if "sub-subgroups" should be calculated.
        
        scheduler (dask scheduler):
            A dask scheduler for the comptation (e.g. :py:func:`dask.distributed.Client.get`)
        prefun (callable):
            A function to preprocess the synapse activation dataframe before binning.
            The function should take a pandas dataframe and return a pandas dataframe.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.prefun`
        applyfun (callable):
            A function to bin the synapse activations.
            The function should take a pandas dataframe and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.applyfun`
        postfun (callable):
            A function to postprocess the binned synapse activations.
            The function should take a pandas series and return a numpy array.
            Default: :py:func:`~data_base.db_initializers.synapse_activation_binning.postfun`
        
    Returns: 
        None. The binned synapse activation data will be stored in :paramref:`db`.
        
    See also:
        :py:meth:`~data_base.db_initializers.prefun`, 
        :py:meth:`~data_base.db_initializers.applyfun`, and
        :py:meth:`~data_base.db_initializers.postfun` for the default functions that bin the synapse activations.
        
    See also:
        :py:meth:`~data_base.db_initializers.load_simrun_general.init` for how to simrun-initialize a database.
    '''
    applyfun = partial(applyfun, maxtime=maxtime)
    postfun = partial(postfun, maxtime=maxtime)
    synapse_activation_postprocess_dask(
        db['synapse_activation'],
        groupby = groupby, db = db,
        scheduler = scheduler,
        prefun = prefun,
        applyfun = applyfun,
        postfun = postfun)

'''Read and write a :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel`.

During saving, the data undergoes the following changes:

- Spike times and lda values are kept with an accuracy of :math:`.01`.
- The index of the spike times is reset, i.e. the ``sim_trial_index`` is not kept.
- The :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel` attribute ``db_list``, which normally contains ``DataBase`` instances, 
  is replaced by a list of strings that only contain the unique_id of each database. 
  This prevents unpickling errors in case the ``DataBase`` has been removed.
- Older versions of reduced models do not have the attribute `st`. 
  They are stored with an empty dataframe (``Rm.st = pd.DataFrame()``) to be compliant with the new version.

The output is a database with the following keys:

.. list-table:: Database keys
   :header-rows: 1

   * - Key
     - Description
   * - ``st``
     - Spike times with a precision of :math:`.01`.
   * - ``lda_value_dicts_<index>``
     - Dictionaries of LDA values with a precision of :math:`.01`.
   * - ``Rm``
     - The reduced model.
'''

# Reading: takes 24% of the time, to_cloudpickle needs (4 x better reading speed)
# Writing: takes 170% of the time, to_cloudpickle needs (70% lower writing speed)
# Filesize: takes 14% of the space, to cloudpickle needs (7 x more space efficient)

from . import parent_classes
import os, cloudpickle
from simrun.reduced_model.get_kernel import ReducedLdaModel
from data_base.data_base import DataBase, get_db_by_unique_id
from . import pandas_to_parquet
from . import numpy_to_zarr
import pandas as pd
import compatibility
import six
import json

if six.PY2:
    from . import numpy_to_msgpack
    numpy_dumper = numpy_to_msgpack
elif six.PY3:
    numpy_dumper = numpy_to_zarr

def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel`
    """
    return isinstance(
        obj, ReducedLdaModel)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):
    """Loader for :py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel` objects"""
    def get(self, savedir):
        """Load the reduced model from the specified folder"""
        db = DataBase(savedir)
        Rm = db['Rm']
        Rm.st = db['st']
        lv = 0
        for d in Rm.lda_value_dicts:
            for k in list(d.keys()):
                key = 'lda_value_dicts_' + str(lv)
                d[k] = db[key]
                lv += 1
        Rm.lda_values = [
            sum(lda_value_dict.values())
            for lda_value_dict in Rm.lda_value_dicts
        ]
        return Rm


def dump(obj, savedir):
    """Save the reduced model in the specified directory as a DataBase.
    
    The database will contain the following keys:
    
    - ``st``: Spike times with a precision of :math:`.01`.
    - ``lda_value_dicts_<index>``: Dictionaries of LDA values with a precision of :math:`.01`.
    - ``Rm``: The reduced model.    
    
    Args:
        obj (:py:class:`~simrun.reduced_model.get_kernel.ReducedLdaModel`): Reduced model to be saved.
        savedir (str): Directory where the reduced model should be stored.
    """
    db = DataBase(savedir)
    Rm = obj
    # keep references of original objects
    try:  # some older versions do not have this attribute
        st = Rm.st
    except AttributeError:
        st = Rm.st = pd.DataFrame()
    lda_values = Rm.lda_values
    lda_value_dicts = Rm.lda_value_dicts
    db_list = Rm.db_list

    if six.PY2:
        from . import pandas_to_msgpack
        st_dumper = pandas_to_msgpack
    elif six.PY3:
        st_dumper = pandas_to_parquet

    try:
        db.set(
            'st',
            Rm.st.round(decimals=2).astype(float).reset_index(drop=True),
            dumper=st_dumper)
        del Rm.st
        del Rm.lda_values  # can be recalculated
        lv = 0
        lda_value_dicts = Rm.lda_value_dicts
        new_lda_value_dicts = []
        for d in Rm.lda_value_dicts:
            new_lda_value_dicts.append({})
            for k in list(d.keys()):
                key = 'lda_value_dicts_' + str(lv)
                db.set(key, d[k].round(decimals=2), dumper=numpy_dumper)
                new_lda_value_dicts[-1][k] = key
                lv += 1
        Rm.lda_value_dicts = new_lda_value_dicts
        # convert db_list to db ids
        Rm.db_list = [
            m.get_id() if not isinstance(m, str) else m for m in Rm.db_list
        ]
        db['Rm'] = Rm
    finally:
        # revert changes to object, deepcopy was causing pickling errors
        Rm.st = st
        Rm.lda_values = lda_values
        Rm.lda_value_dicts = lda_value_dicts
        Rm.db_list = db_list
    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

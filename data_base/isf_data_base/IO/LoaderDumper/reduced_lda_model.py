'''format for reduced models. 
spike times and lda values are kept with an accuracy of .01.
The index of the spike times is reset, i.e. the sim_trial_index is not kept.
The attribute `db_list`, which contains instances of DataBase, is replaced
by a list of strings that only contain the unique_id of each database. This prevents
unpickling errors in case the DataBase has been removed.

Older versions of reduced models, that do not have the attribute `st` will be stored with
an empty dataframe (Rm.st = pd.DataFrame) to be compliant with the new version

Reading: takes 24% of the time, to_cloudpickle needs (4 x better reading speed)
Writing: takes 170% of the time, to_cloudpickle needs (70% lower writing speed)
Filesize: takes 14% of the space, to cloudpickle needs (7 x more space efficient)
'''
from . import parent_classes
import os, cloudpickle
from simrun.reduced_model.get_kernel import ReducedLdaModel
from data_base.data_base import DataBase, get_db_by_unique_id
from . import pandas_to_parquet, pandas_to_msgpack
from . import numpy_to_npz
import pandas as pd
import compatibility
import six
import json

def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, ReducedLdaModel)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
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
                db.set(key, d[k].round(decimals=2), dumper=numpy_to_npz)
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

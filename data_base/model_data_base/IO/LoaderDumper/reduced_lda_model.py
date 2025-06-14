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
'''format for reduced models. 
spike times and lda values are kept with an accuracy of .01.
The index of the spike times is reset, i.e. the sim_trial_index is not kept.
The attribute `mdb_list`, which contains instances of DataBase, is replaced
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
from data_base.model_data_base.model_data_base import ModelDataBase
from . import pandas_to_parquet, pandas_to_msgpack
from . import numpy_to_npz
import pandas as pd
import compatibility
import six


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, ReducedLdaModel)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        mdb = ModelDataBase(savedir)
        Rm = mdb['Rm']
        Rm.st = mdb['st']
        lv = 0
        for d in Rm.lda_value_dicts:
            for k in list(d.keys()):
                key = 'lda_value_dicts_' + str(lv)
                d[k] = mdb[key]
                lv += 1
        Rm.lda_values = [
            sum(lda_value_dict.values())
            for lda_value_dict in Rm.lda_value_dicts
        ]
        return Rm


def dump(obj, savedir):
    mdb = ModelDataBase(savedir)
    Rm = obj
    # keep references of original objects
    try:  # some older versions do not have this attribute
        st = Rm.st
    except AttributeError:
        st = Rm.st = pd.DataFrame()
    lda_values = Rm.lda_values
    lda_value_dicts = Rm.lda_value_dicts
    mdb_list = Rm.db_list

    if six.PY2:
        st_dumper = pandas_to_msgpack
    elif six.PY3:
        st_dumper = pandas_to_parquet

    try:
        mdb.setitem('st',
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
                mdb.setitem(key, d[k].round(decimals=2), dumper=numpy_to_npz)
                new_lda_value_dicts[-1][k] = key
                lv += 1
        Rm.lda_value_dicts = new_lda_value_dicts
        # convert mdb_list to mdb ids
        Rm.db_list = [
            m.get_id() if not isinstance(m, str) else m for m in Rm.db_list
        ]
        mdb['Rm'] = Rm
    finally:
        # revert changes to object, deepcopy was causing pickling errors
        Rm.st = st
        Rm.lda_values = lda_values
        Rm.lda_value_dicts = lda_value_dicts
        Rm.db_list = mdb_list
        #         with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
        #             cloudpickle.dump(Loader(), file_)
        compatibility.cloudpickle_fun(Loader(),
                                      os.path.join(savedir, 'Loader.pickle'))

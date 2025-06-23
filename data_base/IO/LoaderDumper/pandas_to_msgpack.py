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
"""Save and load pandas dataframes to msgpack files.
   
See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_parquet` for saving pandas dataframes to parquet files.

This uses a fork of the original `pandas_to_msgpack` package, `available on PyPI <https://pypi.org/project/isf-pandas-msgpack/>`_
"""


import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
import isf_pandas_msgpack
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        #         return pd.read_msgpack(os.path.join(savedir, 'pandas_to_msgpack'))
        path = os.path.join(savedir, 'pandas_to_msgpack')
        if os.path.exists(path):  # 'everything saved in single file'
            return isf_pandas_msgpack.read_msgpack(
                os.path.join(savedir, 'pandas_to_msgpack'))
        else:
            paths = os.listdir(savedir)
            paths = [p for p in paths if 'pandas_to_msgpack' in p]
            paths = sorted(paths, key=lambda x: int(x.split('_')[-1]))
            dfs = [
                isf_pandas_msgpack.read_msgpack(os.path.join(savedir, p))
                for p in paths
            ]
            return pd.concat(dfs)


def dump(obj, savedir, rows_per_file=None):
    '''rows_per_file: automatically splits dataframe, such that rows_per_file rows of the df are
    saved in each file. This helps with large dataframes which otherwise would hit the 1GB limit of msgpack.'''
    #     obj.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'), compress = 'blosc')
    import os
    if rows_per_file is not None:
        row = 0
        lv = 0
        while True:
            current_obj = obj.iloc[row:row + rows_per_file]
            row += rows_per_file
            if len(current_obj) == 0:
                break
            print(len(current_obj), lv)
            isf_pandas_msgpack.to_msgpack(os.path.join(
                savedir, 'pandas_to_msgpack_{}'.format(lv)),
                                      current_obj,
                                      compress='blosc')
            lv += 1
    else:
        isf_pandas_msgpack.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'),
                                  obj,
                                  compress='blosc')


    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)

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
import dask.dataframe
import pandas as pd
import os


def concat_path_elements_to_filelist(*args):
    '''e.g. 
    args = ['str', [1,2,3], pd.Series([1,2,3])]
    > [['str', 'str', 'str'], [1, 2, 3], [1, 2, 3]]
    '''
    if not args:
        return []

    args = [[arg] if isinstance(arg, (str, int, float)) else list(arg)
            for arg in args]
    max_len = max([len(x) for x in args])
    args = [x * max_len if len(x) == 1 else x for x in args]
    min_len = min([len(x) for x in args])
    assert min_len == max_len
    ret = [os.path.join(*[str(x) for x in x]) for x in zip(*args)]
    return ret


#todo test:
#['str', [1,2,3], pd.Series([1,2,3])] --> [('str', 1, 1), ('str', 2, 2), ('str', 3, 3)]
#'0' --> ['0']


def my_reader(fname, fun):
    df = pd.read_csv(fname)
    if fun is not None:
        df = fun(df)
    return df


def read_csvs(*args, **kwargs):
    '''The native dask read_csv function only supports globstrings. 
    Use this function instead, if you want to provide a explicit filelist.'''
    filelist = concat_path_elements_to_filelist(
        *args)  ## 3hr of debugging: *args, not args
    out = []
    fun = kwargs['fun'] if 'fun' in kwargs else None
    for fname in filelist:
        absolute_path_to_file = os.path.join(fname)
        out.append(dask.delayed(my_reader)(absolute_path_to_file, fun))

    return dask.dataframe.from_delayed(out)

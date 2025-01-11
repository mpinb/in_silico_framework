"""Read dask csv from an explicit filelist instead of only globstring."""

import dask.dataframe
import pandas as pd
import os


def concat_path_elements_to_filelist(*args):
    '''Concatenate path elements to a filelist.
    
    :skip-doc:
    
    Example:: 
        
        >>> args = ['str', [1,2,3], pd.Series([1,2,3])]
        [['str', 'str', 'str'], [1, 2, 3], [1, 2, 3]]
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
    """:skip-doc:"""
    df = pd.read_csv(fname)
    if fun is not None:
        df = fun(df)
    return df


def read_csvs(*args, **kwargs):
    '''Read dask dataframes from csv files.
    
    The native dask read_csv function only supports globstrings. 
    Use this function instead, if you want to provide a explicit filelist.
    '''
    filelist = concat_path_elements_to_filelist(
        *args)  ## 3hr of debugging: *args, not args  # we've all been there. I feel you.
    out = []
    fun = kwargs['fun'] if 'fun' in kwargs else None
    for fname in filelist:
        absolute_path_to_file = os.path.join(fname)
        out.append(dask.delayed(my_reader)(absolute_path_to_file, fun))

    return dask.dataframe.from_delayed(out)

from data_base.IO.dask_wrappers import concat_path_elements_to_filelist
import pandas as pd
from os import sep


def test_concat_path_elements_to_filelist():
    dummy = concat_path_elements_to_filelist('str', [1, 2, 3], pd.Series([1, 2, 3]))
    assert dummy == [f'str{sep}1{sep}1', f'str{sep}2{sep}2', f'str{sep}3{sep}3']
    dummy = concat_path_elements_to_filelist(1, 2, 3)
    assert dummy == [f'1{sep}2{sep}3']
    dummy = concat_path_elements_to_filelist('a', 'b', 'c')
    assert dummy == [f'a{sep}b{sep}c']
    dummy = concat_path_elements_to_filelist()
    assert dummy == []

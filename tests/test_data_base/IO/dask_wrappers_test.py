from data_base.IO.dask_wrappers import *


def test_concat_path_elements_to_filelist():
    dummy = concat_path_elements_to_filelist('str', [1, 2, 3],
                                             pd.Series([1, 2, 3]))
    assert dummy == ['str/1/1', 'str/2/2', 'str/3/3']
    dummy = concat_path_elements_to_filelist(1, 2, 3)
    assert dummy == ['1/2/3']
    dummy = concat_path_elements_to_filelist('a', 'b', 'c')
    assert dummy == ['a/b/c']
    dummy = concat_path_elements_to_filelist()
    assert dummy == []

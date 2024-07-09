from tests.test_data_base import *
from data_base.utils import *
import numpy as np
from pandas.util.testing import assert_frame_equal


def test_pandas_to_array():
    '''make sure pandas to array works with dict, series and dataframe'''
    dict_ = {
        'x_1_y_1': 10,
        'x_2_y_1': 15,
        'x_3_y_1': 7,
        'x_1_y_2': 2,
        'x_2_y_2': 0,
        'x_3_y_2': -1
    }
    s = pd.Series(dict_)
    pdf = s.to_frame(name='bla')

    out_dict_ = pandas_to_array(dict_, lambda index, values: index.split('_')[1], \
                        lambda index, values: index.split('_')[-1], \
                        lambda index, values: values)

    out_s = pandas_to_array(s, lambda index, values: index.split('_')[1], \
                        lambda index, values: index.split('_')[-1], \
                        lambda index, values: values)

    out_pdf = pandas_to_array(pdf, lambda index, values: index.split('_')[1], \
                        lambda index, values: index.split('_')[-1], \
                        lambda index, values: values.bla)

    pdf_expected_output = pd.DataFrame({
        '1': [10, 2],
        '2': [15, 0],
        '3': [7, -1],
        'index': ['1', '2']
    }).set_index('index')
    pdf_expected_output.index.name = None
    assert_frame_equal(pdf_expected_output, out_dict_)
    assert_frame_equal(pdf_expected_output, out_s)
    assert_frame_equal(pdf_expected_output, out_pdf)


def test_cache():
    '''Is really caching values, can cache functions'''
    flag = []

    @cache
    def fun(x):
        flag.append(x)
        return x

    assert len(flag) == 0
    fun(1)
    assert len(flag) == 1
    fun(1)
    assert len(flag) == 1
    fun(fun)
    assert len(flag) == 2


def test_myrepartition(client):
    pdf = pd.DataFrame(np.random.randint(100, size=(1000, 3)))
    ddf = dask.dataframe.from_pandas(pdf, npartitions=10)
    pdf2 = client.compute(myrepartition(ddf, 4)).result()
    pd.util.testing.assert_frame_equal(pdf, pdf2)
    ddf.divisions = tuple([None] * (ddf.npartitions + 1))
    pdf2 = client.compute(myrepartition(ddf, 4)).result()
    pd.util.testing.assert_frame_equal(pdf, pdf2)

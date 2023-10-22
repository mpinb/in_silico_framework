from .context import *
from visualize._decorators import *
import pandas as pd
import pandas.util.testing as pdt
import dask.dataframe as dd
from mock import MagicMock, call


def test_dask_to_pandas():

    def fun(*args, **kwargs):
        return args, kwargs

    fun = dask_to_pandas(fun)

    pdf = pd.DataFrame({'A': [1, 2, 3], 'B': [3, 4, 5]})
    ddf = dd.from_pandas(pdf, npartitions=3)

    result_args, result_kwargs = fun(pdf, ddf, pdf, ddf, A=pdf, B=pdf, C=ddf)

    for val in result_args:
        assert isinstance(val, pd.DataFrame)
    for name in result_kwargs:
        assert isinstance(result_kwargs[name], pd.DataFrame)


def test_subsequent_calls_per_line():
    pdf = pd.DataFrame({'A': [1, 2, 3], 'B': [3, 4, 5]})

    m = MagicMock()

    @subsequent_calls_per_line
    def fun(*args, **kwargs):
        m.args(args)
        m.kwargs(kwargs)

    m = MagicMock()
    fun(1, pdf, pdf, 1, pdf, 3, A=pdf, fig='A')
    call1 = call((1, pdf, pdf, 1, pdf, 3))
    m.args.assert_has_calls([call1])
    call_kwargs_1 = call(dict(A=pdf, fig='A'))
    m.kwargs.assert_has_calls([call_kwargs_1])


#         m = MagicMock()
#         fun(pdf, pdf, pdf, 1, pdf, 3, A = pdf, fig = 'A')
#         call1 = call((pdf.iloc[0], pdf.iloc[0], pdf.iloc[0], 1, pdf, 3))
#         call2 = call((pdf.iloc[1], pdf.iloc[1], pdf.iloc[1], 1, pdf, 3))
#         call3 = call((pdf.iloc[2], pdf.iloc[2], pdf.iloc[2], 1, pdf, 3))
#
#         def compare_fun(x, y):
#             print(type(x))
#             for lv in range(len(x)):
#                 out = True
#                 try:
#                     out = out and (x[lv] == y[lv]).all()
#                     print(1)
#                 except:
#                     try:
#                         out = out and x[lv] == y[lv]
#                         print(2)
#                     except:
#                         out = False
#                         print(x[lv])
#                         print(y[lv])
#             return out
#
#         l = m.args.call_args_list#assert_has_calls([call1, call2, call3])
#         print(list(l))
#         print '_____________________'
#         self.assertTrue(compare_fun(l[0], call1))
#         self.assertTrue(compare_fun(l[1], call2))
#         self.assertTrue(compare_fun(l[1], call2))

#call_kwargs_1 = call(dict(A = pdf, fig = 'A'))
#m.kwargs.assert_has_calls([call_kwargs_1])

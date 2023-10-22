import Interface as I
from . import context

from biophysics_fitting.parameters import param_selector, param_to_kwargs


#@decorators.testlevel(0)
def test_param_selectors():
    params = I.pd.Series({'a.a': 1, 'a.b': 2, 'b.x': 3, 'c.x': 1, 'c.a.b': 7})
    assert len(param_selector(params, 'a')) == 2
    assert param_selector(params, 'a')['a'] == 1
    assert param_selector(params, 'a')['b'] == 2

    assert len(param_selector(params, 'b')) == 1
    assert param_selector(params, 'b')['x'] == 3

    assert len(param_selector(params, 'c')) == 2
    assert len(param_selector(params, 'c.a')) == 1
    assert param_selector(params, 'c.a')['b'] == 7


def test_param_to_kwargs():
    params = I.pd.Series({'a': 1, 'b': 2})

    def fun(**kwargs):
        assert len(list(kwargs.keys())) == 2
        assert kwargs['a'] == 1
        assert kwargs['b'] == 2

    param_to_kwargs(fun)(params=params)

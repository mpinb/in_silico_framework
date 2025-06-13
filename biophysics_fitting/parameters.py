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
'''
Fetch parameters with the dot naming convention.
'''

import pandas as pd
from six import iteritems

__author__ = 'Arco Bast'
__date__ = '2018-11-08'


def param_to_kwargs(fun):
    '''returns a function that can be called with params = [some_Series].
    The content of Series is added to kwargs'''

    def fun2(*args, **kwargs):
        params = kwargs['params']
        del kwargs['params']
        kwargs.update(params.to_dict())
        return fun(*args, **kwargs)

    return fun2


def param_selector(params, s):
    '''Select parameters from a Series with an Index like a.b.c, a.b.d.

    params is a series with an index that contains strings seperated by "."
    Therefore, params can reflect a hierarchy.
    
    Example::
    
        a.a   1
        a.b   2
        c.x   1
        c.a.b 7
    
    This method allows to select from that Series using a string.
    
    Example::
        
        >>> param_selector(params, 'a'):
        a    1
        b    2
        >>> param_selector(params, 'c.a'):
        b    7
    
    Args:
        params (pd.Series): The parameters.
        s (str): The string to select from the parameters.
        
    Returns:
        pd.Series: The selected parameters.
    '''
    split_char = '.'
    import six
    ssplit = s.split(split_char)
    selection = pd.Series({
        k[len(ssplit[0]) + len(split_char):]: v
        for k, v in six.iteritems(params)
        if k.split(split_char)[0] == ssplit[0]
    })
    if len(ssplit) == 1:
        return selection
    elif len(ssplit) > 1:
        return param_selector(selection, split_char.join(ssplit[1:]))
    else:
        raise ValueError()


def set_fixed_params(params, fixed_params=None):
    """Add fixed_params to params.
    
    Args:
        params (pd.Series): The parameters.
        fixed_params (dict): The fixed parameters.
        
    Returns:
        pd.Series: The parameters with the fixed parameters added.
    """
    assert isinstance(params, pd.Series), 'params should be a pd.Series, but you provided a {}'.format(type(params))
    for k, v in iteritems(fixed_params):
        if not k in params.index:
            params[k] = v
    return params
    # return params.append(fixed_params)
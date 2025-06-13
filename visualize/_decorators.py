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

"""Convenience methods for visualizastion

this module provides decorator functions that can be used to:

- convert dask dataframes to pandas dataframes
- iterate over individual rows of a dataframe
- print the types of some function's arguments (useful for debugging)

"""
import inspect
import dask.dataframe as dd
import pandas as pd
import matplotlib.pyplot as plt

Figure = plt.Figure
Axes = plt.Axes
from data_base.utils import skit

def dask_to_pandas(fun):
    '''Decorator that converts function arguments from dask to pandas.
    
    If a dask dataframe is enctounered in the methods, it is computed, converting it to a pandas dataframe.
    
    Usecase: Allows to write methods for pandas for pandas only,
    and they can then stil be used for dask dataframes by outsourcing the logic of converting dask to pandas.
    
    Args:
        fun: The function to decorate.
        
    Returns:
        The same function, but whose arguments are now pandas instead of dask dataframes when called.
    '''
    dask_instances = tuple(x[1] for x in inspect.getmembers(dd, inspect.isclass))

    def retfun(*args, **kwargs):
        args = list(args)
        for lv, x in enumerate(args):
            if isinstance(x, dask_instances):
                args[lv] = x.compute()
        for name in kwargs:
            if isinstance(kwargs[name], dask_instances):
                kwargs[name] = kwargs[name].compute()
        return fun(*args, **kwargs)

    retfun.__doc__ = fun.__doc__
    return retfun


@dask_to_pandas
def pr(*args, **kwargs):
    """Prints the types of the passed arguments.
    
    Args:
        *args: The arguments to print.
        **kwargs: The keyword arguments to print.
    """

    for x in args:
        print((type(x)))
    for name in kwargs:
        print(('{:s}: {:s}'.format((name, type(kwargs[name])))))


def subsequent_calls_per_line(plotfun):
    '''Call a function on each row of a dataframe separately.
    
    Useful for plotfunctions that are designed to operate on :py:class:`pandas.Series` instances,
    rather than on :py:class:`pandas.DataFrame` instances.
    Also useful for parallelizing plotting functions.
    
    The first input argument (i.e. ``args[0]``) is assumed to be an pd.DataFrame instance. 
    
    If the first n args are of type :py:class:`pandas.DataFrame`, each frame
    will be iterated as described above. 
    In this case, it is assumed that all n DataFrames have the same indexes.
    
    Args:
        plotfun: The function to decorate.
        
    Returns:
        Callable: a function that calls ``plotfun`` on each row of the DataFrame(s).
    '''

    def retfun(*args, **kwargs):
        max_lv = -1
        #count number of consecutive args of type pd.DataFrame
        for lv, x in enumerate(args):
            if isinstance(x, (pd.DataFrame)):
                max_lv = lv
            else:
                break

        if max_lv == -1:
            plotfun_kwargs = skit(plotfun, **kwargs)[0]
            return plotfun(*args, **plotfun_kwargs)

        newargs = list(args)
        if isinstance(x, pd.DataFrame):
            iterator = args[0].iterrows
        else:
            iterator = args[0].iteritems
        for index, row in iterator():
            kwargs['groupby_attribute'] = None
            kwargs['label'] = index
            for lv in range(max_lv + 1):
                newargs[lv] = args[lv].loc[index]
            plotfun_kwargs = skit(plotfun, **kwargs)[0]
            fig = plotfun(*newargs, **plotfun_kwargs)
        return fig

    retfun.__doc__ = plotfun.__doc__
    return retfun


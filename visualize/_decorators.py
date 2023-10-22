import inspect
import dask.dataframe as dd
import pandas as pd
import matplotlib.pyplot as plt

Figure = plt.Figure
Axes = plt.Axes
from model_data_base.utils import skit

##
# todo: this is overcomplicated and should be removed
#
##


class ForceReturnException(Exception):

    def __init__(self, return_value):
        self.return_value = return_value


def dask_to_pandas(fun):
    '''decorator, that checks every passed parameter.
    If subtype of dask.dataframe is found, it is converted
    to the corresponding pandas type.
    
    Usecase: Allows, that plotfunctions are written for pandas
    only and can stil be used for dask dataframes by outsourcing
    the logic of converting dask to pandas.
    '''
    dask_instances = tuple(
        x[1] for x in inspect.getmembers(dd, inspect.isclass))

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
    for x in args:
        print((type(x)))
    for name in kwargs:
        print(('{:s}: {:s}'.format((name, type(kwargs[name])))))


def subsequent_calls_per_line(plotfun):
    '''decorator, that can be used on plotfunctions,
    which require pd.Series as input to be used on groups
    of data.
    
    For this, the first input argument (i.e. args[0]) is
    assumed to be an pd.DataFrame instance. If so, the
    first argument will be replaced by one row of the
    dataframe. plotfun will be called seperately with each
    single row in the dataframe.
    
    If the first n args are of type pd.DataFrame, each frame
    will be iterated as described above. In this case, it is
    assumed, that all n DataFrames have the same indexes.
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


def return_figure_or_axis(plotfun):
    '''decorator, that looks, if the fig attribute is specified in kwargs.
    If fig is specified and isinstance plt.fiugre:
        create axis, replace fig with axis, but return fig
    If fig is specified and isinstance axis:
        do not change kwargs. return axis
    If fig is not specified:
        create figure, create axis, call plotfunction with axis
        return figure
        
    To override this behaviour, the called plot function can raise a
    ForceReturnException. The exception has to contain the value,
    that should be returned.
    '''

    def retfun(*args, **kwargs):
        try:
            if 'fig' in kwargs and kwargs['fig'] is not None:
                fig = kwargs['fig']
                if isinstance(fig, Figure):
                    kwargs['fig'] = fig.add_subplot(1, 1, 1)
                    plotfun(*args, **kwargs)
                    #plt.close(fig)
                    return fig
                if isinstance(fig, Axes):
                    return plotfun(*args, **kwargs)
            else:
                fig = plt.figure()
                kwargs['fig'] = fig.add_subplot(1, 1, 1)
                ret = plotfun(*args, **kwargs)
                #plt.close(fig)
                return fig
        except ForceReturnException as e:
            return e.return_value

    retfun.__doc__ = plotfun.__doc__
    return retfun
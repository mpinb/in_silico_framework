'''
date: 15.09.2016

autor: arco bast

the manylines function allowes to make plots in parallel
'''

import matplotlib.pyplot as plt
import pandas as pd
import dask.dataframe as dd
# import dask
from ._figure_array_converter import fig2np, PixelObject
from ._decorators import return_figure_or_axis, ForceReturnException
# from compatibility import multiprocessing_scheduler

npartitions = 80


@return_figure_or_axis
def manylines(df, axis = None, colormap = None, groupby_attribute = None, \
              fig = None, figsize = (15,3), returnPixelObject = False, get = None):
    '''parallelizes the plot of many lines'''
    assert fig is not None  # decorator takes care, that it is allwys axes
    #     assert get is not None
    if returnPixelObject:
        fig = plt.figure(dpi=400, figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.patch.set_alpha(0.0)
        fig.axes[0].get_xaxis().set_visible(False)
        fig.axes[0].get_yaxis().set_visible(False)
    #if isinstance()
    if isinstance(df, pd.DataFrame):
        if returnPixelObject:
            ret = manylines_helper(df, axis = axis, colormap = colormap, \
                                groupby_attribute = groupby_attribute, fig = None, \
                                returnPixelObject = returnPixelObject)
        else:
            ret = manylines_helper(df, axis = axis, colormap = colormap, \
                                groupby_attribute = groupby_attribute, fig = fig, \
                                returnPixelObject = returnPixelObject)

    elif isinstance(df, dd.DataFrame):
        fun = lambda x: manylines_helper(x, \
                                            fig = None, \
                                            axis = axis, \
                                            colormap = colormap, \
                                            groupby_attribute = groupby_attribute, \
                                            figsize = figsize)

        def fun2(x):
            fig = fun(x)
            return pd.Series({'A': fig2np(fig)})

        # print df.npartitions
        figures_list = df.map_partitions(fun2, meta=('A', 'object'))
        # get = dask.multiprocessing.get if get is None else get
        figures_list = figures_list.compute(
            get=get)  #multiprocessing_scheduler)
        # print figures_list
        # if fig is None: fig = plt.figure(figsize = figsize)
        # plt.axis('off')
        # print figures_list
        if not isinstance(fig, plt.Axes):
            ax = fig.add_subplot(111)
        else:
            ax = fig

        for _, img in enumerate(figures_list.values):
            ax.imshow(img, interpolation='nearest', extent=axis, aspect='auto')
        # raise
        # plt.gca().set_position([0, 0, 1, 1])
        # plt.close(fig)
        ret = fig

    else:
        raise RuntimeError(
            "Supported input: dask.dataframe and pandas.DataFrame. " +
            "Recieved %s" % str(type(df)))

    if returnPixelObject:
        assert isinstance(ret, plt.Figure)
        raise ForceReturnException(PixelObject(axis, fig=ret))
    else:
        return ret

def manylines_helper(pdf, axis = None, colormap = None, groupby_attribute = None, \
                     fig = None, figsize = (15,3), returnPixelObject = False):
    '''helper function which runs on a single core and can be called by map_partitions()'''
    # print('helper_called')
    if not isinstance(pdf, pd.DataFrame):
        raise RuntimeError("Supported input: pandas.DataFrame. " +
                           "Recieved %s" % str(type(pdf)))

    # if called in sequential mode: fig is axes due to decorator return_figure_or_axis of the manylines function
    #if called in parallel mode: fig is explicitly set to None, in this case: create figure
    if fig is None:
        # vgl: http://stackoverflow.com/questions/8218608/scipy-savefig-without-frames-axes-only-content
        fig = plt.figure(dpi=400, figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)

        # axes = plt.axes()
        ax.patch.set_alpha(0.0)
        # ax = fig.add_subplot(1,1,1)
        # ax.set_position([0,0,1,1])
        # fig.tight_layout(pad = 0)

        # plt.axis('off')

        # ax = fig.add_subplot(111)
        fig.axes[0].get_xaxis().set_visible(False)
        fig.axes[0].get_yaxis().set_visible(False)
        # ax.plot([0,1,2,3], [1,2,3,4])
        # ax.axis(axis)

    else:
        ax = fig

    # after this point: fig must be axes object:
    from matplotlib.axes import Axes
    assert isinstance(ax, Axes)

    if groupby_attribute is None:
        for _, row in pdf.iterrows():
            ax.plot(row.index.values, row.values, antialiased=False)
    else:
        for _, row in pdf.iterrows():
            label = row[groupby_attribute]
            row = row.drop(groupby_attribute)
            # print row
            if colormap:
                ax.plot(row.index.values, row.values, antialiased=True, \
                          color = colormap[label], label = label)
            else:
                ax.plot(row.index.values, row.values, antialiased=True, \
                           label = label)

    if axis:
        ax.axis(axis)
    # plt.gca().set_position([0.05, 0.05, 0.95, 0.95])
    # fig.savefig(str(int(np.random.rand(1)*100000)) + '.jpg')

    return fig

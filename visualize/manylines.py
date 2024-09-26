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
import distributed
# from compatibility import multiprocessing_scheduler

npartitions = 80


def manylines(
    df, 
    ax = None, 
    axis = None, 
    colormap = None, 
    groupby_attribute = None, 
    figsize = (15,3), 
    returnPixelObject = False, 
    scheduler=None
    ):
    '''Parallelizes the plot of many lines
    
    Args:
        df (pd.DataFrame): the dataframe containing voltage traces,
        ax (matplotlib.pyplot.Axes): an ax instance.
        axis (list): the ax limits, e.g. [1, 10, 1, 10]
        colormap (dict): a colormap, mapping values for :paramref:groupby_attribute to colors.
        groupby_attribute (str): column name to group by.
        figsize (tupe(int)): the size of the Figure
        returnPixelObject (bool): Whether or not to return as a PixelObject
        scheduler (distributed.client.Client | str, optional): a distributed scheduler.

    Returns:
        fig (matplotlib.pyplot.Figure): Figure object containing all lines defined in :paramref:df
    '''

    if returnPixelObject:
        fig = plt.figure(dpi=400, figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.patch.set_alpha(0.0)
        ax.set_visible(False)
        ax.get_yaxis().set_visible(False)

    elif ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    else:
        fig = ax.get_figure()

    if isinstance(df, pd.DataFrame):
        fig, ax = manylines_helper(
            df, 
            axis = axis, 
            colormap = colormap, 
            groupby_attribute = groupby_attribute, 
            ax = ax if returnPixelObject else None
            )

    elif isinstance(df, dd.DataFrame):
        fun = lambda x: manylines_helper(
            x, 
            ax = None, 
            axis = axis, 
            colormap = colormap, 
            groupby_attribute = groupby_attribute, 
            figsize = figsize)

        def fun2(x):
            fig, _ = fun(x)
            return pd.Series({'A': fig2np(fig)})

        figures_list = df.map_partitions(fun2, meta=('A', 'object'))
        if type(scheduler) == distributed.client.Client:
            figures_list = scheduler.compute(figures_list).result()
        elif type(scheduler) == str:
            figures_list = figures_list.compute(scheduler=scheduler)
        else:
            raise NotImplementedError("Please provide either a distributed.client.Client object, or a string as scheduler.")

        for img in figures_list.values:
            ax.imshow(img, interpolation='nearest', extent=axis, aspect='auto')

    else:
        raise RuntimeError(
            "Supported input: dask.dataframe and pandas.DataFrame. " +
            "Recieved %s" % str(type(df)))

    if returnPixelObject:
        return PixelObject(axis, ax=ax)
    else:
        return fig, ax

def manylines_helper(
        pdf, 
        axis = None, 
        colormap = None, 
        groupby_attribute = None,
        ax = None, 
        figsize = (15,3)
        ):
    '''Helper function which runs on a single core and can be called by map_partitions()

    Args:
        pdf (pd.DataFrame): 
            a pandas DataFrame, each row of which will be plotted out.
        axis (tuple | list, optional): 
            axis limits, e.g. (1, 10, 1, 10)
        colormap (dict): 
            A colormap to use for the plot. 
            Must map a label from :paramref:groupby_attribute to a color
        fig (matplotlib.pyplot.Figure, optional): 
            A Figure object to plot on. 
            If specified, will plot on the current active axis. 
            If not, it will create one.
        figsize (tuple): 
            size of the figure.

    Returns:
        fig (maptlotlib.pyplot.Figure): Figure object containing the lines as specified in pdf.
    '''
    if not isinstance(pdf, pd.DataFrame):
        raise RuntimeError(
            "Supported input: pandas.DataFrame. Recieved %s" % str(type(pdf)))

    if ax is None:
        # vgl: http://stackoverflow.com/questions/8218608/scipy-savefig-without-frames-axes-only-content
        fig = plt.figure(dpi=400, figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.patch.set_alpha(0.0)
        fig.axes[0].get_xaxis().set_visible(False)
        fig.axes[0].get_yaxis().set_visible(False)

    else:
        fig = ax.get_figure()

    
    if groupby_attribute is None:
        for _, row in pdf.iterrows():
            ax.plot(row.index.values, row.values, antialiased=False)
    else:
        for _, row in pdf.iterrows():
            label = row[groupby_attribute]
            row = row.drop(groupby_attribute)
            if colormap:
                ax.plot(
                    row.index.values, 
                    row.values, 
                    antialiased=True,
                    color = colormap[label], 
                    label = label)
            else:
                ax.plot(
                    row.index.values, 
                    row.values, 
                    antialiased=True,
                    label = label)

    if axis:
        ax.axis(axis)
    return fig, ax

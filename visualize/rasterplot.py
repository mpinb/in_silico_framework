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

""" 
Efficiently create rasterplots from spike time dataframes.
"""

# import dask
# import dask.dataframe as dd
# from ._figure_array_converter import fig2np
# from compatibility import multiprocessing_scheduler
import matplotlib.pyplot as plt
from ._decorators import *
from data_base.analyze._helper_functions import is_int
from data_base.utils import convertible_to_int


def rasterplot2(
    st,
    ax=None,
    x_offset=0,
    c=None,
    plot_kwargs=dict(solid_capstyle='butt'),
    y_offset=None,
    y_plot_length=1,
    marker='line'):
    """Plot a rasterplot from a spike times dataframe.

    Args:
        st (pandas.DataFrame): 
            A DataFrame containing the spike times, where each row is a single trial of a single unit.
        ax (matplotlib.axes.Axes, optional): 
            An optional Matplotlib Axes object to plot on. If not provided, a new figure and axes are created.
        x_offset (float, optional): 
            An offset to apply to the x-values (event times). Default is 0.
        c (str or array-like, optional): 
            An optional color for the plot. Can be a single color format string, or a sequence of colors.
        plot_kwargs (dict, optional): 
            Additional keyword arguments for the plot function. Default is {'solid_capstyle': 'butt'}.
        y_offset (int, optional): 
            An optional starting y-value for the plot. If not provided, it is set to the number of rows in the DataFrame.
        y_plot_length (float, optional): 
            The length of the line to plot for each event. Default is 1.
        marker (str, optional): 
            The marker style to use for plotting events. Defaults to 'line'. If 'line', lines of defined length are plotted.
    
    Returns:
        None
    """
    if ax is None:
        ax = plt.figure().add_subplot(111)
    if c is not None:
        plot_kwargs['c'] = c
    st = st[[c for c in st.columns if convertible_to_int(c)]]
    if y_offset is None:
        y = len(st)
    else:
        y = y_offset
    for _, v in st.iterrows():
        if marker == 'line':  # make a line of defined length
            dummy = [([v - x_offset, v - x_offset],
                      [y + y_plot_length / 2., y - y_plot_length / 2.])
                     for v in list(v)]
            for d in dummy:
                ax.plot(d[0], d[1], **plot_kwargs)
        else:  # plot with the specified marker
            dummy_x = [vv - x_offset for vv in list(v)]
            dummy_y = [y for vv in list(v)
                      ]
            ax.plot(dummy_x, dummy_y, marker, **plot_kwargs)

        y = y - 1


def rasterplot2_pdf_grouped(
    pdf,
    grouplabel,
    ax=None,
    xlim=None,
    x_offset=0,
    color='k'):
    """Plot a rasterplot per group fo a spike times dataframe.
    
    Similar to :py:meth:`~rasterplot2`, this method plots a rasterplot from a spike times dataframe,
    but groups them with horizontal lines, based on the grouplabel.
    Assumes the spike times dataframe has a column :paramref:`grouplabel`
    
    Args:
        pdf (pandas.DataFrame):
            A DataFrame containing the spike times.
            Must contain a column with label :paramref:`grouplabel`.
        grouplabel (str):
            The column name in the DataFrame to group by.
        ax (matplotlib.axes.Axes, optional):
            An optional Matplotlib Axes object to plot on. If not provided, a new figure and axes are created.
        xlim (tuple, optional):
            The x-axis limits for the plot. Default is ``None``.
        x_offset (float, optional):
            An offset to apply to the x-values (event times). Default is 0.
        color (str, optional):
            The color to use for the plot. Default is 'k'.

    Returns:
        None.
    """
    if ax is None:
        fig = plt.figure(figsize=(7, 4), dpi=600)
        ax = fig.add_subplot(111)
    yticks = []
    ylabels = []
    offset = 0
    labels = pdf[grouplabel].drop_duplicates()
    for label in labels:
        df = pdf[pdf[grouplabel] == label]
        offset += len(df)
        rasterplot2(
            df, 
            ax = ax, 
            y_offset=offset, 
            x_offset = x_offset,
            plot_kwargs = {'c': color, 'linewidth': 2, 'solid_capstyle': 'butt'})
        plt.axhline(offset, c='grey', linewidth=.1)
        yticks.append(offset - len(df) / 2.)
        ylabels.append(label)
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.set_ylim(0, offset + .2)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels)
    try:
        import seaborn as sns
        sns.despine()
    except ImportError:
        pass
    try:
        from IPython import display
        display.display(fig)
    except (ImportError, UnboundLocalError):
        pass
    # plt.close()


@dask_to_pandas
def rasterplot(
    df,
    colormap=None,
    ax=None,
    label=None,
    groupby_attribute=None,
    tlim=None,
    reset_index=True):
    '''Creates a rasterplot from spike times dataframe.
    
    If df is a dask.DataFrame: parallel plotting is used (not recommended, causes bad quality)
    If df is a pandas.DataFrame, serial plotting is used

    Args:
        df (pandas.DataFrame):
            A DataFrame containing the spike times.
        colormap (dict, optional):
            A colormap to use for the plot. 
            Must map a label from :paramref:`groupby_attribute` to a color.
        ax (matplotlib.axes.Axes, optional):
            An optional Matplotlib Axes object to plot on. If not provided, a new figure and axes are created.
        label (str, optional):
            The label for the plot. Default is ``None``.
        groupby_attribute (str, optional):
            The column name in the DataFrame to group by. Default is ``None``.
        tlim (tuple, optional):
            The x-axis limits for the plot. Default is ``None``.
        reset_index (bool, optional):
            If True, reset the index of the DataFrame. Default is ``True``.

    Returns:
        matplotlib.pyplot.Figure: Figure object containing the rasterplot. 
    '''

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)
    else:
        fig = ax.get_figure()
    if reset_index:
        df = df.reset_index()

    if groupby_attribute:
        groups = df.groupby(groupby_attribute)
        for label, group_df in groups:
            rasterplot(
                group_df,
                colormap=colormap,
                ax=ax,
                label=label,
                groupby_attribute=None,
                reset_index=False)
        return fig

    relevant_columns = [_ for _ in df.columns if is_int(_)]
    df = df[relevant_columns]
    times_all = []
    trials_all = []

    # fig.patch.set_alpha(0.0)
    # axes = plt.axes()
    # axes.patch.set_alpha(0.0)

    for index, row in df.iterrows():
        row = list(row)
        times = [time for time in row if is_int(time)]
        times_all.extend(times)
        trials_all.extend([index] * len(times))
    if colormap:
        color = colormap[label]
        ax.plot(times_all, trials_all, 'k|', color=color, label=label)
    else:
        ax.plot(times_all, trials_all, 'k|', label=label)
    if tlim:
        ax.set_xlim(tlim)
    # plt.gca().set_position([0.05, 0.05, 0.95, 0.95])
    return fig



######################################
# currently not used: version supporting parralel plotting

# import pandas as pd
# import dask
# import dask.dataframe as dd
# import matplotlib.pyplot as plt
# from _decorators import *
# from ..settings import multiprocessing_scheduler
# from ..analyze._helper_functions import is_int
# from _figure_array_converter import fig2np
#
#
# @return_figure_or_axis
# def rasterplot(df, colormap = None, fig = None, label = None, groupby_attribute = None, tlim = None, figsize = (15,3)):
#     '''
#     creates a rasterplot,
#     expects dataframe in the usual spike times format
#
#     if df is a dask.DataFrame: parallel plotting is used (not recommended, causes bad quality)
#     if df is a pandas.DataFrame, serial plotting is used
#     '''
#     df = df.reset_index()
#
#     if isinstance(df, pd.DataFrame):
#         fun = lambda x: rasterplot_pd(x, colormap = colormap, fig = fig, label = label, groupby_attribute = groupby_attribute, tlim = tlim, figsize = figsize)
#         return fun(df)
#
#     elif isinstance(df, dd.DataFrame):
#         if tlim is None:
#             raise ValueError("For parallel execution, which is enabled by passing a dask dataframe, tlim has to be set like [0 300]")
#
#         fun = lambda x: rasterplot_pd(x, colormap = colormap, fig = None, label = label, groupby_attribute = groupby_attribute, tlim = tlim, figsize = figsize)
#         fun2 = lambda x: pd.Series({'A': fig2np(fun(x))})
#         figures_list = df.map_partitions(fun2).compute(scheduler=dask.async.get_sync)
#
#         plt.axis('off')
#         #print figures_list
#         for lv, img in enumerate(figures_list.values):
#             ax = fig.imshow(img, interpolation='nearest') #be aware: decorator handles figure and allways passes axes as fig argument
#
#         fig.set_position([0, 0, 1, 1])
#         #plt.close(fig)
#         #print('asdasdasdasd: %s' % type(fig))
#         return fig
#
#
#
# @return_figure_or_axis
# def rasterplot_pd(df, colormap = None, fig = None, label = None, groupby_attribute = None, tlim = None, figsize = (15,3)):
#
#     if groupby_attribute:
#         groups = df.groupby(groupby_attribute)
#         for label, group_df in groups:
#             rasterplot_pd(group_df, colormap=colormap, fig=fig, label = label, groupby_attribute = None)
#         return fig
#
#     relevant_columns = [_ for _ in df if is_int(_)]
#     times_all = []
#     trials_all = []
#     ax = fig #fig.add_subplot(1,1,1)
#
#     fig.patch.set_alpha(0.0)
#     axes = plt.axes()
#     axes.patch.set_alpha(0.0)
#
#
#     for index, row in df.iterrows():
#         row = list(row)
#         times = [time for time in row if is_int(time)]
#         times_all.extend(times)
#         trials_all.extend([index]*len(times))
#     if colormap:
#         color =  colormap[label]
#         ax.plot(times_all, trials_all, 'k|', color = color, label = label)
#     else:
#         ax.plot(times_all, trials_all, 'k|', label = label)
#     if tlim:
#         ax.set_xlim(tlim)
#     plt.gca().set_position([0.05, 0.05, 0.95, 0.95])
#     try:
#         plt.close(fig)
#     except TypeError:
#         pass
#
#     return fig
#

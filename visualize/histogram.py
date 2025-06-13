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

"""Plot line histograms

This module provides convenience methods for plotting line histograms (so no filled surfaces) from precomputed bins.
This is used to plot out e.g. activity data for multiple populations.
"""
from ._decorators import *

@dask_to_pandas
@subsequent_calls_per_line
def histogram(
    hist_bins,
    colormap=None,
    ax=None,
    label=None,
    groupby_attribute=None):
    '''Efficiently plot a histogram from bins.
    
    Uses the decorated function :py:meth:`subsequent_calls_per_line` to speed up plotting bins from pandas or dask dataframes.
    
    Supports groups: simply pass a Series of the format::
    
        labelA: (bins,hist)
        labelB: (bins,hist)
    
    In this case, the label attribute has no function (to be precise: it is overwritten by the decorator subsequent_calls_per_line)
    
    Args:
        hist_bins (tuple): tuple of the format (bins,hist) where bins are the bin edges and hist the bin values. Length of bins needs to be one element longer than hist.
        colormap (dict): dictionary with labels as keys and colors as values. Default is ``None``.
        ax (Axes): The matplotlib axes object. Default is ``None``.
        label (str): The label of the histogram. Default is ``None``.
        
    Returns:
        None
    '''

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    if isinstance(hist_bins, pd.Series):
        hist_bins = hist_bins.iloc[0]

    bins = hist_bins[0]
    hist = hist_bins[1]
    # add points, so stepfunction allways starts and ends on the x-axis
    x = list(bins) + [bins[-1]]
    y = [0] + list(hist) + [0]

    if colormap:
        color = colormap[label]
        ax.step(x, y, color=color, label=label)
    else:
        ax.step(x, y, label=label)

    #try:
    #    plt.close(fig)
    #except TypeError:
    #    pass

    return ax.get_figure()


def histogram2(hist_bins, color=None, ax=None, label=None, mode='step'):
    '''Plot a histogram from bins.
    
    Does not use the decorated function :py:meth:`subsequent_calls_per_line` like :py:meth:`histogram`.
    
    Args:
        hist_bins (tuple): tuple of the format (bins,hist) where bins are the bin edges and hist the bin values. Length of bins needs to be one element longer than hist.
        color (str): The color of the histogram. Default is ``None``.
        ax (Axes): The matplotlib axes object. Default is ``None``.
        label (str): The label of the histogram. Default is ``None``.
        mode (str): The mode of the histogram. Default is `step`. Options: ('step', 'filled').
        
    Returns:
        None
    '''

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)


    bins, hist = hist_bins

    # add points, so we always start  at 0
    x = [bins[0]]
    y = [0]
    # create line that goes in rectangular steps
    for lv in range(len(hist)):
        x += [bins[lv], bins[lv + 1]]
        y += [hist[lv], hist[lv]]
    # add points so we always end at 0
    x += [bins[-1]]
    y += [0]

    if mode == 'step':
        ax.step(x, y, color=color, label=label)
    elif mode == 'filled':
        plt.fill_between(
            x,
            y, [0] * len(x),
            color=color,
            label=label,
            linewidth=0)

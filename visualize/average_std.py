'''
Created on Sep 16, 2016

@author: arco
'''

from ._decorators import dask_to_pandas, subsequent_calls_per_line, return_figure_or_axis


@dask_to_pandas
@return_figure_or_axis  #has to stand above subsequent_calls_per_line
@subsequent_calls_per_line
def average_std(mean,
                std,
                colormap=None,
                fig=None,
                label=None,
                groupby_attribute=None,
                mode='ms',
                axis=None):

    t = mean.index.values.astype("float64")
    mean = mean.values.astype("float64")
    std = std.values.astype("float64")

    ax = fig  #.add_subplot(1,1,1) ###taken care by decorator return_figure_or_axis
    if colormap:
        color = colormap[label]
    else:
        color = 'b'

    plot = ax.plot(t, mean, zorder=3, label=label, color=color)
    if 's' in mode:
        ax.plot(t,
                mean + std,
                zorder=3,
                color=plot[0].get_color(),
                linewidth=0.3,
                alpha=0.3)
        ax.plot(t,
                mean - std,
                zorder=3,
                color=plot[0].get_color(),
                linewidth=0.3,
                alpha=0.3)
        ax.fill_between(t,
                        mean + std,
                        mean - std,
                        zorder=2,
                        alpha=0.1,
                        linewidth=0.0,
                        color=color)

    #if axis: ax.axis(axis)

    return fig

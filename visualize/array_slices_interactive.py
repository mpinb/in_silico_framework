import numpy as np
import pandas as pd
from ipywidgets import interact
import matplotlib.pyplot as plt
from .histogram import histogram


def get_slice_by_x_value(array, xmin, xmax, x):
    step = (xmax - xmin) / float(array.shape[1] - 1)
    nr = list(np.arange(xmin, xmax + step, step))
    #nr = nr.index(min(nr, key=lambda y:abs(y-x))) # get closest value
    nr = [lv for lv in range(len(nr)) if nr[lv] <= x and nr[lv + 1] >= x]
    nr = nr[0]
    return array[:, nr]


def rebin_slice(slice_, min_, max_, wished_binsize, scale_last_bin=False):
    current_binsize = (max_ - min_) / float((len(slice_)))
    if wished_binsize < current_binsize:
        raise ValueError(
            "The current binsize is %s. The wished binsize may not be smaller than this."
            % str(current_binsize))

    nr_consecutive_bins = int(wished_binsize / current_binsize)
    effective_binsize = current_binsize * nr_consecutive_bins
    from six.moves import range as xrange
    print(("effective binsize: {:s}".format(effective_binsize)))
    newslice = [
        sum(slice_[current:current + nr_consecutive_bins])
        for current in xrange(0, len(slice_), nr_consecutive_bins)
    ]
    newbins = np.arange(min_, min_ + effective_binsize * (len(newslice) + 1),
                        effective_binsize)
    assert len(newbins) == len(newslice) + 1  #

    return effective_binsize, np.array(list(newbins)), np.array(list(newslice))


def slider_plot_helper(array,
                       x,
                       xmin,
                       xmax,
                       ymin,
                       ymax,
                       wished_binsize=None,
                       axis=0):
    #for other axis: shuffle arguments
    if axis == 1:
        return slider_plot_helper(array.T,
                                  x,
                                  ymin,
                                  ymax,
                                  xmin,
                                  xmax,
                                  wished_binsize=wished_binsize,
                                  axis=0)
    slice_ = get_slice_by_x_value(array, xmin, xmax, x)
    if wished_binsize is None:
        current_binsize = (ymax - ymin) / float(
            (len(slice_)))  #set wished binsize to current binsize

    effective_binsize, newbins, newslice = rebin_slice(slice_, ymin, ymax,
                                                       wished_binsize)
    #print(effective_binsize)
    return newbins, newslice


def make_plots(pixelObjects,
               x,
               wished_binsize=None,
               axis=0,
               normalize_factors=None):
    out = {}
    import six
    for name, pixelObject in six.iteritems(pixelObjects):
        array = pixelObject.array
        extent = pixelObject.extent
        newbins, newslice = slider_plot_helper(array, x, extent[0], extent[1], extent[2], extent[3], \
                                             wished_binsize = wished_binsize, axis = axis)
        if normalize_factors:
            newslice = newslice / normalize_factors[name]
        out.update({name: (newbins, newslice)})
    return pd.Series(out)


def set_everything_up(pixelObjects, axis=0, normalize_factors=None):
    if axis == 0:
        xmin = pixelObjects.iloc[0].extent[0]
        xmax = pixelObjects.iloc[0].extent[1]
        ymin = pixelObjects.iloc[0].extent[2]
        ymax = pixelObjects.iloc[0].extent[3]
    if axis == 1:
        xmin = pixelObjects.iloc[0].extent[2]
        xmax = pixelObjects.iloc[0].extent[3]
        ymin = pixelObjects.iloc[0].extent[0]
        ymax = pixelObjects.iloc[0].extent[1]

    @interact(x=(xmin, xmax, 1),
              wished_binsize=(0, 10, .1),
              xmin=(ymin, ymax),
              xmax=(ymin, ymax))
    def fun2(x=261, wished_binsize=1, xmin=ymin, xmax=ymax):
        fig = plt.figure()
        hist = make_plots(pixelObjects,
                          x,
                          wished_binsize=wished_binsize,
                          axis=axis,
                          normalize_factors=normalize_factors)
        silent = histogram(hist, fig=fig)
        fig.axes[0].set_xlim(xmin, xmax)
        return fig

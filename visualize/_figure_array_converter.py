'''
autor: arco
date: 16.09.2016
'''
import numpy as np
from ._decorators import return_figure_or_axis


class PixelObject():
    '''holds all the information necessary to reconstruct a plot out of an array'''

    def __init__(self, extent, fig=None, array=None):
        s = "either fig or array has to be specified"
        if fig is None and array is None:
            raise ValueError(s)
        if not fig is None and not array is None:
            raise ValueError(s)
        if not extent:
            raise ValueError(
                "extent / axis has to be specified to generate PixelObject")
        self.extent = extent

        if isinstance(array, np.ndarray):
            self.array = array

        if fig is not None:
            self.array = fig2np(fig)


@return_figure_or_axis
def show_pixel_object(pixelObject, fig=None):
    fig.imshow(pixelObject.array,
               interpolation='nearest',
               extent=pixelObject.extent,
               aspect='auto')
    return fig


def fig2np(fig):
    '''Converts fig-object to np-array as described here by Joe Kington:
    http://stackoverflow.com/questions/7821518/matplotlib-save-plot-to-numpy-array'''

    # If we haven't already shown or saved the plot, then we need to
    # draw the figure first...
    fig.tight_layout(pad=0)
    fig.canvas.draw()

    # Get the RGBA buffer from the figure #http://blogs.candoerz.com/question/169767/pylab-use-plot-result-as-image-directly.aspx
    w, h = fig.canvas.get_width_height()
    buf = np.fromstring(fig.canvas.tostring_argb(), dtype=np.uint8)
    buf.shape = (h, w, 4)

    # canvas.tostring_argb give pixmap in ARGB mode. Roll the ALPHA channel to have it in RGBA mode
    buf = np.roll(buf, 3, axis=2)
    return buf

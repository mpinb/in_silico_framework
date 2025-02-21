'''
autor: arco
date: 16.09.2016
'''
import numpy as np


class PixelObject():
    '''Dataclass to hold pixel information from either a :py:class:`matplotlib.pyplot.Axes` or a numpy array.
    
    Attributes:
        extent (list): The extent of the plot.
        array (numpy.ndarray): The pixel array of the plot.
        
    Raises:
        ValueError: If neither an ax nor an array is specified.
        ValueError: If both an ax and an array are specified
    '''

    def __init__(self, extent, ax=None, array=None):
        """
        Args:
            extent (list): The extent of the plot.
            ax (matplotlib.pyplot.Axes): The axis to convert to a pixel array. Default is `None`.
            array (numpy.ndarray): The pixel array to store. Default is `None`.
        """
        if ax is None and array is None:
            raise ValueError("Please specify an ax or an array (not both)")
        if not ax is None and not array is None:
            raise ValueError("Please specify either an ax, or an array, not both)")
        if not extent:
            raise ValueError(
                "extent / axis has to be specified to generate PixelObject")
        self.extent = extent

        if isinstance(array, np.ndarray):
            self.array = array

        if ax is not None:
            fig = ax.get_figure()
            print(ax)
            print(fig)
            self.array = fig2np(fig)


def show_pixel_object(pixelObject, ax=None):
    """ Displays a PixelObject on an axis

    Args:
        pixelObject (PixelObject): the PixelObject to display
        ax (matplotlib.pyplot.Axes): the axis to display the PixelObject on

    Returns:
        ax (matplotlib.pyplot.Axes): the axis with the PixelObject displayed    
    """
    ax.imshow(pixelObject.array,
               interpolation='nearest',
               extent=pixelObject.extent,
               aspect='auto')
    return ax


def fig2np(fig):
    '''Converts fig-object to pixels as numpy arrays.
    
    This method converts figure objects to numpy arrays.
    These numpy arrays are RGB pixel matrices.
    
    See also:
        http://stackoverflow.com/questions/7821518/matplotlib-save-plot-to-numpy-array
    
    Args:
        fig (matplotlib.pyplot.Figure): The figure object to convert to a numpy array.
        
    Returns:
        numpy.ndarray: The numpy array of the figure.    
    '''

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

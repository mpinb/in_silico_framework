"""Display animations in IPython sessions.

This module proivdes functionality to create and render anmations in an IPython session.
It is of particular use when using Jupyter notebooks.
"""

import numpy as np
import copy
import matplotlib.pyplot as plt
# import dask
import os
import glob
import IPython
import jinja2
import functools
from base64 import b64encode
import multiprocessing
from data_base.utils import chunkIt

html_template = 'animation_template.html'


def find_nearest(array, value):
    """Finds the index of the value in the array that is closest to the value specified in the arguments
    
    See also:
        https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
        
    :skip-doc:
    """
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def get_default_axis(range_var):
    """:skip-doc:"""
    if range_var == 'Vm':
        return (0, 1600), (-80, 0)
    if range_var == 'Ih.gIh':
        return (0, 1600), (-2 * 10e-5, 2 * 10e-5)
    if range_var == 'na_ion':
        return (0, 1600), (0, 300)
    if range_var == 'Ca_HVA.ica':
        return (0, 1600), (-500 * 10e-5, 2 * 10e-5)
    if range_var == 'Ca_LVAst.ica':
        return (0, 1600), (-500 * 10e-5, 2 * 10e-5)
    else:
        return (0, 1600), (-2 * 10e-5, 2 * 10e-5)


def _load_base64(filename, extension='png'):
    """Load a file and encode it in base64.
    
    This is used to load images and embed them in an html file, such as Jupyter notebooks.
    
    Args:
        filename (str): path to file
        extension (str): the file extension. Default: 'png'
        
    Returns:
        str: base64 encoded string
    
    See also:
        https://github.com/jakevdp/JSAnimation/blob/master/JSAnimation/html_writer.py
    """
    with open(filename, 'rb') as f:
        data = f.read()
    return 'data:image/{0};base64,{1}'.format(
        extension,
        b64encode(data).decode('ascii'))


def display_animation(
    files,
    interval=10,
    style=False,
    animID=None,
    embedded=False):
    '''Creates an IPython animation out of files specified in a globstring or a list of paths.
     
    Args:
        files (str | list): globstring or list of paths
        interval (int): time interval between frames
        style (bool): whether to use the style specified in the system default html_template.
        animID: unique integer to identify the animation in the javascript environment of IPython
        embedde  (bool): whether to embed the images as base64 in the html file.
    
    Attention: 
        The paths need to be relative to the location of the ipynb / html file, since
        the are resolved in the browser and not by python
    
    Returns:
        IPython.display.HTML: the animation object    
    '''
    if animID is None:
        animID = np.random.randint(
            10000000000000)  # needs to be unique within one ipynb
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template(html_template)

    if isinstance(files, str):
        if os.path.isdir(files):  # folder provieded --> convert to globstring
            files = os.path.join(files, '*.png')
        listFrames = sorted(glob.glob(files))
    else:
        listFrames = files
    if embedded:
        listFrames = [_load_base64(f) for f in listFrames]
    htmlSrc = template.render(ID=animID,
                              listFrames=listFrames,
                              interval=interval,
                              style=style)

    IPython.display.display(IPython.display.HTML(htmlSrc))


def find_closest_index(list_, value):
    '''Finds the index of the value which is closest to the value specified in the arguments
    
    Args:
        list_ (list): list of values
        value (float): value to find closest index for
        
    Returns:
        int: index of the value in the list'''
    m = min(list(range(len(list_))), key=lambda i: abs(list_[i] - value))
    return m


def get_synapse_points(cell, n):
    """:skip-doc:"""
    pass


def get_lines(cell, time_index, range_vars='Vm'):
    '''Get list of dictionaries of lines that can be displayed using the :py:meth:`plot_lines` function
    
    This is used to generate videos of membrane voltage vs soma distance.
    
    Args:
        cell (:py:class:`single_cell_parser.cell.Cell`): cell object
        time_index (int): index of the time vector
        range_vars (str): range variable to plot
        
    Returns:
        list: list of dictionaries of lines
    '''
    difference_limit = 1
    if isinstance(range_vars, str):
        range_vars = [range_vars]

    cmap = {
        'Soma': 'k',
        'Dendrite': 'b',
        'ApicalDendrite': 'r',
        'AIS': 'g',
        'Myelin': 'y',
        'SpineNeck': 'cyan',
        'SpineHead': 'orange'
    }
    out_all_lines = []
    points_lines = {}  # contains data to be plotted as points
    for currentSec in cell.sections:
        if currentSec.label == "Soma":  #don't plot soma
            continue

        out = {}
        currentSec_backup = currentSec

        parentSec = currentSec.parent

        #compute distance from current section to soma
        dist = 0.0
        parentLabel = parentSec.label

        while parentLabel != 'Soma':
            dist += parentSec.L * currentSec.parentx
            currentSec = parentSec
            parentSec = currentSec.parent
            parentLabel = parentSec.label

        parent_idx = find_nearest(currentSec_backup.parent.relPts,
                                  currentSec_backup.parentx)
        parent_idx_segment = find_nearest(currentSec_backup.parent.segx,
                                          currentSec_backup.parentx)

        #now calculate it segment wise.
        #First point is branchpoint of parent section, because otherwise there will be a gap in the plot
        distance_dummy = [
            dist
        ]  #  + currentSec_backup.parent.relPts[parent_idx]*currentSec_backup.parent.L]
        #calculate each segment distance
        for seg in currentSec_backup:
            distance_dummy.append(dist + seg.x * currentSec_backup.L)

        # voltage traces are a special case
        if range_vars[0] == 'Vm':
            traces_dummy = [
                currentSec_backup.parent.recVList[parent_idx_segment][time_index]
            ]
            for vec in currentSec_backup.recVList:
                traces_dummy.append(vec[time_index])
        # other range vars are saved differently in the cell object compared to Vm
        else:
            vec_list = []  # currentSec_backup.recordVars[range_vars[0]]
            try:
                traces_dummy = [
                    currentSec_backup.parent.recordVars[range_vars[0]]
                    [parent_idx_segment][time_index]
                ]
            except:
                traces_dummy = [np.NaN]
            if not currentSec_backup.recordVars[range_vars[0]]:
                traces_dummy.append(np.nan)
                continue  #if range mechanism is not in section: continue
            for vec in currentSec_backup.recordVars[range_vars[0]]:
                traces_dummy.append(vec[time_index])
                #sec.recordVars[range_vars[0]][lv_for_record_vars]
        
        assert(len(distance_dummy) == len(traces_dummy))
        if len(distance_dummy) == 2:
            label = currentSec_backup.label
            if not label in list(points_lines.keys()):
                points_lines[label] = {}
                points_lines[label]['x'] = []
                points_lines[label]['y'] = []
                points_lines[label]['color'] = cmap[label]
                points_lines[label]['marker'] = '.'
                points_lines[label]['linestyle'] = 'None'
                points_lines[label]['t'] = cell.tVec[time_index]
            difference = np.abs(traces_dummy[1] - traces_dummy[0])
            points_lines[label]['x'].append(distance_dummy[1] if difference >
                                            difference_limit else float('nan'))
            points_lines[label]['y'].append(traces_dummy[1])

        else:
            out['x'] = distance_dummy
            out['y'] = traces_dummy
            out['color'] = cmap[currentSec_backup.label]
            out['label'] = currentSec_backup.label
            out['t'] = cell.tVec[time_index]
            out_all_lines.append(out)
    out_all_lines.extend(list(points_lines.values()))
    return out_all_lines


#%time silent = [get_lines(cell, i) for i in range(1000)]


def init_fig(xlim=(0, 1500), ylim=(-80, 0)):
    """Initialize figure for :py:meth:`cell_to_animation`
    
    Args:
        xlim (tuple): x axis limits
        ylim (tuple): y axis limits
        
    Returns:
        tuple: figure and axis object
    """
    fig = plt.figure(figsize=(5, 3), dpi=72)
    ax = fig.add_subplot(111)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return fig, ax


def plot_lines_fun(lines, ax):
    '''Generate plots out of lines 
    
    Args:
        lines (list): list of dictionaries of lines. Generated by :py:meth:`get_lines`
        ax: axis object
        
    Returns:
        list: list of line objects'''
    out_lines = []
    lines = copy.deepcopy(lines)
    for line in lines:
        x = line['x']
        y = line['y']
        t = line['t']
        del line['x']
        del line['y']
        del line['t']

        dummy, = ax.plot(x, y, **line)
        out_lines.append(dummy)
        ax.set_title("%.3f" % t)
    return out_lines


#@dask.delayed(traverse = False)
def _in_parallel_context(paths, lines_objects, xlim=(0, 1500), ylim=(-80, 0)):
    
    '''Helper function to launch generation of images in parallel
    
    Some ideas how to speed up figure drawing are taken from: http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
    
    Args:
        paths (list): list of paths where to save images
        lines_objects (list): list of dictionaries of lines
        xlim (tuple): x axis limits
        ylim (tuple): y axis limits
        
    Returns:
        None
    '''
    fig, ax = init_fig(xlim, ylim)
    plot_lines = plot_lines_fun(lines_objects[0], ax)

    for path, lines_object in zip(paths, lines_objects):
        for line, plot_line in zip(lines_object, plot_lines):
            plot_line.set_ydata(line['y'])
            ax.set_title("%.3f" % line['t'])
        fig.savefig(path)
    plt.close()


def parallelMovieMaker(basedir, lines, xlim=(0, 1500), ylim=(-80, 0)):
    '''Creates figures in parallel and returns animation object.
    
    Args:
        basedir (str): path to store images
        lines (list): list of dictionaries of lines (generated by function generate_lines)
        xlim (tuple): limits of x axis
        ylim (tuple): limits of y axis
        
    Returns:
        list: list of paths to images
    '''
    print("parallelMovieMaker")
    import tempfile
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    basepath = tempfile.mkdtemp(dir=basedir, prefix='animation_')
    print("files are here: {}".format(os.path.join(basepath, '*.png')))
    paths = [
        os.path.join(basepath,
                     str(i).zfill(6) + '.png') for i in range(len(lines))
    ]

    # split paths and lines in chunks
    paths_chunks = chunkIt(paths, multiprocessing.cpu_count())
    lines_chunks = chunkIt(lines, multiprocessing.cpu_count())
    delayed_list = [_in_parallel_context(path, line, xlim = xlim, ylim = ylim) \
                    for path, line in zip(paths_chunks, lines_chunks)]

    #dask.compute(delayed_list, scheduler="multiprocessing", optimize = False)
    #print "start computing"
    #dask.delayed(delayed_list).compute(scheduler="multiprocessing", optimize = False)

    return paths

def cell_to_animation(
    cell, 
    xlim = None, 
    ylim = None, 
    tstart = 245, 
    tend = 310, 
    tstep = 1,
    range_vars = 'Vm', 
    plot_synaptic_input = False,
    outdir = 'animation'):
    '''Takes a cell object and creates a 2d animation plotting the range_vars vs soma distance over time.
    
    Args:
        outdir (str): folder, where animation should be saved. The result will be .png files.
    
        xlim (tuple): tuple like (0, 1600) that defines the limits of the x axis.
                If None, tries to get default values for range var from get_default_axis
                Default: None. 
        ylim (tuple): tuple like (-80 0) that defines the limits of the y axis
                If None, tries to get default values for range var from get_default_axis
                Default: None.     
        tstart (float): time when animation should be started
        tend (float): time when animation should be stopped
        tstep (float): timestep between frames
        range_vars (str | list): str or list of str: range vars to display, default: 'Vm'
        
    Returns:
        list: list of paths to images
    '''

    if isinstance(range_vars, str):
        range_vars = [range_vars]
    indices = [
        find_closest_index(cell.tVec, i)
        for i in np.arange(tstart, tend, tstep)
    ]  #in case of vardt, pic
    lines = [get_lines(cell, index, range_vars=range_vars) for index in indices]
    if xlim is None and ylim is None:
        xlim, ylim = get_default_axis(range_vars[0])
    paths = parallelMovieMaker(outdir, lines, xlim=xlim, ylim=ylim)
    return paths


@functools.wraps(cell_to_animation)
def cell_to_ipython_animation(*args, **kwargs):
    """Wrapper function to display the animation in the IPython notebook
    
    
    Args:
        *args: arguments for :py:meth:`cell_to_animation`
        **kwargs: keyword arguments for :py:meth:`cell_to_animation`
        
    Returns:
        IPython.display.HTML: the animation object
    """
    try:
        embedded = kwargs['embedded']
        del kwargs['embedded']
    except KeyError:
        embedded = False
    paths = cell_to_animation(*args, **kwargs)
    ani = display_animation(paths, embedded=embedded)
    return ani

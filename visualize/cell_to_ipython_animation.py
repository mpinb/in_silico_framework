import numpy as np
import matplotlib.pyplot as plt
# import dask
import os
import glob
import IPython
import jinja2
import functools
from base64 import b64encode
import multiprocessing
from model_data_base.utils import chunkIt

html_template = 'animation_template.html'


def find_nearest(array, value):
    'https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array'
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def get_default_axis(range_var):
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
    #https://github.com/jakevdp/JSAnimation/blob/master/JSAnimation/html_writer.py
    with open(filename, 'rb') as f:
        data = f.read()
    return 'data:image/{0};base64,{1}'.format(extension,
                                              b64encode(data).decode('ascii'))


def display_animation(files,
                      interval=10,
                      style=False,
                      animID=None,
                      embedded=False):
    '''creates an IPython animation out of files specified in a globstring or a list of paths.
     
    animID: unique integer to identify the animation in the javascript environment of IPython
    files: globstring or list of paths
    interval: time interval between frames
    
    CAVEAT: the paths need to be relative to the location of the ipynb / html file, since
    the are resolved in the browser and not by python'''
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
    '''returns index of value within list_, which is closest to the value specified in the arguments'''
    m = min(list(range(len(list_))), key=lambda i: abs(list_[i] - value))
    return m


def get_synapse_points(cell, n):
    pass


def get_lines(cell, n, range_vars='Vm'):
    '''returns list of dictionaries of lines that can be displayed using the plot_lines function'''
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
                currentSec_backup.parent.recVList[parent_idx_segment][n]
            ]
            for vec in currentSec_backup.recVList:
                traces_dummy.append(vec[n])
        # other range vars are saved differently in the cell object compared to Vm
        else:
            vec_list = []  # currentSec_backup.recordVars[range_vars[0]]
            try:
                traces_dummy = [
                    currentSec_backup.parent.recordVars[range_vars[0]]
                    [parent_idx_segment][n]
                ]
            except:
                [np.NaN]
            if not vec_list:
                continue  #if range mechanism is not in section: continue
            for vec in vec_list:
                traces_dummy.append(vec[n])
                #sec.recordVars[range_vars[0]][lv_for_record_vars]

        if len(distance_dummy) == 2:
            label = currentSec_backup.label
            if not label in list(points_lines.keys()):
                points_lines[label] = {}
                points_lines[label]['x'] = []
                points_lines[label]['y'] = []
                points_lines[label]['color'] = cmap[label]
                points_lines[label]['marker'] = '.'
                points_lines[label]['linestyle'] = 'None'
                points_lines[label]['t'] = cell.tVec[n]
            difference = np.abs(traces_dummy[1] - traces_dummy[0])
            points_lines[label]['x'].append(distance_dummy[1] if difference >
                                            difference_limit else float('nan'))
            points_lines[label]['y'].append(traces_dummy[1])

        else:
            out['x'] = distance_dummy
            out['y'] = traces_dummy
            out['color'] = cmap[currentSec_backup.label]
            out['label'] = currentSec_backup.label
            out['t'] = cell.tVec[n]
            out_all_lines.append(out)
    out_all_lines.extend(list(points_lines.values()))
    return out_all_lines


#%time silent = [get_lines(cell, i) for i in range(1000)]


def init_fig(xlim=(0, 1500), ylim=(-80, 0)):
    fig = plt.figure(figsize=(5, 3), dpi=72)
    ax = fig.add_subplot(111)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return fig, ax


import copy


def plot_lines_fun(lines, ax):
    '''generate plots out of lines '''
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
    # some ideas how to speed up figure drawing are taken from here:
    # http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
    '''helper function to launch generation of images in parallel'''
    fig, ax = init_fig(xlim, ylim)
    plot_lines = plot_lines_fun(lines_objects[0], ax)

    for path, lines_object in zip(paths, lines_objects):
        for line, plot_line in zip(lines_object, plot_lines):
            plot_line.set_ydata(line['y'])
            ax.set_title("%.3f" % line['t'])
        fig.savefig(path)
    plt.close()


def parallelMovieMaker(basedir, lines, xlim=(0, 1500), ylim=(-80, 0)):
    '''creates figures in parallel and returns animation object.
    basedir: path to store images
    lines: list of dictionaries of lines (generated by function generate_lines)
    xlim: limits of x axis
    ylim: limits of y axis
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

    #dask.compute(delayed_list, get = dask.multiprocessing.get, optimize = False)
    #print "start computing"
    #dask.delayed(delayed_list).compute(get = dask.multiprocessing.get, optimize = False)

    return paths

def cell_to_animation(cell, xlim = None, ylim = None, tstart = 245, tend = 310, tstep = 1, \
                              range_vars = 'Vm', plot_synaptic_input = False, \
                              outdir = 'animation'):
    '''takes a cell object and creates a 2d animation
    
    outdir: folder, where animation should be saved. The result will be .png files.
 
    xlim: tuple like (0, 1600) that defines the limits of the x axis.
            If None, tries to get default values for range var from get_default_axis
            Default: None. 
    ylim: tuple like (-80 0) that defines the limits of the y axis
            If None, tries to get default values for range var from get_default_axis
            Default: None.     
    tstart: time when animation should be started
    tend: time when animation should be stopped
    tstep: timestep between frames
    range_vars: str or list of str: range vars to display, default: 'Vm'
    return glob: if false: only returns animation object, else returns 
                tuple with globstring and animation object
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
    try:
        embedded = kwargs['embedded']
        del kwargs['embedded']
    except KeyError:
        embedded = False
    paths = cell_to_animation(*args, **kwargs)
    ani = display_animation(paths, embedded=embedded)
    return ani

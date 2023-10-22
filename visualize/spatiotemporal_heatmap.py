from matplotlib import use as use_matplotlib_backend

use_matplotlib_backend('Agg')
from matplotlib import pyplot as plt

excitatory = [
    'L6cc', 'L2', 'VPM', 'L4py', 'L4ss', 'L4sp', 'L5st', 'L6ct', 'L34',
    'L6ccinv', 'L5tt'
]
inhibitory = [
    'SymLocal1', 'SymLocal2', 'SymLocal3', 'SymLocal4', 'SymLocal5',
    'SymLocal6', 'L45Sym', 'L1', 'L45Peak', 'L56Trans', 'L23Trans'
]

def pixels2figure(pixels, t_max = 400, z_max = 1600, vmin=-.005, vmax=.005, fig = None,\
                  xlabel = "t [ms]", ylabel = "soma distance [micrometers]",
                  colorbarlabel = 'active synapses / ms / micrometer / stim',
                  cmap = 'seismic'):
    '''takes pixels and returns histogram'''
    if not fig:
        fig = plt.figure()
    plt.imshow(pixels, interpolation='nearest', aspect = 'auto', vmin=vmin, \
               vmax=vmax, extent = [0, t_max, 0, z_max], cmap=cmap)
    plt.colorbar(label=colorbarlabel)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    return fig


if __name__ == '__main__':
    pixels = [[0, 1, 2], [3, 4, 5], [-1, -2, -3]]
    pixels2figure(pixels).savefig('tests.png')

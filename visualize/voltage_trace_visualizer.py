from IPython import display
from . import plt


def plot_vt(voltage_traces, key='BAC.hay_measure'):
    plt.figure()
    plt.plot(voltage_traces[key]['tVec'],
             voltage_traces[key]['vList'][0],
             c='k')
    try:
        plt.plot(voltage_traces[key]['tVec'],
                 voltage_traces[key]['vList'][1],
                 c='r')
    except IndexError:
        pass
    display.display(plt.gcf())
    plt.close()

"""Visualize voltage traces from the results of a :py:class:`~biophysics_fitting.simulator.Simulator` object.

this module provides convenience methods to visualize the voltage traces of all stimuli run by a
:py:class:`~biophysics_fitting.simulator.Simulator` object.

.. figure:: ../../../_static/_images/voltage_traces.png

   Example voltage traces from the Hay stimulus protocols (:cite:`Hay_Hill_Schuermann_Markram_Segev_2011`).
   The top row show the :py:class:`~biophysics_fitting.hay_evaluation_python.BAC` and :py:class:`~biophysics_fitting.hay_evaluation_python.bAP` stimuli.
   The bottom row show the three step currents.
"""


from IPython import display
from . import plt


def plot_vt(voltage_traces, key='BAC.hay_measure'):
    """Plot voltage traces from simulation results.
    
    The results of e.g. :py:class:`biophysics_fitting.simulator.Simulator` are nested dictionaries,
    containing various voltage traces. NEURON simulation results are NEURON vectors. 
    This is a helper method to extract that data and plot out specific voltage traces from those results.

    Args:
        voltage_traces (dict): dictionary containing the voltage traces.
        key (str): key to access the specific voltage trace to plot.

    Returns:
        None
    """
    plt.figure()
    plt.plot(
        voltage_traces[key]['tVec'],
        voltage_traces[key]['vList'][0],
        c='k')
    try:
        plt.plot(
            voltage_traces[key]['tVec'],
            voltage_traces[key]['vList'][1],
            c='r')
    except IndexError:
        pass
    display.display(plt.gcf())
    plt.close()

def visualize_vt(vt, fig=None, soma_color='k', dend_color='#f7941d', BAC_select = 295+80, lw=2, **kwargs):
    """Visualize voltage traces from the Hay stimulus protocols.

    The results of e.g. :py:class:`biophysics_fitting.simulator.Simulator` are nested dictionaries,
    containing various voltage traces. NEURON simulation results are NEURON vectors.
    This is a helper method to extract that data and plot out specific voltage traces from those results.

    Args:
        vt (dict): dictionary containing the voltage traces. 
            Must contain the keys:

            - 'BAC.hay_measure'
            - 'bAP.hay_measure'
            - 'StepOne.hay_measure'
            - 'StepTwo.hay_measure'
            - 'StepThree.hay_measure'
        
        fig (matplotlib.figure.Figure): figure to plot the voltage traces on.
        soma_color (str): color to plot the soma voltage traces.
        dend_color (str): color to plot the dendrite voltage traces.
        BAC_select (int): timepoint for the end of the BAC stimulus.

    Returns:
        None

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more details on the stimulus protocols.
    """
    if lw not in kwargs:
        kwargs['lw'] = lw
    if fig is None:
        fig = plt.figure(dpi=200, figsize=(8, 6))
    ax = fig.add_subplot(2, 2, 1)
    t = vt['BAC.hay_measure']['tVec']
    vs = vt['BAC.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < BAC_select)
    ax.plot(t[select] - 295, vs[0][select], soma_color, **kwargs)
    # ax.plot(t[select]-295,vs[2][select], '#f7941d')
    ax.plot(t[select] - 295, vs[1][select], dend_color, **kwargs)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 2, 2)
    t = vt['bAP.hay_measure']['tVec']
    vs = vt['bAP.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < 295 + 80)
    ax.plot(t[select] - 295, vs[0][select], soma_color, **kwargs)
    ax.plot(t[select] - 295, vs[2][select], dend_color, **kwargs)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 3, 4)
    t = vt['StepOne.hay_measure']['tVec']
    vs = vt['StepOne.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color, **kwargs)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 5)
    t = vt['StepTwo.hay_measure']['tVec']
    vs = vt['StepTwo.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color, **kwargs)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 6)
    t = vt['StepThree.hay_measure']['tVec']
    vs = vt['StepThree.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color, **kwargs)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    for ax in fig.axes:
        ax.set_ylim(-90, 40)
        ax.axis('off')

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

def visualize_vt(vt, fig=None, soma_color='k', dend_color='#f7941d', BAC_select = 295+80):
    if fig is None:
        fig = plt.figure(dpi=200, figsize=(8, 6))
    ax = fig.add_subplot(2, 2, 1)
    t = vt['BAC.hay_measure']['tVec']
    vs = vt['BAC.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < BAC_select)
    ax.plot(t[select] - 295, vs[0][select], soma_color)
    # ax.plot(t[select]-295,vs[2][select], '#f7941d')
    ax.plot(t[select] - 295, vs[1][select], dend_color)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 2, 2)
    t = vt['bAP.hay_measure']['tVec']
    vs = vt['bAP.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < 295 + 80)
    ax.plot(t[select] - 295, vs[0][select], soma_color)
    ax.plot(t[select] - 295, vs[2][select], dend_color)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 3, 4)
    t = vt['StepOne.hay_measure']['tVec']
    vs = vt['StepOne.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 5)
    t = vt['StepTwo.hay_measure']['tVec']
    vs = vt['StepTwo.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 6)
    t = vt['StepThree.hay_measure']['tVec']
    vs = vt['StepThree.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    for ax in fig.axes:
        ax.set_ylim(-90, 40)
        ax.axis('off')
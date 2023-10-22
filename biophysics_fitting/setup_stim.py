import neuron
from . import utils

h = neuron.h


def _append(cell, name, item):
    try:
        getattr(cell, name)
    except AttributeError:
        setattr(cell, name, [])
    getattr(cell, name).append(item)


def setup_soma_step(cell, amplitude=None, delay=None, duration=None, dist=0):
    if dist == 0:
        sec = cell.soma
        x = 0.5
    else:
        sec, x = utils.get_inner_section_at_distance(cell, dist)
    iclamp = h.IClamp(x, sec=sec)
    iclamp.delay = delay  # give the cell time to reach steady state
    iclamp.dur = duration  # 5ms rectangular pulse
    iclamp.amp = amplitude  # 1.9 ?? todo ampere
    _append(cell, 'iclamp', iclamp)


def setup_apical_epsp_injection(cell,
                                dist=None,
                                amplitude=None,
                                delay=None,
                                rise=1.0,
                                decay=5):
    sec, x = utils.get_inner_section_at_distance(cell, dist)
    iclamp2 = h.epsp(x, sec=sec)
    iclamp2.onset = delay
    iclamp2.imax = amplitude
    iclamp2.tau0 = rise  # rise time constant
    iclamp2.tau1 = decay  # decay time constant
    _append(cell, 'epsp', iclamp2)


def setup_bAP(cell, delay=295):
    setup_soma_step(cell, amplitude=1.9, delay=delay, duration=5)


def setup_BAC(cell, dist=970, delay=295):
    try:
        len(
            delay
        )  # check if delay is iterable ... alternative checks were even more complex
    except TypeError:
        setup_soma_step(cell, amplitude=1.9, delay=delay, duration=5)
        setup_apical_epsp_injection(cell,
                                    dist=dist,
                                    amplitude=.5,
                                    delay=delay + 5)
    else:
        for d in delay:
            setup_BAC(cell, dist=dist, delay=d)


def setup_StepOne(cell, delay=700):
    setup_soma_step(cell, amplitude=0.619, delay=delay, duration=2000)


def setup_StepTwo(cell, delay=700):
    setup_soma_step(cell, amplitude=0.793, delay=delay, duration=2000)


def setup_StepThree(cell, delay=700):
    setup_soma_step(cell, amplitude=1.507, delay=delay, duration=2000)

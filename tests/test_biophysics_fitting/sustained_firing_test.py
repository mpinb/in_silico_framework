'''
test sustained firing neuron model for visual inspection
'''

import sys
import time
import os, os.path
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
import numpy as np
import matplotlib.pyplot as plt
from .context import cellParamName

h = neuron.h
import logging

logger = logging.getLogger("ISF").getChild(__name__)

__author__ = 'Robert Egger'
__date__ = '2013-01-28'


def test_BAC_firing():
    neuronParameters = scp.build_parameters(cellParamName)
    scp.load_NMODL_parameters(neuronParameters)
    cellParam = neuronParameters.neuron

    cell = scp.create_cell(cellParam)

    tStop = 3000.0
    neuronParameters.sim.tStop = tStop
    tIStart = 700.0
    duration = 2000.0


    RinCorrection = 1.0
    iAmpSoma1 = 0.619 * RinCorrection
    iAmpSoma2 = 0.793 * RinCorrection
    iAmpSoma3 = 1.507 * RinCorrection

    t1, vmSoma1 = soma_injection(
        cell, 
        amplitude=iAmpSoma1, 
        delay=tIStart, 
        duration=duration,
        simParam=neuronParameters.sim)
    t2, vmSoma2 = soma_injection(
        cell, 
        amplitude=iAmpSoma2, 
        delay=tIStart, 
        duration=duration,
        simParam=neuronParameters.sim)
    t3, vmSoma3 = soma_injection(
        cell, 
        amplitude=iAmpSoma3, 
        delay=tIStart, 
        duration=duration,
        simParam=neuronParameters.sim)

    # plt.figure(1)
    # plt.plot(t1, vmSoma1, 'k', label='soma')
    # plt.xlabel('time [ms]')
    # plt.ylabel('Vm [mV]')
    # plt.title('soma current injection amp=%.2f nA' % (iAmpSoma1))
    # plt.legend()
    # plt.figure(2)
    # plt.plot(t2, vmSoma2, 'k', label='soma')
    # plt.xlabel('time [ms]')
    # plt.ylabel('Vm [mV]')
    # plt.title('soma current injection amp=%.2f nA' % (iAmpSoma2))
    # plt.legend()
    # plt.figure(3)
    # plt.plot(t3, vmSoma3, 'k', label='soma')
    # plt.xlabel('time [ms]')
    # plt.ylabel('Vm [mV]')
    # plt.title('soma current injection amp=%.2f nA' % (iAmpSoma3))
    # plt.legend()



def soma_injection(
    cell,
    amplitude,
    delay,
    duration,
    simParam,
    ):
    iclamp = h.IClamp(0.5, sec=cell.soma)
    iclamp.delay = delay
    iclamp.dur = duration
    iclamp.amp = amplitude

    logger.info('soma current injection: {:.2f} nA'.format(amplitude))
    tVec = h.Vector()
    tVec.record(h._ref_t)
    startTime = time.time()
    scp.init_neuron_run(simParam, vardt=True)
    stopTime = time.time()
    dt = stopTime - startTime
    logger.info('NEURON runtime: {:.2f} s'.format(dt))

    vmSoma = np.array(cell.soma.recVList[0])
    t = np.array(tVec)

    cell.re_init_cell()

    return t, vmSoma


def write_sim_results(fname, t, v):
    with open(fname, 'w') as outputFile:
        header = '# simulation results\n'
        header += '# t\tvsoma'
        header += '\n\n'
        outputFile.write(header)
        for i in range(len(t)):
            line = str(t[i])
            line += '\t'
            line += str(v[i])
            line += '\n'
            outputFile.write(line)
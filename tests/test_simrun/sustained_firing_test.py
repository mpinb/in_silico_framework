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

h = neuron.h
import logging

logger = logging.getLogger("ISF").getChild(__name__)

__author__ = 'Robert Egger'
__date__ = '2013-01-28'


def test_BAC_firing(fname):
    neuronParameters = scp.build_parameters(fname)
    scp.load_NMODL_parameters(neuronParameters)
    cellParam = neuronParameters.neuron

    #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical)
    cell = scp.create_cell(cellParam)

    totalArea = 0.0
    somaArea = 0.0
    apicalArea = 0.0
    basalArea = 0.0
    axonArea = 0.0
    for sec in cell.sections:
        totalArea += sec.area
        if sec.label == 'Soma':
            somaArea += sec.area
        if sec.label == 'ApicalDendrite':
            for seg in sec:
                apicalArea += h.area(seg.x, sec=sec)


#            apicalArea += sec.area
        if sec.label == 'Dendrite':
            basalArea += sec.area
        if sec.label == 'AIS':
            axonArea += sec.area

    logger.info('total area = {:.2f} micron^2'.format(totalArea))
    logger.info('soma area = {:.2f} micron^2'.format(somaArea))
    logger.info('apical area = {:.2f} micron^2'.format(apicalArea))
    logger.info('basal area = {:.2f} micron^2'.format(basalArea))
    logger.info('axon area = {:.2f} micron^2'.format(axonArea))

    tStop = 3000.0
    neuronParameters.sim.tStop = tStop
    #    neuronParameters.sim.dt = 0.005
    tIStart = 700.0
    duration = 2000.0

    #    RinCorrection = 41.9/32.3
    #    RinCorrection = 41.9/24.5
    RinCorrection = 1.0
    iAmpSoma1 = 0.619 * RinCorrection
    iAmpSoma2 = 0.793 * RinCorrection
    iAmpSoma3 = 1.507 * RinCorrection

    visualize = False
    t1, vmSoma1 = soma_injection(cell, iAmpSoma1, tIStart, duration,
                                 neuronParameters.sim, visualize)
    t2, vmSoma2 = soma_injection(cell, iAmpSoma2, tIStart, duration,
                                 neuronParameters.sim, visualize)
    t3, vmSoma3 = soma_injection(cell, iAmpSoma3, tIStart, duration,
                                 neuronParameters.sim, visualize)

    plt.figure(1)
    plt.plot(t1, vmSoma1, 'k', label='soma')
    plt.xlabel('time [ms]')
    plt.ylabel('Vm [mV]')
    plt.title('soma current injection amp=%.2f nA' % (iAmpSoma1))
    plt.legend()
    plt.figure(2)
    plt.plot(t2, vmSoma2, 'k', label='soma')
    plt.xlabel('time [ms]')
    plt.ylabel('Vm [mV]')
    plt.title('soma current injection amp=%.2f nA' % (iAmpSoma2))
    plt.legend()
    plt.figure(3)
    plt.plot(t3, vmSoma3, 'k', label='soma')
    plt.xlabel('time [ms]')
    plt.ylabel('Vm [mV]')
    plt.title('soma current injection amp=%.2f nA' % (iAmpSoma3))
    plt.legend()
    #    plt.figure(4)
    #    plt.plot(t4, vmSoma4, 'k', label='soma')
    #    plt.plot(t4, vmApical4, 'r', label='apical')
    #    plt.xlabel('time [ms]')
    #    plt.ylabel('Vm [mV]')
    #    plt.title('apical current injection amp=%.2f nA' % (iAmpApical2))
    #    plt.legend()
    plt.show()


def soma_injection(cell,
                   amplitude,
                   delay,
                   duration,
                   simParam,
                   saveVisualization=False):
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

    if saveVisualization:
        visFName = 'visualization/soma_injection_86/'
        visFName += 'soma_current_injection_amp_%.1fnA_dur_%.0fms' % (amplitude,
                                                                      duration)
        scp.write_cell_simulation(visFName, cell, ['Vm'], t, allPoints=True)

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


if __name__ == '__main__':
    #    anomalous_rectifier()
    fname = sys.argv[1]
    test_BAC_firing(fname)

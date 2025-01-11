'''
test passive properties neuron model for visual inspection
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


def test_passive_props():
    neuronParameters = scp.build_parameters(cellParamName)
    scp.load_NMODL_parameters(neuronParameters)
    cellParam = neuronParameters.neuron

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
        if sec.label == 'AIS' or sec.label == 'Myelin':
            axonArea += sec.area

    logger.info('total area = {:.2f} micron^2'.format(totalArea))
    logger.info('soma area = {:.2f} micron^2'.format(somaArea))
    logger.info('apical area = {:.2f} micron^2'.format(apicalArea))
    logger.info('basal area = {:.2f} micron^2'.format(basalArea))
    logger.info('axon area = {:.2f} micron^2'.format(axonArea))

    tStop = 600.0
    neuronParameters.sim.tStop = tStop
    #    neuronParameters.sim.dt = 0.005
    tIStart = 295.0
    tIDur = 600.0

    tList = []
    vList = []

    iAmpRange = [-0.5 + i * 0.2 for i in range(6)]  # nA
    for iAmp in iAmpRange:
        iclamp = h.IClamp(0.5, sec=cell.soma)
        iclamp.delay = tIStart
        iclamp.dur = tIDur
        iclamp.amp = iAmp

        logger.info('current stimulation: {:.2f} nA'.format(iAmp))
        tVec = h.Vector()
        tVec.record(h._ref_t)
        startTime = time.time()
        scp.init_neuron_run(neuronParameters.sim, vardt=True)
        stopTime = time.time()
        dt = stopTime - startTime
        logger.info('NEURON runtime: {:.2f} s'.format(dt))

        vmSoma = np.array(cell.soma.recVList[0])
        t = np.array(tVec)
        tList.append(t)
        vList.append(vmSoma)

        tau = compute_tau_effective(t[np.where(t >= tIStart)],
                                    vmSoma[np.where(t >= tIStart)])
        logger.info('tau = {:.2f} ms'.format(tau))
        dVEffective = vmSoma[-1] - vmSoma[np.where(t >= tIStart)][0]
        RInEffective = dVEffective / iAmp
        logger.info('RIn = {:.2f} MOhm'.format(RInEffective))

        cell.re_init_cell()

        logger.info('-------------------------------')

    showPlots = True
    if showPlots:
        plt.figure(1)
        for i in range(len(tList)):
            currentStr = 'I=%.2f nA' % iAmpRange[i]
            plt.plot(tList[i], vList[i], label=currentStr)
        plt.legend()
        plt.show()


def compute_tau_effective(t, v):
    dV = v[-1] - v[0]
    vTau = 0.63212 * dV + v[0]
    tau = -1.0
    for i in range(len(v)):
        if dV > 0:
            if v[i] > vTau:
                tau = t[i] - t[0]
                break
        elif dV < 0:
            if v[i] < vTau:
                tau = t[i] - t[0]
                break
    return tau


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
    test_passive_props(fname)

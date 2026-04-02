'''
test BAC firing for visual inspection
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

    tStop = 600.0
    neuronParameters.sim.tStop = tStop
    #    neuronParameters.sim.dt = 0.005
    tIStart = 295.0
    duration = 5.0
    apicalDt = 5.0
    iAmpSoma = 1.9
    iAmpApical = 0.5
    apicalTauRise = 1.0
    apicalTauDecay = 5.0
    apicalBifurcationDistance = 800.0  # cell ID 86
    apicalInjectionDistance = 620.0  # cell ID 86

    apicalBifurcationSec = get_apical_section_at_distance(cell, distance=apicalBifurcationDistance)

    t1, vmSoma1, vmApical1 = soma_injection(
        cell,
        amplitude=iAmpSoma,
        delay=tIStart, 
        duration=duration,
        apicalSec=apicalBifurcationSec,
        apicalInjectionDistance=apicalInjectionDistance,
        simParam=neuronParameters.sim, 
    )
    t2, vmSoma2, vmApical2 = apical_injection(
        cell, 
        apicalBifurcationSec=apicalBifurcationSec,
        apicalInjectionDistance=apicalInjectionDistance,
        amplitude=iAmpApical, 
        delay=tIStart,
        tauRise=apicalTauRise, 
        tauDecay=apicalTauDecay,
        simParam=neuronParameters.sim
        )
    t3, vmSoma3, vmApical3 = soma_apical_injection(
        cell, 
        somaAmplitude=iAmpSoma, 
        somaDelay=tIStart, 
        somaDuration=duration, 
        apicalBifurcationSec=apicalBifurcationSec,
        apicalInjectionDistance=apicalInjectionDistance, 
        apicalAmplitude=iAmpApical, 
        apicalDelayDt=apicalDt, 
        apicalTauRise=apicalTauRise,
        apicalTauDecay=apicalTauDecay, 
        simParam=neuronParameters.sim
    )


def soma_injection(
    cell,
    amplitude,
    delay,
    duration,
    apicalSec,
    apicalInjectionDistance,
    simParam,
    ):
    logger.info('selected apical section:')
    #    h.psection(sec=apicalSec)
    logger.info(apicalSec.name())
    somaDist = cell.distance_to_soma(apicalSec, 0.0)
    apicalx = (apicalInjectionDistance - somaDist) / apicalSec.L
    logger.info('distance to soma: {:.2f} micron'.format(somaDist))
    logger.info('apicalInjectionDistance: {:.2f} micron'.format(
        apicalInjectionDistance))
    logger.info('apicalx: {:.2f}'.format(apicalx))

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
    minSeg = -1
    mindx = 1.0
    for i in range(len(apicalSec.segx)):
        x = apicalSec.segx[i]
        dx = np.abs(x - apicalx)
        if dx < mindx:
            mindx = dx
            minSeg = i
    vmApical = np.array(apicalSec.recVList[minSeg])
    t = np.array(tVec)

    cell.re_init_cell()

    return t, vmSoma, vmApical


def apical_injection(
    cell,
    apicalBifurcationSec,
    apicalInjectionDistance,
    amplitude,
    delay,
    tauRise,
    tauDecay,
    simParam,
    ):
    logger.info('selected apical section:')
    #    h.psection(sec=apicalBifurcationSec)
    logger.info(apicalBifurcationSec.name())
    somaDist = cell.distance_to_soma(apicalBifurcationSec, 0.0)
    apicalx = (apicalInjectionDistance - somaDist) / apicalBifurcationSec.L
    logger.info('distance to soma: {:.2f} micron'.format(somaDist))
    logger.info('apicalInjectionDistance: {:.2f} micron'.format(
        apicalInjectionDistance))
    logger.info('apicalx: {:.2f}'.format(apicalx))

    iclamp = h.epsp(apicalx, sec=apicalBifurcationSec)
    iclamp.onset = delay
    iclamp.imax = amplitude
    iclamp.tau0 = tauRise
    iclamp.tau1 = tauDecay

    logger.info('apical current injection: {:.2f} nA'.format(amplitude))
    tVec = h.Vector()
    tVec.record(h._ref_t)
    startTime = time.time()
    scp.init_neuron_run(simParam, vardt=True)
    stopTime = time.time()
    dt = stopTime - startTime
    logger.info('NEURON runtime: {:.2f} s'.format(dt))

    vmSoma = np.array(cell.soma.recVList[0])
    minSeg = -1
    mindx = 1.0
    for i in range(len(apicalBifurcationSec.segx)):
        x = apicalBifurcationSec.segx[i]
        dx = np.abs(x - apicalx)
        if dx < mindx:
            mindx = dx
            minSeg = i
    vmApical = np.array(apicalBifurcationSec.recVList[minSeg])
    t = np.array(tVec)

    cell.re_init_cell()

    return t, vmSoma, vmApical

def soma_apical_injection(
    cell, 
    somaAmplitude, 
    somaDelay, 
    somaDuration, 
    apicalBifurcationSec, 
    apicalInjectionDistance, 
    apicalAmplitude,
    apicalDelayDt, 
    apicalTauRise, 
    apicalTauDecay, 
    simParam, 
    ):
    logger.info('selected apical section:')
    #    h.psection(sec=apicalBifurcationSec)
    logger.info(apicalBifurcationSec.name())
    somaDist = cell.distance_to_soma(apicalBifurcationSec, 0.0)
    apicalx = (apicalInjectionDistance - somaDist) / apicalBifurcationSec.L
    logger.info('distance to soma: {:.2f} micron'.format(somaDist))
    logger.info('apicalInjectionDistance: {:.2f} micron'.format(
        apicalInjectionDistance))
    logger.info('apicalx: {:.2f}'.format(apicalx))

    iclamp = h.IClamp(0.5, sec=cell.soma)
    iclamp.delay = somaDelay
    iclamp.dur = somaDuration
    iclamp.amp = somaAmplitude

    iclamp2 = h.epsp(apicalx, sec=apicalBifurcationSec)
    iclamp2.onset = somaDelay + apicalDelayDt
    iclamp2.imax = apicalAmplitude
    iclamp2.tau0 = apicalTauRise
    iclamp2.tau1 = apicalTauDecay

    logger.info('soma current injection: {:.2f} nA'.format(somaAmplitude))
    logger.info('apical current injection: {:.2f} nA'.format(apicalAmplitude))
    tVec = h.Vector()
    tVec.record(h._ref_t)
    startTime = time.time()
    scp.init_neuron_run(simParam, vardt=True)
    stopTime = time.time()
    dt = stopTime - startTime
    logger.info('NEURON runtime: {:.2f} s'.format(dt))

    vmSoma = np.array(cell.soma.recVList[0])
    minSeg = -1
    mindx = 1.0
    for i in range(len(apicalBifurcationSec.segx)):
        x = apicalBifurcationSec.segx[i]
        dx = np.abs(x - apicalx)
        if dx < mindx:
            mindx = dx
            minSeg = i
    vmApical = np.array(apicalBifurcationSec.recVList[minSeg])
    t = np.array(tVec)

    cell.re_init_cell()

    return t, vmSoma, vmApical


def get_apical_section_at_distance(cell, distance):
    '''determine interior apical dendrite section (i.e. no ending section)
    closest to given distance'''
    closestSec = None
    minDist = 1e9
    for branchSectionList in cell.branches['ApicalDendrite']:
        for sec in branchSectionList:
            secRef = h.SectionRef(sec=sec)
            if secRef.nchild():
                dist = cell.distance_to_soma(sec, 1.0)
                dist = abs(dist - distance)
                if dist < minDist:
                    minDist = dist
                    closestSec = sec
    return closestSec

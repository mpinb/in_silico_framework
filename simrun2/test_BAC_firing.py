'''
Created on Jan 28, 2013

passive properties L2 neuron model

@author: robert
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


def test_BAC_firing(fname):
    neuronParameters = scp.build_parameters(fname)
    scp.load_NMODL_parameters(neuronParameters)
    cellParam = neuronParameters.neuron

    cell = scp.create_cell(cellParam)
    #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical, allPoints=True)
    #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical)
    #    cell = scp.create_cell(cellParam)

    #    h.psection(sec=cell.soma)
    #    for branchSectionList in cell.branches['ApicalDendrite']:
    #        for sec in branchSectionList:
    #            dist0 = cell.distance_to_soma(sec, 0.0)
    #            dist05 = cell.distance_to_soma(sec, 0.5)
    #            dist1 = cell.distance_to_soma(sec, 1.0)
    #            print 'distance 0.0 = %.2f' % dist0
    #            print 'distance 0.5 = %.2f' % dist05
    #            print 'distance 1.0 = %.2f' % dist1
    #            h.psection(sec=sec)
    #            for seg in sec:
    #                print 'x = %.2f' % seg.x
    #                print 'Ih gbar = %.8f' % seg.Ih.gIhbar
    #                print 'should be = %.8f' % (0.0002*(-0.8696 + 2.0870*np.exp(3.6161*cell.distance_to_soma(sec, seg.x)/1576.55286112)))
    #    for branchSectionList in cell.branches['Dendrite']:
    #        for sec in branchSectionList:
    #            dist0 = cell.distance_to_soma(sec, 0.0)
    #            dist05 = cell.distance_to_soma(sec, 0.5)
    #            dist1 = cell.distance_to_soma(sec, 1.0)
    #            print 'distance 0.0 = %.2f' % dist0
    #            print 'distance 0.5 = %.2f' % dist05
    #            print 'distance 1.0 = %.2f' % dist1
    #            h.psection(sec=sec)
    #            for seg in sec:
    #                print 'x = %.2f' % seg.x
    #                print 'Ih gbar = %.8f' % seg.Ih.gIhbar
    #    for branchSectionList in cell.branches['AIS']:
    #        for sec in branchSectionList:
    #            dist0 = cell.distance_to_soma(sec, 0.0)
    #            dist05 = cell.distance_to_soma(sec, 0.5)
    #            dist1 = cell.distance_to_soma(sec, 1.0)
    #            print 'distance 0.0 = %.2f' % dist0
    #            print 'distance 0.5 = %.2f' % dist05
    #            print 'distance 1.0 = %.2f' % dist1
    #            h.psection(sec=sec)

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
    duration = 5.0
    apicalDt = 5.0
    iAmpSoma = 1.9
    iAmpApical = 0.5
    apicalTauRise = 1.0
    apicalTauDecay = 5.0
    #    apicalBifurcationDistance = 620.0 # Hay et al. cell1
    #    apicalBifurcationDistance = 450.0 # cell ID 87
    apicalBifurcationDistance = 800.0  # cell ID 86
    apicalInjectionDistance = 620.0  # cell ID 86
    #    apicalBifurcationDistance = 1100.0 # cell ID 86
    #    apicalInjectionDistance = 1015.0 # cell ID 86
    #    apicalBifurcationDistance = 903.0 # cell ID 93
    #    apicalInjectionDistance = 772.0 # cell ID 93
    apicalBifurcationSec = get_apical_section_at_distance(
        cell, apicalBifurcationDistance)

    #    somaDistances = []
    #    diameters = []
    #    Ihbar = []
    #    CaHVAbar = []
    #    CaLVAbar = []
    #    gPas = []
    #    for sec in cell.sections:
    #        if sec.label == 'ApicalDendrite' or sec.label == 'Soma' or sec.label == 'Dendrite':
    #            for seg in sec:
    #                dist = cell.distance_to_soma(sec, seg.x)
    #                diam = seg.diam
    #                somaDistances.append(dist)
    #                diameters.append(diam)
    #                Ihbar.append(seg.Ih.gIhbar)
    ##                CaHVAbar.append(seg.Ca_HVA.gCa_HVAbar)
    ##                CaLVAbar.append(seg.Ca_LVAst.gCa_LVAstbar)
    #                gPas.append(seg.pas.g)

    #    plt.figure(1)
    #    plt.plot(somaDistances, diameters, 'ko', label='diameter')
    #    plt.legend()
    #    plt.figure(2)
    #    plt.plot(somaDistances, Ihbar, 'ko', label='Ih_bar')
    #    plt.legend()
    ##    plt.figure(3)
    ##    plt.plot(somaDistances, CaHVAbar, 'ro', label='CaHVA_bar')
    ##    plt.legend()
    ##    plt.figure(4)
    ##    plt.plot(somaDistances, CaLVAbar, 'bo', label='CaLVA_bar')
    ##    plt.legend()
    #    plt.figure(5)
    #    plt.plot(somaDistances, gPas, 'bo', label='gPas')
    #    plt.legend()
    #    plt.show()

    #    h.psection(sec=apicalBifurcationSec)
    #    for seg in apicalBifurcationSec:
    #        print 'x: %.2f' % seg.x
    #        print 'gCa_LVAstbar: ',
    #        print seg.Ca_LVAst.gCa_LVAstbar
    #        print 'gCa_HVAbar: ',
    #        print seg.Ca_HVA.gCa_HVAbar
    #        print 'gIhbar: ',
    #        print seg.Ih.gIhbar
    visualize = False
    t1, vmSoma1, vmApical1 = soma_injection(cell, iAmpSoma, tIStart, duration,
                                            apicalBifurcationSec,
                                            apicalInjectionDistance,
                                            neuronParameters.sim, visualize)
    t2, vmSoma2, vmApical2 = apical_injection(cell, apicalBifurcationSec,
                                              apicalInjectionDistance,
                                              iAmpApical, tIStart,
                                              apicalTauRise, apicalTauDecay,
                                              neuronParameters.sim, visualize)
    t3, vmSoma3, vmApical3 = soma_apical_injection(
        cell, iAmpSoma, tIStart, duration, apicalBifurcationSec,
        apicalInjectionDistance, iAmpApical, apicalDt, apicalTauRise,
        apicalTauDecay, neuronParameters.sim, visualize)
    #    #iAmpApical2 = 2.5
    #    #t4, vmSoma4, vmApical4 = apical_injection(cell, apicalBifurcationSec, iAmpApical2, tIStart, apicalTauRise, apicalTauDecay, neuronParameters.sim)

    #    for i in range(len(t1)):
    #        print t1[i],
    #        print '\t',
    #        print vmSoma1[i]

    showPlots = True
    if showPlots:
        plt.figure(1)
        plt.plot(t1, vmSoma1, 'k', label='soma')
        plt.plot(t1, vmApical1, 'r', label='apical')
        plt.xlabel('time [ms]')
        plt.ylabel('Vm [mV]')
        plt.title('soma current injection amp=%.2f nA' % (iAmpSoma))
        plt.legend()
        plt.figure(2)
        plt.plot(t2, vmSoma2, 'k', label='soma')
        plt.plot(t2, vmApical2, 'r', label='apical')
        plt.xlabel('time [ms]')
        plt.ylabel('Vm [mV]')
        plt.title('apical current injection amp=%.2f nA' % (iAmpApical))
        plt.legend()
        plt.figure(3)
        plt.plot(t3, vmSoma3, 'k', label='soma')
        plt.plot(t3, vmApical3, 'r', label='apical')
        plt.xlabel('time [ms]')
        plt.ylabel('Vm [mV]')
        plt.title('soma + apical current injection amp=%.2f/%.2f nA' %
                  (iAmpSoma, iAmpApical))
        plt.legend()
        #        plt.figure(4)
        #        plt.plot(t4, vmSoma4, 'k', label='soma')
        #        plt.plot(t4, vmApical4, 'r', label='apical')
        #        plt.xlabel('time [ms]')
        #        plt.ylabel('Vm [mV]')
        #        plt.title('apical current injection amp=%.2f nA' % (iAmpApical2))
        #        plt.legend()
        plt.show()


def soma_injection(cell,
                   amplitude,
                   delay,
                   duration,
                   apicalSec,
                   apicalInjectionDistance,
                   simParam,
                   saveVisualization=False):
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

    if saveVisualization:
        visFName = 'visualization/soma_injection_86/'
        visFName += 'soma_current_injection_amp_%.1fnA_dur_%.0fms' % (amplitude,
                                                                      duration)
        scp.write_cell_simulation(visFName, cell, ['Vm'], t, allPoints=True)

    cell.re_init_cell()

    return t, vmSoma, vmApical


def apical_injection(cell,
                     apicalBifurcationSec,
                     apicalInjectionDistance,
                     amplitude,
                     delay,
                     tauRise,
                     tauDecay,
                     simParam,
                     saveVisualization=False):
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

    if saveVisualization:
        visFName = 'visualization/apical_injection_86/'
        visFName += 'apical_current_injection_amp_%.1fnA' % (amplitude)
        scp.write_cell_simulation(visFName, cell, ['Vm'], t, allPoints=True)

    cell.re_init_cell()

    return t, vmSoma, vmApical

def soma_apical_injection(cell, somaAmplitude, somaDelay, somaDuration, apicalBifurcationSec, apicalInjectionDistance, apicalAmplitude,\
                          apicalDelayDt, apicalTauRise, apicalTauDecay, simParam, saveVisualization=False):
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

    if saveVisualization:
        visFName = 'visualization/soma_apical_injection_86/'
        visFName += 'soma_apical_current_injection_soma_amp_%.1fnA_dur_%.0fms_apical_amp_%.1fnA_dt_%.0fms' % (
            somaAmplitude, somaDuration, apicalAmplitude, apicalDelayDt)
        scp.write_cell_simulation(visFName, cell, ['Vm'], t, allPoints=True)

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


def scale_apical(cell):
    '''
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    '''
    dendScale = 2.5
    scaleCount = 0
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            dist = cell.distance_to_soma(sec, 1.0)
            if dist > 1000.0:
                continue
#            for cell 86:
            if scaleCount > 32:
                break
            scaleCount += 1
            #            dummy = h.pt3dclear(sec=sec)
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = dendScale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)


#                x, y, z = sec.pts[i]
#                sec.diamList[i] = sec.diamList[i]*dendScale
#                d = sec.diamList[i]
#                dummy = h.pt3dadd(x, y, z, d, sec=sec)

    logger.info('Scaled {:d} apical sections...'.format(scaleCount))


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

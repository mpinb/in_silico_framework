'''
Created on Nov 6, 2012

@author: regger
'''

import numpy as np
import neuron

h = neuron.h

#    TODO: this needs to be automated... i.e., should be such that
#    section, or better, segment is passed as an argument and all
#    ionic/axial/capacitive currents are automatically calculated
#    => add automatic recording of all ionic (and synaptic?) currents
#    and conductances to PySection/Synapse classes


def compute_soma_currents(cell, currents, tVec):
    '''
    TODO: this needs to be automated... i.e., should be such that   
    section, or better, segment is passed as an argument and all    
    ionic/axial/capacitive currents are automatically calculated    
    => add automatic recording of all ionic (and synaptic?) currents
    and conductances to PySection/Synapse classes                   
    '''
    #===========================================================================
    # units of axial currents: muS*mV = nA = 10^3 pA
    # units of ionic currents: mA/cm^2 = 10^-8 mA/mum^2 = 10^-2 nA/mum^2 = 10 pA/mum^2
    # units of capacitive current: muF/cm^2*mV/ms = 10^-8 muA/mum^2 = 0.01 pA/mum^2
    #===========================================================================
    t = np.array(tVec)
    iPas = 10 * np.array(currents['ipas']) * cell.soma.area
    iNa = 10 * np.array(currents['ina']) * cell.soma.area
    iKd = 10 * np.array(currents['ikd']) * cell.soma.area
    vSoma = np.array(cell.soma.recVList[0])
    dendCurrs = []
    iDendTotal = np.zeros_like(t)
    dendLabels = ('ApicalDendrite', 'Dendrite')
    for label in dendLabels:
        for dend in cell.branches[label]:
            #            loop through all, otherwise section
            #            is not popped from NEURON section stack!!!
            #            better ideas???
            secCnt = 0
            for sec in dend:
                if not secCnt:
                    vDend = np.array(sec.recVList[0])
                    ri = h.ri(sec.segx[0], sec=sec)
                    dendCurrs.append(1000 / ri * (vDend - vSoma))
                    iDendTotal += dendCurrs[-1]


#                only interested in branch root section,
#                therefore jump into outer loop
#                break
                secCnt += 1

    vAx = np.array(cell.structures['AIS'][0].recVList[0])
    riAx = h.ri(cell.structures['AIS'][0].segx[0],
                sec=cell.structures['AIS'][0])
    iAx = 1000 / riAx * (vAx - vSoma)

    dV = np.diff(vSoma)
    dt = np.diff(t)
    iCap_ = 0.01 * cell.soma.cm * cell.soma.area * dV / dt
    #    repeat last element of iCap for alignment with t axis
    iCap = np.append(iCap_, iCap_[-1])

    currents = {}
    currents['iax'] = iAx
    currents['idend'] = iDendTotal
    currents['ipas'] = iPas
    currents['ina'] = iNa
    currents['ikd'] = iKd
    currents['icap'] = iCap

    return currents


def analyze_voltage_trace(vTrace, tTrace):
    """
    takes neuron Vectors and finds time and
    amplitude of max depolarization
    """
    v = np.array(vTrace)
    t = np.array(tTrace)
    maxV = np.max(v)
    maxT = t[np.argmax(v)]
    return maxT, maxV
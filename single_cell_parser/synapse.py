'''
Created on Mar 30, 2012

@author: regger
'''
from neuron import h
from collections import Sequence
import numpy as np


class Synapse(object):
    '''
    Synapse base class
    Contains information about pre- and postsynaptic cell type,
    branch ID of postsynaptic cell, branch pt ID,
    and xyz-coordinates of synapse location
    Biophysical mechanisms are specified in subclasses
    '''

    def __init__(
        self,
        edgeID,
        edgePtID,
        edgex,
        preCellType='',
        postCellType=''):
        '''
        ID of attached section in cell.sections
        self.secID = edgeID
        
        ID of attached point in cell.sections[self.secID].pts
        self.ptID = edgePtID
        
        relatice coordinate along attached section
        self.x = edgex
        
        self.preCellType = preCellType
        reference to presynaptic cell (PointCell)
        self.preCell = None
        
        reference to presynaptic release site (PointCell)
        self.releaseSite = None
        
        self.postCellType = postCellType
        
        3D coordinates of synapse location
        self.coordinates = None
        
        stores hoc mechanisms and NetCons
        self.receptors = {}
        self.netcons = []
        
        self.weights = None
        
        self._active = False
        
        self.pruned = False
        '''
        self.secID = edgeID
        self.ptID = edgePtID
        self.x = edgex
        self.preCellType = preCellType
        self.preCell = None
        self.releaseSite = None
        self.postCellType = postCellType
        self.coordinates = None
        self.receptors = {}
        self.netcons = []
        self.weight = None
        self._active = False
        self.pruned = False

    def is_active(self):
        return self._active

    def activate_hoc_syn(self, source, preCell, targetCell, receptors):
        '''setup of all necessary hoc connections.
        stores all mechanisms and NetCons for reference counting.'''
        self.releaseSite = source
        self.preCell = preCell
        '''careful: point processes not allowed at nodes between sections
        (x=0 or x=1) if ions are used in this mechanism (e.g. Ca in synapses)'''
        minX = targetCell.sections[self.secID].segx[0]
        maxX = targetCell.sections[self.secID].segx[-1]
        x = targetCell.sections[self.secID].relPts[self.ptID]
        if x < minX:
            x = minX
        if x > maxX:
            x = maxX
        hocSec = targetCell.sections[self.secID]
        for recepStr in list(receptors.keys()):
            recep = receptors[recepStr]
            hocStr = 'h.'
            hocStr += recepStr
            hocStr += '(x, sec=hocSec)'
            newSyn = eval(hocStr)
            newNetcon = h.NetCon(source.spikes, newSyn)
            newNetcon.threshold = recep.threshold
            newNetcon.delay = recep.delay
            if self.weight is None:
                errstr = 'Synaptic weights are not set! This should not occur!'
                raise RuntimeError(errstr)
            else:
                for i in range(len(self.weight[recepStr])):
                    newNetcon.weight[i] = self.weight[recepStr][i]
            self.receptors[recepStr] = newSyn
            self.netcons.append(newNetcon)
        self._active = True

    def disconnect_hoc_synapse(self):
        if self.releaseSite:
            self.releaseSite.turn_off()
        self.preCell = None
        self.netcons = []
        self.receptors = {}
        self.weight = None
        self._active = False


class ExSyn(Synapse):
    '''
    simple excitatory synapse for playing around
    '''

    def __init__(self, edgeID, edgePtID, preCellType='', postCellType=''):
        Synapse.__init__(self,
                         edgeID,
                         edgePtID,
                         preCellType='',
                         postCellType='')

    def activate_hoc_syn(self,
                         source,
                         targetCell,
                         threshold=10.0,
                         delay=0.0,
                         weight=0.0):
        x = targetCell.sections[self.secID].relPts[self.ptID]
        hocSec = targetCell.sections[self.secID]
        self.syn = h.ExpSyn(x, hocSec)
        self.syn.tau = 1.7
        self.syn.e = 0.0
        self.netcon = h.NetCon(source, self.syn, threshold, delay, weight)
        self._active = True

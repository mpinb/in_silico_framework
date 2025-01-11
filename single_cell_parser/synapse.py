'''

'''
from neuron import h
from collections import Sequence
import numpy as np

__author__ = 'Robert Egger'
__date__ = '2012-03-30'

class Synapse(object):
    '''Synapse class for synaptic activations and NEURON API.

    Used in :py:class:`single_cell_parser.cell.Cell` to store synapse information,
    and to activate/deactivate synapses in NEURON.
    
    See also:
        This is not the same class as :py:class:`singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`.
        This class is specialized for the NEURON simulator, and is used to store synapse information and activate/deactivate synapses in NEURON.

    Attributes:
        secID (int): ID of attached section in cell.sections
        ptID (int): ID of attached point in cell.sections[self.secID].pts
        x (float): Relative coordinate along attached section (from 0 to 1)
        preCellType (str): Reference to presynaptic cell (PointCell)
        preCell (PointCell): Reference to presynaptic cell (PointCell)
        releaseSite (PointCell): Release site of presynaptic cell.
        postCellType (str): Reference to postsynaptic cell (PointCell)
        coordinates (list): 3D coordinates of synapse location
        receptors (dict): Stores hoc mechanisms
        netcons (list): Stores NetCons
        weight (float): Synaptic weight
        _active (bool): Activation status
        pruned (bool): Pruning status
    '''

    def __init__(
        self,
        edgeID,
        edgePtID,
        edgex,
        preCellType='',
        postCellType=''):
        '''
        Args:
            edgeID (int): ID of attached section in cell.sections
            edgePtID (int): ID of attached point in cell.sections[edgeID].pts
            edgex (float): relative coordinate along attached section
            preCellType (str): reference to presynaptic cell (PointCell)
            postCellType (str): reference to postsynaptic cell (PointCell)
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
        stores all mechanisms and NetCons for reference counting.
        
        Args:
            source (:py:class:`single_cell_parser.cell.PointCell`): 
                Presynaptic cell whose :py:attr:`single_cell_parser.cell.PointCell.spikes` attribute is used as ``source`` in NEURON's NetCon object.
                Note that in the context of a synapse, ``spikes`` means release times, which is not necessarily the same as the presynaptic spike times.
        '''
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
        """Disconnect the synapse from the neuron model.
        
        
        """
        if self.releaseSite:
            self.releaseSite.turn_off()
        self.preCell = None
        self.netcons = []
        self.receptors = {}
        self.weight = None
        self._active = False


class ExSyn(Synapse):
    '''Simple excitatory synapse.

    Used for testing purposes.

    Attributes:
        syn (h.ExpSyn): hoc ExpSyn object
        netcon (h.NetCon): hoc NetCon object
        _active (bool): activation status
    '''

    def __init__(self, edgeID, edgePtID, preCellType='', postCellType=''):
        Synapse.__init__(
            self,
            edgeID,
            edgePtID,
            preCellType='',
            postCellType='')

    def activate_hoc_syn(
            self,
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

# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Synapse class for synaptic activations and NEURON API.

Used in :class:`single_cell_parser.cell.Cell` to store synapse information,
and to activate/deactivate synapses in NEURON.

See also:
    :class:`single_cell_parser.cell.Cell`.
'''
from neuron import h
from single_cell_parser.parameters import NTParameterSet

__author__ = 'Robert Egger'
__date__ = '2012-03-30'

class Synapse(object):
    '''Synapse class for synaptic activations and NEURON API.

    Used in :class:`single_cell_parser.cell.Cell` to store synapse information,
    and to activate/deactivate synapses in NEURON.
    
    See also:
        This is not the same class as :class:`singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`.
        This class is specialized for the NEURON simulator, and is used to store synapse information and activate/deactivate synapses in NEURON.

    Attributes:
        secID (int): ID of attached section in cell.sections
        ptID (int): ID of attached point in cell.sections[self.secID].pts
        x (float): Relative coordinate along attached section (from 0 to 1)
        preCellType (str): Type of the presynaptic :class:`~single_cell_parser.cell.PointCell`
        preCell (:class:`~single_cell_parser.cell.PointCell`): Reference to presynaptic :class:`~single_cell_parser.cell.PointCell`
        releaseSite (:class:`~single_cell_parser.cell.PointCell`): Release site of presynaptic cell.
        postCellType (str): Postsynaptic cell type.
        coordinates (list): 3D coordinates of synapse location
        receptors (:class:`~single_cell_parser.parameters.NTParameterSet`): Stores hoc mechanisms
        netcons (list): Stores NetCons
        weight (float): Synaptic weight
        _active (bool): Activation status
        pruned (bool): Pruning status
    '''

    def __init__(
        self,
        edgeID,
        edgePtID,
        edgex=None,
        preCellType='',
        postCellType=''):
        '''
        Args:
            edgeID (int): ID of attached section in cell.sections
            edgePtID (int): ID of attached point in cell.sections[edgeID].pts
            preCellType (str): reference to presynaptic :class:`~single_cell_parser.cell.PointCell`
            postCellType (str): reference to postsynaptic :class:`~single_cell_parser.cell.PointCell`
        '''
        self.secID = edgeID
        self.ptID = edgePtID
        self.x = edgex  # TODO unused
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
        """Check if the synapse is active.
        
        Returns:
            bool: Activation status of the synapse.
            
        See also:
            :func:`activate_hoc_syn` and :func:`disconnect_hoc_synapse`
        """
        return self._active

    def activate_hoc_syn(self, source, preCell, targetCell, receptors):
        '''Setup of all necessary hoc connections.
        
        Stores all mechanisms and NetCons for reference counting.
        
        Args:
            source (:class:`single_cell_parser.cell.PointCell`): 
                Presynaptic cell whose :attr:`single_cell_parser.cell.PointCell.spikes` attribute is used as ``source`` in NEURON's NetCon object.
                Note that in the context of a synapse, ``spikes`` means release times, which is not necessarily the same as the presynaptic spike times.
            preCell (:class:`single_cell_parser.cell.PointCell`): Presynaptic cell.
            targetCell (:class:`single_cell_parser.cell.Cell`): Postsynaptic cell.
            receptors (:class:`~single_cell_parser.parameters.NTParameterSet`): 
                Dictionary or :class:`~single_cell_parser.parameters.NTParameterSet` of receptors. 
                Each individual receptor in this collection must be of the type :class:`~single_cell_parser.parameters.NTParameterSet`.
        '''
        assert isinstance(receptors, NTParameterSet), 'receptors must be single_cell_parser.parameters.NTParameterSet, but they are of type %s' % type(receptors)
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
        for receptor_name, receptor in receptors.items():
            receptor = receptors[receptor_name]
            # newSyn = eval("h.{}(x, sec=hocSec)".format(receptor_name))
            new_synapse = getattr(h, receptor_name)(x, sec=hocSec)
            new_netcon = h.NetCon(source.spikes, new_synapse)
            new_netcon.threshold = receptor.threshold
            new_netcon.delay = receptor.delay
            if self.weight is None:
                errstr = 'Synaptic weights are not set! This should not occur!'
                raise RuntimeError(errstr)
            else:
                for i in range(len(self.weight[receptor_name])):
                    new_netcon.weight[i] = self.weight[receptor_name][i]
            self.receptors[receptor_name] = new_synapse
            self.netcons.append(new_netcon)
        self._active = True

    def disconnect_hoc_synapse(self):
        """Disconnect the synapse from the neuron model.
        
        Disconnecting the synapse turns off the release site and removes the :class:`neuron:NetCon`
        
        See also:
            :func:`activate_hoc_syn`.
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
            weight=0.0
    ):

        '''Setup of all necessary hoc connections.
        
        Stores all mechanisms and NetCons for reference counting.
        
        Args:
            source (:class:`single_cell_parser.cell.PointCell`): 
                Presynaptic cell whose :attr:`single_cell_parser.cell.PointCell.spikes` attribute is used as ``source`` in NEURON's NetCon object.
                Note that in the context of a synapse, ``spikes`` means release times, which is not necessarily the same as the presynaptic spike times.
            targetCell (:class:`single_cell_parser.cell.Cell`): Postsynaptic cell.
            threshold (float): Activation threshold. default is :math:`10mV`
            delay (float): Delay between the activation of the presynaptic cell and the synapse. Default is :math:`0ms`
            weight (float): Weight of the synapse.
        '''
        x = targetCell.sections[self.secID].relPts[self.ptID]
        hocSec = targetCell.sections[self.secID]
        self.syn = h.ExpSyn(x, hocSec)
        self.syn.tau = 1.7
        self.syn.e = 0.0
        self.netcon = h.NetCon(source, self.syn, threshold, delay, weight)
        self._active = True

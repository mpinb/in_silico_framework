from neuron import h

from single_cell_parser.synapse import Synapse

class GBSynapse(Synapse):
    '''Glutamatergic synapse implementing Graupner and Brunel (2012) synaptic-plasticity model.
    Taken from Chindemi et al., 2022.

    Attributes:
        syn (h.GluSynapse): hoc GluSynapse object
        netcon (h.NetCon): hoc NetCon object
        _active (bool): activation status
    '''

    def __init__(self, section, segment, preCellType='', postCellType=''):
        Synapse.__init__(
            self,
            section,
            segment,
            0,  # edgex not used
            preCellType,
            postCellType
        )

    def activate_hoc_syn(
        self,
        source,
        targetCell,
        threshold=10.0,
        delay=0.0,
        weight=1.0
    ):
        x = targetCell.sections[self.secID].relPts[self.ptID]
        hocSec = targetCell.sections[self.secID]
        self.syn = h.GBSynapse(x, hocSec)
        self.netcon = h.NetCon(source, self.syn, threshold, delay, weight)
        self._active = True

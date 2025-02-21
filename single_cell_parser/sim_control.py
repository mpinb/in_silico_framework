'''Run a NEURON current injection simulation.

Deprecated. Simulations are set up using the high-level interface :py:class:`~biophysics_fitting.simulator.Simulator`.
Can still be useful for low-level control with NEURON.
'''

import numpy as np
#import matplotlib.pyplot as plt
import neuron
from . import cell_parser
from . import reader
from . import synapse_mapper as smap
import matplotlib.pyplot as plt

__author__ = 'Robert Egger'
__date__ = '2012-03-19'

class SimControl(object):
    '''Control a current clamp simulation.

    Deprecated. Simulations are set up using the high-level interface :py:class:`~biophysics_fitting.simulator.Simulator`.
    Can still be useful for low-level control with NEURON.
    
    Example:

        >>> cell = CellParser()
        >>> sim = SimControl(cell=cell.get_cell())
        >>> sim.go()
        >>> sim.show()
    

    Attributes:
        cell (:py:class:`neuron.h.Section`): The cell to simulate.
        simTime (float): Simulation time [ms]. Default: 5 [ms]
        dt (float): Time step [ms]. Default: 0.001 [ms]
        T (float): Temperature [C]. Default
        goAlready (bool): Simulation status
        h (:py:class:`neuron.h`): NEURON interface
    '''

    def __init__(self, cell=None, sim_time=5, dt=0.001, T=37):
        '''
        Args:
            cell (:py:class:`neuron.h.Section`): The cell to simulate.
            simTime (float): Simulation time (ms). Default: 5
            dt (float): Time step (ms). Default: 0.001
            T (float): Temperature (Celsius). Default: 37
        '''
        self.cell = cell
        self.simTime = sim_time
        self.dt = dt
        self.T = T
        self.goAlready = False
        self.h = neuron.h

    def set_IClamp(self, delay=1, amp=-1, dur=3):
        """Initializes values for current clamp.
        
        Default values:
          
          delay = 1 ms
          amp   = -1 nA
          dur   = 3 ms
        """
        stim = self.h.IClamp(self.cell.neuronTree.soma.hocSec(0.5))
        stim.delay = delay
        stim.amp = amp
        stim.dur = dur
        self.stim = stim

    def show(self):
        """Plot the voltage trace."""
        if self.go_already:
            x = np.array(self.rec_t)
            y = np.array(self.rec_v)
            plt.plot(x, y)
            plt.title("1st spike")
            plt.xlabel("Time [ms]")
            plt.ylabel("Voltage [mV]")
            plt.axis(xmin=0, xmax=self.simTime, ymin=-80, ymax=60)
            plt.show()
        else:
            print("""First you have to `go()` the simulation.""")

    def set_recording(self):
        """Record the voltage trace."""
        # Record Time
        self.rec_t = self.h.Vector()
        self.rec_t.record(self.h._ref_t)
        # Record Voltage
        self.rec_v = self.h.Vector()
        self.rec_v.record(self.cell.soma(0.5)._ref_v)

    def go(self, simTime=None):
        """Run the simulation."""
        self.set_recording()
        self.h.celsius = self.T
        print('Temperature = {:d}'.format(int(self.h.celsius)))
        #        self.h.dt = self.dt
        self.cvode = self.h.CVode()
        self.cvode.active()
        self.h.finitialize(self.cell.E)
        neuron.init()
        if simTime:
            neuron.run(simTime)
        else:
            neuron.run(self.simTime)
        self.go_already = True


if __name__ == '__main__':
    #    fname = 'test_morphology.hoc'
    fname = '93_CDK080806_marcel_3x3_registered_zZeroBarrel.hoc.am-14678.hoc'
    testParser = cell_parser.CellParser(fname)
    testParser.spatialgraph_to_cell()
    testParser.spatialgraph_to_hoc(['Soma', 'Dendrite', 'ApicalDendrite'])
    testParser.spatialgraph_to_hoc(['Axon'])
    testParser.insert_passive_membrane('Soma')
    testParser.insert_passive_membrane('Dendrite')
    testParser.insert_passive_membrane('ApicalDendrite')
    testParser.insert_passive_membrane('Axon')
    testParser.insert_hh_membrane('Soma')
    testParser.insert_hh_membrane('Dendrite')
    testParser.insert_hh_membrane('ApicalDendrite')
    testParser.insert_hh_membrane('Axon')

    synapseFName = 'SynapseCount.14678.am'
    synDist = reader.read_scalar_field(synapseFName)
    mapper = smap.SynapseMapper(testParser.cell, synDist)
    mapper.create_synapses('VPM')

    #    quick test of synapse activation
    mech_str = '/Users/robert/neuron/nrn-7.2/share/examples/nrniv/netcon/i386/.libs/libnrnmech.so'
    load_flag = neuron.h.nrn_load_dll(mech_str)
    if not load_flag:
        err_str = 'Failed to load NMODL mechanism from ' + mech_str
        raise RuntimeError(err_str)
    tvec = neuron.h.Vector([10.0])
    vs = neuron.h.VecStim()
    vs.play(tvec)

    for syn in testParser.cell.synapses['VPM']:
        syn.activate_hoc_syn(vs, testParser.cell, weight=0.002)

    sim = SimControl(cell=testParser.get_cell(), sim_time=100, dt=0.01)
    #    sim.set_IClamp(delay=3.0, amp=1.1, dur=95)
    sim.go()
    sim.show()

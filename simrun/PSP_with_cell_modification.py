'''Calculate PSPs depending on cell modifications.

Such modifications include:
- A current injection into the soma, to ensure a certain resting potential
- A coincident current injection triggering a burst, to investigate the effect of bursts on somatic integration of consecutive input
- Synaptic input, to investigate the effect of one more synapse activation on top of such input to the somatic subthreshold potential
'''

import Interface as I
from biophysics_fitting.setup_stim import setup_soma_step
from scipy.optimize import minimize, minimize_scalar
from simrun.synaptic_strength_fitting import PSPs


class PSP_with_current_injection:
    '''Simulate EPSPs and IPSPs while the soma is voltage-clamped to a fixed membrane potential.
    
    The membrane potential is clamped by injecting a current into the soma.
        
    Attributes:
        neuron_param (NTParameterSet): Parameters of the neuron model.
        confile (str): Path to the network connectivity (:ref:`con_file_format`) file.
        target_vm (float): Membrane potential to clamp the soma to (in :math:`mV`).
        delay (float): Delay before the current injection starts (in :math:`ms`).
        duration (float): Duration of the current injection (in :math:`ms`).
        optimize_for_timepoint (float): 
            Timepoint for membrane voltage optimization (in :math:`ms`).
            This usually coincides with the timepoint of a single synapse activation, after the membrane voltage has stabilized.
        tEnd (float): End time of the simulation (in :math:`ms`).
        cell_modify_functions (dict):
            Dictionary of cell modification functions (see :py:mod:`~single_cell_parser.cell_modify_functions`).
            The keys are the names of the functions, the values are the parameters of the functions.
        bounds (tuple):
            Limits for the current injection optimization to clamp the membrane potential (in :math:`nA`).
        holding_current (float):
            Current that needs to be injected to hold the somatic potential at :paramref:`target_vm`.
            
    See also:
        :py:mod:`single_cell_parser.cell_modify_functions` for available cell modification functions.
    '''
    def __init__(
        self,
        neuron_param,
        confile,
        target_vm=-70,
        delay=100,
        duration=200,
        optimize_for_timepoint=150,
        tEnd=300,
        cell_modify_functions={},
        bounds=(0, 0.7)):
        """
        Args:
        neuron_param (NTParameterSet): Parameters of the neuron model.
        confile (str): Path to the network connectivity (:ref:`con_file_format`) file.
        target_vm (float): Membrane potential to clamp the soma to (in :math:`mV`).
        delay (float): Delay before the current injection starts (in :math:`ms`).
        duration (float): Duration of the current injection (in :math:`ms`).
        optimize_for_timepoint (float): 
            Timepoint for membrane voltage optimization (in :math:`ms`).
            This usually coincides with the timepoint of a single synapse activation, after the membrane voltage has stabilized.
        tEnd (float): End time of the simulation (in :math:`ms`).
        cell_modify_functions (dict):
            Dictionary of cell modification functions (see :py:mod:`~single_cell_parser.cell_modify_functions`).
            The keys are the names of the functions, the values are the parameters of the functions.
        bounds (tuple):
            Limits for the current injection optimization to clamp the membrane potential (in :math:`nA`).
        """
        self.confile = confile
        self.neuron_param = I.scp.NTParameterSet(neuron_param.as_dict())
        self.target_vm = target_vm
        self.delay = delay
        self.duration = duration
        self.optimize_for_timepoint = optimize_for_timepoint
        self.tEnd = tEnd
        self.holding_current = None
        self.cell_modify_functions = cell_modify_functions
        self.bounds = bounds
        if len(cell_modify_functions) > 0:
            if not 'cell_modify_functions' in list(self.neuron_param.neuron.keys()):
                self.neuron_param.neuron['cell_modify_functions'] = {}
                print(cell_modify_functions)
            self.neuron_param.neuron['cell_modify_functions'].update(
                cell_modify_functions)

    def optimize_holding_current(self):
        '''Calculate the current that needs to be injected to hold the somatic potential at :paramref:`target_vm`.
        
        :paramref:`target_vm` is defined during initialization of the object
        '''
        print('starting optimization of holding current. target membrane potential is {} mV'.format(self.target_vm))
        bounds = self.bounds
        x = minimize_scalar(
            I.partial(self._objective_fun),
            tol=.01,
            bounds=bounds,
            method='Bounded')
        if x.fun < 0.1:
            print('solution found')
            print('deviation / mV: {}'.format(I.np.sqrt(x.fun)))
            print('current / mV: {}'.format(I.np.sqrt(x.x)))
            self.holding_current = x.x
        else:
            self.plot_current_injection_voltage_trace()
            raise RuntimeError("A solution has not been found")
        self.plot_current_injection_voltage_trace()

    def _objective_fun(self, current):
        '''Callable to optimize. 
        
        Input must be current in :math:`nA` and output must be squared deviation from :paramref:`target_vm` in :math:`mV^2` at the timepoint :paramref:`optimize_for_timepoint`.
        '''
        tVec, vm = self._get_current_dependent_vt(current)
        if max(vm[tVec > self.delay]) > -40:  # there may be no spikes
            print('careful: there are spikes during the PSP experiment!')
            return 10000
        tNew = I.np.arange(0, self.tEnd, 0.025)
        vmNew = I.np.interp(tNew, tVec, vm)
        out = (vmNew[int(self.optimize_for_timepoint / 0.025)] - self.target_vm)**2
        print(vmNew, out)
        return out

    def _get_current_dependent_vt(self, current):
        '''Run the current injection simulation
        
        Args:
            current (float): Current to inject into the soma (in :math:`nA`).
            
        Returns:
            tuple: Time vector and membrane potential vector as numpy arrays.
        '''
        with I.silence_stdout:
            cell = I.scp.create_cell(self.neuron_param.neuron)
        setup_soma_step(cell, current, self.delay, self.duration)
        self.neuron_param.sim.tStop = self.tEnd
        I.scp.init_neuron_run(self.neuron_param.sim, vardt=True)
        return I.np.array(cell.tVec), I.np.array(cell.soma.recVList[0])

    def plot_current_injection_voltage_trace(self):
        '''Visualize the voltage trace during the current injection
        '''
        if self.holding_current is None:
            self.optimize_holding_current()
            #raise RuntimeError("Call optimize_holding_current first!")
        tVec, vt = self._get_current_dependent_vt(self.holding_current)
        I.plt.plot(tVec, vt)
        I.display.display(I.plt.gcf())

    def get_neuron_param_with_current_injection(self):
        '''Get a :ref:`cell_params_format` file with a current injection.
        
        The current injection is set up such that the potential :paramref:`target_vm` is reached at the timepoint :paramref:`optimize_for_timepoint`
        '''
        if self.holding_current is None:
            self.optimize_holding_current()
            #raise RuntimeError("Call optimize_holding_current first!")
        neuron_param = I.scp.NTParameterSet(self.neuron_param.as_dict())
        dummy_param = {
            'amplitude': self.holding_current,
            'duration': self.duration,
            'delay': self.delay
        }
        if not 'cell_modify_functions' in list(neuron_param.neuron.keys()):
            neuron_param.neuron['cell_modify_functions'] = {}
        neuron_param.neuron['cell_modify_functions'][
            'soma_current_injection'] = dummy_param
        return I.scp.NTParameterSet(neuron_param)

    def get_psp_simulator(self, gExRange=[1.0], exc_inh='exc', mode='synapses'):
        '''Set up a :py:class:`~simrun.synaptic_strength_fitting.PSPs` object to simulate individual synapse PSPs.
        
        This method initializes a PSPs object with the given parameters to simulate excitatory or inhibitory postsynaptic potentials.
        
        Args:
            mode (str): Mode of the simulation. Options:
            
            - ``'synapses'`` to activate individual synapses (default)
            - ``'cells'`` to activate individual cells
            
        Returns:
            PSPs: Object to simulate PSPs
        '''
        psp = PSPs(
            self.get_neuron_param_with_current_injection(),
            self.confile,
            gExRange=gExRange,
            mode=mode,
            exc_inh=exc_inh,
            tEnd=self.tEnd,
            tStim=self.optimize_for_timepoint)
        return psp

    def get_psp_simulator_exc_and_inh_combined(
        self,
        gExRange=[1.0],
        mode='synapses'):
        '''Set up and combine excitatory and inhibitory PSP simulators.
        
        This method initializes two PSPs objects, one for excitatory and one for inhibitory postsynaptic potentials, 
        and combines them into a single PSPs object.

        Args:
            gExRange (list): Range of excitatory conductance values to simulate (in :math:`\mu S`). Default: ``[1.0]``
            mode (str): Mode of the simulation. Options:
            
            - ``'synapses'`` to activate individual synapses (default)
            - ``'cells'`` to activate individual cells
            
        Returns:
            PSPs: Combined PSPs object with both excitatory and inhibitory components.
        '''
        psp_inh = self.get_psp_simulator(exc_inh='inh',
                                         gExRange=gExRange,
                                         mode=mode)
        print('len psp_inh', len(psp_inh._delayeds))
        psp_exc = self.get_psp_simulator(exc_inh='exc',
                                         gExRange=gExRange,
                                         mode=mode)
        print('len psp_exc', len(psp_exc._delayeds))
        psp_excinh = combine_PSP_objects(psp_exc, psp_inh)
        return psp_excinh

    def get(self):
        '''Get the final :py:class:`~simrun.synaptic_strength_fitting.PSPs` object.
        
        Shortcut to get the combined excitatory and inhibitory PSP object.
        
        Returns:
            :py:class:`~simrun.synaptic_strength_fitting.PSPs`: PSP object to simulate PSPs
        '''
        return self.get_psp_simulator_exc_and_inh_combined()


def combine_PSP_objects(PSPexc, PSPinh):
    """Combine two PSPs objects into one.
    
    Args:
        PSPexc (:py:class:`~simrun.synaptic_strength_fitting.PSPs`): :py:class:`~simrun.synaptic_strength_fitting.PSPs` object for excitatory synapses.
        PSPinh (:py:class:`~simrun.synaptic_strength_fitting.PSPs`): :py:class:`~simrun.synaptic_strength_fitting.PSPs` object for inhibitory synapses.
        
    Returns:
        :py:class:`~simrun.synaptic_strength_fitting.PSPs`: Combined :py:class:`~simrun.synaptic_strength_fitting.PSPs` object with both excitatory and inhibitory components.
    """
    assert PSPexc.neuron_param == PSPinh.neuron_param
    assert PSPexc.confile == PSPinh.confile
    assert PSPexc.gExRange == PSPinh.gExRange
    assert PSPexc.AMPA_component == PSPinh.AMPA_component
    assert PSPexc.NMDA_component == PSPinh.NMDA_component
    assert PSPexc.tStim == PSPinh.tStim
    assert PSPexc.tEnd == PSPinh.tEnd
    assert PSPexc.vardt == PSPinh.vardt
    assert PSPexc.mode == PSPinh.mode
    #     psp_out = PSPs(PSPexc.neuron_param, PSPexc.confile, PSPexc.gExRange,
    #                    PSPexc.AMPA_component, PSPexc.NMDA_component,
    #                    PSPexc.vardt, PSPexc.mode)
    psp_out = PSPexc
    #    psp_out.result = PSPexc.result + PSPinh.result
    psp_out._delayeds = PSPexc._delayeds + PSPinh._delayeds
    psp_out._keys = PSPexc._keys + PSPinh._keys
    return psp_out

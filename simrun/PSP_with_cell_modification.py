'''This module deals with the calculation of PSPs depending on cell modifications.

Such modifications could be a current injection into the soma to ensure a certain resting potential.
Other modificaiotns could be a coincident current injection triggering a burst to investigate
the effect of bursts on somatic integration of consecutive input.
Also, the modification could be synaptic input, to investigate the effect of one more synapse activation
on top of such input to the somatic subthreashold potential.
'''

import Interface as I
from biophysics_fitting.setup_stim import setup_soma_step
from scipy.optimize import minimize, minimize_scalar
from simrun.synaptic_strength_fitting import PSPs


class PSP_with_current_injection:
    '''allows to simulate EPSPs and IPSPs, where the soma resting potential is set to a
    defined potential by the injection of a constant current.'''

    def __init__(self,
                 neuron_param,
                 confile,
                 target_vm=-70,
                 delay=100,
                 duration=200,
                 optimize_for_timepoint=150,
                 tEnd=300,
                 cell_modify_functions={},
                 bounds=(0, 0.7)):
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
            if not 'cell_modify_functions' in list(
                    self.neuron_param.neuron.keys()):
                self.neuron_param.neuron['cell_modify_functions'] = {}
                print(cell_modify_functions)
            self.neuron_param.neuron['cell_modify_functions'].update(
                cell_modify_functions)

    def optimize_holding_current(self):
        '''finds the current that needs to be injected to hold the somatic potential at target_vm.
        target_vm is defined during initialization of the object.
        bounds: (min_current, max_current) in which the optimizer searches'''
        print(
            'starting optimization of holding current. target membrane potential is {} mV'
            .format(self.target_vm))
        bounds = self.bounds
        x = minimize_scalar(I.partial(self._objective_fun),
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
        '''function that gets optimized. Receives current, returns squared deviation from self.target_vm 
        at timepoint self.optimize_for_timepoint'''
        tVec, vm = self._get_current_dependent_vt(current)
        if max(vm[tVec > self.delay]) > -40:  # there may be no spikes
            print('careful: there are spikes during the PSP experiment!')
            return 10000
        tNew = I.np.arange(0, self.tEnd, 0.025)
        vmNew = I.np.interp(tNew, tVec, vm)
        out = (vmNew[int(self.optimize_for_timepoint / 0.025)] -
               self.target_vm)**2
        print(vmNew, out)
        return out

    def _get_current_dependent_vt(self, current):
        '''runs the current injection simulation'''
        with I.silence_stdout:
            cell = I.scp.create_cell(self.neuron_param.neuron)
        setup_soma_step(cell, current, self.delay, self.duration)
        self.neuron_param.sim.tStop = self.tEnd
        I.scp.init_neuron_run(self.neuron_param.sim, vardt=True)
        return I.np.array(cell.tVec), I.np.array(cell.soma.recVList[0])

    def plot_current_injection_voltage_trace(self):
        '''visualizes current_injection voltage trace'''
        if self.holding_current is None:
            self.optimize_holding_current()
            #raise RuntimeError("Call optimize_holding_current first!")
        tVec, vt = self._get_current_dependent_vt(self.holding_current)
        I.plt.plot(tVec, vt)
        I.display.display(I.plt.gcf())

    def get_neuron_param_with_current_injection(self):
        '''returns neuron_param, where a current injection is set up such that 
        the potential self.target_vm is reached at the timepoint self.optimize_for_timepoint'''
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
        '''returns simrun.synaptic_strength_fitting.PSPs method, which is set up to simulate
        individual synapse PSPs '''
        psp = PSPs(self.get_neuron_param_with_current_injection(),
                   self.confile,
                   gExRange=gExRange,
                   mode=mode,
                   exc_inh=exc_inh,
                   tEnd=self.tEnd,
                   tStim=self.optimize_for_timepoint)
        return psp

    def get_psp_simulator_exc_and_inh_combined(self,
                                               gExRange=[1.0],
                                               mode='synapses'):
        '''call the run method of the returned object to execute the computation'''
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
        '''returns final PSP object'''
        return self.get_psp_simulator_exc_and_inh_combined()


def combine_PSP_objects(PSPexc, PSPinh):
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

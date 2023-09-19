import Interface as I
import numpy as np
from biophysics_fitting.simulator import run_fun
from biophysics_fitting.parameters import set_fixed_params, param_to_kwargs
from biophysics_fitting.setup_stim import setup_soma_step
from biophysics_fitting.utils import tVec, vmSoma, vmApical, vmMax
from biophysics_fitting.hay_complete_default_setup import interpolate_vt
from biophysics_fitting import utils
from functools import partial
from neuron import h 
from crit_freq import setup_soma_step_with_current

######################################################
# Simulator which runs the hyperpolarizing stimuli protocols
######################################################

def _append(cell, name, item):
    try:
        getattr(cell, name)
    except AttributeError:
        setattr(cell, name, [])
    getattr(cell, name).append(item)
    
# make this nicer 
def record_with_current(cell):
    return {'tVec': tVec(cell), 
        'vList': (vmSoma(cell), vmApical(cell, dist)), 
        'iList': np.array(cell.iList)}
    
def record_at_dist_with_current(cell, dist = None):
    if dist: 
        return {'tVec': tVec(cell), 
            'vList': (vmSoma(cell), vmApical(cell, dist)), 
            'iList': np.array(cell.iList)}
    return record_with_current(cell)
    
    
def modify_simulator_to_run_hyperpolarizing_stimuli(s, duration = None, delay = None, amplitude = None):
    """typical defaults:duration = 1000, delay = 1000, amplitude = -0.05"""
    tStop = duration + delay + 1000
    s.setup.stim_run_funs.append(['hyperpolarizing.run', param_to_kwargs(partial(run_fun, T = 34.0, Vinit = -75.0, dt = 0.025, 
                                                                                 recordingSites = [], tStart = 0.0, tStop = tStop, vardt = True))])
    s.setup.stim_setup_funs.append(['hyperpolarizing.stim', param_to_kwargs(partial(setup_soma_step_with_current, amplitude = amplitude, delay = delay,
                                                                                    duration = duration))])
    s.setup.stim_response_measure_funs.append(['hyperpolarizing.measure', param_to_kwargs(partial(record_at_dist_with_current))])
    
    
def modify_simulator_to_run_dend_hyperpolarizing_stimuli(s, duration = None, delay = None, amplitude = None, dist = None):
    """typical defaults:duration = 1000, delay = 1000, amplitude = -0.05, dist = 400"""
    tStop = duration + delay + 1000
    s.setup.stim_run_funs.append(['dend_hyperpolarizing.run', param_to_kwargs(partial(run_fun, T = 34.0, Vinit = -75.0, dt = 0.025,
                                                                                      recordingSites = [], tStart = 0.0, tStop = tStop, vardt = True))])
    s.setup.stim_setup_funs.append(['dend_hyperpolarizing.stim', param_to_kwargs(partial(setup_soma_step_with_current, amplitude = amplitude, delay =
                                                                                         delay, duration = duration, dist = dist))])
    s.setup.stim_response_measure_funs.append(['dend_hyperpolarizing.measure', param_to_kwargs(partial(record_at_dist_with_current, dist = dist))])
    
######################################################
# Evaluator which can evaluate the hyperpolarizing stimuli protocols
######################################################                                  
                                               
class Hyperpolarizing:
    def __init__(self, 
                 delay = 1000,
                 duration = 1000,
                 amplitude = -0.05, 
                 definitions={'Rin':('Rin',46.8,18.6), 
                             'Sag':('Sag',36.6,9.2),
                             'Attenuation':('Attenuation',20,10)}):
    
        self.delay = delay
        self.duration = duration
        self.amplitude = amplitude
        self.definitions = definitions
        
    def get(self, **voltage_traces): #not voltage traces but tVec and vList 
        out = {}
        for name,(_,mean,std) in iter(self.definitions.items()):
            out.update(getattr(self, name)(voltage_traces, mean, std))
        return out    
        
    def Rin(self, voltage_traces, mean, std):
        t,v = voltage_traces['tVec'],voltage_traces['vList']
        Rin = (np.amin(v[0]) - v[0][int(np.where(t == (self.delay-20))[0])])/self.amplitude
       
        return {'hyperpolarizing.Rin.raw': Rin, 'hyperpolarizing.Rin.normalized': (Rin - mean)/std, 'hyperpolarizing.Rin':(Rin - mean)/std}

    def Sag(self, voltage_traces, mean, std):
        
        t,v = voltage_traces['tVec'],voltage_traces['vList']
    
        d = np.where(t == self.delay)[0]
        c = np.where(t == (self.delay+self.duration-20))
        b = np.where(t == (self.delay+self.duration))
        baseline = v[0][int(np.where(t == (self.delay-20))[0])]

        sag_difference = np.average(v[0][int(c[0]):int(b[0])]) - I.np.amin(v[0][int(d):])
        sag = (sag_difference/(I.np.amin(v[0][int(d):])-baseline))*-100
    
        return {'hyperpolarizing.Sag.raw': sag, 'hyperpolarizing.Sag.normalized': (sag - mean)/std, 'hyperpolarizing.Sag':(sag - mean)/std}
   
    def Attenuation(self,  voltage_traces, mean, std): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'], voltage_traces['iList']
        
        c = np.where(t == (self.delay-10))
        b = np.where(t == (self.delay))

        v0_baseline = np.average(v[0][int(c[0]):int(b[0])])
        v1_baseline = np.average(v[1][int(c[0]):int(b[0])])             

        v0 = np.min(v[0][int(b[0]):]) - v0_baseline
        v1 =  np.min(v[1][int(b[0]):]) - v1_baseline
    
        Attenuation = v1/v0
        return {'hyperpolarizing.Attenuation.raw': Attenuation, 'hyperpolarizing.Attenuation.normalized': (Attenuation - mean)/std, 'hyperpolarizing.Attenuation':(Attenuation - mean)/std}           
    
    
class Dend_hyperpolarizing:
    def __init__(self, 
                 delay = 300,
                 duration = 200,
                 amplitude = -0.05, 
                 definitions={'Dend_Rin':('Dend_Rin',46.8,18.6)}):
    
        self.delay = delay
        self.duration = duration
        self.amplitude = amplitude
        self.definitions = definitions
        
    def get(self, **voltage_traces):
        out = {}
        for name,(_,mean,std) in iter(self.definitions.items()):
            out.update(getattr(self, name)(voltage_traces, mean, std))
        return out    
        
    def Dend_Rin(self, voltage_traces, mean, std):
        t,v = voltage_traces['tVec'],voltage_traces['vList']
        d = np.where(t == self.delay)[0]
        
        Rin = (np.amin(v[1][int(d):]) - v[1][int(np.where(t == (self.delay-20))[0])])/self.amplitude
       
        return {'hyperpolarizing.Dend_Rin.raw': Rin, 'hyperpolarizing.Dend_Rin.normalized': (Rin - mean)/std, 'hyperpolarizing.Dend_Rin':(Rin - mean)/std}
    
def modify_evaluator_to_evaluate_hyperpolarizing_stimuli(e): 
    hpz = Hyperpolarizing()
    d_hpz = Dend_hyperpolarizing()
                                               
    e.setup.evaluate_funs.append(['hyperpolarizing.measure', hpz.get,'hyperpolarizing.features'])
    e.setup.evaluate_funs.append(['dend_hyperpolarizing.measure', d_hpz.get,'dend_hyperpolarizing.features'])
                               
    
######################################################
# Combiner which can evaluate the crit. freq. protocols
######################################################

def modify_combiner_to_add_hyperpolarizing_stimuli_error(c):
    c.setup.append('hyperpolarizing.Rin', ['hyperpolarizing.Rin'])
    c.setup.append('hyperpolarizing.Sag', ['hyperpolarizing.Sag'])
    c.setup.append('hyperpolarizing.Attenuation', ['hyperpolarizing.Attenuation'])
    c.setup.append('hyperpolarizing.Dend_Rin', ['hyperpolarizing..Dend_Rin'])
    
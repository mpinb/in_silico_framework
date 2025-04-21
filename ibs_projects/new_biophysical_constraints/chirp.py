import Interface as I
import numpy as np
from biophysics_fitting.simulator import run_fun
from biophysics_fitting.parameters import set_fixed_params, param_to_kwargs
from biophysics_fitting.setup_stim import setup_soma_step
from biophysics_fitting.utils import tVec, vmSoma, vmApical, vmMax
from biophysics_fitting import utils
from functools import partial
from neuron import h 
import scipy.signal
import scipy.ndimage as ndi
import math

######################################################
# Simulator which runs the chirp protocols
######################################################

def _append(cell, name, item):
    try:
        getattr(cell, name)
    except AttributeError:
        setattr(cell, name, [])
    getattr(cell, name).append(item)
    
    
def make_chirp_stim(duration = None, delay = None, final_freq = None):
    tt = np.linspace(0, final_freq, duration)
    #linear chirp over time points tt, from 1Hz to final_freq, in duration ms (duration/1000 secs), starting from baseline (phi=-90)
    chirp_log = scipy.signal.chirp(t = tt , f0= 1, t1 = duration/1000, f1 = final_freq, phi=-90) 
    chirp_log = np.concatenate((np.zeros(delay), chirp_log))
    t_stim = tt*1000
    v_stim = 0.05*chirp_log
    
    return t_stim, v_stim
    
    
def setup_iclamp_vplay(cell, delay = None, duration = None, final_freq = None, dist = None):
    t_stim, v_stim = make_chirp_stim(duration = duration, delay = delay, final_freq = final_freq)
    stim_duration_incl_delay = delay + duration 
    
    if dist == 0: 
        sec = cell.soma
        x = 0.5
    else:
        sec, x = utils.get_inner_section_at_distance(cell, dist)  

    iclamp = h.IClamp(x, sec=sec)

    iclamp.delay = 0 # the actual delay is integrated into the v_stim
    iclamp.dur = stim_duration_incl_delay

    iList = h.Vector()
    iList.record(iclamp._ref_i)

    v_stim = h.Vector(v_stim)
    t_stim = h.Vector(t_stim)
    v_stim.play(iclamp._ref_amp, t_stim, False)

    _append(cell, 'iclamp', iclamp)
    _append(cell, 'iList', iList)
    _append(cell, 't_stim', t_stim)
    _append(cell, 'v_stim', v_stim)


def record_chirp_dist(cell, recSite_dist = None, recSite2 = None):
    assert(recSite2 is not None)
    return {'tVec': tVec(cell), 
        'vList': (vmSoma(cell), vmApical(cell, recSite_dist), vmApical(cell, recSite2)),
        'iList': np.array(cell.iList)}

    
def modify_simulator_to_run_chirp_stimuli(s, delay = None, duration = None, final_freq  = None, dist = None):
    """typical defaults: delay = 300, duration = 10000, final_freq = 20, dist = 400"""
    
    tStop = duration + delay
    
    # # 'Run function'
    chirp_run = I.partial(run_fun, T = 34.0, Vinit = -75.0, dt = 0.025, 
                                     recordingSites = [], tStart = 0.0, tStop = tStop, vardt = True)
    
    s.setup.stim_run_funs.append(['chirp.run', param_to_kwargs(chirp_run)])
    s.setup.stim_run_funs.append(['chirp_dend.run', param_to_kwargs(chirp_run)])

    s.setup.stim_setup_funs.append(['chirp.stim', param_to_kwargs(I.partial(setup_iclamp_vplay, delay = delay, duration = duration, final_freq = 20, dist = 0))])
    s.setup.stim_setup_funs.append(['chirp_dend.stim', param_to_kwargs(I.partial(setup_iclamp_vplay, delay = delay, duration = duration, final_freq = 20, dist = dist))])

    s.setup.stim_response_measure_funs.append(['chirp.hay_measure', param_to_kwargs(I.partial(record_chirp_dist, recSite_dist = dist))])
    s.setup.stim_response_measure_funs.append(['chirp_dend.hay_measure', param_to_kwargs(I.partial(record_chirp_dist, recSite_dist = dist))])
    

######################################################
# Evaluator which can evaluate the chirp protocol
######################################################

def polyfilt_smoothing(freq_axis, Z_P):
    '''Z_P is either ZAP or ZPP'''
    cropped_Z_P =  [y for x, y in zip(freq_axis, Z_P) if x>= 1]
    cropped_freq =  [x for x, y in zip(freq_axis, Z_P) if x>= 1]

    coefs = I.np.polyfit(cropped_freq, cropped_Z_P, 13)

    freq_axis_high_res = I.np.arange(0.0,20.0001,0.01)
    fit = [I.np.polyval(coefs, x) for x in freq_axis_high_res]
    return freq_axis_high_res, fit

#new evaluation with fitting 
class Chirp: 
    def __init__(self,  
                 delay = None,
                 duration = None,
                 definitions={'Res_freq':('Res_freq',3.81,0.68), #the std is not actually std. it's a place holder, larger than real std (0.11) to make x*3 close to the experimental range 
                             'ZPP':('ZPP',5,1)}):

        
        #
        self.delay = delay
        self.duration = duration
        self.definitions = definitions
    
    def get(self, **voltage_traces): #not voltage traces but tVec and vList 
        out = {}
        for name,(_,mean,std) in iter(self.definitions.items()):
            out.update(getattr(self, name)(voltage_traces, mean, std))
        return out   

    def variables(self, voltage_traces): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        
        tStop = self.delay + self.duration
        delay_ratio = (self.delay)/tStop
        signal_start = int(len(i)*delay_ratio)
        n = len(i[signal_start:])
        freq_axis = I.np.fft.rfftfreq(n, d=2.5e-5)
        freq_indx = int(np.where(freq_axis > 20)[0][0])
        freq_axis = freq_axis[1:freq_indx]
        return signal_start, freq_axis, freq_indx
        
    def fft_mag(self, voltage_traces, signal): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        v_dendrite = voltage_traces['vList'][2] 
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)
        
        return (I.np.abs(I.np.fft.rfft(signal[signal_start:]))[1:freq_indx])

    def Res_freq(self, voltage_traces, mean, std):
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)

        stim_fft = self.fft_mag(voltage_traces, i)
        response_fft = self.fft_mag(voltage_traces, v)
        ZAP = response_fft/stim_fft
        freq_axis_high_res, fit = polyfilt_smoothing(freq_axis, ZAP)
        Res_freq = freq_axis_high_res[(np.where(fit == max(fit)))[0]][0]
        
        return {'chirp.res_freq.normalized': (Res_freq- mean)/std, 'chirp.res_freq.raw': Res_freq,'chirp.res_freq': I.np.abs((Res_freq- mean)/std), 
               'chirp.ZAP': fit}
                 
    def ZPP(self, voltage_traces, mean, std): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)

        z_ratio = I.np.fft.rfft(v[signal_start:])/I.np.fft.rfft(i[signal_start:])
        ZPP = (I.np.angle(z_ratio)[1:freq_indx])*(180/I.np.pi)
        
        freq_axis_high_res, fit = polyfilt_smoothing(freq_axis, ZPP)
        return {'chirp.ZPP': fit, 'chirp.freq_axis': freq_axis, 'chirp.freq_axis_high_res': freq_axis_high_res}
    
    
class Chirp_dend: 
    def __init__(self, 
                 delay = None,
                 duration = None,
                 definitions={'Res_freq_dend':('Res_freq_dend',6,1.3),  #the std is not actually std. it's a place holder, larger than real std to make x*3 close to the experimental range 
                             'Transfer_dend':('Transfer_dend',5.82,1.2),  #the std is not actually std. it's a place holder, larger than real std (0.17) to make x*3 close to the experimental range 
                             'ZPP_dend':('ZPP_dend',5,1)}):
    
        self.delay = delay
        self.duration = duration
        self.definitions = definitions
    
    def get(self, **voltage_traces): #not voltage traces but tVec and vList 
        out = {}
        for name,(_,mean,std) in iter(self.definitions.items()):
            out.update(getattr(self, name)(voltage_traces, mean, std))
        return out   

    def variables(self, voltage_traces): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        
        tStop = self.delay + self.duration
        delay_ratio = tStop/self.delay 
        signal_start = int(len(i)/delay_ratio +1)
        n = len(i[signal_start:])
        freq_axis = I.np.fft.rfftfreq(n, d=2.5e-5)
        freq_indx = int(np.where(freq_axis > 20)[0][0])
        freq_axis = freq_axis[1:freq_indx]
        return signal_start, freq_axis, freq_indx
        
    def fft_mag(self, voltage_traces, signal): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        v_dendrite = voltage_traces['vList'][1] 
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)
        
        return (I.np.abs(I.np.fft.rfft(signal[signal_start:]))[1:freq_indx])/(len(signal)/2)
        
    def Res_freq_dend(self, voltage_traces, mean, std):
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        v_dendrite = voltage_traces['vList'][1]
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)

        stim_fft = self.fft_mag(voltage_traces, i)
        response_fft = self.fft_mag(voltage_traces, v_dendrite)
        ZAP = response_fft/stim_fft
        freq_axis_high_res, fit = polyfilt_smoothing(freq_axis, ZAP)
        Res_freq = freq_axis_high_res[(np.where(fit == max(fit)))[0]][0]
        
        return {'chirp.res_freq_dend': I.np.abs((Res_freq- mean)/std), 'chirp.res_freq_dend.normalized': (Res_freq- mean)/std, 'chirp.res_freq_dend.raw': Res_freq, 
               'chirp.ZAP_dend': fit}
   
    def Transfer_dend(self, voltage_traces, mean, std):
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        v_dendrite = voltage_traces['vList'][1] 
        
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)
        
        stim_fft = self.fft_mag(voltage_traces, i)
        response_fft = self.fft_mag(voltage_traces, v)
        ZAP = response_fft/stim_fft
        freq_axis_high_res, fit = polyfilt_smoothing(freq_axis, ZAP)
        Transfer = freq_axis_high_res[(np.where(fit == max(fit)))[0]][0]
        
        return {'chirp.transfer_dend': I.np.abs((Transfer - mean)/std), 
                'chirp.transfer_dend.normalized': (Transfer - mean)/std,
                'chirp.transfer_dend.raw': Transfer, 
               'chirp.transfer_ZAP': fit}              
                 
    def ZPP_dend(self, voltage_traces, mean, std): 
        t,v,i = voltage_traces['tVec'],voltage_traces['vList'][0], voltage_traces['iList'][0]
        signal_start, freq_axis, freq_indx = self.variables(voltage_traces)
        
        z_ratio = I.np.fft.rfft(v[signal_start:])/I.np.fft.rfft(i[signal_start:])
        ZPP = (I.np.angle(z_ratio)[1:freq_indx])*(180/I.np.pi)
        
        freq_axis_high_res, fit = polyfilt_smoothing(freq_axis, ZPP)
        
#         #zpp at the dendrite 
#         v_dendrite = voltage_traces['vList'][1] 
#         z_ratio_d = I.np.fft.rfft(v_dendrite[signal_start:])/I.np.fft.rfft(i[signal_start:])
#         ZPP_dend_dend = (I.np.angle(z_ratio_d)[1:freq_indx])*(180/I.np.pi)
#         freq_axis_high_res, fit_d = polyfilt_smoothing(freq_axis, ZPP_dend_dend)
#         #

        return {'chirp.ZPP_dend': fit, 'chirp.freq_axis': freq_axis,  'chirp.freq_axis_high_res': freq_axis_high_res}
               #'chirp.ZPP_dend_dend': fit_d}

def Synch(dict_): 
    #ZPP: impedance phase profile
    #ZAP: impedance amplitude profile


        synch = {}
        if not 'chirp.freq_axis_high_res' in dict_:
            return dict_
        
        T, A1, A2 = dict_['chirp.freq_axis_high_res'], dict_['chirp.ZPP'], dict_['chirp.ZPP_dend']
        
        for x, a1, a2 in zip(T, A1, A2): 
            if abs(a1 - a2) < 0.5 and x>1: # below 1 Hz is not sampled by the chirp stimulus
                synch[x] = (a1, a2)

        if synch:       
            # seperate intervals in which the two curves are close
            intervals = [] # intervals refers to the consecutive timepoints in which both curves are close
            in_interval = False
            for t in T:
                if t in synch:
                    if in_interval == False:
                        intervals.append([]) # intervals refers to the consecutive timepoints in which both curves are close
                    a1, a2 = synch[t]
                    intervals[-1].append((t, a1-a2))
                    in_interval = True        
                else:
                    in_interval = False

            # select intervals, which contain a crossing
            intervals_with_crossing = []
            for i in intervals:
                differences = [x[1] for x in i]
                max_ = max(differences)
                min_ = min(differences)
                if (max_ > 0) and (min_ < 0):
                    intervals_with_crossing.append(i)

            if intervals_with_crossing: 
                selected_interval = intervals_with_crossing[-1]
                synch_freq = I.np.mean([x[0] for x in selected_interval])
            else: 
                synch_freq = -1000
                dict_['chirp.no_intervals_with_crosssing'] = True
        #     synch_freq = [(x+y)/2 for (x,y) in synch_freq]
        else: 
            synch_freq = -1000
            dict_['chirp.not_close'] = True

        mean = 6.63
        std = 1.5 

        dict_['chirp.synch_freq.raw'] = synch_freq
        dict_['chirp.synch_freq.normalized'] = (synch_freq - mean)/std
        dict_['chirp.synch_freq'] = I.np.abs((synch_freq - mean)/std)
                
        return dict_
    
    
def modify_evaluator_to_evaluate_chirp_stimuli(e, delay = None, duration = None):
    """typical defaults: delay = 300, duration = 10000"""
    
    chirp = Chirp(delay = delay, duration = duration)
    chirp_dend = Chirp_dend(delay = delay, duration = duration)
    
    e.setup.evaluate_funs.append(['chirp.hay_measure', chirp.get,'chirp.features'])
    e.setup.evaluate_funs.append(['chirp_dend.hay_measure', chirp_dend.get,'chirp_dend.features'])
    e.setup.finalize_funs.append(Synch)

    
######################################################
# Combiner which can evaluate the crit. freq. protocols
######################################################

def modify_combiner_to_add_chirp_error(c):
    c.setup.append('chirp.synch_freq', ['chirp.synch_freq'])
    c.setup.append('chirp.transfer_dend', ['chirp.transfer_dend'])
    c.setup.append('chirp.res_freq_dend', ['chirp.res_freq_dend'])
    c.setup.append('chirp.res_freq', ['chirp.res_freq'])
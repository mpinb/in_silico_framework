'''
A Python translation of the evaluation functions used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.
This module provides methods to run Hay's stimulus protocols, and evaluate the resulting voltage traces.
'''

import numpy as np
from .ephys import *

__author__ = 'Arco Bast'
__date__ = '2018-11-08'

# moved to the bottom to resolve circular import
# from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf

objectives_step = [
    'AI1', 'AI2', 'AI3', 'APh1', 'APh2', 'APh3', 'APw1', 'APw2', 'APw3', 'DI1',
    'DI2', 'ISIcv1', 'ISIcv2', 'ISIcv3', 'TTFS1', 'TTFS2', 'TTFS3', 'fAHPd1',
    'fAHPd2', 'fAHPd3', 'mf1', 'mf2', 'mf3', 'sAHPd1', 'sAHPd2', 'sAHPd3',
    'sAHPt1', 'sAHPt2', 'sAHPt3'
]  # objectives for the step current injection protocol

objectives_BAC = [
    'BAC_APheight', 'BAC_ISI', 'BAC_ahpdepth', 'BAC_caSpike_height',
    'BAC_caSpike_width', 'BAC_spikecount', 'bAP_APheight', 'bAP_APwidth',
    'bAP_att2', 'bAP_att3', 'bAP_spikecount'
]  # objectives for the BAC and bAP protocols


def normalize(raw, mean, std):
    """Normalize a raw value.
    
    Args:
        raw: raw value
        mean: mean value
        std: standard deviation
        
    Returns:
        float: normalized value"""
    return np.mean(np.abs(raw - mean)) / std


def nan_if_error(fun):
    """Wrapper method that returns nan if an error occurs.
    
    Args:
        fun: function to run
        
    Returns:
        function: wrapped function
    """
    def helper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except:
            return float('nan')

    return helper


class BAC:
    """
    This class contains methods to calculate various metrics
    to assess the accuracy of some simulation based on the voltage trace
    it produced. These metrics were introduced by Idan Segev, and illustrated in
    "Ion channel distributions in cortical neurons are optimized for energy-efficient
    active dendritic computations" by Arco Bast and Marcel Oberlaender :cite:`Guest_Bast_Narayanan_Oberlaender`.
    """

    def __init__(
        self,
        hot_zone_thresh=-55,
        soma_thresh=-30,
        ca_max_after_nth_somatic_spike=2,
        stim_onset=295,
        stim_duration=45,
        repolarization=-55,
        punish=250,
        punish_last_spike_after_deadline=True,
        punish_minspikenum=2,
        punish_returning_to_rest_tolerance=2.,
        punish_max_prestim_dendrite_depo=-50,
        prefix='',
        definitions=None
        ):

        self.hot_zone_thresh = hot_zone_thresh
        self.soma_thresh = soma_thresh
        self.ca_max_after_nth_somatic_spike = ca_max_after_nth_somatic_spike
        self.stim_onset = stim_onset
        self.stim_duration = stim_duration
        self.definitions = definitions if definitions is not None else {
            'BAC_APheight': ('AP_height', 25.0, 5.0),
            'BAC_ISI': ('BAC_ISI', 9.901, 0.8517),
            'BAC_ahpdepth': ('AHP_depth_abs', -65.0, 4.0),
            'BAC_caSpike_height': ('BAC_caSpike_height', 6.73, 2.54),
            'BAC_caSpike_width': ('BAC_caSpike_width', 37.43, 1.27),
            'BAC_spikecount': ('Spikecount', 3.0, 0.01)
        }
        self.repolarization = repolarization
        self.punish = punish
        self.punish_last_spike_after_deadline = punish_last_spike_after_deadline
        self.punish_minspikenum = punish_minspikenum
        self.punish_returning_to_rest_tolerance = punish_returning_to_rest_tolerance
        self.punish_max_prestim_dendrite_depo = punish_max_prestim_dendrite_depo
        self.prefix = prefix

    def get(self, **voltage_traces):
        import six
        spikecount = self.BAC_spikecount(voltage_traces)['.raw']
        out = {}
        for name, (_, mean, std) in six.iteritems(self.definitions):
            # special case in the original code were in the case of two somatic spikes
            # 7 is substracted from the mean
            if spikecount == 2 and name == 'BAC_caSpike_width':
                mean = mean - 7.
            out_current = getattr(self, name)(voltage_traces)
            out_current['.normalized'] = normalize(out_current['.raw'], mean,
                                                   std)
            checks = [v for k, v in six.iteritems(out_current) if 'check' in k]
            if all(checks):
                out_current[''] = out_current['.normalized']
            else:
                out_current[''] = 20.  # *std
            out_current = {name + k: v for k, v in six.iteritems(out_current)}
            out.update(out_current)
        return self.check(out, voltage_traces)

    def check(self, out, voltage_traces):
        # checking for problems in voltage trace
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        vmax = None  # voltage_traces['vMax']
        err = trace_check_err(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            punish=self.punish)
        err_flags = trace_check(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            minspikenum=self.punish_minspikenum,
            soma_threshold=self.soma_thresh,
            returning_to_rest=self.punish_returning_to_rest_tolerance,
            name='BAC',
            vmax=vmax)
        if self.punish_last_spike_after_deadline:
            relevant_err_flags = err_flags
        else:
            import six
            relevant_err_flags = {
                k: v
                for k, v in six.iteritems(err_flags)
                if not 'last_spike_before_deadline' in k
            }
        for name in list(self.definitions.keys()):
            if not all(relevant_err_flags.values()):
                out[name] = err
            elif out[name] > self.punish:
                out[name] = self.punish * 0.75
            # change from hay algorithm by arco: if high depolarization anywhere in the dendrite occurs before stimulus, put highest punish value
            if not err_flags['BAC.check_max_prestim_dendrite_depo']:
                out[name] = self.punish
        out['BAC.err'] = err
        out.update(err_flags)
        out = {self.prefix + k: out[k] for k in out.keys()}
        return out

    def BAC_spikecount(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.raw': nan_if_error(spike_count)(t, v, thresh=self.soma_thresh)
        }

    def BAC_APheight(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.check_1AP':
                nan_if_error(AP_height_check_1AP)(t, v,
                                                  thresh=self.soma_thresh),
            '.raw':
                nan_if_error(AP_height)(t, v, thresh=self.soma_thresh)
        }

    def BAC_ISI(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        stim_end = self.stim_onset + self.stim_duration
        r = self.repolarization
        return {
            '.check_2_or_3_APs':
                nan_if_error(BAC_ISI_check_2_or_3_APs)(t,
                                                       v,
                                                       thresh=self.soma_thresh),
            '.check_repolarization':
                nan_if_error(BAC_ISI_check_repolarization)(t,
                                                           v,
                                                           stim_end=stim_end,
                                                           repolarization=r),
            '.raw':
                nan_if_error(BAC_ISI)(t, v, thresh=self.soma_thresh)
        }

    def BAC_ahpdepth(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.check_2AP':
                nan_if_error(AHP_depth_abs_check_2AP)(t,
                                                      v,
                                                      thresh=self.soma_thresh),
            '.raw':
                nan_if_error(AHP_depth_abs)(t, v, thresh=self.soma_thresh)
        }

    def BAC_caSpike_height(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        v_dend = voltage_traces['vList'][1]
        tend = self.stim_duration + self.stim_onset
        return {'.check_1_Ca_AP': nan_if_error(BAC_caSpike_height_check_1_Ca_AP)(t,v,v_dend,thresh=self.hot_zone_thresh),
                '.check_>=2_Na_AP': nan_if_error(BAC_caSpike_height_check_gt2_Na_spikes)(t,v,v_dend,thresh=self.soma_thresh),
                '.check_ca_max_after_nth_somatic_spike':  \
                    nan_if_error(BAC_caSpike_height_check_Ca_spikes_after_Na_spike)(t,v,v_dend,
                                                                      n=self.ca_max_after_nth_somatic_spike,
                                                                      thresh=self.soma_thresh),
                '.raw': nan_if_error(BAC_caSpike_height)(t,v,v_dend,ca_thresh=self.hot_zone_thresh,tstim=self.stim_onset)}

    def BAC_caSpike_width(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        v_dend = voltage_traces['vList'][1]
        return {
            '.check_1_Ca_AP':
                nan_if_error(BAC_caSpike_width_check_1_Ca_AP)
                (t, v, v_dend, thresh=self.hot_zone_thresh),
            '.raw':
                nan_if_error(BAC_caSpike_width)(t,
                                                v,
                                                v_dend,
                                                thresh=self.hot_zone_thresh)
        }


class bAP:

    def __init__(
        self,
        soma_thresh=-30,
        stim_onset=295,
        stim_duration=5,
        bAP_thresh='+2mV',
        punish=250.,
        punish_last_spike_after_deadline=True,
        punish_minspikenum=1,
        punish_returning_to_rest_tolerance=2.,
        definitions={
            'bAP_APheight': ('AP_height', 25.0, 5.0),
            'bAP_APwidth': ('AP_width', 2.0, 0.5),
            'bAP_att2': ('BPAPatt2', 45.0, 10.0),
            'bAP_att3': ('BPAPatt3', 36.0, 9.33),
            'bAP_spikecount': ('Spikecount', 1.0, 0.01)
        }):

        self.soma_thresh = soma_thresh
        self.stim_onset = stim_onset
        self.stim_duration = stim_duration
        self.definitions = definitions
        self.bAP_thresh = bAP_thresh
        self.punish = punish
        self.punish_last_spike_after_deadline = punish_last_spike_after_deadline
        self.punish_minspikenum = punish_minspikenum
        self.punish_returning_to_rest_tolerance = punish_returning_to_rest_tolerance

    def get(self, **voltage_traces):
        out = {}
        import six
        for name, (_, mean, std) in six.iteritems(self.definitions):
            out_current = getattr(self, name)(voltage_traces)
            out_current['.normalized'] = normalize(out_current['.raw'], mean,
                                                   std)
            checks = [v for k, v in six.iteritems(out_current) if 'check' in k]
            if all(checks):
                out_current[''] = out_current['.normalized']
            else:
                out_current[''] = 20  # *std
            out_current = {name + k: v for k, v in six.iteritems(out_current)}
            out.update(out_current)
        return self.check(out, voltage_traces)

    def check(self, out, voltage_traces):
        # checking for problems in voltage trace
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        vmax = None  # voltage_traces['vMax']
        err = trace_check_err(t,
                              v,
                              stim_onset=self.stim_onset,
                              stim_duration=self.stim_duration,
                              punish=self.punish)
        err_flags = trace_check(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            minspikenum=self.punish_minspikenum,
            soma_threshold=self.soma_thresh,
            returning_to_rest=self.punish_returning_to_rest_tolerance,
            name='bAP',
            vmax=vmax)
        if self.punish_last_spike_after_deadline:
            relevant_err_flags = err_flags
        else:
            import six
            relevant_err_flags = {
                k: v
                for k, v in six.iteritems(err_flags)
                if not 'last_spike_before_deadline' in k
            }
        for name in list(self.definitions.keys()):
            if not all(relevant_err_flags.values()):
                out[name] = err
            elif out[name] > self.punish:
                out[name] = self.punish * 0.75
            if not err_flags['bAP.check_max_prestim_dendrite_depo']:
                out[name] = self.punish
        out['bAP.err'] = err
        out.update(err_flags)
        return out

    def bAP_APheight(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.check_1AP':
                nan_if_error(AP_height_check_1AP)(t, v,
                                                  thresh=self.soma_thresh),
            '.raw':
                nan_if_error(AP_height)(t, v, thresh=self.soma_thresh)
        }

    def bAP_APwidth(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.check_1AP':
                nan_if_error(AP_width_check_1AP)(t, v, thresh=self.soma_thresh),
            '.raw':
                nan_if_error(AP_width)(t, v, thresh=self.soma_thresh)
        }

    def bAP_spikecount(self, voltage_traces):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        return {
            '.raw': nan_if_error(spike_count)(t, v, thresh=self.soma_thresh)
        }

    def _bAP_att(self, voltage_traces, _n=1):
        t, v = voltage_traces['tVec'], voltage_traces['vList'][0]
        v_dend = voltage_traces['vList'][_n]
        return {
            '.raw':
                nan_if_error(BPAPatt)(t, v_dend, self.bAP_thresh,
                                      self.stim_onset),
            '.check_1_AP':
                nan_if_error(BPAPatt_check_1_AP)(t, v, thresh=self.soma_thresh),
            '.check_relative_height':
                nan_if_error(BPAPatt_check_relative_height)
                (t, v, v_dend, self.bAP_thresh, self.stim_onset)
        }

    def bAP_att2(self, voltage_traces):
        return self._bAP_att(voltage_traces, _n=1)

    def bAP_att3(self, voltage_traces):
        return self._bAP_att(voltage_traces, _n=2)


def get_evaluate_bAP(**kwargs):
    bap = bAP(**kwargs)

    def fun(**kwargs):
        return bap.get(kwargs)

    return fun


def get_evaluate_BAC(**kwargs):
    bac = BAC(**kwargs)

    def fun(**kwargs):
        return bac.get(kwargs)

    return fun

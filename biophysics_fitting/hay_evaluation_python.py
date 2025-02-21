"""
A Python translation of the evaluation functions used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.
This module provides methods to run Hay's stimulus protocols, and evaluate the resulting voltage traces.
"""

from typing import Any

import numpy as np
import six
from six import iteritems

from biophysics_fitting.hay_specification import (
    HAY_BAC_DEFINITIONS,
    HAY_BAP_DEFINITIONS,
    HAY_STEP1_DEFINITIONS,
    HAY_STEP2_DEFINITIONS,
    HAY_STEP3_DEFINITIONS,
)

from .ephys import *

__author__ = "Arco Bast"
__date__ = "2018-11-08"

# moved to the bottom to resolve circular import
# from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf

objectives_step = [
    "AI1",
    "AI2",
    "AI3",
    "APh1",
    "APh2",
    "APh3",
    "APw1",
    "APw2",
    "APw3",
    "DI1",
    "DI2",
    "ISIcv1",
    "ISIcv2",
    "ISIcv3",
    "TTFS1",
    "TTFS2",
    "TTFS3",
    "fAHPd1",
    "fAHPd2",
    "fAHPd3",
    "mf1",
    "mf2",
    "mf3",
    "sAHPd1",
    "sAHPd2",
    "sAHPd3",
    "sAHPt1",
    "sAHPt2",
    "sAHPt3",
]  # objectives for the step current injection protocol

objectives_BAC = [
    "BAC_APheight",
    "BAC_ISI",
    "BAC_ahpdepth",
    "BAC_caSpike_height",
    "BAC_caSpike_width",
    "BAC_spikecount",
    "bAP_APheight",
    "bAP_APwidth",
    "bAP_att2",
    "bAP_att3",
    "bAP_spikecount",
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
            return float("nan")

    return helper


class BAC:
    """Evaluate the :math:`BAC` stimulus protocol.

    These metrics were introduced by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`, and illustrated in :cite:t:`Guest_Bast_Narayanan_Oberlaender`.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_BAC` for more information on the stimulus protocol.

    Attributes:
        hot_zone_thresh (float): The threshold for APs in the dendritic voltage trace. Defaults to :math:`-55` mV.
        soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30` mV.
        ca_max_after_nth_somatic_spike (int): The number of somatic spikes after which the calcium spike maximum should occur. Defaults to :math:`2`.
        stim_onset (float): The onset of the stimulus (ms). Defaults to :math:`295` ms.
        stim_duration (float): The duration of the stimulus (ms). Defaults to :math:`45` ms.
        repolarization (float): The target repolarization voltage after the stimulus.
            See :py:meth:`~biophysics_fitting.ephys.BAC_ISI_check_repolarization`.
            Defaults to :math:`-55` mV.
        punish (float): The punishment value in units of :math:`\sigma`.
            Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
            Defaults to :math:`250`.
        punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
        punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol.
        punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
        prefix (str): The prefix for the evaluation metric checks. Defaults to an empty string.
        definitions (dict): The empirical means and standard deviations for the evaluation metrics. Defaults to::

            {
                'BAC_APheight': ('AP_height', 25.0, 5.0),
                'BAC_ISI': ('BAC_ISI', 9.901, 0.8517),
                'BAC_ahpdepth': ('AHP_depth_abs', -65.0, 4.0),
                'BAC_caSpike_height': ('BAC_caSpike_height', 6.73, 2.54),
                'BAC_caSpike_width': ('BAC_caSpike_width', 37.43, 1.27),
                'BAC_spikecount': ('Spikecount', 3.0, 0.01)
            }
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
        punish_returning_to_rest_tolerance=2.0,
        punish_max_prestim_dendrite_depo=-50,
        prefix="",
        definitions=HAY_BAC_DEFINITIONS,
    ):
        """
        Args:
            hot_zone_thresh (float): The threshold for APs in the dendritic voltage trace. Defaults to :math:`-55` mV.
            soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30` mV.
            ca_max_after_nth_somatic_spike (int): The number of somatic spikes after which the calcium spike maximum should occur. Defaults to :math:`2`.
            stim_onset (float): The onset of the stimulus (ms). Defaults to :math:`295` ms.
            stim_duration (float): The duration of the stimulus (ms). Defaults to :math:`45` ms.
            repolarization (float): The target repolarization voltage after the stimulus.
                See :py:meth:`~biophysics_fitting.ephys.BAC_ISI_check_repolarization`.
                Defaults to :math:`-55` mV.
            punish (float): The punishment value in units of :math:`\sigma`.
                Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
                Defaults to :math:`250`.
            punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
            punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol.
            punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
            prefix (str): The prefix for the evaluation metric checks. Defaults to an empty string.
            definitions (dict): The definitions for the evaluation metrics. See also: :py:attr:`definitions`.
        """
        # TODO: punish_max_prestim_dendrite_depo is unused?
        self.hot_zone_thresh = hot_zone_thresh
        self.soma_thresh = soma_thresh
        self.ca_max_after_nth_somatic_spike = ca_max_after_nth_somatic_spike
        self.stim_onset = stim_onset
        self.stim_duration = stim_duration
        self.definitions = definitions
        self.repolarization = repolarization
        self.punish = punish
        self.punish_last_spike_after_deadline = punish_last_spike_after_deadline
        self.punish_minspikenum = punish_minspikenum
        self.punish_returning_to_rest_tolerance = punish_returning_to_rest_tolerance
        self.punish_max_prestim_dendrite_depo = punish_max_prestim_dendrite_depo
        self.prefix = prefix

    def get(self, **voltage_traces):
        """Get the full evaluation of the voltage traces for BAC firing.

        Args:
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        spikecount = self.BAC_spikecount(voltage_traces)[".raw"]
        out = {}
        for evaluation_metric, (_, mean, std) in six.iteritems(self.definitions):
            # special case in the original code were in the case of two somatic spikes
            # 7 is substracted from the mean
            if spikecount == 2 and evaluation_metric == "BAC_caSpike_width":
                mean = mean - 7.0
            evaluation_current_metric = getattr(self, evaluation_metric)(voltage_traces)
            evaluation_current_metric[".normalized"] = normalize(
                evaluation_current_metric[".raw"], mean, std
            )
            checks = [
                v for k, v in six.iteritems(evaluation_current_metric) if "check" in k
            ]
            if all(checks):
                evaluation_current_metric[""] = evaluation_current_metric[".normalized"]
            else:
                evaluation_current_metric[""] = 20.0  # *std
            evaluation_current_metric = {
                evaluation_metric + suffix: evaluation_value
                for suffix, evaluation_value in six.iteritems(evaluation_current_metric)
            }
            out.update(evaluation_current_metric)
        return self.check(out, voltage_traces)

    def check(self, out, voltage_traces):
        """Check for problems in the voltage trace.

        This should be called after evaluating the voltage traces.
        it is e.g. the last step in :py:meth:`get`, where it adds the checks to the output dictionary.

        This method checks if the voltage trace:

        - has at least 2 APs present.
        - properly returns to rest.
        - has no spikes before stimulus onset (in soma or dendrite).
        - has its last spike before the deadline.
        - there is no dendritic spike before stimulus onset

        Args:
            out: dictionary with the evaluation metrics
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        # checking for problems in voltage trace
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        vmax = None  # voltage_traces['vMax']

        # basic error check - used if trace e.g. does not spike at all.
        # penalizes low variance, slightly less penalizes higher variance
        err = trace_check_err(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            punish=self.punish,
        )
        err_flags = trace_check(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            minspikenum=self.punish_minspikenum,
            soma_threshold=self.soma_thresh,
            returning_to_rest=self.punish_returning_to_rest_tolerance,
            name="BAC",
            vmax=vmax,
        )
        if self.punish_last_spike_after_deadline:
            relevant_err_flags = err_flags
        else:
            import six

            relevant_err_flags = {
                k: v
                for k, v in six.iteritems(err_flags)
                if not "last_spike_before_deadline" in k
            }
        for evaluation_metric_name in list(self.definitions.keys()):
            if not all(relevant_err_flags.values()):
                out[evaluation_metric_name] = err
            elif out[evaluation_metric_name] > self.punish:
                out[evaluation_metric_name] = self.punish * 0.75
            # change from hay algorithm by arco: if high depolarization anywhere in the dendrite occurs before stimulus, put highest punish value
            if not err_flags["BAC.check_max_prestim_dendrite_depo"]:
                out[evaluation_metric_name] = self.punish
        out["BAC.err"] = err
        out.update(err_flags)
        out = {self.prefix + k: out[k] for k in out.keys()}
        return out

    def BAC_spikecount(self, voltage_traces):
        """Get the number of spikes in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".raw"`` to the number of spikes in the somatic voltage trace.
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {".raw": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh)}

    def BAC_APheight(self, voltage_traces):
        """Get the height of the first action potential in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the height of the first action potential in the somatic voltage trace.

        See also:
            :py:func:`AP_height`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(AP_height_check_1AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AP_height)(t, v, thresh=self.soma_thresh),
        }

    def BAC_ISI(self, voltage_traces):
        """Get the interspike interval in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2_or_3_APs"`` to whether there are 2 or 3 action potentials in the somatic voltage trace,
                ``".check_repolarization"`` to whether the voltage trace repolarizes after the stimulus,
                and ``".raw"`` to the interspike interval in the somatic voltage trace.

        See also:
            :py:func:`BAC_ISI`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        stim_end = self.stim_onset + self.stim_duration
        r = self.repolarization
        return {
            ".check_2_or_3_APs": nan_if_error(BAC_ISI_check_2_or_3_APs)(
                t, v, thresh=self.soma_thresh
            ),
            ".check_repolarization": nan_if_error(BAC_ISI_check_repolarization)(
                t, v, stim_end=stim_end, repolarization=r
            ),
            ".raw": nan_if_error(BAC_ISI)(t, v, thresh=self.soma_thresh),
        }

    def BAC_ahpdepth(self, voltage_traces):
        """Get the afterhyperpolarization depth in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2AP"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the afterhyperpolarization depth in the somatic voltage trace.

        See also:
            :py:func:`AHP_depth_abs`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2AP": nan_if_error(AHP_depth_abs_check_2AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AHP_depth_abs)(t, v, thresh=self.soma_thresh),
        }

    def BAC_caSpike_height(self, voltage_traces):
        """Get the height of the calcium spike in the dendritic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1_Ca_AP"`` to whether there is at least one calcium spike in the dendritic voltage trace,
                ``".check_>=2_Na_AP"`` to whether there are at least two action potentials in the somatic voltage trace,
                ``".check_ca_max_after_nth_somatic_spike"`` to whether the calcium spike occurs after the nth somatic spike,
                and ``".raw"`` to the height of the calcium spike in the dendritic voltage trace.

        See also:
            :py:func:`BAC_caSpike_height`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        v_dend = voltage_traces["vList"][1]
        tend = self.stim_duration + self.stim_onset
        return {
            ".check_1_Ca_AP": nan_if_error(BAC_caSpike_height_check_1_Ca_AP)(
                t, v, v_dend, thresh=self.hot_zone_thresh
            ),
            ".check_>=2_Na_AP": nan_if_error(BAC_caSpike_height_check_gt2_Na_spikes)(
                t, v, v_dend, thresh=self.soma_thresh
            ),
            ".check_ca_max_after_nth_somatic_spike": nan_if_error(
                BAC_caSpike_height_check_Ca_spikes_after_Na_spike
            )(
                t,
                v,
                v_dend,
                n=self.ca_max_after_nth_somatic_spike,
                thresh=self.soma_thresh,
            ),
            ".raw": nan_if_error(BAC_caSpike_height)(
                t, v, v_dend, ca_thresh=self.hot_zone_thresh, tstim=self.stim_onset
            ),
        }

    def BAC_caSpike_width(self, voltage_traces):
        """Get the width of the calcium spike in the dendritic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1_Ca_AP"`` to whether there is at least one calcium spike in the dendritic voltage trace,
                and ``".raw"`` to the width of the calcium spike in the dendritic voltage trace.

        See also:
            :py:func:`BAC_caSpike_width`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        v_dend = voltage_traces["vList"][1]
        return {
            ".check_1_Ca_AP": nan_if_error(BAC_caSpike_width_check_1_Ca_AP)(
                t, v, v_dend, thresh=self.hot_zone_thresh
            ),
            ".raw": nan_if_error(BAC_caSpike_width)(
                t, v, v_dend, thresh=self.hot_zone_thresh
            ),
        }


class bAP:
    """Evaluate the :math:`bAP` stimulus protocol.

    These metrics were introduced by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`, and illustrated in :cite:t:`Guest_Bast_Narayanan_Oberlaender`.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_bAP` for more information on the stimulus protocol.

    Attributes:
        soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30` mV.
        stim_onset (float): The onset of the stimulus (ms). Defaults to :math:`295` ms.
        stim_duration (float): The duration of the stimulus (ms). Defaults to :math:`5` ms.
        bAP_thresh (float): The threshold for the backpropagating action potential. Defaults to :math:`+2` mV.
        punish (float): The punishment value in units of :math:`\sigma`.
            Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
            Defaults to :math:`250 \sigma`.
        punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
        punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol.
        punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
        definitions (dict): The empirical means and standard deviations for the evaluation metrics. Defaults to::

            {
                'bAP_APheight': ('AP_height', 25.0, 5.0),
                'bAP_APwidth': ('AP_width', 2.0, 0.5),
                'bAP_att2': ('BPAPatt2', 45.0, 10.0),
                'bAP_att3': ('BPAPatt3', 36.0, 9.33),
                'bAP_spikecount': ('Spikecount', 1.0, 0.01)
            }
    """

    def __init__(
        self,
        soma_thresh=-30,
        stim_onset=295,
        stim_duration=5,
        bAP_thresh="+2mV",
        punish=250.0,
        punish_last_spike_after_deadline=True,
        punish_minspikenum=1,
        punish_returning_to_rest_tolerance=2.0,
        definitions=HAY_BAP_DEFINITIONS,
    ):
        """
        Args:
            soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30\ mV`.
            stim_onset (float): The onset of the stimulus (:math:`ms`). Defaults to :math:`295\ ms`.
            stim_duration (float): The duration of the stimulus (:math:`ms`). Defaults to :math:`5\ ms`.
            bAP_thresh (float): The threshold for the backpropagating action potential. Defaults to :math:`+2\ mV`.
            punish (float): The punishment value in units of :math:`\sigma`.
                Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
                Defaults to :math:`250 \sigma`.
            punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
            punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol. Defaults to :math:`1`.
            punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
            definitions (dict): The definitions for the evaluation metrics. See also: :py:attr:`definitions`.
        """
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
        """Get the full evaluation of the voltage traces for bAP firing.

        Args:
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        out = {}
        for name, (_, mean, std) in iteritems(self.definitions):
            out_current = getattr(self, name)(voltage_traces)
            out_current[".normalized"] = normalize(out_current[".raw"], mean, std)
            checks = [v for k, v in iteritems(out_current) if "check" in k]
            if all(checks):
                out_current[""] = out_current[".normalized"]
            else:
                out_current[""] = 20  # *std
            out_current = {name + k: v for k, v in iteritems(out_current)}
            out.update(out_current)
        return self.check(out, voltage_traces)

    def check(self, out, voltage_traces):
        """Check for problems in the voltage trace.

        This should be called after evaluating the voltage traces.
        it is e.g. the last step in :py:meth:`get`, where it adds the checks to the output dictionary.

        This method checks if the voltage trace:

        - has at least 1 AP present.
        - properly returns to rest.
        - has no spikes before stimulus onset (in soma or dendrite).
        - has its last spike before the deadline.

        Args:
            out: dictionary with the evaluation metrics
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        # checking for problems in voltage trace
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        vmax = None  # voltage_traces['vMax']
        err = trace_check_err(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            punish=self.punish,
        )
        err_flags = trace_check(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            minspikenum=self.punish_minspikenum,
            soma_threshold=self.soma_thresh,
            returning_to_rest=self.punish_returning_to_rest_tolerance,
            name="bAP",
            vmax=vmax,
        )
        if self.punish_last_spike_after_deadline:
            relevant_err_flags = err_flags
        else:
            relevant_err_flags = {
                k: v
                for k, v in iteritems(err_flags)
                if not "last_spike_before_deadline" in k
            }
        for name in list(self.definitions.keys()):
            if not all(relevant_err_flags.values()):
                out[name] = err
            elif out[name] > self.punish:
                out[name] = self.punish * 0.75
            if not err_flags["bAP.check_max_prestim_dendrite_depo"]:
                out[name] = self.punish
        out["bAP.err"] = err
        out.update(err_flags)
        return out

    def bAP_APheight(self, voltage_traces):
        """Get the height of the first action potential in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
            and ``".raw"`` to the height of the first action potential in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.APheight`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(AP_height_check_1AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AP_height)(t, v, thresh=self.soma_thresh),
        }

    def bAP_APwidth(self, voltage_traces):
        """Get the width of the first action potential in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
            and ``".raw"`` to the width of the first action potential in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.APwidth`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(AP_width_check_1AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AP_width)(t, v, thresh=self.soma_thresh),
        }

    def bAP_spikecount(self, voltage_traces):
        """Get the number of spikes in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".raw"`` to the number of spikes in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.spike_count`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {".raw": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh)}

    def _bAP_att(self, voltage_traces, _n=1):
        """Get the backpropagating action potential attenuation.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.
            _n (int):
                The index of the dendritic voltage trace.
                Index :math:`0` is the somatic voltage trace,
                index :math:`1` is the first dendritic voltage trace, and
                index :math:`2` is the second dendritic voltage trace.
                Defaults to :math:`1` i.e. the first pipette in the dendrite.

        Returns:
            dict: Dictionary mapping ``".raw"`` to the backpropagating action potential attenuation.

        See also:
            :py:meth:`~biophysics_fitting.ephys.BPAPatt`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        v_dend = voltage_traces["vList"][_n]
        return {
            ".raw": nan_if_error(BPAPatt)(t, v_dend, self.bAP_thresh, self.stim_onset),
            ".check_1_AP": nan_if_error(BPAPatt_check_1_AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".check_relative_height": nan_if_error(BPAPatt_check_relative_height)(
                t, v, v_dend, self.bAP_thresh, self.stim_onset
            ),
        }

    def bAP_att2(self, voltage_traces):
        """Get the backpropagating action potential attenuation between the soma and first dendritic pipette location.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".raw"`` to the backpropagating action potential attenuation.

        See also:
            :py:meth:`~biophysics_fitting.ephys.BPAPatt`
        """
        return self._bAP_att(voltage_traces, _n=1)

    def bAP_att3(self, voltage_traces):
        """Get the backpropagating action potential attenuation between the soma and second dendritic pipette location.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".raw"`` to the backpropagating action potential attenuation.

        See also:
            :py:meth:`~biophysics_fitting.ephys.BPAPatt`
        """
        return self._bAP_att(voltage_traces, _n=2)


class _Step:
    """Template class for evaluating step current injections.

    These metrics were introduced by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`, and illustrated in :cite:t:`Guest_Bast_Narayanan_Oberlaender`.

    See also:
        :py:meth:`biophysics_fitting.setup_stim` for more information on the stimulus protocols.

    Attributes:
        soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30` mV.
        stim_onset (float): The onset of the stimulus (ms). Defaults to :math:`700` ms.
        stim_duration (float): The duration of the stimulus (ms). Defaults to :math:`2000` ms.
        punish (float): The punishment value in units of :math:`\sigma`.
            Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
            Defaults to :math:`250`.
        punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
        punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol.
        punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
        prefix (str): The prefix for the evaluation metric checks. Defaults to an empty string.
        definitions (dict): The empirical means and standard deviations for the evaluation metrics. These are overridden by each child class.
        name (str): The name of the stimulus protocol. Defaults to ``'StepTemplate'``.
        step_index (int): The index of the step stimulus protocol. Defaults to :math:`0`. Options are: ``[1, 2, 3]``.
    """

    def __init__(
        self,
        soma_thresh=-30,
        stim_onset=700,
        stim_duration=2000,
        punish=250.0,
        punish_last_spike_after_deadline=True,
        punish_minspikenum=5,
        punish_returning_to_rest_tolerance=2.0,
        definitions=None,
        name="StepTemplate",
        step_index=0,
    ):
        """
        Args:
            soma_thresh (float): The threshold for APs in the somatic voltage trace. Defaults to :math:`-30\ mV`.
            stim_onset (float): The onset of the stimulus (:math:`ms`). Defaults to :math:`700\ ms`.
            stim_duration (float): The duration of the stimulus (:math:`ms`). Defaults to :math:`2000\ ms`.
            punish (float): The punishment value in units of :math:`\sigma`.
                Used as a baseline if the voltage trace cannot be evaluated on a metric (e.g. if it does not contain an AP).
                Defaults to :math:`250 \sigma`.
            punish_last_spike_after_deadline (bool): Whether to punish if the last spike is after the deadline. Defaults to ``True``
            punish_minspikenum (int): The minimum number of spikes required for this stimulus protocol. Defaults to :math:`5`.
            punish_returning_to_rest_tolerance (float): The tolerance for returning to rest (:math:`mV`). Defaults to :math:`2 mV`.
            definitions (dict): The definitions for the evaluation metrics. See also: :py:attr:`definitions`.
            name (str): The name of the stimulus protocol. Defaults to ``'StepTemplate'``.
            step_index (int): The index of the step stimulus protocol. Defaults to :math:`0`. Options are: ``[1, 2, 3]``.
        """

        assert (
            definitions is not None
        ), "The Step class is a template, and must be filled with mean and st values (definitions), depending on the current amplitude. Refer to bipohysics_fitting.hay_specification for the definitions."
        self.soma_thresh = soma_thresh
        self.stim_onset = stim_onset
        self.stim_duration = stim_duration
        self.definitions = definitions
        self.punish = punish
        self.punish_last_spike_after_deadline = punish_last_spike_after_deadline
        self.punish_minspikenum = punish_minspikenum
        self.punish_returning_to_rest_tolerance = punish_returning_to_rest_tolerance
        self.name = name
        self.step_index = step_index

    def get(self, **voltage_traces):
        """Get the full evaluation of the voltage traces for the step current injection.

        Args:
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        out = {}
        for name, (_, mean, std) in iteritems(self.definitions):
            out_current = getattr(self, name)(voltage_traces)
            out_current[".normalized"] = normalize(out_current[".raw"], mean, std)
            checks = [v for k, v in iteritems(out_current) if "check" in k]
            if all(checks):
                out_current[""] = out_current[".normalized"]
            else:
                out_current[""] = 20  # *std
            out_current = {name + k: v for k, v in iteritems(out_current)}
            out.update(out_current)
        return self.check(out, voltage_traces)

    def check(self, out, voltage_traces):
        """Check for problems in the voltage trace.

        Args:
            out: dictionary with the evaluation metrics
            voltage_traces: dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: dictionary with the evaluation metrics, containing the raw values, normalized values, and checks.
        """
        # checking for problems in voltage trace
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        vmax = None  # voltage_traces['vMax']
        err = trace_check_err(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            punish=self.punish,
        )
        err_flags = trace_check(
            t,
            v,
            stim_onset=self.stim_onset,
            stim_duration=self.stim_duration,
            minspikenum=self.punish_minspikenum,
            soma_threshold=self.soma_thresh,
            returning_to_rest=self.punish_returning_to_rest_tolerance,
            name=self.name,
            vmax=vmax,
        )
        for name in list(self.definitions.keys()):
            if not all(err_flags.values()):
                out[name] = err
            elif out[name] > self.punish:
                out[name] = self.punish * 0.75
        out["{}.err".format(self.name)] = err
        out.update(err_flags)
        return out

    def mf(self, voltage_traces):
        """Get the mean frequency of the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the mean frequency of the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_mean_frequency`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh),
            ".raw": nan_if_error(STEP_mean_frequency)(
                t, v, self.stim_duration, thresh=self.soma_thresh
            ),
        }

    def AI(self, voltage_traces):
        """Get the adaptation index of the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2ISI"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the adaptation index of the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_adaptation_index`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2ISI": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh),
            ".raw": nan_if_error(STEP_adaptation_index)(
                t,
                v,
                stim_end=self.stim_onset + self.stim_duration,
                thresh=self.soma_thresh,
            ),
        }

    def ISIcv(self, voltage_traces):
        """Get the coefficient of variation of the interspike interval in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2ISI"`` to whether there are 2 action potentials in the somatic voltage trace,
            and ``".raw"`` to the coefficient of variation of the interspike interval in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_coef_var`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2ISI": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh),
            ".raw": nan_if_error(STEP_coef_var)(
                t,
                v,
                stim_end=self.stim_onset + self.stim_duration,
                thresh=self.soma_thresh,
            ),
        }

    def DI(self, voltage_traces):
        """Get the ISI of the first two spikes in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the delay index of the initial spike.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_delay_index`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2ISI": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh),
            ".raw": nan_if_error(STEP_initial_ISI)(t, v, thresh=self.soma_thresh),
        }

    def TTFS(self, voltage_traces):
        """Get the time to first spike in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the time to first spike in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_time_to_first_spike`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(spike_count)(t, v, thresh=self.soma_thresh),
            ".raw": nan_if_error(STEP_time_to_first_spike)(
                t, v, self.stim_onset, thresh=self.soma_thresh
            ),
        }

    def AHP_depth_abs(self, voltage_traces):
        """Get the afterhyperpolarization depth in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2AP"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the afterhyperpolarization depth in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.AHP_depth_abs`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2AP": nan_if_error(AHP_depth_abs_check_2AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AHP_depth_abs)(t, v, thresh=self.soma_thresh),
        }

    def APh(self, voltage_traces):
        """Get the AP heights fo all APs in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the AP heights in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.AP_height`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(AP_height_check_1AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AP_height)(t, v, thresh=self.soma_thresh),
        }

    def fAHPd(self, voltage_traces):
        """Get the fast afterhyperpolarization depth in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2AP"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the fast afterhyperpolarization depth in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_fast_ahp_depth`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2AP": nan_if_error(AHP_depth_abs_check_2AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(STEP_fast_ahp_depth)(t, v, thresh=self.soma_thresh),
        }

    def sAHPd(self, voltage_traces):
        """Get the slow afterhyperpolarization depth in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2AP"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the slow afterhyperpolarization depth in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.STEP_slow_ahp_depth`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2AP": nan_if_error(AHP_depth_abs_check_2AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(STEP_slow_ahp_depth)(t, v, thresh=self.soma_thresh),
        }

    def sAHPt(self, voltage_traces):
        """Get the slow afterhyperpolarization time in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_2AP"`` to whether there are 2 action potentials in the somatic voltage trace,
                and ``".raw"`` to the slow afterhyperpolarization time in the somatic voltage trace.
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_2AP": nan_if_error(AHP_depth_abs_check_2AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(STEP_slow_ahp_time)(t, v, thresh=self.soma_thresh),
        }

    def APw(self, voltage_traces):
        """Get the AP widths of all APs in the somatic voltage trace.

        Args:
            voltage_traces (dict): dictionary with the voltage traces of the soma and dendrite.

        Returns:
            dict: Dictionary mapping ``".check_1AP"`` to whether there is at least one action potential in the somatic voltage trace,
                and ``".raw"`` to the AP widths in the somatic voltage trace.

        See also:
            :py:meth:`~biophysics_fitting.ephys.AP_width`
        """
        t, v = voltage_traces["tVec"], voltage_traces["vList"][0]
        return {
            ".check_1AP": nan_if_error(AP_width_check_1AP)(
                t, v, thresh=self.soma_thresh
            ),
            ".raw": nan_if_error(AP_width)(t, v, thresh=self.soma_thresh),
        }

    def __getattr__(self, name):
        """Suffix the evaluation objective with the step index."""
        assert hasattr(
            self, name.rstrip(str(self.step_index))
        ), f"Attribute {name} not found in {self.name}"
        return object.__getattribute__(self, name.rstrip(str(self.step_index)))


class StepOne(_Step):
    """Evaluate Step current one.

    This class initializes all the evaluation metrics for the ``StepOne`` stimulus protocol.
    The empirically observed objectives are in this case::

        {
            'mf1': ("Mean frequency", 9.0, 0.88),
            'AI1': ("Adaptation Index", 0.0035999999999999999, 0.0091000000000000004),
            'ISIcv1': ("Interspike interval coefficient of variation", 0.12039999999999999, 0.032099999999999997),
            'DI1': ("Doublet Interspike Interval", 57.75, 33.479999999999997),
            'TTFS1': ("Time to first spike", 43.25, 7.3200000000000003),
            'APh1': ("AP height", 26.227399999999999,4.9702999999999999),
            'fAHPd1': ("Fast after-hyperpolarization depth", -51.951099999999997, 5.8212999999999999),
            'sAHPd1': ("Slow after-hyperpolarization depth", -58.0443, 4.5814000000000004),
            'sAHPt1': ("Slow after-hyperpolarization time", 0.23760000000000001, 0.0299),
            'APw1': ("AP width", 1.3077000000000001, 0.16650000000000001)
        }

    See also:
        :py:class:`_Step` for the template class, and :py:meth:`biophysics_fitting.setup_stim.setp_StepOne` for more information on the stimulus protocol.
    """

    def __init__(self):
        super().__init__(
            definitions=HAY_STEP1_DEFINITIONS, name="StepOne", step_index="1"
        )


class StepTwo(_Step):
    """Evaluate Step current two.

    This class initializes all the evaluation metrics for the ``StepTwo`` stimulus protocol.
    The empirically observed objectives are in this case::

        {
            'mf2': ("Mean frequency", 14.5, 0.56000000000000005),
            'AI2': ("Adaptation Index", 0.0023, 0.0055999999999999999),
            'ISIcv2': ("Interspike Interval coeffitient of variation", 0.10829999999999999, 0.036799999999999999),
            'DI2': ("Doublet interspike interval", 6.625, 8.6500000000000004),
            'TTFS2': ("Ti;e to first spike", 19.125, 7.3099999999999996),
            'APh2': ("Ap height", 16.520900000000001,6.1127000000000002),
            'fAHPd2': ("Fast after-hyperpolarization depth", -54.194899999999997, 5.5705999999999998),
            'sAHPd2': ("Slow after-hyperpolarization depth", -60.512900000000002, 4.6717000000000004),
            'sAHPt2': ("Slow after-hyperpolarization time", 0.2787, 0.026599999999999999),
            'APw2': ("AP width", 1.3833,0.2843)
        }

    See also:
        :py:class:`_Step` for the template class, and :py:meth:`biophysics_fitting.setup_stim.setp_StepTwo` for more information on the stimulus protocol.
    """

    def __init__(self):
        super().__init__(
            definitions=HAY_STEP2_DEFINITIONS, name="StepTwo", step_index="2"
        )


class StepThree(_Step):
    """Evaluate Step current three.

    This class initializes all the evaluation metrics for the ``StepThree`` stimulus protocol.
    The empirically observed objectives are in this case::

        {
            'mf3': ("Mean frequency", 22.5,2.2222),
            'AI3': ("Adaptation index", 0.0045999999999999999, 0.0025999999999999999),
            'ISIcv3': ("Interspike interval coefficient of variation", 0.095399999999999999, 0.014),
            'DI3': ("Doublet interspike interval", 5.38, 0.83),
            'TTFS3': ("Time to first spike", 7.25,1.0),
            'APh3': ("AP height", 16.436800000000002, 6.9321999999999999),
            'fAHPd3': ("Fast afterhypoerpolarization depth", -56.557899999999997, 3.5834000000000001),
            'sAHPd3': ("Slow after-hyperpolarization depth", -59.99230000000001, 3.9247000000000005),
            'sAHPt3': ("Slow after-hyperpolarization time",   0.21310000000000001, 0.036799999999999999),
            'APw3': ("AP zidth", 1.8647, 0.41189999999999999)
        }

    See also:
        :py:class:`_Step` for the template class, and :py:meth:`biophysics_fitting.setup_stim.setp_StepThree` for more information on the stimulus protocol.
    """

    def __init__(self):
        super().__init__(
            definitions=HAY_STEP3_DEFINITIONS, name="StepThree", step_index="3"
        )


def get_evaluate_bAP(**kwargs):
    """Get the evaluation function for the :math:`bAP` stimulus protocol.

    Initializes a :py:class:`bAP` object with the given keyword arguments,
    and returns a function that evaluates the voltage traces.

    Args:
        **kwargs: Additional or overriding keyword arguments for the :py:class:`bAP` object. Defaults to None.

    Returns:
        Callable: function that evaluates the voltage traces.
    """
    bap = bAP(**kwargs)

    def fun(**kwargs):
        return bap.get(**kwargs)

    return fun


def get_evaluate_BAC(**kwargs):
    """Get the evaluation function for the :math:`BAC` stimulus protocol.

    Initializes a :py:class:`BAC` object with the given keyword arguments,
    and returns a function that evaluates the voltage traces.

    Args:
        **kwargs: Additional or overriding keyword arguments for the :py:class:`BAC` object. Defaults to None.

    Returns:
        Callable: function that evaluates the voltage traces.
    """
    bac = BAC(**kwargs)

    def fun(**kwargs):
        return bac.get(**kwargs)

    return fun


def get_evaluate_StepOne(**kwargs):
    """Get the evaluation function for the :math:`StepOne` stimulus protocol.

    Initializes a :py:class:`StepOne` object with the given keyword arguments,
    and returns a function that evaluates the voltage traces.

    Args:
        **kwargs: Additional or overriding keyword arguments for the :py:class:`StepOne` object. Defaults to None.

    Returns:
        Callable: function that evaluates the voltage traces.
    """
    step = StepOne(**kwargs)

    def fun(**kwargs):
        return step.get(**kwargs)

    return fun


def get_evaluate_StepTwo(**kwargs):
    """Get the evaluation function for the :math:`StepTwo` stimulus protocol.

    Initializes a :py:class:`StepTwo` object with the given keyword arguments,
    and returns a function that evaluates the voltage traces.

    Args:
        **kwargs: Additional or overriding keyword arguments for the :py:class:`StepTwo` object. Defaults to None.

    Returns:
        Callable: function that evaluates the voltage traces.
    """
    step = StepTwo(**kwargs)

    def fun(**kwargs):
        return step.get(**kwargs)

    return fun


def get_evaluate_StepThree(**kwargs):
    """Get the evaluation function for the :math:`StepTwo` stimulus protocol.

    Initializes a :py:class:`StepTwo` object with the given keyword arguments,
    and returns a function that evaluates the voltage traces.

    Args:
        **kwargs: Additional or overriding keyword arguments for the :py:class:`StepThree` object. Defaults to None.

    Returns:
        Callable: function that evaluates the voltage traces.
    """
    step = StepThree(**kwargs)

    def fun(**kwargs):
        return step.get(**kwargs)

    return fun


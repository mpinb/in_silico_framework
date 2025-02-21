"""
This module provides convenience methods for Hay's model specification (see :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`).
"""

import json

import pandas as pd
import os
CWD = os.path.abspath(os.path.dirname(__file__))

# filepath: /home/bgmeulem/Documents/in_silico_framework/biophysics_fitting/hay_specification.py
with open(os.path.join(CWD, "hay_objectives_empirical.json"), "r") as f:
    objectives_empirical = json.load(f)

HAY_BAP_DEFINITIONS = objectives_empirical["HAY_BAP_DEFINITIONS"]
HAY_BAC_DEFINITIONS = objectives_empirical["HAY_BAC_DEFINITIONS"]
HAY_STEP1_DEFINITIONS = objectives_empirical["HAY_STEP1_DEFINITIONS"]
HAY_STEP2_DEFINITIONS = objectives_empirical["HAY_STEP2_DEFINITIONS"]
HAY_STEP3_DEFINITIONS = objectives_empirical["HAY_STEP3_DEFINITIONS"]


def get_hay_objective_names():
    """Get the names of the objectives used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.

    Returns:
        list: The names of the objectives.
    """
    return [
        "bAP_APwidth",
        "bAP_APheight",
        "bAP_spikecount",
        "bAP_att2",
        "bAP_att3",
        "BAC_ahpdepth",
        "BAC_APheight",
        "BAC_ISI",
        "BAC_caSpike_height",
        "BAC_caSpike_width",
        "BAC_spikecount",
        "mf1",
        "mf2",
        "mf3",
        "AI1",
        "AI2",
        "ISIcv1",
        "ISIcv2",
        "AI3",
        "ISIcv3",
        "DI1",
        "DI2",
        "APh1",
        "APh2",
        "APh3",
        "TTFS1",
        "TTFS2",
        "TTFS3",
        "fAHPd1",
        "fAHPd2",
        "fAHPd3",
        "sAHPd1",
        "sAHPd2",
        "sAHPd3",
        "sAHPt1",
        "sAHPt2",
        "sAHPt3",
        "APw1",
        "APw2",
        "APw3",
    ]


def get_hay_param_names():
    """Get the names of the parameters used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.

    Returns:
        list: The names of the parameters."""
    return [
        "NaTa_t.soma.gNaTa_tbar",
        "Nap_Et2.soma.gNap_Et2bar",
        "K_Pst.soma.gK_Pstbar",
        "K_Tst.soma.gK_Tstbar",
        "SK_E2.soma.gSK_E2bar",
        "SKv3_1.soma.gSKv3_1bar",
        "Ca_HVA.soma.gCa_HVAbar",
        "Ca_LVAst.soma.gCa_LVAstbar",
        "CaDynamics_E2.soma.gamma",
        "CaDynamics_E2.soma.decay",
        "NaTa_t.axon.gNaTa_tbar",
        "Nap_Et2.axon.gNap_Et2bar",
        "K_Pst.axon.gK_Pstbar",
        "K_Tst.axon.gK_Tstbar",
        "SK_E2.axon.gSK_E2bar",
        "SKv3_1.axon.gSKv3_1bar",
        "Ca_HVA.axon.gCa_HVAbar",
        "Ca_LVAst.axon.gCa_LVAstbar",
        "CaDynamics_E2.axon.gamma",
        "CaDynamics_E2.axon.decay",
        "none.soma.g_pas",
        "none.axon.g_pas",
        "none.dend.g_pas",
        "none.apic.g_pas",
        "Im.apic.gImbar",
        "NaTa_t.apic.gNaTa_tbar",
        "SKv3_1.apic.gSKv3_1bar",
        "Ca_HVA.apic.gCa_HVAbar",
        "Ca_LVAst.apic.gCa_LVAstbar",
        "SK_E2.apic.gSK_E2bar",
        "CaDynamics_E2.apic.gamma",
        "CaDynamics_E2.apic.decay",
    ]


def get_hay_params_pdf():
    """Get the parameter boundaries used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.

    Returns:
        pd.DataFrame: The parameter boundaries."""
    d = {
        "max": [
            4.0,
            0.01,
            1.0,
            0.1,
            0.1,
            2.0,
            0.001,
            0.01,
            0.05,
            1000.0,
            4.0,
            0.01,
            1.0,
            0.1,
            0.1,
            2.0,
            0.001,
            0.01,
            0.05,
            1000.0,
            5.02e-05,
            5.0e-05,
            0.0001,
            0.0001,
            0.001,
            0.04,
            0.04,
            0.005,
            0.2,
            0.01,
            0.05,
            200.0,
        ],
        "min": [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0005,
            20.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0005,
            20.0,
            2.0e-05,
            2.0e-05,
            3.0e-05,
            3.0e-05,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0005,
            20.0,
        ],
        "param_names": get_hay_param_names(),
    }
    return pd.DataFrame(d).set_index("param_names", drop=True)[["min", "max"]]


def get_hay_problem_description():
    """Get the problem description used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.

    The resulting pd.DataFrame contains the following columns:

        - objective: The name of the objective as an acronym, prefixed with the stimulus.
        - feature: The full name of the objective.
        - stim_name: The name of the stimulus.
        - stim_type: The type of the stimulus (bAP, BAC or SquarePulse).
        - mean: The empirically observed mean value of the feature.
        - std: The empirically observed standard deviation of the feature.

    The names of the objectives are prefixed with the stimulus name. The suffix
    acronyms mean the following:

    .. list-table::
        :header-rows: 1

        * - Objective
          - Meaning
        * - spikecount
          - Amount of spikes
        * - APheight
          - AP height
        * - APwidth
          - AP width
        * - att2
          - Attenuation of the bAP between soma and recSite 1
        * - att3
          - Attenuation of the bAP between soma and recSite 2
        * - ahpdepth
          - After-hyperpolarization depth
        * - ISI
          - Interspike interval
        * - caSpike_height
          - height of the Ca2+-spike
        * - caSpike_width
          - Width of the Ca2+-spike
        * - mf1
          - Spike frequency
        * - AI1
          - Adaptation index
        * - ISIcv1
          - Interspike interval: coefficient of variation
        * - DI1
          - Initial burst interspike interval (time between first and second AP)
        * - TTFS1
          - First spike latency
        * - APh1
          - AP height
        * - fAHPd1
          - Fast AP depth
        * - sAHPd1
          - Slow after-hyperpolarization depth
        * - sAHPt1
          - Slow after-hyperpolarization time
        * - APw1
          - Ap half-width

    Returns:
        pd.DataFrame: The problem description, containing the objectives, objective names, stimulus type, mean and std for each objective.

    Note:
        These features are unique to Layer 5 Pyramidal Neurons in the Rat Barrel Cortex.
        Other celltypes will have different values for these features, and may not even
        have these features at all. See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    d = {
        "feature": {
            0: "Spikecount",
            1: "AP_height",
            2: "AP_width",
            3: "BPAPatt2",
            4: "BPAPatt3",
            5: "AHP_depth_abs",
            6: "AP_height",
            7: "BAC_ISI",
            8: "BAC_caSpike_height",
            9: "BAC_caSpike_width",
            10: "Spikecount",
            11: "mean_frequency2",
            12: "adaptation_index2",
            13: "ISI_CV",
            14: "doublet_ISI",
            15: "time_to_first_spike",
            16: "AP_height",
            17: "AHP_depth_abs_fast",
            18: "AHP_depth_abs_slow",
            19: "AHP_slow_time",
            20: "AP_width",
            21: "mean_frequency2",
            22: "adaptation_index2",
            23: "ISI_CV",
            24: "doublet_ISI",
            25: "time_to_first_spike",
            26: "AP_height",
            27: "AHP_depth_abs_fast",
            28: "AHP_depth_abs_slow",
            29: "AHP_slow_time",
            30: "AP_width",
            31: "mean_frequency2",
            32: "adaptation_index2",
            33: "ISI_CV",
            34: "time_to_first_spike",
            35: "AP_height",
            36: "AHP_depth_abs_fast",
            37: "AHP_depth_abs_slow",
            38: "AHP_slow_time",
            39: "AP_width",
        },
        "mean": {
            0: 1.0,
            1: 25.0,
            2: 2.0,
            3: 45.0,
            4: 36.0,
            5: -65.0,
            6: 25.0,
            7: 9.9009999999999998,
            8: 6.7300000000000004,
            9: 37.43,
            10: 3.0,
            11: 9.0,
            12: 0.0035999999999999999,
            13: 0.12039999999999999,
            14: 57.75,
            15: 43.25,
            16: 26.227399999999999,
            17: -51.951099999999997,
            18: -58.0443,
            19: 0.23760000000000001,
            20: 1.3077000000000001,
            21: 14.5,
            22: 0.0023,
            23: 0.10829999999999999,
            24: 6.625,
            25: 19.125,
            26: 16.520900000000001,
            27: -54.194899999999997,
            28: -60.512900000000002,
            29: 0.2787,
            30: 1.3833,
            31: 22.5,
            32: 0.0045999999999999999,
            33: 0.095399999999999999,
            34: 7.25,
            35: 16.436800000000002,
            36: -56.557899999999997,
            37: -59.9923,
            38: 0.21310000000000001,
            39: 1.8647,
        },
        "objective": {
            0: "bAP_spikecount",
            1: "bAP_APheight",
            2: "bAP_APwidth",
            3: "bAP_att2",
            4: "bAP_att3",
            5: "BAC_ahpdepth",
            6: "BAC_APheight",
            7: "BAC_ISI",
            8: "BAC_caSpike_height",
            9: "BAC_caSpike_width",
            10: "BAC_spikecount",
            11: "mf1",
            12: "AI1",
            13: "ISIcv1",
            14: "DI1",
            15: "TTFS1",
            16: "APh1",
            17: "fAHPd1",
            18: "sAHPd1",
            19: "sAHPt1",
            20: "APw1",
            21: "mf2",
            22: "AI2",
            23: "ISIcv2",
            24: "DI2",
            25: "TTFS2",
            26: "APh2",
            27: "fAHPd2",
            28: "sAHPd2",
            29: "sAHPt2",
            30: "APw2",
            31: "mf3",
            32: "AI3",
            33: "ISIcv3",
            34: "TTFS3",
            35: "APh3",
            36: "fAHPd3",
            37: "sAHPd3",
            38: "sAHPt3",
            39: "APw3",
        },
        "std": {
            0: 0.01,
            1: 5.0,
            2: 0.5,
            3: 10.0,
            4: 9.3300000000000001,
            5: 4.0,
            6: 5.0,
            7: 0.85170000000000001,
            8: 2.54,
            9: 1.27,
            10: 0.01,
            11: 0.88,
            12: 0.0091000000000000004,
            13: 0.032099999999999997,
            14: 33.479999999999997,
            15: 7.3200000000000003,
            16: 4.9702999999999999,
            17: 5.8212999999999999,
            18: 4.5814000000000004,
            19: 0.029899999999999999,
            20: 0.16650000000000001,
            21: 0.56000000000000005,
            22: 0.0055999999999999999,
            23: 0.036799999999999999,
            24: 8.6500000000000004,
            25: 7.3099999999999996,
            26: 6.1127000000000002,
            27: 5.5705999999999998,
            28: 4.6717000000000004,
            29: 0.026599999999999999,
            30: 0.2843,
            31: 2.2222,
            32: 0.0025999999999999999,
            33: 0.014,
            34: 1.0,
            35: 6.9321999999999999,
            36: 3.5834000000000001,
            37: 3.9247000000000001,
            38: 0.036799999999999999,
            39: 0.41189999999999999,
        },
        "stim_name": {
            0: "bAP",
            1: "bAP",
            2: "bAP",
            3: "bAP",
            4: "bAP",
            5: "BAC",
            6: "BAC",
            7: "BAC",
            8: "BAC",
            9: "BAC",
            10: "BAC",
            11: "StepOne",
            12: "StepOne",
            13: "StepOne",
            14: "StepOne",
            15: "StepOne",
            16: "StepOne",
            17: "StepOne",
            18: "StepOne",
            19: "StepOne",
            20: "StepOne",
            21: "StepTwo",
            22: "StepTwo",
            23: "StepTwo",
            24: "StepTwo",
            25: "StepTwo",
            26: "StepTwo",
            27: "StepTwo",
            28: "StepTwo",
            29: "StepTwo",
            30: "StepTwo",
            31: "StepThree",
            32: "StepThree",
            33: "StepThree",
            34: "StepThree",
            35: "StepThree",
            36: "StepThree",
            37: "StepThree",
            38: "StepThree",
            39: "StepThree",
        },
        "stim_type": {
            0: "bAP",
            1: "bAP",
            2: "bAP",
            3: "bAP",
            4: "bAP",
            5: "BAC",
            6: "BAC",
            7: "BAC",
            8: "BAC",
            9: "BAC",
            10: "BAC",
            11: "SquarePulse",
            12: "SquarePulse",
            13: "SquarePulse",
            14: "SquarePulse",
            15: "SquarePulse",
            16: "SquarePulse",
            17: "SquarePulse",
            18: "SquarePulse",
            19: "SquarePulse",
            20: "SquarePulse",
            21: "SquarePulse",
            22: "SquarePulse",
            23: "SquarePulse",
            24: "SquarePulse",
            25: "SquarePulse",
            26: "SquarePulse",
            27: "SquarePulse",
            28: "SquarePulse",
            29: "SquarePulse",
            30: "SquarePulse",
            31: "SquarePulse",
            32: "SquarePulse",
            33: "SquarePulse",
            34: "SquarePulse",
            35: "SquarePulse",
            36: "SquarePulse",
            37: "SquarePulse",
            38: "SquarePulse",
            39: "SquarePulse",
        },
    }

    return pd.DataFrame.from_dict(d)


# def get_hay_problem_description():
#     setup_hay_evaluator()
#     sol = h.mc.get_sol()
#     stim_count = int(h.mc.get_stimulus_num())
#     stims = [sol.o(cur_stim).get_type().s for cur_stim in range(stim_count)]

#     objective_names = []
#     feature_types = []
#     stim_types = []
#     stim_names = []
#     mean = []
#     std = []
#     for lv in range(int(sol.count())):
#         for i in range (len(h.evaluator.stimulus_feature_type_list.o(lv))):
#             objective_names.append(h.evaluator.stimulus_feature_name_list.o(lv).o(i).s)
#             feature_types.append(h.evaluator.stimulus_feature_type_list.o(lv).o(i).s)
#             stim_types.append(sol.o(lv).get_type().s)
#             stim_names.append(sol.o(lv).get_name().s)
#             mean.append(h.evaluator.feature_mean_list.o(lv)[i])
#             std.append(h.evaluator.feature_std_list.o(lv)[i])
#     return I.pd.DataFrame(dict(objective = objective_names,
#                                feature = feature_types,
#                                stim_type = stim_types,
#                                stim_name = stim_names,
#                                mean = mean, std = std))[['objective', 'feature',
#                                                          'stim_name', 'stim_type',
#                                                          'mean', 'std']]


def get_feasible_model_params():
    """Get the parameters of a feasible model.

    These are sensible parameters, but have no guarantee to provide a working model.
    Useful for testing purposes, or as a quick seedpoint for the :py:mod:`biophysics_fitting.optimizer`.

    Returns:
        pd.DataFrame: The parameters of a feasible model.
    """
    pdf = get_hay_params_pdf()
    x = [
        1.971849,
        0.000363,
        0.008663,
        0.099860,
        0.073318,
        0.359781,
        0.000530,
        0.004958,
        0.000545,
        342.880108,
        3.755353,
        0.002518,
        0.025765,
        0.060558,
        0.082471,
        0.922328,
        0.000096,
        0.000032,
        0.005209,
        248.822554,
        0.000025,
        0.000047,
        0.000074,
        0.000039,
        0.000436,
        0.016033,
        0.008445,
        0.004921,
        0.003024,
        0.003099,
        0.0005,
        116.339356,
    ]
    pdf["x"] = x
    return pdf


def get_feasible_model_objectives():
    """Get the objectives of a feasible model.

    These are typical values of a working model. Useful for testing purposes.

    Returns:
        pd.DataFrame: The objectives of a feasible model."""
    pdf = get_hay_problem_description()
    index = get_hay_objective_names()
    y = [
        1.647,
        3.037,
        0.0,
        2.008,
        2.228,
        0.385,
        1.745,
        1.507,
        0.358,
        1.454,
        0.0,
        0.568,
        0.893,
        0.225,
        0.75,
        2.78,
        0.194,
        1.427,
        3.781,
        5.829,
        1.29,
        0.268,
        0.332,
        1.281,
        0.831,
        1.931,
        0.243,
        1.617,
        1.765,
        1.398,
        1.126,
        0.65,
        0.065,
        0.142,
        5.628,
        6.852,
        2.947,
        1.771,
        1.275,
        2.079,
    ]
    s = pd.Series(y, index=index)
    pdf.set_index("objective", drop=True, inplace=True)
    pdf["y"] = s
    return pdf

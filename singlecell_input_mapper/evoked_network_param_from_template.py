#!/usr/bin/python
"""
Runfile to create a :ref:`network_params_format` file that captures the population activity of a rat barrel cortex during passive whisker touch in anasthesized animals.

Reads in a template parameter file and sets the PSTHs for each celltype to the PSTHs of the evoked activity.
Such PSTHs can be computed from spike time recordings using e.g. :py:mod:`~singlecell_input_mapper.evoked_PSTH_from_spike_times`.

Attention:
    This module is specific to the model of the rat barrel cortex and the experimental conditions of the passive whisker touch experiment.
    It is not intended to be used for other models or experiments.
    However, it may serve as a template for other experimental conditions.
"""
import sys, os
import single_cell_parser as scp
import getting_started
from data_base.dbopen import dbopen
__author__ = "Robert Egger"

#evokedPrefix = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/evoked_activity/'
#evokedPrefix = '/home/abast/test/neurosim_getting_started/getting_started_files/functional_constraints/evoked_activity/PW_SuW_RF_CDK/'
evokedPrefix = os.path.join(
    getting_started.parent,
    'example_data',
    'functional_constraints',
    'evoked_activity',
    'PW_SuW_RF_CDK') + '/'
#L2EvokedName = evokedPrefix + 'L2_3x3_PSTH_template_0-50_10ms.param'
#L34EvokedName = evokedPrefix + 'L34_3x3_PSTH_template_0-20_1ms_20-50_10ms.param'
#L4pyEvokedName = evokedPrefix + 'L4py_3x3_PSTH_template_0-50_10ms.param'
#L4spEvokedName = evokedPrefix + 'L4sp_3x3_PSTH_template_0-20_1ms_20-50_10ms.param'
#L4ssEvokedName = evokedPrefix + 'L4ss_3x3_PSTH_template_0-20_1ms_20-50_10ms.param'
#L5stEvokedName = evokedPrefix + 'L5st_3x3_PSTH_template_0-50_10ms.param'
#L5ttEvokedName = evokedPrefix + 'L5tt_3x3_PSTH_template_0-20_1ms_20-50_10ms.param'
#L6ccEvokedName = evokedPrefix + 'L6cc_3x3_PSTH_template_0-20_1ms_20-50_10ms.param'
#L6ccinvEvokedName = evokedPrefix + 'L6ccinv_3x3_PSTH_template_0-50_10ms.param'
#L6ctEvokedName = evokedPrefix + 'L6ct_3x3_PSTH_template_0-50_10ms.param'
#VPMEvokedName = evokedPrefix + 'VPM_3x3_PSTH_template.param'
#L1EvokedName = evokedPrefix + 'L1_3x3_PSTH_template_all_0-50_10ms.param'
#L2EvokedName = evokedPrefix + 'L2_3x3_PSTH.param'
#L34EvokedName = evokedPrefix + 'L34_3x3_PSTH.param'
#L4pyEvokedName = evokedPrefix + 'L4py_3x3_PSTH.param'
#L4spEvokedName = evokedPrefix + 'L4sp_3x3_PSTH.param'
#L4ssEvokedName = evokedPrefix + 'L4ss_3x3_PSTH.param'
#L5stEvokedName = evokedPrefix + 'L5st_3x3_PSTH.param'
#L5ttEvokedName = evokedPrefix + 'L5tt_3x3_PSTH.param'
#L6ccEvokedName = evokedPrefix + 'L6cc_3x3_PSTH.param'
#L6ccinvEvokedName = evokedPrefix + 'L6ccinv_3x3_PSTH.param'
#L6ctEvokedName = evokedPrefix + 'L6ct_3x3_PSTH.param'
#===============================================================================
# Used for model run1:
#===============================================================================
L2EvokedName = evokedPrefix + 'L2_3x3_PSTH_UpState.param'
L34EvokedName = evokedPrefix + 'L34_3x3_PSTH_UpState.param'
L4pyEvokedName = evokedPrefix + 'L4py_3x3_PSTH_UpState.param'
L4spEvokedName = evokedPrefix + 'L4sp_3x3_PSTH_UpState.param'
L4ssEvokedName = evokedPrefix + 'L4ss_3x3_PSTH_UpState.param'
L5stEvokedName = evokedPrefix + 'L5st_3x3_PSTH_UpState.param'
L5ttEvokedName = evokedPrefix + 'L5tt_3x3_PSTH_UpState.param'
L6ccEvokedName = evokedPrefix + 'L6cc_3x3_PSTH_UpState.param'
#L6ccEvokedName = evokedPrefix + 'L6cc_3x3_PSTH_UpState_other_active_timing.param'
L6ccinvEvokedName = evokedPrefix + 'L6ccinv_3x3_PSTH_UpState.param'
L6ctEvokedName = evokedPrefix + 'L6ct_3x3_PSTH_UpState.param'
VPMEvokedName = evokedPrefix + 'VPM_3x3_PSTH.param'
#===============================================================================
# END Used for model run1
#===============================================================================
#L1EvokedName = evokedPrefix + 'L1_3x3_PSTH_template_all_0-50_10ms.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_3x3_PSTH_template_PW_0-50_10ms.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_3x3_PSTH_template_PW_0-50_10ms.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_3x3_PSTH_template_PW_0-50_10ms.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_3x3_PSTH_template_PW_0-50_10ms.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_3x3_PSTH_template_PW_0-50_10ms.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_3x3_PSTH_template_PW_SuW_0.5_PW_SuW_L6cc_timing-1ms.param'
#===============================================================================
# Used for model run1:
#===============================================================================
L1EvokedName = evokedPrefix + 'L1_3x3_PSTH_template_PW_0-50_10ms.param'
L23TransEvokedName = evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
L45PeakEvokedName = evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
L45SymEvokedName = evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
L56TransEvokedName = evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal1EvokedName = evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal2EvokedName = evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal3EvokedName = evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal4EvokedName = evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal5EvokedName = evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
SymLocal6EvokedName = evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param'
#===============================================================================
# END Used for model run1
#===============================================================================

#===============================================================================
# Used for model INH response control:
#===============================================================================
#L1EvokedName = evokedPrefix + 'L1_3x3_PSTH_template_PW_0-50_10ms.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_2.0_SuW_1.0_V2.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_0.5_SuW_0.25_V2.param'
#===============================================================================
# END Used for model INH response control
#===============================================================================
#L1EvokedName = evokedPrefix + 'L1_3x3_PSTH_template_PW_0-50_10ms.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_0.67_SuW_0.57.param'
#L23TransEvokedName = evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#L45PeakEvokedName = evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#L45SymEvokedName = evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#L56TransEvokedName = evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal1EvokedName = evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal2EvokedName = evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal3EvokedName = evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal4EvokedName = evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal5EvokedName = evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
#SymLocal6EvokedName = evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_2.0_SuW_1.0.param'
L2EvokedParam = scp.build_parameters(L2EvokedName)
L34EvokedParam = scp.build_parameters(L34EvokedName)
L4pyEvokedParam = scp.build_parameters(L4pyEvokedName)
L4spEvokedParam = scp.build_parameters(L4spEvokedName)
L4ssEvokedParam = scp.build_parameters(L4ssEvokedName)
L5stEvokedParam = scp.build_parameters(L5stEvokedName)
L5ttEvokedParam = scp.build_parameters(L5ttEvokedName)
L6ccEvokedParam = scp.build_parameters(L6ccEvokedName)
L6ccinvEvokedParam = scp.build_parameters(L6ccinvEvokedName)
L6ctEvokedParam = scp.build_parameters(L6ctEvokedName)
VPMEvokedParam = scp.build_parameters(VPMEvokedName)
L1EvokedParam = scp.build_parameters(L1EvokedName)
L23TransEvokedParam = scp.build_parameters(L23TransEvokedName)
L45PeakEvokedParam = scp.build_parameters(L45PeakEvokedName)
L45SymEvokedParam = scp.build_parameters(L45SymEvokedName)
L56TransEvokedParam = scp.build_parameters(L56TransEvokedName)
SymLocal1EvokedParam = scp.build_parameters(SymLocal1EvokedName)
SymLocal2EvokedParam = scp.build_parameters(SymLocal2EvokedName)
SymLocal3EvokedParam = scp.build_parameters(SymLocal3EvokedName)
SymLocal4EvokedParam = scp.build_parameters(SymLocal4EvokedName)
SymLocal5EvokedParam = scp.build_parameters(SymLocal5EvokedName)
SymLocal6EvokedParam = scp.build_parameters(SymLocal6EvokedName)
#evokedTemplates = {'L5tt': L5ttEvokedParam,\
#'L6cc': L6ccEvokedParam,\
#'VPM': VPMEvokedParam}
#evokedTemplates = {'L6cc': L6ccEvokedParam,\
#'VPM': VPMEvokedParam}
#evokedTemplates = {'VPM': VPMEvokedParam}
# control:
evokedTemplates = {
    'L2': L2EvokedParam,
    'L34': L34EvokedParam,
    'L4py': L4pyEvokedParam,
    'L4sp': L4spEvokedParam,
    'L4ss': L4ssEvokedParam,
    'L5st': L5stEvokedParam,
    'L5tt': L5ttEvokedParam,
    'L6cc': L6ccEvokedParam,
    'L6ccinv': L6ccinvEvokedParam,
    'L6ct': L6ctEvokedParam,
    'VPM': VPMEvokedParam,
    'L1': L1EvokedParam,
    'L23Trans': L23TransEvokedParam,
    'L45Peak': L45PeakEvokedParam,
    'L45Sym': L45SymEvokedParam,
    'L56Trans': L56TransEvokedParam,
    'SymLocal1': SymLocal1EvokedParam,
    'SymLocal2': SymLocal2EvokedParam,
    'SymLocal3': SymLocal3EvokedParam,
    'SymLocal4': SymLocal4EvokedParam,
    'SymLocal5': SymLocal5EvokedParam,
    'SymLocal6': SymLocal6EvokedParam,
    }
# L6cc inactivated:
#evokedTemplates = {'L2': L2EvokedParam,\
#                    'L34': L34EvokedParam,\
#                    'L4py': L4pyEvokedParam,\
#                    'L4sp': L4spEvokedParam,\
#                    'L4ss': L4ssEvokedParam,\
#                    'L5st': L5stEvokedParam,\
#                    'L5tt': L5ttEvokedParam,\
#                    'L6ccinv': L6ccinvEvokedParam,\
#                    'L6ct': L6ctEvokedParam,\
#                    'VPM': VPMEvokedParam,\
#                    'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
# L5tt inactivated:
#evokedTemplates = {'L2': L2EvokedParam,\
#                    'L34': L34EvokedParam,\
#                    'L4py': L4pyEvokedParam,\
#                    'L4sp': L4spEvokedParam,\
#                    'L4ss': L4ssEvokedParam,\
#                    'L5st': L5stEvokedParam,\
#                    'L6cc': L6ccEvokedParam,\
#                    'L6ccinv': L6ccinvEvokedParam,\
#                    'L6ct': L6ctEvokedParam,\
#                    'VPM': VPMEvokedParam,\
#                    'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
# L4ss inactivated:
#evokedTemplates = {'L2': L2EvokedParam,\
#                    'L34': L34EvokedParam,\
#                    'L4py': L4pyEvokedParam,\
#                    'L4sp': L4spEvokedParam,\
#                    'L5st': L5stEvokedParam,\
#                    'L5tt': L5ttEvokedParam,\
#                    'L6cc': L6ccEvokedParam,\
#                    'L6ccinv': L6ccinvEvokedParam,\
#                    'L6ct': L6ctEvokedParam,\
#                    'VPM': VPMEvokedParam,\
#                    'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
# L3py/L4sp inactivated:
#evokedTemplates = {'L2': L2EvokedParam,\
#                    'L4py': L4pyEvokedParam,\
#                    'L4ss': L4ssEvokedParam,\
#                    'L5st': L5stEvokedParam,\
#                    'L5tt': L5ttEvokedParam,\
#                    'L6cc': L6ccEvokedParam,\
#                    'L6ccinv': L6ccinvEvokedParam,\
#                    'L6ct': L6ctEvokedParam,\
#                    'VPM': VPMEvokedParam,\
#                    'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
## VPM inactivated:
#evokedTemplates = {'L2': L2EvokedParam,\
#                    'L34': L34EvokedParam,\
#                    'L4py': L4pyEvokedParam,\
#                    'L4sp': L4spEvokedParam,\
#                    'L4ss': L4ssEvokedParam,\
#                    'L5st': L5stEvokedParam,\
#                    'L5tt': L5ttEvokedParam,\
#                    'L6cc': L6ccEvokedParam,\
#                    'L6ccinv': L6ccinvEvokedParam,\
#                    'L6ct': L6ctEvokedParam,\
#                    'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
# EXC types evoked generic
#evokedTemplates = {'L1': L1EvokedParam,\
#                    'L23Trans': L23TransEvokedParam,\
#                    'L45Peak': L45PeakEvokedParam,\
#                    'L45Sym': L45SymEvokedParam,\
#                    'L56Trans': L56TransEvokedParam,\
#                    'SymLocal1': SymLocal1EvokedParam,\
#                    'SymLocal2': SymLocal2EvokedParam,\
#                    'SymLocal3': SymLocal3EvokedParam,\
#                    'SymLocal4': SymLocal4EvokedParam,\
#                    'SymLocal5': SymLocal5EvokedParam,\
#                    'SymLocal6': SymLocal6EvokedParam,\
#                    }
# EXC/INH types evoked generic
#evokedTemplates = {}

# anatomical PC + surround columns (3x3)
# ranging from (potentially) 1-9, starting at row-1, arc-1,
# then increasing by arc and then by row up to row+1, arc+1
# e.g. for C2: B1=1, B2=2, B3=3, C1=4, C2=5, C3=6, D1=7, D2=8, D3=9
surroundColumns = {
    'A1': {'Alpha': 4, 'A1': 5, 'A2': 6, 'B1': 8, 'B2': 9},\
    'A2': {'A1': 4, 'A2': 5, 'A3': 6, 'B1': 7, 'B2': 8, 'B3': 9},\
    'A3': {'A2': 4, 'A3': 5, 'A4': 6, 'B2': 7, 'B3': 8, 'B4': 9},\
    'A4': {'A3': 4, 'A4': 5, 'B3': 7, 'B4': 8},\
    'Alpha': {'Alpha': 5, 'A1': 6, 'Beta': 8, 'B1': 9},\
    'B1': {'Alpha': 1, 'A1': 2, 'A2': 3, 'Beta': 4, 'B1': 5, 'B2': 6, 'C1': 8, 'C2': 9},\
    'B2': {'A1': 1, 'A2': 2, 'A3': 3, 'B1': 4, 'B2': 5, 'B3': 6, 'C1': 7, 'C2': 8, 'C3': 9},\
    'B3': {'A2': 1, 'A3': 2, 'A4': 3, 'B2': 4, 'B3': 5, 'B4': 6, 'C2': 7, 'C3': 8, 'C4': 9},\
    'B4': {'A3': 1, 'A4': 2, 'B3': 4, 'B4': 5, 'C3': 7, 'C4': 8},\
    'Beta': {'Alpha': 2, 'Beta': 5, 'B1': 6, 'Gamma': 8, 'C1': 9},\
    'C1': {'Beta': 1, 'B1': 2, 'B2': 3, 'Gamma': 4, 'C1': 5, 'C2': 6, 'D1': 8, 'D2': 9},\
    'C2': {'B1': 1, 'B2': 2, 'B3': 3, 'C1': 4, 'C2': 5, 'C3': 6, 'D1': 7, 'D2': 8, 'D3': 9},\
    'C3': {'B2': 1, 'B3': 2, 'B4': 3, 'C2': 4, 'C3': 5, 'C4': 6, 'D2': 7, 'D3': 8, 'D4': 9},\
    'C4': {'B3': 1, 'B4': 2, 'C3': 4, 'C4': 5, 'D3': 7, 'D4': 8},\
    'Gamma': {'Beta': 2, 'Gamma': 5, 'C1': 6, 'Delta': 8, 'D1': 9},\
    'D1': {'Gamma': 1, 'C1': 2, 'C2': 3, 'Delta': 4, 'D1': 5, 'D2': 6, 'E1': 8, 'E2': 9},\
    'D2': {'C1': 1, 'C2': 2, 'C3': 3, 'D1': 4, 'D2': 5, 'D3': 6, 'E1': 7, 'E2': 8, 'E3': 9},\
    'D3': {'C2': 1, 'C3': 2, 'C4': 3, 'D2': 4, 'D3': 5, 'D4': 6, 'E2': 7, 'E3': 8, 'E4': 9},\
    'D4': {'C3': 1, 'C4': 2, 'D3': 4, 'D4': 5, 'E3': 7, 'E4': 8},\
    'Delta': {'Gamma': 2, 'Delta': 5, 'D1': 6, 'E1': 9},\
    'E1': {'Delta': 1, 'D1': 2, 'D2': 3, 'E1': 5, 'E2': 6},\
    'E2': {'D1': 1, 'D2': 2, 'D3': 3, 'E1': 4, 'E2': 5, 'E3': 6},\
    'E3': {'D2': 1, 'D3': 2, 'D4': 3, 'E2': 4, 'E3': 5, 'E4': 6},\
    'E4': {'D3': 1, 'D4': 2, 'E3': 4, 'E4': 5}}
# correspondence between anatomical column
# and whisker PSTH relative to PW whisker
# (e.g, C2 whisker deflection in B1
# looks like D3 whisker deflection in C2)
surroundPSTHLookup = {1: 'D3', 2: 'D2', 3: 'D1', 4: 'C3', 5: 'C2',\
                        6: 'C1', 7: 'B3', 8: 'B2', 9: 'B1'}

deflectionOffset = 245.0  #ms; to allow same analysis as CDK JPhys 2007
#deflectionOffset = 345.0 #ms; model2 needs more time to get to steady state

# write cluster parameter file yes/no
clusterParameters = False

def create_network_parameter(
    templateParamName,
    cellNumberFileName,
    synFileName,
    conFileName,
    whisker,
    outFileName,
    write_all_celltypes=False,
    ):
    """Generate and write out a :ref:`network_parameters_format` file defining the evoked activity of a passive whisker touch scenario.
    
    Reads in a template file for a network, where the parameters of each celltype are already defined, but the values are not set.
    Sets the PSTHs (i.e. spike probability per temporal bin) for each cell in the network, depending on the celltype, columnm, and which :paramref:`whisker` was deflected.
    Spike probabilities only depend on the celltype, column, and deflected whisker.
    Spike times are then Poisson sampled from these PSTHs.
    A spike does not guarantee a synapse relase, but rather the probability of release upon a spike is set for each celltype.
    
    The template file contains the key "network" with the following info for each celltype:
    
        - celltype: 'spiketrain' or 'pointcell'
        - interval: spike interval
        - synapses: containing receptor information (type, weight and time dynamics) and release probability
            - receptors
                - receptor type
                    - threshold: threshold for activation
                    - delay: delay for activation
                    - weight: weight of the synapse
        - releaseProb: probability that a synapse gets activated if the cell spikes
            
    Args:
        templateParamName (str): Name of the template parameter file.
        cellNumberFileName (str): Name of the file containing the number of cells for each celltype and column.
        synFileName (str) : Name of the `.syn` file, defining the synapse types.
        conFileName (str): Name of the `.con` file, defining the connections.
        whisker (str): Which whisker is to be deflected.
        outFileName (str): Name of the output file.
        write_all_celltypes (bool): Whether to write out parameter information for all cell types, even if they do not spike during the configured experimental condition.
        
    Example:
    
        >>> templateParam = json.loads(templateParamName)
        >>> templateParam
        {
        "info": {
            "date": "11Feb2015",
            "name": "evoked_activity",
            "author": "name",
        },
        "network": {
            "cell_type_1": {
                "celltype": "spiketrain",
                "interval": 2173.9,
                "synapses": {
                    "receptors": {
                        "glutamate_syn": {
                            "threshold": 0.0,
                            "delay": 0.0,
                                "parameter": {
                                "tau1": 26.0,
                                "tau2": 2.0,
                                "tau3": 2.0,
                                "tau4": 0.1,
                                "decayampa": 1.0,
                                "decaynmda": 1.0,
                                "facilampa": 0.0,
                                "facilnmda": 0.0,
                                },
                            "weight": [1.47, 1.47],
                        },
                    },
                "releaseProb": 0.6,
                },
            },
            "cell_type_2": {...},
            ...
    }
    """
    print('*************')
    print('creating network parameter file from template {:s}'.format(
        templateParamName))
    print('*************')

    templateParam = scp.build_parameters(templateParamName)
    cellTypeColumnNumbers = load_cell_number_file(cellNumberFileName)

    nwParam = scp.NTParameterSet({
        'info': templateParam.info,
        'NMODL_mechanisms': templateParam.NMODL_mechanisms
    })
    #    nwParam.info = templateParam.info
    #    nwParam.NMODL_mechanisms = templateParam.NMODL_mechanisms
    nwParam.network = {}

    if clusterParameters:
        clusterBasePath = '/gpfs01/bethge/home/regger'
        nwParamCluster = scp.NTParameterSet({'info': templateParam.info})
        nwParamCluster.NMODL_mechanisms = templateParam.NMODL_mechanisms.tree_copy(
        )
        nwParamCluster.network = {}
        synFileNameIndex = synFileName.find('L5tt')
        synFileNameCluster = clusterBasePath + '/data/' + synFileName[
            synFileNameIndex:]
        conFileNameCluster = synFileNameCluster[:-4] + '.con'
        for mech in nwParamCluster.NMODL_mechanisms:
            mechPath = nwParamCluster.NMODL_mechanisms[mech]
            if '/nas1/Data_regger' in mechPath:
                mechPathIndex = mechPath.find('L5tt')
                newMechPath = clusterBasePath + '/data/' + mechPath[
                    mechPathIndex:]
            if '/home/regger' in mechPath:
                newMechPath = clusterBasePath + mechPath[12:]
            nwParamCluster.NMODL_mechanisms[mech] = newMechPath


    # for cellType in cellTypeColumnNumbers.keys():
    for cellType in list(templateParam.network.keys()):
        cellTypeParameters = templateParam.network[cellType]
        # CellTyepeParameters typically include :
        # 'celltype': 'spiketrain' or "pointcell"
        # 'interval': spike interval
        # 'synapses': containing receptor information (kind and time dynamics) and release probability
        for column in list(cellTypeColumnNumbers[cellType].keys()):
            numberOfCells = cellTypeColumnNumbers[cellType][column]
            if numberOfCells == 0 and not write_all_celltypes:
                continue
            cellTypeName = cellType + '_' + column
            
            # init empty template and fill values
            nwParam.network[cellTypeName] = cellTypeParameters.tree_copy()
            if clusterParameters:
                nwParamCluster.network[cellTypeName] = cellTypeParameters.tree_copy()
            
            # calculate PSTH depending on the column, the deflected whisker and the cell type
            PSTH = whisker_evoked_PSTH(column, whisker, cellType)
            
            if PSTH is not None:
                interval = nwParam.network[cellTypeName].pop('interval')
                nwParam.network[cellTypeName].celltype = {
                    'spiketrain': {
                        'interval': interval
                    }
                }
                nwParam.network[cellTypeName].celltype['pointcell'] = PSTH
                nwParam.network[cellTypeName].celltype['pointcell']['offset'] = deflectionOffset
                if clusterParameters:
                    interval = nwParamCluster.network[cellTypeName].pop('interval')
                    nwParamCluster.network[cellTypeName].celltype = {
                        'spiketrain': {
                            'interval': interval
                        }
                    }
                    nwParamCluster.network[cellTypeName].celltype['pointcell'] = PSTH
                    nwParamCluster.network[cellTypeName].celltype['pointcell']['offset'] = deflectionOffset
            nwParam.network[cellTypeName].cellNr = numberOfCells
            nwParam.network[cellTypeName].synapses.distributionFile = synFileName
            nwParam.network[cellTypeName].synapses.connectionFile = conFileName
            if clusterParameters:
                nwParamCluster.network[cellTypeName].cellNr = numberOfCells
                nwParamCluster.network[cellTypeName].synapses.distributionFile = synFileNameCluster
                nwParamCluster.network[cellTypeName].synapses.connectionFile = conFileNameCluster

    nwParam.save(outFileName)
    clusterOutFileName = outFileName[:-6] + '_cluster.param'
    if clusterParameters:
        nwParamCluster.save(clusterOutFileName)


def whisker_evoked_PSTH(
        column, 
        deflectedWhisker, 
        cellType
    ):
    """
    Fetch the PSTHs of each celltype in a barrel cortex :paramref:`column` for evoked activity reflecting 
    a passive whisker touch scenario.
    This method does not generate such data, but reads it in from existing files containing such empirical measurements, 
    and parses it. These existing data files are set as global variables in this runfile. For other activity data, adapt these file names.
    
    The data linked in this runfile are for experiments where the C2 whisker was deflected.
    For situations where other :paramref:`deflectedwhisker`s are requested, activity data of equivalent
    columns relative to the C2 is requested.
    
    Example:
        >>> column = 'B2'  # I want activity from B2 column
        >>> deflectedWhisker = 'C1'  # I want activity reflecting deflection of C1 whisker (not C2)
        >>> cellType = 'L6ct'
        >>> params = whisker_evoked_PSTH(column=column, deflectedWhisker=deflectedWhisker, cellType=cellType)
        >>> print(params)  # This is activity data from the C3 column for C2 whisker deflection i.e. equivalent activity
        {
            'distribution': 'PSTH', 
            'intervals': [(40.0, 41.0), (43.0, 44.0), (49.0, 50.0)], 
            'probabilities': [0.0057, 0.0057, 0.0057]
            }

    Args:
        column (str): the column in the barrel cortex for which to parse the PSTHs.
        deflectedWhisker (str): Which whisker was deflected.
        cellType (str): Which cell type you want the PSTH for.

    Returns:
        parameters.ParameterSet: 
            The PSTH for the given cell type in a C2-relative equivalent column, reflecting the deflection of the given whisker.
    """
    # The columns that surround the column of deflected whisker, plus the column of the deflected whisker itself
    columns = list(surroundColumns[deflectedWhisker].keys())
    # Cell types in these columns for which we have evoked activity data
    evokedTypes = list(evokedTemplates.keys())
    if column not in columns or cellType not in evokedTypes:
        return None
    # NTParameterset of PSTHs of these cell types
    evokedTemplate = evokedTemplates[cellType]
    # Equivalent column relative to C2
    PSTHwhisker = surroundPSTHLookup[surroundColumns[deflectedWhisker][column]]
    PSTHstr = cellType + '_' + PSTHwhisker
    PSTH = evokedTemplate[PSTHstr]
    return PSTH


def load_cell_number_file(cellNumberFileName):
    """Load the cell number file.
    
    The cell number file must have the following format::
    
        Anatomical_area Presynaptic_cell_type   n_cells
        A1	cell_type_1	8
        A1	cell_type_2	14
        ...

    Args:
        cellNumberFileName (str): Path to the cell number file.
        
    Returns:
        dict: Dictionary of the form {celltype: {column: nr_of_cells}}
        
    Example:
        >>> load_cell_number_file(
        ...    'getting_started/example_data/anatomical_constraints/'
        ...    '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389/'
        ...    '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389/'
        ...    'NumberOfConnectedCells.csv'
        ...    )
        {
            'L4py': {
                'A1': 8, 
                'A2': 1, 
                'A3': 7, 
                'A4': 3, 
                'Alpha': 9, 
                'B1': 72, 
                'B2': 30, 
                'B3': 97, 
                'B4': 30, 
                'Beta': 0, 
                'C1': 59, 
                'C2': 374, 
                'C3': 88, 
                'C4': 3, 
                'D1': 22, 
                'D2': 89, 
                'D3': 59, 
                'D4': 0, 
                'Delta': 0, 
                'E1': 0, 
                'E2': 0, 
                'E3': 0, 
                'E4': 0, 
                'Gamma': 16}, 
                'L6cc': {...}, 
                ... 
    """
    cellTypeColumnNumbers = {}
    with dbopen(cellNumberFileName, 'r') as cellNumberFile:
        lineCnt = 0
        for line in cellNumberFile:
            if line:
                lineCnt += 1
            if lineCnt <= 1:
                continue
            splitLine = line.strip().split('\t')
            column = splitLine[0]
            cellType = splitLine[1]
            numberOfCells = int(splitLine[2])
            if cellType not in cellTypeColumnNumbers:
                cellTypeColumnNumbers[cellType] = {}
            cellTypeColumnNumbers[cellType][column] = numberOfCells

    return cellTypeColumnNumbers


if __name__ == '__main__':
    #    if len(sys.argv) == 7:
    if len(sys.argv) == 6:
        templateParamName = sys.argv[1]
        cellNumberFileName = sys.argv[2]
        synFileName = sys.argv[3]
        #        conFileName = sys.argv[4]
        conFileName = synFileName[:-4] + '.con'
        whisker = sys.argv[4]
        outFileName = sys.argv[5]
        create_network_parameter(templateParamName, cellNumberFileName,
                                 synFileName, conFileName, whisker, outFileName)
    else:
        #        print 'parameters: [templateParamName] [cellNumberFileName] [synFileName] [conFileName] [deflected whisker] [outFileName]'
        print(
            'parameters: [ongoingTemplateParamName] [cellNumberFileName] [synFileName (absolute path)] [deflected whisker] [outFileName]'
        )

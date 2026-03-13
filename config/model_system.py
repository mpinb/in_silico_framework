# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Cell type configuration.

This module keeps track of which cell types are used throughout ISF.
This should be set on a per-project basis. Adapting this file usually invalidates previously created
:ref:`syn_file_format` files, :ref:`con_file_format` files, and :ref:`network_parameters_format` files.

These cell types are used to keep track of presynaptic cells in network modeling, and their
associated synapse types.
"""
from pathlib import Path

# - Barrel cortex cell types
EXCITATORY = [
    "L2",       # Layer 2
    "L34",      # Layer 3/4
    "L4py",     # Layer 4 pyramidal
    "L4sp",     # Layer 4 spiny
    "L4ss",     # Layer 4 spiny stellate
    "L5st",     # Layer 5 slender-tufted
    "L5tt",     # Layer 5 thick-tufted
    "L6cc",     # Layer 6 cortico-cortical
    "L6ccinv",  # Layer 6 cortico-cortical inverted
    "L6ct",     # Layer 6 corticothalamic
    "VPM"       # Ventral posteromedial nucleus (VPM)
]

INHIBITORY = [
    'L1',
    'L23Trans',
    'L45Peak',
    'L45Sym',
    'L56Trans',
    'SymLocal1',
    'SymLocal2',
    'SymLocal3',
    'SymLocal4',
    'SymLocal5',
    'SymLocal6',
]


prefix = Path(__name__).parent / "getting_started" / "functional_constraints" / "evoked_activity"
EVOKED_ACTIVITY_DATA = {
    'L2':        prefix / 'L2_3x3_PSTH_UpState.param',
    'L34':       prefix / 'L34_3x3_PSTH_UpState.param',
    'L4py':      prefix / 'L4py_3x3_PSTH_UpState.param',
    'L4sp':      prefix / 'L4sp_3x3_PSTH_UpState.param',
    'L4ss':      prefix / 'L4ss_3x3_PSTH_UpState.param',
    'L5st':      prefix / 'L5st_3x3_PSTH_UpState.param',
    'L5tt':      prefix / 'L5tt_3x3_PSTH_UpState.param',
    'L6cc':      prefix / 'L6cc_3x3_PSTH_UpState.param',
    'L6ccinv':   prefix / 'L6ccinv_3x3_PSTH_UpState.param',
    'L6ct':      prefix / 'L6ct_3x3_PSTH_UpState.param',
    'VPM':       prefix / 'VPM_3x3_PSTH.param',
    'L1':        prefix / 'L1_3x3_PSTH_template_PW_0-50_10ms.param',
    'L23Trans':  prefix / 'L23Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L45Peak':   prefix / 'L45Peak_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L45Sym':    prefix / 'L45Sym_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L56Trans':  prefix / 'L56Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal1': prefix / 'SymLocal1_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal2': prefix / 'SymLocal2_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal3': prefix / 'SymLocal3_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal4': prefix / 'SymLocal4_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal5': prefix / 'SymLocal5_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal6': prefix / 'SymLocal6_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
}
"""
:ref:`activity_data_format` files containing empirical data on _in vivo_ PSTHs of all cell types considered in this project.
All cell types configured in :param:`EXCITATORY` and :param:`INHIBITORY` must have a corresponding file here.
These are used to generate :ref:`network_param_format` files.

Note that the top-level pipeline [TODO] also allows you to pass in such a filelist as an argument; the filelist defined here is merely a default.
This filelist is simply defined here for convenience, as it tends to not change throughout a project.
"""
# TODO: finish docstring when landed on a good API and name etc.
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
"""Configure default locations to look for data, when not explicitly given in those pipelines that require it

All pipelines in ISF allow you to provide data objects, or paths to where this data is stored.
Depending on which variables you are investigating, there are certain kinds of data that are not expected to change much throughout the project.

For example, when investigating the mechanisms underlying a specific in vivo stimulus, it can make sense to keep the
activity data of this stimulus fixed.

This user configuration allows you to set default paths to such data. Some pipelines fall back to these paths when
no data is explicitly passed. 

.. caution::
   Please be careful when using these default fallback values. 

   1. Code is not explicitly reproducible when relying on these fallback values. If the fallback values change, the same code can give different results.
   2. It can be very easy to forget you set these.

   It should always be preferred to pass data directly to the pipelines that require them.
   Only those configurations that you expect to _never_ change, or settings that are deemed truly baseline 
   (e.g. a stimulus offset that is inherently tied to _all_ data) should be considered here.

"""
from pathlib import Path
from getting_started import example_data_dir
ACTIVITY_DATA_DIR = Path(example_data_dir) / "functional_constraints" / "evoked_activity"

# -------------------- Activity data
# For full control of the generation of network paramters, please use the NetworkParamBuilder instead.

ACTIVITY_DATA_MAP = {
    'A1':       ACTIVITY_DATA_DIR / "A1_stim.param",
    'A2':       ACTIVITY_DATA_DIR / "A2_stim.param",
    'A3':       ACTIVITY_DATA_DIR / "A3_stim.param",
    'A4':       ACTIVITY_DATA_DIR / "A4_stim.param",
    'Alpha':    ACTIVITY_DATA_DIR / "Alpha_stim.param",
    'B1':       ACTIVITY_DATA_DIR / "B1_stim.param",
    'B2':       ACTIVITY_DATA_DIR / "B2_stim.param",
    'B3':       ACTIVITY_DATA_DIR / "B3_stim.param",
    'B4':       ACTIVITY_DATA_DIR / "B4_stim.param",
    'Beta':     ACTIVITY_DATA_DIR / "Beta_stim.param",
    'C1':       ACTIVITY_DATA_DIR / "C1_stim.param",
    'C2':       ACTIVITY_DATA_DIR / "C2_stim.param",
    'C3':       ACTIVITY_DATA_DIR / "C3_stim.param",
    'C4':       ACTIVITY_DATA_DIR / "C4_stim.param",
    'D1':       ACTIVITY_DATA_DIR / "D1_stim.param",
    'D2':       ACTIVITY_DATA_DIR / "D2_stim.param",
    'D3':       ACTIVITY_DATA_DIR / "D3_stim.param",
    'D4':       ACTIVITY_DATA_DIR / "D4_stim.param",
    'Delta':    ACTIVITY_DATA_DIR / "Delta_stim.param",
    'E1':       ACTIVITY_DATA_DIR / "E1_stim.param",
    'E2':       ACTIVITY_DATA_DIR / "E2_stim.param",
    'E3':       ACTIVITY_DATA_DIR / "E3_stim.param",
    'E4':       ACTIVITY_DATA_DIR / "E4_stim.param",
    'Gamma':    ACTIVITY_DATA_DIR / "Gamma_stim.param",
}
"""
:ref:`activity_data_format` files containing empirical data on _in vivo_ PSTHs of all cell types considered in this project.
These are used to generate :ref:`network_param_format` files.

These files are used when passing a string instead of actual :ref:`activity_data_format` to 
:meth:`~singlecell_input_mapper.network_param_from_tepmlate.build_network_param_from_template`.
Those strings will be interpreted as a key that should map to activity data files defined here.
"""

NETWORK_PARAM_TEMPLATE_FN = Path(example_data_dir) / "functional_constraints" / "ongoing_activity" / "ongoing_activity_celltype_template_exc_conductances_fitted.param"
"""A template :ref:`network_parameters_format` file containing filled-in values for synapse dynamics and ongoing firing intervals.

If no template is passed to :meth:`~singlecell_input_mapper.network_param_from_tepmlate.build_network_param_from_template`,
this is the fallback file that will be used instead.
"""

ADDITIONAL_NETWORK_ACTIVITY_PARAMS = {
    "offset": 245
}
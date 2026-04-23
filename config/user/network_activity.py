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

NETWORK_PARAM_TEMPLATE_FN = Path(example_data_dir) / "functional_constraints" / "ongoing_activity" / "ongoing_activity_celltype_template_exc_conductances_fitted.param"
"""A template :ref:`network_parameters_format` file containing filled-in values for synapse dynamics and ongoing firing intervals.
Useful for setting data that is not expected to change throughout a project.

If no template is passed to :meth:`~singlecell_input_mapper.network_param_from_tepmlate.build_network_param_from_template`,
this is the fallback file that will be used instead.
"""

ADDITIONAL_NETWORK_ACTIVITY_PARAMS = {
    "offset": 245
}
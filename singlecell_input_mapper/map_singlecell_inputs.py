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

"""Top-level pipeline to map synapses onto a postsynaptic cell.

The purpose of this module is to provide access to synapse mapping strategies.
These are either defined by the user in user config, or can be explicitly invoked.

The currently supported synapse mapping strategies in ISF are:
- :mod:`~singlecell_input_mapper.udvary2022`
"""
import logging
from config.user.network_connectivity import SELECTED_SYNAPSE_MAPPING_METHOD
from config import AVAILABLE_SYNAPSE_MAPPING_METHODS
from .udvary2022 import map_singlecell_inputs as udvary2022

logger = logging.getLogger("ISF").getChild(__name__)

__author__ = "Robert Egger"

def map_singlecell_inputs(
    *args,
    **kwargs
) -> None:
    """Infer which synapse embedding strategy to run.

    This function checks the user configuration and runs the configured network embedding strategy.

    Currently supported strategies are:
    - :mod:`~singlecell_input_mapper.udvary2022`

    See also:
        :mod:`config.user.network_connectivity` for configuring network embedding strategies.
    """

    if SELECTED_SYNAPSE_MAPPING_METHOD == "udvary2022":
        from .udvary2022 import map_singlecell_inputs as map_singlecell_inputs_udvary2022
        map_singlecell_inputs_udvary2022(
            *args,
            **kwargs
        )
    else:
        raise NotImplementedError(
            f"The selected network embedding method {SELECTED_SYNAPSE_MAPPING_METHOD} is not implemented. Please use one of {AVAILABLE_SYNAPSE_MAPPING_METHODS}"
        )
    

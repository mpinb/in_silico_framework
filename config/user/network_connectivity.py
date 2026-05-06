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
"""
Configure the default values for synapse mapping and network connectivity workflows in ISF.

This module allows the user to configure default settings for synapse mapping in ISF.

In particular, it allows:

- Setting a default synapse mapping strategy
- Setting default paths for data sources for this synapse mapping strategy

We generally recommend to always explicitly pass both the synapse mapping strategy and the data sources, as it makes the code more explicit. Relying too much on these default values can have the undesirable side effect that the same code may yield different results, when these values are changed.
"""
from pathlib import Path
from .. import AVAILABLE_SYNAPSE_MAPPING_METHODS

SELECTED_SYNAPSE_MAPPING_METHOD = "udvary2022"
"""Which synapse mapping workflow to use for calculating synapse positions on the morphology. Default is :mod:`~singlecell_input_mapper.udvary2022`"""

prefix = Path(__file__).parent.parent.parent / "barrel_cortex"

DATA_REQS_UDVARY2022 = {
    'numberOfCellsSpreadsheetName':   prefix / "nrCells.csv",
    'connectionsSpreadsheetName' :    prefix / "ConnectionsV8.csv",
    'ExPSTDensityName' :              prefix / "PST/EXNormalizationPSTs.am",
    'InhPSTDensityName' :             prefix / "PST/INHNormalizationPSTs.am",
    'boutonDensityFolderName' :       prefix / "singleaxon_boutons_ascii",
    'nrOfSamples':                    50,
}


assert SELECTED_SYNAPSE_MAPPING_METHOD in AVAILABLE_SYNAPSE_MAPPING_METHODS, \
    f"The chosen synapse mapping method {SELECTED_SYNAPSE_MAPPING_METHOD} is not available. Available methods are: {AVAILABLE_SYNAPSE_MAPPING_METHODS}"

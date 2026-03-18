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

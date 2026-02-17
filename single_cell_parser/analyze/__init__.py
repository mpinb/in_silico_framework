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

'''
Analyze the results of single cell simulations and its network embeddings:

- :py:mod:`membrane_potential_analysis`
    - Post-synaptic time histograms (PSTHs)
    - Spike detection
    - Simple statistics of membrane voltage
- :py:mod:`currents`
    - Find time and voltage of max depolarisation
    - Compute currents in the soma
- :py:mod:`synapse analysis`
    - Activation times of synapses
    - intracellular distances
    - distances to synapses
'''

from .membrane_potential_analysis import SpikeInit
from .membrane_potential_analysis import vm_mean
from .membrane_potential_analysis import vm_std
from .membrane_potential_analysis import compute_mean_psp_amplitude
from .membrane_potential_analysis import compute_vm_std_windows
from .membrane_potential_analysis import compute_vm_histogram
from .membrane_potential_analysis import compute_uPSP_amplitude
from .membrane_potential_analysis import simple_spike_detection
from .membrane_potential_analysis import PSTH_from_spike_times
from .membrane_potential_analysis import RecordingSiteManager
from .currents import compute_soma_currents
from .currents import analyze_voltage_trace
from .synanalysis import synapse_distances
from .synanalysis import synapse_distances_2D
from .synanalysis import synapse_activation_times
from .synanalysis import compute_synapse_distances_times
from .synanalysis import compute_syn_distance
from .synanalysis import compute_syn_distances
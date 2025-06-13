# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

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
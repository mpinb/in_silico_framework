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

"""Run simulations of network-embedded neuron models.

This package provides a framework to run simulations of network-embedded neuron models.
They allow to run new simulations from existing parameter files, or to re-run existing simulations with
adapted parameters for the cell and/or network.
"""
import tables
import neuron
from mechanisms import l5pt as l5pt_mechanisms
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/netcon')
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/channels')

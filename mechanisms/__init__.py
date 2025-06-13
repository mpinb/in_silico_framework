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

"""
This directory contains the `.mod` files that define the biophysical behaviour of ion channels, such as conductivity, states, derivative states and initial conditions. 
In addition, it contains network connectivity parameters that define synaptic connections.

These are used by the NEURON simulator as variable parameters for solving the partial differential equations that describe the biophysics of a neuron.

In this direrctory, you will find cell-specific biphysical mechanisms organizeed per folder. Each folder has its own __init__ file that sets up these mechanisms using NEURON.
"""

from . import l5pt
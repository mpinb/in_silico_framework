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
Calculate the connectivity of individual neuron morphologies.
Based on methods and data presented in :cite:t:`Egger_Dercksen_Udvary_Hege_Oberlaender_2014` and :cite:t:`Udvary_Harth_Macke_Hege_De_Kock_Sakmann_Oberlaender_2022`.

This package contains methods to create anatomical realizations for the connectivity of single neurons.
To create anatomical realizations, it is recommended to use the high-level
pipeline :py:meth:`~singlecell_input_mapper.map_singlecell_inputs.map_singlecell_inputs`, which call supon various methods and classes presented in this package.

Inputs:

- The morphology and location of the postsynaptic neuron
- number of cells per cell type, per anatomical area.
- The 3D density of post-synaptic targets (PSTs) in the neuropil (cell type unspecific)
- The 3D density of boutons in the neuropil (cell type specific)
- The 1D and 2D densities of PSTs onto the postsynaptic neuron per length and area (cell type specific)

"""
from __future__ import absolute_import
from .reader import *
from .writer import *
from .network_embedding import *
from .synapse_mapper import *
from .scalar_field import *
from .cell import CellParser

__author__ = 'Robert Egger'
#===============================================================================
# for testing only
#===============================================================================
#from writer import *
#from cell import *
#from synapse_mapper import *
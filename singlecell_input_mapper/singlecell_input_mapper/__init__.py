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
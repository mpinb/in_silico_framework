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
This directory contains the `.mod` files that define the biophysical behaviour of ion channels, such as conductivity, states, derivative states and initial conditions. 
In addition, it contains network connectivity parameters that define synaptic connections.

These are used by the NEURON simulator as variable parameters for solving the partial differential equations that describe the biophysics of a neuron.

In this direrctory, you will find cell-specific biphysical mechanisms organizeed per folder. Each folder has its own __init__ file that sets up these mechanisms using NEURON.
"""

from . import l5pt
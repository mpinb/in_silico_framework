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

"""Run simulations of network-embedded neuron models.

This package provides a framework to run simulations of network-embedded neuron models.
They allow to run new simulations from existing parameter files, or to re-run existing simulations with
adapted parameters for the cell and/or network.
"""
import tables
import neuron
import mechanisms
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/netcon')
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/channels')

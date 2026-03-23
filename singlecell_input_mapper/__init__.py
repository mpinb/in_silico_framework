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

"""Create an empirically constrained dense connectome model with presynaptic activity.

This package provides classes and methods to create a dense connectome model with defined activity patterns.
It can be largely divided in two parts: :ref:`connectivity` and :ref:`activity`.

.. _connectivity:
 
Connectivity
------------

:mod:`singlecell_input_mapper.map_singlecell_inputs` is responsible for assigning synapses to the morphology of a postsynaptic neuron, 
and keeping track of the synapse type and associated presynaptic cell type. 
Based on this presynaptic cell type, different spike times can be generated (see section Activity below).
Assigning synapses onto the postsynaptic morphology is referred to as a 'network embedding'. 
A network embedding for a given morphology is uniquely defined as a :ref:`syn_file_format` and :ref:`conf_file_format` file.

.. _activity:

Activity
--------

This section is responsible for generating activity patterns for the assigned synapses based in empirically observed PSTHs of the presynaptic neurons.
ISF distinguishes two kinds of activity:

1. Ongoing activity: the baseline synaptic activity patterns in the absence of the in vivo condition of interest. The ongoing activity is defined in tandem with the network parameters in a :ref:`network_parameters_format` file.
2. Evoked activity: the activity patterns in response to a specific in vivo condition. Its file format is described in :ref:`activity_data_format`. 

The general workflow is as follows:

1. Read in individual spike times of presynaptic neurons.
2. Create PSTHs for each cell type for the ongoing and evoked activity. Such files are present in getting_started/example_data/functional_constraints
3. Create a network parameter file from the PSTHs.

"""

__author__  = ["Robert Egger", "Arco Bast", "Bjorge Meulemeester"]

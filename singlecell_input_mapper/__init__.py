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
This data is generated or read directly from empirical data sources, and added to a single :ref:`network_parameters_format`.

.. _connectivity:
 
Connectivity
------------

:mod:`singlecell_input_mapper.map_singlecell_inputs` is responsible for assigning synapses to the morphology of a postsynaptic neuron, 
and keeping track of the synapse type and associated presynaptic cell type. 
Based on the presynaptic cell type of each synapse, ISf can generate spike times for each presynaptic source (see section Activity below).
Assigning synapses onto the postsynaptic morphology is referred to as a 'network embedding'. 
A network embedding for a given morphology is uniquely defined as a :ref:`syn_file_format` and :ref:`con_file_format` file.

ISF currently implements the following workflows to generate :ref:`syn_file_format` and :ref:`con_file_format` files:

- :mod:`~singlecell_input_mapper.udvary2022`

.. hint::
   If you work on a model system that does not have the required input data for these workflows, we recommend to infer
   synapse locations in whichever way is most suited to your model system, and convert this information to 
   :ref:`syn_file_format` and :ref:`con_file_format` files. These file formats are pruposfully simple and human-readable.

.. _activity:

Activity
--------

This section is responsible for generating activity patterns for the assigned synapses based in empirically observed PSTHs of the presynaptic neurons.
ISF distinguishes two kinds of activity:

1. Ongoing activity: the baseline synaptic activity patterns in the absence of the in vivo condition of interest. The ongoing activity is defined in tandem with the network parameters in a :ref:`network_parameters_format` file.
2. Evoked activity: the activity patterns in response to a specific in vivo condition. Its file format is described in :ref:`activity_data_format`. 

"""

__author__  = ["Robert Egger", "Arco Bast", "Bjorge Meulemeester"]

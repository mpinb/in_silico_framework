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

"""Create an empirically constrained dense connectome model with presynaptic activity.

This package provides classes and methods to create a dense connectome model with defined activity patterns.
It can be largely divided in two parts: :ref:`connectivity` and :ref:`activity`.

See also:
    This package should not be confused with :py:mod:`single_cell_parser`. 
    
    This package is specialized to create empirically consistent network models, providing fine-grained control over the
    network realization process, and ability to constrain it with empirical data.
    
    :py:mod:`single_cell_parser` provides only basic functionality to recreate such network realizations from the results generated here.
    The purpose of :py:mod:`single_cell_parser` is to provide an API to the NEURON simulator, and read in results from network realizations.
  
.. _connectivity:
 
Connectivity
------------

:py:mod:`singlecell_input_mapper.singlecell_input_mapper` is responsible for assigning synapses to the morphology of a postsynaptic neuron, 
and keeping track of the synapse type and associated presynaptic cell type. Based on this presynaptic cell type, different spike times can be generated (see section Activity below).
Assigning synapses onto the postsynaptic morphology is referred to as a 'network realization'. The network realization in ISF is based on the following inputs:

- The morphology and location of the postsynaptic neuron
- The 3D density of post-synaptic targets (PSTs) in the brain region of interest (cell type unspecific)
- The 3D density of boutons in the brain region of interest (cell type specific)
- The 1D and 2D densities of PSTs onto the postsynaptic neuron per length and area (cell type specific)

See :py:mod:`singlecell_input_mapper.singlecell_input_mapper` for more information, and :py:meth:`singlecell_input_mapper.map_singlecell_inputs.map_singlecell_inputs` for a pipeline to create anatomical realizations.

Other ways of network realization are also possible, depending on the empirical data available.
If you want to use other methods, please familiarize yourself with the data formats such that you can either:

1. Convert the input data to the required input format for ISF and run the same network realization pipeline. Input file formats are described in more detail in :py:mod:`singlecell_input_mapper.map_singlecell_inputs`.
2. Create your own network realization, and convert the output to the format used in ISF. These are :ref:`syn_file_format` and :ref:`con_file_format` files. For more info on how to generate and use these, refer to the network modeling section of the :ref:`tutorials`

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
__author__  = "Robert Egger"
__credits__ = ["Robert Egger", "Arco Bast"]

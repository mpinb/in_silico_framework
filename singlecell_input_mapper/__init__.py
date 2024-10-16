"""Create an empirically constrained dense connectome model with presynaptic activity.

This package provides classes and methods to create a dense connectome model with defined activity patterns.
It can be largely divided in two parts: :ref:`connectivity` and :ref:`activity`.

Attention:
    This package should not be confused with :py:mod:`single_cell_parser`. 
    
    This package is specialized to create empirically consistent network models, providing fine-grained control over the
    network realization process, and ability to constrain it with empirical data.
    :py:mod:`single_cell_parser` provides only basic functionality to generate network realizations and activity,
    while its purpose is to provide an API to the NEURON simulator, and read in results from network realizations.
  
    In any case, beware of the following classes and methods that are duplicates in name, but not in functionality:
    
    .. list-table:: 
        :header-rows: 1

        * - :py:mod:`singlecell_input_mapper.singlecell_input_mapper`
          - :py:mod:`single_cell_parser`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`
          - :py:class:`~single_cell_parser.cell.Cell`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.CellParser`
          - :py:class:`~single_cell_parser.cell_parser.CellParser`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.reader.Edge`
          - :py:class:`~single_cell_parser.reader.Edge`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper`
          - :py:class:`~single_cell_parser.synapse_mapper.SynapseMapper`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`
          - :py:class:`~single_cell_parser.scalar_field.ScalarField`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`
          - :py:class:`~single_cell_parser.network.NetworkMapper`
        * - :meth:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`
          - :meth:`~single_cell_parser.synapse.Synapse`
        * - :meth:`~singlecell_input_mapper.singlecell_input_mapper.reader.read_hoc_file`
          - :meth:`~single_cell_parser.reader.read_hoc_file`
        * - :meth:`~singlecell_input_mapper.singlecell_input_mapper.reader.read_scalar_field`
          - :meth:`~single_cell_parser.reader.read_scalar_field`

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
2. Create your own network realization, and convert the output to the format used in ISF. These are `.syn` and `.con` files, and described in more detail in the [tutorials](../getting_started/tutorials/2. network models/2.1 Anatomical embedding.ipynb).

.. _activity:

Activity
--------

This section is responsible for generating activity patterns for the assigned synapses based in empirically observed PSTHs of the presynaptic neurons.
ISF distinguishes two kinds of activity:

1. Ongoing activity: the baseline synaptic activity patterns in the absence of the in-vivo condition of interest. The ongoing activity is defined in tandem with the network parameters in a :ref:`network_parameters_format` file.
2. Evoked activity: the activity patterns in response to a specific in-vivo condition. Its file format is described in :ref:`activity_data_format`. 

The general workflow is as follows:

1. Read in individual spike times of presynaptic neurons.
2. Create PSTHs for each cell type for the ongoing and evoked activity. Such files are present in getting_started/example_data/functional_constraints
3. Create a network parameter file from the PSTHs.

"""
__author__  = "Robert Egger"
__credits__ = ["Robert Egger", "Arco Bast"]

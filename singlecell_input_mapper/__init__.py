"""
Create a dense connectome model with presynaptic activity.

This package provides classes and methods to create a dense connectome model with defined activity patterns.
It can be largely divided in two parts: connectivity and activity.

Connectivity
------------

:py:mod:`singlecell_input_mapper.singlecell_input_mapper` is responsible for assigning synapses to the morphology of a postsynaptic neuron, 
and keeping track of th3e synapse type and associated presynaptic cell type. Based on this presynaptic cell type, different spike times can be generated (see section Activity below).
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

Activity
--------

This section is responsible for generating activity patterns for the assigned synapses based in empirically observed PSTHs of the presynaptic neurons.
ISF distinguishes two kinds of activity:

1. Ongoing activity: the baseline synaptic activity patterns in the absence of the in-vivo condition of interest.
2. Evoked activity: the activity patterns in response to a specific in-vivo condition.

The general workflow is as follows:

1. Read in individual spike times of presynaptic neurons.
2. Create PSTHs for each cell type for the ongoing and evoked activity. Such files are present in getting_started/example_data/functional_constraints
3. Create a network parameter file from the PSTHs.

Evoked and ongoing activity each have their separate network parameter file. Example activity data for evoked activity can be found in the form of PSTHs in getting_started/example_data/functional_constraints/evoked_activity.
Ongoing activity network parameter files can be found in getting_started/example_data/functional_constraints/ongoing_activity and has the following format::

        {
        "info": {
            "date": "11Feb2015",
            "name": "evoked_activity",
            "author": "name",
        },
        "network": {
            "cell_type_1": {
                "celltype": "spiketrain" or "pointcell",
                "interval": average interval between spikes for the given experimental condition,
                "synapses": {
                    "receptors": {
                        "glutamate_syn": {
                            "threshold": 0.0,
                            "delay": 0.0,
                                "parameter": {
                                "tau1": 26.0,
                                "tau2": 2.0,
                                "tau3": 2.0,
                                "tau4": 0.1,
                                "decayampa": 1.0,
                                "decaynmda": 1.0,
                                "facilampa": 0.0,
                                "facilnmda": 0.0,
                                },
                            "weight": [1.47, 1.47],
                        },
                    },
                "releaseProb": 0.6,
                },
            },
            "cell_type_2": {...},
            ...
    }
"""
.. _file_formats:

====================
File & data formats
====================

.am
===

The Amira proprietary file format. See `here <https://www.csc.kth.se/~weinkauf/notes/amiramesh.html>`_ for more information.
This flexible format can be used to store 3D scalar meshes, 3D neuron morphology reconstructions, slice image data etc.

Readers:

- :py:mod:`~single_cell_parser.reader.read_scalar_field`
- :py:mod:`~single_cell_parser.reader.read_landmark_file`

.. _hoc_file_format:

.hoc
====
NEURON :cite:`hines2001neuron` file format for neuron morphologies. 
Documentation can be found `here <https://nrn.readthedocs.io/en/latest/guide/hoc_chapter_11_old_reference.html>`_.
The morphology is specified as a tree structure: the different sections of a neuron 
(pieces separated between branching points or branches endings) are connected in order. 
Each section is formed by a set of points, defined by their 3D coordinates and the diameter of the 
neuron structure at that point ``(pt3dadd -> x, y, z, diameter)``.

Readers:

- :py:mod:`~single_cell_parser.cell_parser`
- :py:meth:`~single_cell_parser.reader.read_hoc_file`

Example::

    {create soma}
    {access soma}
    {nseg = 1}
    {pt3dclear()}
    {pt3dadd(1.933390,221.367004,-450.045990,12.542000)}
    {pt3dadd(2.321820,221.046997,-449.989990,13.309400)}
    ...
    {pt3dadd(13.961900,210.149002,-447.901001,3.599700)}

    {create BasalDendrite_1_0}
    {connect BasalDendrite_1_0(0), soma(0.009696)}
    {access BasalDendrite_1_0}
    {nseg = 1}
    {pt3dclear()}
    {pt3dadd(6.369640, 224.735992, -452.399994, 2.040000)}
    {pt3dadd(6.341550, 222.962997, -451.906006, 2.040000)}
    ...

.. _mod_file_format:

.mod
====
NEURON :cite:`hines2001neuron` file format for neuron mechanisms. Documentation can be found `here <https://neuron.yale.edu/neuron/docs/using-nmodl-files>`_.
Used to define channel and synapse dynamics in NEURON simulations.
See the folder `mechanisms` in the project source.

.. _con_file_format:

.con
====
ISF custom file format to store connectivity data. 
To be used in conjunction with an associated :ref:`syn_file_format` file and morphology :ref:`hoc_file_format` file.
It numbers each synapse, and links it to its associated presynaptic cell type and ID.
While a :ref:`syn_file_format` file and :ref:`hoc_file_format` file provide the anatomical realization of a network,
the addition of a :ref:`con_file_format` file makes it into a functional realization, as it allows linking the synapses to
their presynaptic cells, which in turn allow cell type specific activation patters (see: :py:meth:`single_cell_parser.network.NetworkMapper`).

Readers:

- :py:mod:`~single_cell_parser.reader.read_functional_realization_map`

Example::

    # Anatomical connectivity realization file; only valid with synapse realization:
    # synapse_ralization_file.syn
    # Type - cell ID - synapse ID

    L6cc_A3 0       0
    L6cc_A3 1       1
    L6cc_A3 2       2
    L6cc_A3 3       3
    L6cc_A3 4       4
    L6cc_A3 4       5
    ...

.. _syn_file_format:

.syn
====
ISF custom file format to store synapse locations onto a morphology. 
This file fully captures an anatomical realization of a network.
Only valid with an associated morphology :ref:`hoc_file_format` file.

For each synapse, it provides the synapse type and location onto the morphology.
Each row index corresponds to its synapse ID, providing a backlink to the :ref:`con_file_format` file format.
The location is encoded as a section ID and x (a normalized distance along the section),
to be consistent with NEURON syntax.

To create a functional network (i.e., known presynaptic origin), 
it must be used in conjunction with an associated :ref:`con_file_format` file.

Readers:

- :py:mod:`~single_cell_parser.reader.read_synapse_realization`
- :py:mod:`~single_cell_parser.reader.read_pruned_synapse_realization`

Example::

    # Synapse distribution file
    # corresponding to cell: 86_L5_86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center
    # Type - section - section.x

    VPM_E1  112     0.138046479525
    VPM_E1  130     0.305058053119
    VPM_E1  130     0.190509288017
    VPM_E1  9       0.368760777084
    VPM_E1  110     0.0
    VPM_E1  11      0.120662910562
    ...

.. _param_file_format:

.param
======
ISF custom file format to save JSON-like ASCII data. These can be read in using :py:mod:`single_cell_parser`.
Used in a variety of ways, as seen below.

.. _cell_parameters_format:

Cell parameters
---------------

:ref:`param_file_format` file to store biophysical parameters of a cell.
Includes the path to the :ref:`hoc_file_format` morphology file, biophysical properties of the cell per cellular 
structure (i.e. soma, dendrite, axon initial segment ...),
and basic simulation parameters. Simulation parameters are usually overridden by higher level modules, 
such as :py:mod:`simrun`.

To access different structures of a cell::

    >>> cell_parameters.neuron.keys()
    ['Myelin', 'Soma', 'AIS', 'filename', 'Dendrite', 'ApicalDendrite']

Example::

    {
        'info': {...},
        'neuron': {
            'filename': 'getting_started/example_data/anatomical_constraints/*.hoc',
            'Soma': {
                'properties': {
                    'Ra': 100.0,
                    'cm': 1.0,
                    'ions': {'ek': -85.0, 'ena': 50.0}
                    },
                'mechanisms': {
                    'global': {},
                    'range': {
                        'pas': {
                            'spatial': 'uniform',
                            'g': 3.26e-05,
                            'e': -90},
                        'Ca_LVAst': {
                            'spatial': 'uniform',
                            'gCa_LVAstbar': 0.00462},
                        'Ca_HVA': {...},
                        ...,}}},
            'Dendrite': {...},
            'ApicalDendrite': {...},
            'AIS': {...},
            'Myelin': {...},
            'cell_modify_functions': {
                'scale_apical': {'scale': 2.1}
            },
        'sim': {
            'Vinit': -75.0,
            'tStart': 0.0,
            'tStop': 250.0,
            'dt': 0.025,
            'T': 34.0,
            'recordingSites': ['getting_started/example_data/apical_proximal_distal_rec_sites.landmarkAscii']}
    }

.. _activity_data_format:

Activity data
-------------
:ref:`param_file_format` files are used to store activity data covering spike times and time bins for specific cell types in response to a stimulus, as seen in e.g. getting_started/example_data/functional_constraints/evoked_activity/

Example::

    {
    "L4ss_B1": {
    "distribution": "PSTH",
    "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
    "probabilities": [-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,0.0062,-0.0004,0.0129,0.0062,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,0.0062,0.0062,-0.0004,-0.0004,-0.0004],
    },
    "L4ss_B2": {
    "distribution": "PSTH",
    "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
    "probabilities": [-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,0.0129,0.0062,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004],
    },
    ...
    }

.. _network_parameters_format:

Network parameters
------------------
The :ref:`param_file_format` format is used to store network parameters, 
describing the activation of presynaptic cells and synapses during the scenario we want to simulate. 

For each presynaptic cell type in the network, this following information is provided:

.. list-table:: Network Parameters
   :header-rows: 1

   * - Parameter
     - Description
   * - ``celltype``
     - Spiking type of the presynaptic cell ("spiketrain", or "pointcell").
   * - ``interval``
     - Average interval of the spikes.
   * - ``synapses``
     - Additional synapse information (see table below)
   * - ``cellNr``
     - Amount of connected presynaptic cells of this type.

The ``synapse`` key of each presynaptic cell type contains the following information:

.. list-table:: Synapse parameters
   :header-rows: 1

   * - Parameter
     - Description
   * - ``receptors``
     - Dictionary of synapse properties per receptor type (e.g. ``gaba_syn``): threshold, delay, weight, reversal potential and time dynamics.
   * - ``releaseProb``
     - Release probability of this synapse upon a spike of its associated presynaptic cell. 
       A synapse is either active or not active, never inbetween.
   * - ``connectionFile``
     - Reference to an associated :ref:`con_file_format` file for this cell type's synapses.
   * - ``distributionFile``
     - Reference to an associated :ref:`syn_file_format` file for this cell type's synapses.
        
Example::

    {
    "info": {
        "date": "11Feb2015",
        "name": "evoked_activity",
        "author": "name",
    },
    "network": {
        "cell_type_1": {
            "celltype": "spiketrain",
            "interval": 2173.9,
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
            "cellNr": 1,
            "noise": 0.0,
            "start": 0.0,
            "nspikes": 2,
            },
        },
        "cell_type_2": {
            "celltype": "pointcell",
            "distribution": "PSTH"
            "intervals": [(0, 10), (10, 20), (20, 40), (40, 50)],
            "probabilities": [0.0, 0.01, 0.05, 0.0],
            "offset": 0.0,
        },
        ...
    }


Dataframes
==========

The output format of various simulation pipelines are usually a dataframe. below, you find common formats used throughout ISF.

The :py:mod:`simrun` module produces output files in ``.csv`` or ``.npz`` format. many of these files
need to be created for each individual simulation trial. 
These raw output files are usually parsed into single dataframes for further analysis using a ``db_initializers`` submodule (see e.g. 
:py:mod:`~data_base.isf_data_base.db_initializers.load_simrun_general`).


.. _syn_activation_format:

Synapse activation
------------------

The raw output of the :py:mod:`simrun` module contains ``.csv`` files containing the synaptic activations onto a post-synaptic cell 
for each individual simulation trial. Each file contains the following information for each synapse during a particular simulation trial:

- type
- ID (for identifying the corresponding presynaptic cell)
- location (section ID, section pt ID, soma distance)
- dendrite label (e.g. ``"ApicalDendrite"``)
- activation times

An example of the format is shown below:

.. _syn_activation_csv_format:

.. list-table:: ``simulation_run<sim_trial>_synapses.csv``
    :header-rows: 1


    * - synapse type
      - synapse ID
      - soma distance
      - section ID
      - section pt ID
      - dendrite label
      - activation times
      - 
      - 
    * - presyn_cell_type_1
      - 0
      - 150.0
      - 24
      - 0
      - 'basal'
      - 10.2, 80.5, 140.8
      - 
      - 
    * - presyn_cell_type_1
      - 1
      - 200.0
      - 112
      - 0
      - 'apical'
      - 
      - 
      - 
    * - presyn_cell_type_2
      - 2
      - 250.0
      - 72
      - 0
      - 'apical'
      - 300.1, 553.5
      - 
      - 

These individual files are usually gathered and parsed into a single dataframe containing all trials for further analysis:

.. _syn_activation_df_format:

.. list-table::
    :header-rows: 1

    * - trial index
      - synapse type
      - synapse ID
      - soma distance
      - section ID
      - section pt ID
      - dendrite label
      - activation times
      - 
      - 
    * - 0
      - presyn_cell_type_1
      - 0
      - 150.0
      - 24
      - 0
      - 'basal'
      - 10.2, 80.5, 140.8
      - 
      - 
    * - 0
      - presyn_cell_type_1
      - 1
      - 200.0
      - 112
      - 0
      - 'apical'
      - 
      - 
      - 
    * - 0
      - presyn_cell_type_2
      - 2
      - 250.0
      - 72
      - 0
      - 'apical'
      - 300.1, 553.5
      - 
      - 

Writers:
    
- :py:meth:`~single_cell_parser.writer.write_synapse_activation_file` is used by :py:mod:`simrun` and :py:mod:`~single_cell_parser.analyze.synanalysis`
   to write raw output data.
- :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` parses these files into a pandas dataframe.

Attention:
    Not every spike of a presynaptic cell necessarily induces a synapse activation. Each synapse has a specific release
    probability and delay (see :ref:`network_parameters_format`).
    For this reason, the spike times of the presynaptic cells is saved separately (see :ref:`spike_times_format`).

.. _spike_times_format:

Spike times
-----------
The raw output of the :py:mod:`simrun` module contains ``.csv`` files containing the spike times of presynaptic cells 
for each individual simulation trial. Each file contains the following information for each synapse during a particular simulation trial:

- type
- ID (for identifying the corresponding synapse, and cell location)
- activation times

An example of the format is shown below:

.. _spike_times_csv_format:

.. list-table:: ``simulation_run<sim_trial>presynaptic_cells.csv``
    :header-rows: 1

    * - cell type
      - cell ID
      - activation times
      - 
      - 
    * - presyn_cell_type_1
      - 0
      - 10.2
      - 80.5
      - 140.8
    * - presyn_cell_type_1
      - 1
      - 300.1
      - 553.5
      - 
    * - presyn_cell_type_2
      - 2
      - 100.2
      - 200.5
      - 300.8
  
These individual files are usually gathered and parsed into a single dataframe containing all trials for further analysis:

.. _spike_times_df_format:

.. list-table::
    :header-rows: 1

    * - trial index
      - cell type
      - cell ID
      - activation times
      - 
      - 
    * - 0
      - presyn_cell_type_1
      - 0
      - 10.2
      - 80.5
      - 140.8
    * - 0
      - presyn_cell_type_1
      - 1
      - 300.1
      - 553.5
      - 
    * - 0
      - presyn_cell_type_2
      - 2
      - 100.2
      - 200.5
      - 300.8

Writers:

- :py:meth:`~single_cell_parser.writer.write_presynaptic_spike_file` is used by :py:mod:`simrun` and :py:mod:`~single_cell_parser.analyze.synanalysis`
   to write raw output data.
- :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` parses these files into a pandas dataframe.

Attention:
    Not every spike of a presynaptic cell necessarily induces a synapse activation. Each synapse has a specific release
    probability and delay (see :ref:`network_parameters_format`).
    For this reason, the synapse activations are saved separately (see :ref:`syn_activation_format`).

Voltage traces
--------------

The raw output of the :py:mod:`simrun` module contains ``.npz`` or ``.csv`` files containing the voltage traces of the postsynaptic cells.
Unlike the synapse activations and spike times, it is possible for one such file to contain multiple trials.

.. _voltage_traces_csv_format:

.. list-table:: ``vm_all_traces.csv``
    :header-rows: 1

    * - t
      - Vm run 00
      - Vm run 01
      - Vm run 02
    * - 100.0
      - -61.4607218758
      - -55.1366909604
      - -67.1747143695
    * - 100.025
      - -61.4665809176
      - -55.1294343391
      - -67.1580037786
    * - 100.05
      - -61.4735021526
      - -55.1223216173
      - -67.1424366078
    * - 100.075
      - -61.4814187507
      - -55.1153403448
      - -67.1279980017

.. _voltage_traces_npz_format:

``vm_all_traces.npz``::

    array([[0.        , 0.025     , 0.05      , 0.075     , 0.1       ],
       [0.88623465, 0.39617305, 0.51784511, 0.1193737 , 0.60248805],
       [0.6766885 , 0.71217337, 0.05441688, 0.47759073, 0.92410834],
       [0.4959228 , 0.81927651, 0.77370012, 0.46643348, 0.61893358]])

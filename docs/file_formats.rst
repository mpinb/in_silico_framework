============
File formats
============

.am
===

The Amira proprietary file format. See `here <https://www.csc.kth.se/~weinkauf/notes/amiramesh.html>`_ for more information.
This flexible format can be used to store 3D scalar meshes, 3D neuron morphology reconstructions, slice image data etc.

.hx
===
AMIRA proprietary file format for saving AMIRA projects.

.hoc
====
NEURON :cite:`hines2001neuron` file format for neuron morphologies. Documentation can be found `here <https://nrn.readthedocs.io/en/latest/guide/hoc_chapter_11_old_reference.html>`_.
Used for 3D morphology reconstructions. Can be read with :py:mod:`single_cell_parser.cell_parser`.

.mod
====
NEURON :cite:`hines2001neuron` file format for neuron mechanisms. Documentation can be found `here <https://neuron.yale.edu/neuron/docs/using-nmodl-files>`.
Used to define channel and synapse dynamics in NEURON simulations.
See the folder `mechanisms` in the project source.

.con
====
ISF custom file format to store neuron connection data. To be used in conjunction with an associated `.syn` file and morphology.
It numbers each synapse, and links it to its associated presynaptic cell type and ID.

Example::

    # Anatomical connectivity realization file; only valid with synapse realization:
    # 86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389.syn
    # Type - cell ID - synapse ID

    L6cc_A3 0       0
    L6cc_A3 1       1
    L6cc_A3 2       2
    L6cc_A3 3       3
    L6cc_A3 4       4
    L6cc_A3 4       5
    ...

.syn
====
ISF custom file format to store synapse data. To be used in conjunction with an associated `.con` file and morphology.
For each synapse, it provides the synapse type and location onto the post-synaptic cell.
The location is encoded as a section ID and x (a normalized distance along the section),
to be consistent with NEURON syntax.

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

.param
======
ISF custom file format to save JSON-like ASCII data. These can be read in using :py:mod:`single_cell_parser`.
Used in a variety of ways, as seen below.

Activity data
-------------
The `.param` format is used to store activity data covering spike times and time bins for specific cell types in response to a stimulus, as seen in e.g. getting_started/example_data/functional_constraints/evoked_activity/

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

Network parameters
------------------
The `.param` format is used to store network parametrs, containing synapse information and ongoing spike intervals for various cell types in a network.
Such synapse information contains the receptor type(s), rise and decay time dynamics (if applicable), weights, and release probabilities upon spike.
        
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
            },
        },
        "cell_type_2": {...},
        ...
    }
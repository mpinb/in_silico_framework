.. _file_formats:

###################
File & data formats
###################


.. md-tab-set::

   .. md-tab-item:: Hide data sources

      .. include:: paramfile_overview.rst

   .. md-tab-item:: Show data sources

      .. include:: paramfile_overview_w_data_sources.rst


.. _syn_file_format:

.syn
****
ISF custom file format to store synapse locations onto a morphology.
Only valid with an associated morphology :ref:`morphology_file_format` file.

For each synapse, it provides the synapse type and location onto the morphology.
Each row index corresponds to its synapse ID, providing a link to a corresponding :ref:`con_file_format` file.
The location is encoded as a section ID and x (a normalized distance along the section),
to be consistent with NEURON syntax.

To create a functional network (i.e., known presynaptic origin), 
it must be used in conjunction with an associated :ref:`con_file_format` file.

Example::

    # Synapse distribution file
    # corresponding to cell: morphology.hoc
    # Type - section - section.x

    VPM_E1  112     0.138046479525
    VPM_E1  130     0.305058053119
    VPM_E1  130     0.190509288017
    VPM_E1  9       0.368760777084
    VPM_E1  110     0.0
    VPM_E1  11      0.120662910562
    ...

.. _con_file_format:

.con
****
ISF custom file format to store connectivity data. 
To be used in conjunction with an associated :ref:`syn_file_format` file and morphology :ref:`morphology_file_format` file.
It numbers each synapse, and links it to its associated presynaptic cell type and ID.
While a :ref:`syn_file_format` file and :ref:`morphology_file_format` file provide the anatomical realization of a morphology embedding into a network,
the addition of a :ref:`con_file_format` file makes possible to construct a functional realization, as it allows linking the synapses to
presynaptic cells of a dense connectome model, which in turn allows to assign cell type specific activation patterns 
to each synapse. ISF's workflow is designed to create these files in tandem, so they always co-exist.

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

.. _param_file_format:

.param
******
ISF custom file format to save JSON-like ASCII data for cell parameters, network parameters, and activity data.
The ``.param`` format is valid Python code, but differs from JSON, as it allows trailing comma's, single quotes, and tuples. JSON does not.
``.param`` files can be read using :mod:`~single_cell_parser.parameters.build_parameters`.

.. seealso:: 
  :mod:`simrun.parameters_to_cell` to rerun a simulation from these parameterfiles.

.. seealso::
  :mod:`~single_cell_parser.parameters.build_parameters` to read these parameterfiles.

.. _cell_parameters_format:

Cell parameters
===============

:ref:`param_file_format` file to store biophysical parameters of a cell.
Includes a reference to a :ref:`morphology_file_format` morphology file, 
biophysical properties of the cell per morphological structure (e.g. soma, dendrite, axon initial segment ...),
and basic simulation parameters. Morphology structure labels should match those inferred from the morphology file.

Parameters under the key ``*.mechanisms.range`` are range mechanisms, and their name should match the name of a loaded :ref:`mod_file_format` file.
Note that the mechanism name in :ref:`mod_file_format` files are defined in the ``NEURON`` block as a ``SUFFIX`` or ``POINTPROCESS``, and have little to do with the file name.

.. seealso::
   The :ref:`mod_file_format` file documentation for how these files are structured.

Each range mechanism must have the key ``spatial``, and its value must match one of the supported spatial profiles in ISF. All spatial profiles except for ``"uniform"`` require additional parameters that need to be defined for a given range mechanism. E.g. the exponential profile expects the parameters ``offset``, ``linScale``, ``_lambda``, ``xOffset``. Distances for these spatial profiles are calculated in terms of distance to soma.
If ``"distance": "relative"`` is passed for a range mechanism, the distance dependency is scaled by the maximum distance of all sections with the same label. E.g. for a simple dendrite, this means that all distance metrics are scaled with the length of the longest dendrite. This is useful for setting scaling parameters without necessarily having to worry about the exact dimensions of the neurites beforehand.
Spatial profiles are evaluated on a segment-by-segment basis: the segment center is used as the distance dependency of each spatial profile, and channels are uniform within a single segment.

.. seealso::
   :meth:`~single_cell_parser.cell_parser.CellParser.insert_range_mechanisms` for an overview of the available spatial profiles for range mechanisms.

All other remaining parameters of a range mechanism must be valid attributes of a NEURON segment, such as passive properties, or parameters defined in ``PARAMETER`` blocks in loaded :ref:`mod_file_format` files. Typically, channels only expose their conductance density as a parameter, but there is nothing stopping you from also exposing e.g. :math:`\tau_m` and :math:`m_\infty`. The simplest range mechanism entry in a neuron parameter file is thus::

  # The range mechanism name, defined as a SUFFIX in a loaded .mod file
  'Ca_LVAst': {
      # non-parametrized profile - simply uses gbar
      'spatial': 'uniform',
      # the conductance density parameter, exposed in the PARAMETER block of the .mod file
      'gCa_LVAstbar': 0.00462
      },

Conductance densities are given in :math:`S/cm^2`, spatial coordinates and distances in :math:`\mu m`, and time in :math:`ms`.


To access different structures of a cell::

    >>> cell_parameters.neuron.keys()
    ['Myelin', 'Soma', 'AIS', 'Dendrite', 'ApicalDendrite']

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
                        "Ih": {
                            "spatial": "exponential",
                            "distance": "relative",
                            "gIhbar": 0.0002,
                            "offset": -0.8696,
                            "linScale": 2.0870,
                            "_lambda": 3.6161,
                            "xOffset": 0.0},
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


.. _network_parameters_format:

Network parameters
==================
The :ref:`param_file_format` format is used to store network parameters, 
describing the presynaptic cells and their synaptic activations.
Only valid with an associated :ref:`morphology_file_format` morphology file, :ref:`syn_file_format` file, and :ref:`con_file_format` file.

For each presynaptic cell type in the network, this following information is provided:

.. list-table:: Network Parameters
   :header-rows: 1

   * - Parameter
     - Description
   * - ``celltype``
     - Spiking type of the presynaptic cell ("spiketrain", or "pointcell").
   * - ``synapses``
     - Additional synapse information (see table below)
   * - ``cellNr``
     - Amount of connected presynaptic cells of this type.

The ``synapses`` key of each presynaptic cell type contains the following information:

.. list-table:: Synapse parameters
   :header-rows: 1

   * - Parameter
     - Description
   * - ``releaseProb``
     - Release probability of this synapse upon a spike of its associated presynaptic cell. 
       A synapse is either active or not active, never inbetween.
   * - ``connectionFile``
     - Reference to an associated :ref:`con_file_format` file for this cell type's synapses.
   * - ``distributionFile``
     - Reference to an associated :ref:`syn_file_format` file for this cell type's synapses.
   * - ``receptors``
     - Dictionary of synapse properties per receptor type (e.g. ``gaba_syn``). Properties are given below.

Each ``synapses.receptors.<receptor type>`` in ``synapses.receptors`` contains the following information:

.. list-table:: Receptor parameters
   :header-rows: 1

   * - Parameter
     - Description
   * - ``delay``
     - Delay between the presynaptic cell activation and the downstream synapse activation in :math:`ms`. Often defaults to :math:`0`.
   * - ``threshold``
     - Threshold of the synapse.
   * - ``weight``
     - Weight of the synapse. 
       Note that excitatory glutamate are :math:`AMPA` and :math:`NMDA` superpositions, and thus require two weights.
   * - ``parameter``
     - Receptor-specific parameters for the synapse dynamics. 
       For example, for an AMPA synapse, this could be the decay time constant, the facilitation, etc.

.. seealso::
  The receptor parameters are used for NEURON's `NetCon <https://www.neuron.yale.edu/neuron/static/py_doc/modelspec/programmatic/network/netcon.html#NetCon>`_.
        
Example::

    {
    "info": {
      "date": "11Feb2015",
      "name": "evoked_activity",
      "author": "name",
    },
    "network": {
      "cell_type_1": {
        "cellNr": 20
        "celltype": {
          'pointcell': {
            'distribution': 'PSTH_poissontrain', 
            'intervals': [(0, 274.7), (274.7, 295), (295, 945), (945, 1145)], 
            'offset': 0.0, 
            'rates': [1.4357770278148136, 1.0890981376857083, 1.7588271630292192, 1.4357770278148136]
          }
        },
        "synapses": {
          "receptors": {
            'glutamate_syn': {
              'delay': 0.0, 
              'parameter': {
                'decayampa': 1.0, 
                'decaynmda': 1.0, 
                'facilampa': 0.0, 
                'facilnmda': 0.0, 
                'tau1': 26.0, 
                'tau2': 2.0, 
                'tau3': 2.0, 
                'tau4': 0.1}, 
              'threshold': 0.0, 
              'weight': [1.5480934081344324, 1.5480934081344324]
              }
          },
          "releaseProb": 0.5,
          "connectionFile": "presyn_cells.con",
          "distributionFile": "syn_locations.syn"
        }
      },
      "cell_type_2": {...},
      ...
    }

.. _activity_data_format:

Activity data
=============
:ref:`param_file_format` files are used to store activity data. Activity data can be defined by the following activity distributions:

.. list-table:: Activity Distributions
    :header-rows: 1

    * - Distribution Type
      - Required Parameters
    * - "normal"
      - "spikeT", "spikeWidth", "offset"
    * - "uniform"
      - "window", "offset"
    * - "lognormal"
      - "mu", "sigma", "offset"
    * - "PSTH"
      - "intervals", "probabilities", "offset"
    * - "PSTH_absolute_number"
      - "intervals", "number_active_synapses", "offset"
    * - "PSTH_poissontrain_v2"
      - "bins", "rates", "offset"
    * - "poissontrain_modulated"
      - "rate_before_t_offset", "mean_rate", "max_modulation", "modulation_frequency", "bin_size", "phase_distribution", "offset"

A single :ref:`activity_data_format` file must specify the activity data for a single cell type, for all anatomical areas.
Anatomical areas can e.g. be columns in the barrel cortex (:math:`A1` - :math:`D4` & :math:`\alpha` - :math:`\delta`), or hippocampal subfields (:math:`CA1` - :math:`CA4`). 
If you do not want to make a distinction between individual anatomical areas in the model system you are using, 
or it simply doesn't make sense to do so, it is fine to set this value to a single area. 
In that case, the parameter file below would contain only one entry.

Example::

    {
    "celltypeA_area1": {
    "distribution": "PSTH",
    "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
    "probabilities": [-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,0.0062,-0.0004,0.0129,0.0062,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,0.0062,0.0062,-0.0004,-0.0004,-0.0004],
    },
    "celltypeA_area2": {
    "distribution": "PSTH",
    "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
    "probabilities": [-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,0.0129,0.0062,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,0.0062,-0.0004,-0.0004,-0.0004,-0.0004,-0.0004],
    },
    "celltypeA_area3": {
    "distribution": "lognormal",
    "mu": 1.0,
    "sigma": 0.5,
    "offset": 15
    }
    "celltypeA_area4": {
    "distribution": "uniform",
    "offset": 140,
    "window": 50,
    "activeFrac": 0.8,
    }
    ...
    }

.. seealso::
  :meth:`~singlecell_input_mapper.network_param_builder.NetworkParamBuilder.add_activity`


.. _ongoing_activity_data_format:

Ongoing activity data
*********************
In addition to :ref:`activity_data_format`, ISF provides additional API for ongoing activity separately.
Ongoing activity is modeled as a Poisson spiketrain with a certain interval.

The data format should be a two-column ``.csv`` table. The column names are ignored, and only present for clarity.
The first column must be the cell type. This may include the anatomical area as a suffix, but does not need to.

.. list-table:: Ongoing activity example data format
   :header-rows: 1

   * - Cell type	
     - Ongoing firing interval (ms)
   * - celltype1	
     - 909.1
   * - celltype2
     - 2173.9
   * - celltype3
     - 142.9
   * - celltype4
     - 3225.8
   * - celltype5
     - 142.9
   * - celltype6
     - 142.9
   * - ...
     - ..

  
.. note::
   While you can specify the anatomical area as a suffix for each cell type, the default behavior of ISF is to asusme this is not the case, and
   ongoing activity is defined per cell type, independent of the anatomical area.
   If you do need per-area specificity in the ongoing activity, consult the arguments of the corresponding :ref:`network_parameters_format` builder function.

.. seealso::
   :meth:`~singlecell_input_mapper.network_param_builder.NetworkParamBuilder.add_ongoing_activity`



.. _simresult_dir_format:

Raw simulation results
**********************

Simulations run by :mod:`simrun` have a fixed folder structure. They contain a single file of somatic :ref:`voltage_traces_format`,
one file of dendritic :ref:`voltage_traces_format` per ``recSite`` found in the :ref:`cell_parameters_format`, and a collection of :ref:`syn_activation_format` and
:ref:`spike_times_format` files. 

The voltage traces are written to a single ``.csv`` file (since the amount of timesteps is known in advance, at least for non-variable timesteps),
but the synapse and cell activation data is written to a separate file for each simulation trial (the amount 
of spikes and synapse activations is not known in advance).

The amount of simulation runs per parameter configuration (i.e. the product of :param:`~simrun.run_new_simulations.run_new_simulations.nSweeps` 
and :param:`~simrun.run_new_simulations.run_new_simulations.nprocs` keyword arguments in any simrun function) corresponds
to:

- The amount of voltage columns in the :ref:`voltage_traces_format` files
- The amount of :ref:`syn_activation_format` files
- The amount of :ref:`spike_times_format` files

Example:

.. code-block:: shell

  user@host:/path/to/results/20241212-1542_seed379159821_pid209402$ ls | column
  hostname_somacpu042
  seed379159821_pid209402_network_model.param
  seed379159821_pid209402_neuron_model.param
  seed379159821_pid209402_pos_3_ID_000_sec_073_seg_000_x_0.056_somaDist_607.8_vm_dend_traces.csv
  seed379159821_pid209402_pos_3_ID_001_sec_073_seg_008_x_0.944_somaDist_805.7_vm_dend_traces.csv
  seed379159821_pid209402_vm_all_traces.csv
  simulation_run0000_presynaptic_cells.csv
  simulation_run0000_synapses.csv
  simulation_run0001_presynaptic_cells.csv
  simulation_run0001_synapses.csv
  simulation_run0002_presynaptic_cells.csv
  simulation_run0002_synapses.csv
  simulation_run0003_presynaptic_cells.csv
  simulation_run0003_synapses.csv
  simulation_run0004_presynaptic_cells.csv
  simulation_run0004_synapses.csv


.. seealso::
  The :mod:`simrun` functions used to produce these simulation results:

  - :mod:`simrun.run_new_simulations`
  - :mod:`simrun.rerun_db`

.. seealso::
  To get a :class:`~single_cell_parser.cell.Cell` object from such a simulation, refer to :mod:`simrun.sim_trial_to_cell_object`


Dataframes
**********

The output format of various simulation pipelines are usually a dataframe. below, you find common formats used throughout ISF.

The :mod:`simrun` package produces output files in ``.csv`` or ``.npz`` format. many of these files
need to be created for each individual simulation trial. 
These :ref:`simresult_dir_format` are usually parsed into single dataframes for further analysis using a ``db_initializers`` submodule (see e.g. 
:mod:`~data_base.db_initializers.load_simrun_general`).


.. _syn_activation_format:

Synapse activation
==================

The raw output of the :mod:`simrun` package contains ``.csv`` files containing the synaptic activations onto a post-synaptic cell 
for each individual simulation trial. Each file contains the following information for each synapse during a particular simulation trial:

- type
- ID (for identifying the corresponding presynaptic cell)
- location (section ID, section pt ID, soma distance)
- dendrite label (e.g. ``"ApicalDendrite"``)
- activation times

These individual files are usually gathered and parsed into a single dataframe containing all trials for further analysis:
An example of the raw and parsed format is shown below:

Raw :mod:`simrun` output
---------------------------

.. list-table:: Synapse activations (single trial)
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
      - 10.2
      - 80.5
      - 140.8
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
      - 300.1
      - 553.5
      - 

Parsed dataframe
----------------

.. list-table:: Synapse activations (all trials)
    :header-rows: 1

    * - trial index
      - synapse type
      - synapse ID
      - soma distance
      - section ID
      - section pt ID
      - dendrite label
      - 1
      - 2
      - 3
    * - 0
      - presyn_cell_type_1
      - 0
      - 150.0
      - 24
      - 0
      - 'basal'
      - 10.2
      - 80.5
      - 140.8
    * - 0
      - presyn_cell_type_2
      - 1
      - 200.0
      - 112
      - 0
      - 'apical'
      - 100.2
      - 
      - 
    * - 1
      - presyn_cell_type_1
      - 0
      - 150.0
      - 24
      - 0
      - 'basal'
      - 10.2
      - 140.8
      - 
    * - 1
      - presyn_cell_type_2
      - 1
      - 200.0
      - 112
      - 0
      - 'apical'
      - 100.2
      - 138.4
      - 

.. attention::

   Not every spike of a presynaptic cell necessarily induces a synapse activation. Each synapse has a specific release
   probability and delay (see :ref:`network_parameters_format`).
   For this reason, the spike times of the presynaptic cells is saved separately (see :ref:`spike_times_format`).

.. _spike_times_format:

Presynaptic spike times
=======================
The raw output of the :mod:`simrun` package contains ``.csv`` files containing the spike times of presynaptic cells 
for each individual simulation trial. Each file contains the following information for each synapse during a particular simulation trial:

- type
- ID (for identifying the corresponding synapse, and cell location)
- activation times

These individual files are usually gathered and parsed into a single dataframe containing all trials for further analysis
An example of the raw and parsed format is shown below:

Raw :mod:`simrun` output
---------------------------

.. list-table:: Presynaptic spike times (single trial)
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


Parsed dataframe
----------------

.. list-table:: Presynaptic spike times (all trials)
    :header-rows: 1

    * - trial index
      - cell type
      - cell ID
      - 1
      - 2
      - 3
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

- :func:`~single_cell_parser.io.activity.write_presynaptic_spike_times` is used by :mod:`simrun` and :mod:`~single_cell_parser.analyze.synanalysis`
   to write raw output data.
- :func:`data_base.db_initializers.load_simrun_general.init` parses these files into a pandas dataframe.

.. attention::

   Not every spike of a presynaptic cell necessarily induces a synapse activation. Each synapse has a specific release
   probability and delay (see :ref:`network_parameters_format`).
   For this reason, the synapse activations are saved separately (see :ref:`syn_activation_format`).

.. _voltage_traces_format:

Voltage traces
==============

The raw output of the :mod:`simrun` package contains ``.npz`` or ``.csv`` files containing the voltage traces of the postsynaptic cells.
Unlike the synapse activations and spike times, it is possible for one such file to contain multiple trials.

.. _voltage_traces_csv_format:

Voltage trace ``.csv``
----------------------

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

Voltage trace ``.npz``
----------------------

``vm_all_traces.npz``::

    array([[100.0, 100.025, 100.05, 100.075],
           [-61.4607218758, -61.4665809176, -61.4735021526, -61.4814187507],
           [-55.1366909604, -55.1294343391, -55.1223216173, -55.1153403448],
           [-67.1747143695, -67.1580037786, -67.1424366078, -67.1279980017]])

.. _voltage_traces_df_format:

Voltage trace dataframe
-----------------------

The parsed dataframe is usually created by the :func:`data_base.db_initializers.load_simrun_general.init` function.

.. list-table:: ``voltage trace dataframe``
   :header-rows: 1

   * - ``sim_trial_index``
     - 0.000
     - 0.025
     - 0.050
     - 0.075
     - ...
   * - trial_0
     - -75.0 
     - -75.017715 
     - -75.033995 
     - -75.04979
     - ...
   * - trial_1
     - -75.0
     - -75.017722
     - -75.034002
     - -75.049797
     - ...



.. _morphology_file_format:

Morphology
**********

ISF supports two file formats for morphologies:

- A :ref:`hoc_file_format` file format
- The :ref:`swc_file_format` file format

.. _hoc_file_format:

.hoc
====
NEURON :cite:`hines2001neuron` file format for scripting in ``.hoc``.

The :ref:`hoc_file_format` format is used for HOC scripts.
HOC scripts support a variety of commands and integrate directly with NEURON.
Throughout ISF, you may find some example morphologies using the HOC scripting language to define morphology.
These only use a subset of :ref:`hoc_file_format` commands.
The information contained in this subset of HOC commands is nearly identical to the information that can be specified in :ref:`swc_file_format`. 
The only information that this :ref:`hoc_file_format` subset can capture, that cannot be captured the same way in :ref:`swc_file_format`, is the connection coordinate between two sections.
:ref:`hoc_file_format` allows the definition of a connection between two sections as a continuous coordinate, even if this coordinate lands between two points. 
:ref:`swc_file_format` defines connectivity in terms of point ID, and so every connection in :ref:`swc` necessarily connects to a point, not in-between points.
For most use-cases, this difference is trivial, since sections are generally defined as a neurite between connection points, and so every connection point is at relative coordinate ``x=0`` or ``x=1`` anyways.
One notable exception is the soma, where sections are sometimes allowed to connect at a relative coordinate that deviates from ``0`` and ``1``.
Even then, ISF by default connects child sections to the soma at ``x=0.5`` anyways, so this information is not used in ISF.

.. seealso::
   :attr:`~single_cell_parser.cell_parser.CellParser.spatialgraph_to_cell.force_connect_soma_halfway` is ``True`` by default, meaning the default behavior of ISF is to connect direct
   descendants of the soma at ``x=0.5``.

The subset of :ref:`hoc_file_format` used in ISF for morphologies specifies (for each morphology section):

- The section name in a standardized format: ``<label>_<child_idx>``
- The :math:`(x, y, z)` coordinates of each point per section
- The diameter of each point per section
- To which parent section each section connects, and where

Each section name follows the naming convention ``<label>_<child_idx>``, where the ``label``
contains both a label name, and an index tracking how many sections of this label exist.
For this reason, the label index starts at ``1``. The ``<child_idx>`` denotes the index of each child
section that starts from this label. For example, the very first part of the first section of type ``"Dendrite"``
will look like: ``"Dendrite_1_0"``. Here, the ``1`` denotes there are so far only 1 instances of a section with label ``"Dendrite"``
All child sections of this section will start with the same string, e.g. ``"Dendrite_1_0_1_0"`` is the first child of ``"Dendrite_1_0_1"``,
which is in turn the second child of ``"Dendrite_1_0"``. Other sections with the same label that are not children of ``"Dendrite_1_0"`` will e.g.
look like ``"Dendrite_2_0*"`` or ``"Dendrite_3_0*"`` etc.

Connectivity between sections is defined by a line::

  {connect <label>_<child_idx>(x1), <parent_label>(x2)}

This defines how the current section ``<label>_<child_idx>`` connects to its parent section.
``x1`` and ``x2`` denote the relative coordinates of the connection between both sections.
``x1`` denotes where along the current section the connections occurs. Normally, ``x1`` always equals ``0``, meaning the connection point is at the start of the current section.
``x2`` denotes where along the parent section the connection occurs. This almost always equals ``1`` (meaning the connection is at the end of the parent section), since sections are
almost always defined as a piece of neurite between two connection points. A notable example is the soma; sections may (and often do) connect at
different points on the soma, and not always at the end: ``Soma(1.0)``.

.. seealso::
  Refer to the `NEURON hoc documentation <https://nrn.readthedocs.io/en/latest/guide/hoc_chapter_11_old_reference.html>`_ for more info.

.. seealso::
  :meth:`~single_cell_parser.io.morphology.convert_hoc_to_swc` for a converter from :ref:`hoc_file_format` to :ref:`swc_file_format`.

Readers:

- :mod:`~single_cell_parser.cell_parser`
- :func:`~single_cell_parser.io.morphology.hoc.read_hoc`

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

.. _swc_file_format:

.swc
====
SWC (Stockley-Wheal-Cannon) is a simple morphology file format, specifying for each point the:

- Point ID
- Section type
- :math:`(x, y, z)` coordinates
- Radius
- Parent point ID

Connectivity between sections is inferred simply based on the parent point ID.
If the point ID is not consecutive, a new section starts.
If more than 1 other point refer to the same point ID, a new section starts.

Section types in :ref:`swc_file_format` follow a fixed integer convention:

.. list-table::
   
   * - 1
     - "Soma"
   * - 2
     - "Axon"
   * - 3
     - "Dendrite"
   * - 4
     - "ApicalDendrite"
   * - 5
     - "Custom"
   * - 6
     - "Unspecified"
   * - 7
     - "Glial process"
   * - >7
     - "Custom"


Readers:

- :mod:`~single_cell_parser.cell_parser`
- :func:`~single_cell_parser.io.morphology.swc.read_swc`

.. seealso::
  Consult https://swc-specification.readthedocs.io/en/latest/swc.html
  for the official documentation on SWC.

.. seealso::
  :meth:`~single_cell_parser.io.morphology.convert_swc_to_hoc` for a converter from :ref:`swc_file_format` to :ref:`hoc_file_format`


Example::

    # pID type  x             y           z           r        parent ID     
    1     1     -126.687302   397.872009  -379.372986 2.542405 -1
    2     1     -126.425797   397.434021  -379.303009 2.801655  1
    3     1     -126.164299   396.996002  -379.234009 3.0609    2
    4     1     -125.9506     396.481995  -379.165985 3.295415  3
    ...
    43    1     -111.478897   383.348022 -378.470001  4.131965  42
    44    1     -111.100601   383.018005 -378.457001  3.47198   43
    45    3     -128.1241     390.917023 -377.123993  0.62      8
    46    3     -126.512604   390.572998 -377.480988  0.62      45
    ...


.. _mod_file_format:

.mod
****
``MODL`` is a file format Used to define dynamical systems as simply as reasonably possible.
NEURON :cite:t:`hines2001neuron` provides an extension to this format called ``NMODL``, in this
case to define channel and synapse dynamics for use in NEURON simulations.
NEURON translates these files to ``C`` (and to ``C++`` since NEURON 9.0), to be compiled to machine code on the host machine.

``NMODL`` files are categorized in blocks. 
We highlight some important ones below:

.. list-table::

  * - NEURON
    - NEURON :cite:t:`hines2001neuron` specific specification, such as ``READ`` and ``WRITE`` statements, 
      defining which global variables this particular mechanism needs access to (e.g. intracellular :math:`Ca^{2+}` for :math:`Ca^{2+}`-activated channels).
      The mechanism's name is defined as either a ``SUFFIX`` or ``POINTPROCESS`` in this block.
      This is the name that will be accessible by the user, and how NEURON will register it in the NEURON or Python namespace.
  * - PARAMETER
    - Free parameters used in this mechanism. 
      These are the parameters the user has direct access to, and can be tweaked during optimization or exploration.
  * - STATE
    - State variables. 
      These are the time-dependent variables in the differential equations defining the system.
  * - BREAKPOINT
    - Main computation block. 
      This will be evaluated every timestep. Configures what to solve, and which solver to use.
  * - DERIVATIVE
    - If the dynamical system is governed by differential equations, they are defined here.
  * - PROCEDURE
    - A set of instructions that can be named. 
      This is the NMODL equivalent of defining a function. 
      This is often used to define the equations of the dynamical system, or the most verbose aspects of it. 
      That way, the DERIVATIVE block can use human-readable variable names.


Example:

.. code-block:: NMODL

  :Reference : :		Adams et al. 1982 - M-currents and other potassium currents in bullfrog sympathetic neurones

  NEURON {
    : Name of this mechanism, defined as a SUFFIX
    : For localized mechanisms (e.g. a single synapse), POINTPROCESS is used to name the mechanism
    SUFFIX Im
    : Uses the ion Potassium (k), needs read access to the potassium reversal potential (ek), writes out potassium current (ik)
    USEION k READ ek WRITE ik
    : Range variables - can be recorded by the user. These should also appear in PARAMETER or ASSIGNED
    RANGE gImbar, gIm, ik
  }

  UNITS	{
    (S) = (siemens)
    (mV) = (millivolt)
    (mA) = (milliamp)
  }

  PARAMETER {
    : Free parameters. 
    : Everything defined here will be accessible and tunable by the user.
    : These are the ones e.g. optimized or explored.
    gImbar = 0.00001 (S/cm2) 
  }

  ASSIGNED {
    v	(mV)
    ek	(mV)
    ik	(mA/cm2)
    gIm	(S/cm2)
    mInf
    mTau
    mAlpha
    mBeta
  }

  STATE { 
    : The time-dependent gating variable. This channel only has one.
    m
  }

  : What to calculate each time step
  BREAKPOINT {
    : Solve the DERIVATIVE block named "states"
    : Use `cnexp` (Crank-Nicolson, exponential)
    : For more info, see https://www.neuronsimulator.org/en/latest/nmodl/transpiler/notebooks/nmodl-sympy-solver-cnexp.html#Implementation
    SOLVE states METHOD cnexp
    : Calculate the conductance of the Im current = conductance density * gating variable
    gIm = gImbar*m
    : Calculate the Im current from the conductance
    ik = gIm*(v - ek)
  }

  : The ODEs defining the dynamical system. We name it "states". Not to be confused with the "STATE" block.
  DERIVATIVE states {
    : Run the procedure named "rates" - evaluate mInf and mTau based on the current value of voltage
    rates(v)
    : Define the gating variable time dependency - linear first-order ODE
    m' = (mInf-m) / mTau
  }

  INITIAL {
    : Run the procedure named "rates" - evaluate mInf and mTau based on the current value of voltage
    rates(v)
    : Set the initial value of m to mInf i.e. the value of m if t -> inf for the current voltage
    m = mInf
  }

  PROCEDURE rates(v) {
    : Simple procedure named "rates"
    : Calculates mTau and mInf, used in the DERIVATIVE block
    UNITSOFF
      mAlpha = 3.3e-3*exp(2.5*0.04*(v - -35))
      mBeta = 3.3e-3*exp(-2.5*0.04*(v - -35))
      mInf = mAlpha / (mAlpha + mBeta)
      mTau = 1 / (mAlpha + mBeta)
    UNITSON
  }



.. seealso::
   Refer to the `NEURON NMODL documentation <https://www.neuronsimulator.org/en/9.0.0/nmodl/language/nmodl.html>`_,
   `compneuro <https://neuronline.github.io/compneuro/software/neuron/nmodl/>`_, 
   or :cite:t:`hines2001neuron` (chapters 9 and 10) for more info on ``BLOCKS`` and their meaning, usage, or any other
   aspect of MODL/NMODL.

.. seealso::
   See the folder `mechanisms` in the project source for convenience methods for compiling mechanisms or checking
   if they exist in the NEURON namespace.







.. _am_file_format:

.am
***

The Amira proprietary VTK-like file format. Refer to the `amira documentation <https://assets.thermofisher.com/TFS-Assets/MSD/Product-Guides/users-guide-amira-software-2019.pdf>`_ for more information.
This flexible format can be used to store 3D scalar meshes, 3D neuron morphology reconstructions, slice image data etc.

Readers:

- :mod:`~single_cell_parser.io.amira.read_scalar_field`
- :mod:`~single_cell_parser.io.amira.read_landmark_file`


.. container:: doc-feedback

  Documentation unclear, incomplete, broken or wrong? `Let us know <https://github.com/mpinb/in_silico_framework/issues/new?template=documentation.md&labels=docs>`_

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
"""Top-level pipeline to map synapses onto a postsynaptic cell according to :cite:t:`Udvary_Harth_Macke_Hege_De_Kock_Sakmann_Oberlaender_2022`.

This module provides a full pipeline for creating dense connectome models
of the rat barrel cortex, based on methods and data presented in 
:cite:t:`Udvary_Harth_Macke_Hege_De_Kock_Sakmann_Oberlaender_2022` and :cite:t:`Egger_Dercksen_Udvary_Hege_Oberlaender_2014`.

This runfile assumes you have downloaded and extracted the barrel cortex model data from
https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/JZPULNa.
If this is not the case, please consult ``installer/download_bc_model`` and extract.

Attention:
    This file is specific to the barrel cortex model data. If you want to use it for other data,
    you need to adapt the paths to the data accordingly. This runfile can serve as a template.

Inputs:

- Morphology of the postsynaptic neuron
- 3D density field of synapses across the entire neuropil.
- Number of cells per cell type in the neuropil.
- Connections spreadsheet containing Post-Synaptic Targets (PSTs) per unit of length and area
- Bouton locations of individual axon tracings per presynaptic cell type.

Attention:
    This runfile has default values for the barrel cortex, and so assumes that you have downloaded 
    and extracted the barrel cortex model data from
    https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/JZPULNa.
    If this is not the case, please consult ``installer/download_bc_model`` and extract,
    or adapt the paths in this file to your data.

This module then uses :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`
to assign synapses to a single post-synaptic cell morphology, based on the inputs mentioned above.
This happens according to the following pipeline:

1. The bouton density field and PST density fields are converted to scalar fields with defined voxel resolution.
2. Calculates the overlap between these voxels and the dendrites of the postsynaptic neuron morphology 
   using Liang-Barsky clipping :cite:`liang1984new`. Only these voxels are further considered for potential synapses.
3. Calculates a synapse density field by multiplying the bouton density field with the PST density fields
   at these voxels.
4. Normalizes the previous synapse density fields using cell-type specific PST length/area constraints and the number of 
   cells per cell type.
5. Poisson samples synapses from this normalized synapse density field to realize synapses. 
   These are randomly placed onto the dendritic branch within that voxel. One such sample is called an "anatomical realization".
6. (optional) Repeat steps 4 and 5 to create a collection of anatomical realizations. 

Density meshes are accessed using :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`.
:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper` makes use of 
:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseDensity` for steps 2, 3 and 4,
and finalizes step 5 by itself.

Primary output:

- Synapse location (:ref:`syn_file_format`) and connectivity (:ref:`con_file_format`) file compatible with ISF.

Additional outputs:

- summary file containing information about number and presynaptic type
  and column of anatomical synapses
- AmiraMesh landmark file containing 3D synapse locations of anatomical
  synapses of each presynaptic type and column
"""

from __future__ import absolute_import
from .reader import *
from .writer import *
from .network_embedding import *
from .synapse_mapper import *
from .scalar_field import *
from .cell import CellParser
import glob
import logging
import os.path
import sys
import time

import getting_started

from config.user.cell_types import EXCITATORY, INHIBITORY
from config.user.network_connectivity import DATA_REQS_UDVARY2022

__author__ = "Robert Egger"

logger = logging.getLogger("ISF").getChild(__name__)


def map_singlecell_inputs(
    cellName,
    cellTypeName,
    nrOfSamples=50,
    numberOfCellsSpreadsheetName=None,
    connectionsSpreadsheetName=None,
    ExPSTDensityName=None,
    InhPSTDensityName=None,
    boutonDensityFolderName=None,
):
    r"""Map inputs to a single cell morphology.

    These inputs need to be organized per anatomical structure. Anatomical structures
    can be arbitrary spatial regions of the brain tissue, or anatomically well-defined
    areas, e.g. barrels in a barrel cortex.

    Steps:

    1. Loads in the data:

        - Cell morphology
        - Number of cells per cell type
        - Connection probabilities between cell types
        - PST densities for normalization of innervation calculations

    2. Loads in the bouton densities:

        - For each anatomical area
        - For each presynaptic cell type

    3. Creates a :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField` for each bouton density.
    4. Creates a :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper` object.
    5. Creates a network embedding for the cell using :func:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper.create_network_embedding`.

    The naming of each anatomical area needs to be consistent between:

    - The number of cells per cell type spreadsheet
    - The bouton folders containing axon traces

    Args:
        cellName (str):
            path to a :ref:`hoc_file_format` file containing the morphology of the cell.
        cellTypeName (str):
            name of the postsynaptic cell type.
        nrOfSamples (int):
            number of samples to use for the network embedding.
        numberOfCellsSpreadsheetName (str):
            Path to the a spreadsheet, containing each neuropil structures as columns, and celltypes row indices.
            Values indicate how much of each celltype was found in each neuropil structure.
        connectionsSpreadsheetName (str):
            Path to a spreadsheet, containing the connection probabilities between each presynaptic and postsynaptic cell type.
        ExPSTDensityName (str):
            Path to the PST density file for excitatory synapses.
        InhPSTDensityName (str):
            Path to the PST density file for inhibitory synapses.
        boutonDensityFolderName:
            A directory containing the following subdirectory structure:
            anatomical_area/presynaptic_cell_type/\*.am

    Returns:
        None. 
            Writes the results to disk, at the same location as the input :param:`cellName`.
            Results consist of a :ref:`syn_file_format`, :ref:`conf_file_format` file, and a ``.csv`` file containing the amount of connected 
            presynaptic cells per cell type, and per anatomical area.
    """
    if not (cellTypeName in EXCITATORY) and not (cellTypeName in INHIBITORY):
        errstr = "Unknown cell type %s!"
        raise TypeError(errstr)

    if numberOfCellsSpreadsheetName == None:
        logger.info("No numberOfCellsSpreadsheetName passed. Falling back to user-configured one.")
        try: numberOfCellsSpreadsheetName = str(DATA_REQS_UDVARY2022["numberOfCellsSpreadsheetName"])
        except KeyError as e: raise RuntimeError("No numberOfCellsSpreadsheetName configured in user configuration. Aborting... ") from e
    if connectionsSpreadsheetName == None:
        logger.info("No connectionsSpreadsheetName passed. Falling back to user-configured one.")
        try: connectionsSpreadsheetName = str(DATA_REQS_UDVARY2022["connectionsSpreadsheetName"])
        except KeyError as e: raise RuntimeError("No connectionsSpreadsheetName configured in user configuration. Aborting... ") from e
    if ExPSTDensityName == None:
        logger.info("No ExPSTDensityName passed. Falling back to user-configured one.")
        try: ExPSTDensityName = str(DATA_REQS_UDVARY2022["ExPSTDensityName"])
        except KeyError as e: raise RuntimeError("No ExPSTDensityName configured in user configuration. Aborting... ") from e
    if InhPSTDensityName == None:
        logger.info("No InhPSTDensityName passed. Falling back to user-configured one.")
        try: InhPSTDensityName = str(DATA_REQS_UDVARY2022["InhPSTDensityName"])
        except KeyError as e: raise RuntimeError("No InhPSTDensityName configured in user configuration. Aborting... ") from e
    if boutonDensityFolderName == None:
        logger.info("No boutonDensityFolderName passed. Falling back to user-configured one.")
        try: boutonDensityFolderName = str(DATA_REQS_UDVARY2022["boutonDensityFolderName"])
        except KeyError as e: raise RuntimeError("No boutonDensityFolderName configured in user configuration. Aborting... ") from e

    start_t_sec_total = time.time()

    logger.info("Loading cell morphology")
    parser = CellParser(cellName)
    parser.spatialgraph_to_cell()
    singleCell = parser.get_cell()  # This is a sim.Cell, not scp.cell
    logger.debug("Cell morphology loaded")

    # --------------------- Read in data ---------------------
    logger.info("Loading spreadsheets and bouton/PST densities...")

    logger.info("    Loading numberOfCells spreadsheet {:s}".format(numberOfCellsSpreadsheetName))
    numberOfCellsSpreadsheet = read_celltype_numbers_spreadsheet(numberOfCellsSpreadsheetName)
    logger.debug("    numberOfCells spreadsheet loaded".format(numberOfCellsSpreadsheetName))

    logger.debug("    Loading connections spreadsheet {:s}".format(connectionsSpreadsheetName))
    connectionsSpreadsheet = read_connections_spreadsheet(connectionsSpreadsheetName)
    logger.debug("    Connections spreadsheet loaded")

    logger.debug("    Loading PST density {:s}".format(ExPSTDensityName))
    ExPSTDensity = read_scalar_field(ExPSTDensityName)
    ExPSTDensity.resize_mesh()
    logger.debug("    PST density {:s} loaded".format(ExPSTDensityName))
    logger.debug("    Loading PST density {:s}".format(InhPSTDensityName))
    InhPSTDensity = read_scalar_field(InhPSTDensityName)
    InhPSTDensity.resize_mesh()


    boutonDensities = {}
    anatomical_areas = list(numberOfCellsSpreadsheet.keys())
    preCellTypes = numberOfCellsSpreadsheet[anatomical_areas[0]]

    # --------------------- Load bouton densities ---------------------
    logger.info("    Loading bouton densities from folder {:s} (may take a while)".format(boutonDensityFolderName))
    bouton_start = time.time()
    boutonDensities = read_bouton_densities_per_area_per_ct(
        dirname=boutonDensityFolderName,
        anatomical_areas=anatomical_areas,
        cell_types=preCellTypes
    )
    logger.info("    Loaded bouton densities in {:.2f} s".format(time.time() - bouton_start))

    # Actually create the network embedding
    inputMapper = NetworkMapper(
        postCell=singleCell,
        postCellType=cellTypeName,
        cellTypeNumbersSpreadsheet=numberOfCellsSpreadsheet,
        connectionsSpreadsheet=connectionsSpreadsheet,
        exPST=ExPSTDensity,
        inhPST=InhPSTDensity,
    )
    inputMapper.exCellTypes = EXCITATORY
    inputMapper.inhCellTypes = INHIBITORY

    logger.info("Creating network embedding for  {:s}".format(cellName))
    inputMapper.create_network_embedding(cellName, boutonDensities, nrOfSamples=nrOfSamples)

    # Record time and write summary
    end_t_sec_total = time.time()
    duration = (end_t_sec_total - start_t_sec_total) / 60.0
    logger.info("Runtime: {:.1f} minutes".format(duration))

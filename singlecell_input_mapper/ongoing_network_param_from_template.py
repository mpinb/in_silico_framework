#!/usr/bin/python
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

"""
Create a network parameter template file.
"""

import sys
import single_cell_parser as scp
from data_base.dbopen import dbopen
import logging
from .reader import read_cell_number_file

logger = logging.getLogger("ISF").getChild(__name__)


def create_network_parameter(
    templateParamName,
    cellNumberFileName,
    synFileName,
    conFileName,
    outFileName,
    write_all_celltypes=False
    ):
    """Create a template :ref:`network_parameters_format` file containing ongoing activity data for a given network embedding.
    
    The parameter file defines the PSTHs for each cell type under some in vivo condition. 
    In the template, ongoing activity is set as a default value for each cell type.
    The network parameter file converts the PSTHs to firing rates in fixed temporal bins, and adds the following information:
    
    - synapse types
    - mechanisms
    - dynamics
    - release probabilities
        
    Args:
        templateParamName (str): 
            Name of the template param containing the PSTHs for each cell type. 
            These can be generated from .cluster files of spike time recordings by e.g. :func:`~singlecell_input_mapper.evoked_PSTH_from_spike_times.create_average_celltype_PSTH_from_clusters`.
        cellNumberFileName (str):
            Name of the file containing the amount of cells per column in the barrel cortex.
        synFileName (str): 
            Name of the `.syn` file, defining the synapse types.
        conFileName (str): 
            Name of the `.con` file, defining the connections.
        outFileName (str): 
            Name of the output file.
        write_all_celltypes (bool): 
            Whether to write out parameter information for all cell types, even if they do not spike during the configured experimental condition.
    
    """
    logger.info('*************')
    logger.info('creating network parameter file from template {:s}'.format(templateParamName))
    logger.info('*************')

    templateParam = scp.build_parameters(templateParamName)
    cellTypeColumnNumbers = read_cell_number_file(cellNumberFileName)

    ongoing_netp = scp.NTParameterSet({
        'info': templateParam.info,
        'NMODL_mechanisms': templateParam.NMODL_mechanisms,
        'network': {}
    })

    for anatomical_area in list(cellTypeColumnNumbers.keys()):
        template_netp = templateParam.network[anatomical_area]
        for column in list(cellTypeColumnNumbers[anatomical_area].keys()):
            numberOfCells = cellTypeColumnNumbers[anatomical_area][column]
            if numberOfCells == 0 and not write_all_celltypes:
                continue
            cell_type_name_full = anatomical_area + '_' + column
            ongoing_netp.network[cell_type_name_full] = template_netp.tree_copy()
            ongoing_netp.network[cell_type_name_full].cellNr = numberOfCells
            ongoing_netp.network[cell_type_name_full].synapses.distributionFile = synFileName
            ongoing_netp.network[cell_type_name_full].synapses.connectionFile = conFileName

    ongoing_netp.save(outFileName)
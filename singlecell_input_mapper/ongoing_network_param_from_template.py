#!/usr/bin/python
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

"""
Create a network parameter template file.
"""

import sys
import single_cell_parser as scp
from data_base.dbopen import dbopen


def create_network_parameter(
    templateParamName,
    cellNumberFileName,
    synFileName,
    conFileName,
    outFileName,
    write_all_celltypes=False
    ):
    """Create a template :ref:`network_parameters_format` file from a template parameter file and a cell number file.
    
    The parameter file defines the PSTHs for each cell type under some in vivo condition. For the template, ongoing activity is set as a default value for each cell type.
    The network parameter file converts the PSTHs to firing rates in fixed temporal bins, and adds the following information:
    
    - synapse types
    - mechanisms
    - dynamics
    - release probabilities
        
    Args:
        templateParamName (str): 
            Name of the template param containing the PSTHs for each cell type. 
            These can be generated from .cluster files of spike time recordings by e.g. :py:meth:`~singlecell_input_mapper.evoked_PSTH_from_spike_times.create_average_celltype_PSTH_from_clusters`.
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
    print('*************')
    print('creating network parameter file from template {:s}'.format(
        templateParamName))
    print('*************')

    templateParam = scp.build_parameters(templateParamName)
    cellTypeColumnNumbers = load_cell_number_file(cellNumberFileName)

    nwParam = scp.NTParameterSet({
        'info': templateParam.info,
        'NMODL_mechanisms': templateParam.NMODL_mechanisms
    })
    #    nwParam.info = templateParam.info
    #    nwParam.NMODL_mechanisms = templateParam.NMODL_mechanisms
    nwParam.network = {}

    for cellType in list(cellTypeColumnNumbers.keys()):
        cellTypeParameters = templateParam.network[cellType]
        for column in list(cellTypeColumnNumbers[cellType].keys()):
            numberOfCells = cellTypeColumnNumbers[cellType][column]
            if numberOfCells == 0 and not write_all_celltypes:
                continue
            cellTypeName = cellType + '_' + column
            nwParam.network[cellTypeName] = cellTypeParameters.tree_copy()
            nwParam.network[cellTypeName].cellNr = numberOfCells
            nwParam.network[
                cellTypeName].synapses.distributionFile = synFileName
            nwParam.network[cellTypeName].synapses.connectionFile = conFileName

    nwParam.save(outFileName)


def load_cell_number_file(cellNumberFileName):
    """Load the cell number file.
    
    The cell number file must have the following format::
    
        Anatomical_area Presynaptic_cell_type   n_cells
        A1	cell_type_1	8
        A1	cell_type_2	14
        ...

    Args:
        cellNumberFileName (str): Path to the cell number file.
        
    Returns:
        dict: Dictionary of the form {celltype: {column: nr_of_cells}}
        
    Example:
        >>> load_cell_number_file(
        ...    'getting_started/example_data/anatomical_constraints/'
        ...    'example_embedding_86_C2_center/'
        ...    'NumberOfConnectedCells.csv'
        ...    )
        {
            'L4py': {
                'A1': 8, 
                'A2': 1, 
                'A3': 7, 
                'A4': 3, 
                'Alpha': 9, 
                'B1': 72, 
                'B2': 30, 
                'B3': 97, 
                'B4': 30, 
                'Beta': 0, 
                'C1': 59, 
                'C2': 374, 
                'C3': 88, 
                'C4': 3, 
                'D1': 22, 
                'D2': 89, 
                'D3': 59, 
                'D4': 0, 
                'Delta': 0, 
                'E1': 0, 
                'E2': 0, 
                'E3': 0, 
                'E4': 0, 
                'Gamma': 16}, 
                'L6cc': {...}, 
                ...    
    """
    cellTypeColumnNumbers = {}
    with dbopen(cellNumberFileName, 'r') as cellNumberFile:
        lineCnt = 0
        for line in cellNumberFile:
            if line:
                lineCnt += 1
            if lineCnt <= 1:
                continue
            splitLine = line.strip().split('\t')
            column = splitLine[0]
            cellType = splitLine[1]
            numberOfCells = int(splitLine[2])
            if cellType not in cellTypeColumnNumbers:
                cellTypeColumnNumbers[cellType] = {}
            cellTypeColumnNumbers[cellType][column] = numberOfCells

    return cellTypeColumnNumbers


if __name__ == '__main__':
    if len(sys.argv) == 5:
        templateParamName = sys.argv[1]
        cellNumberFileName = sys.argv[2]
        synFileName = sys.argv[3]
        #        conFileName = sys.argv[4]
        conFileName = synFileName[:-4] + '.con'
        outFileName = sys.argv[4]
        create_network_parameter(templateParamName, cellNumberFileName,
                                 synFileName, conFileName, outFileName)
    else:
        #        print 'parameters: [templateParamName] [cellNumberFileName] [synFileName] [conFileName] [outFileName]'
        print(
            'parameters: [templateParamName] [cellNumberFileName] [synFileName] [outFileName]'
        )

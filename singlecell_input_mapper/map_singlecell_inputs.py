#===============================================================================
# SingleCellInputMapper
# Tool for estimating connectivity (inputs) of individual neuron morphologies
# registered into standard barrel cortex model.
# Based on methods and data presented in:
# Egger, Dercksen et al., Frontiers Neuroanatomy 2014
#
# Inputs:
# - single neuron morphology
# - 3D PST densities for normalization of innervation calculations
# - number of cells per cell type spreadsheets
# - connections spreadsheet containing PST length/area constants
# - presynaptic bouton densities of individual axon morphologies
#   sorted by presynaptic column and cell type
# Outputs:
# - summary file containing information about number and presynaptic type
#   and column of anatomical synapses
# - AmiraMesh landmark file containing 3D synapse locations of anatomical
#   synapses of each presynaptic type and column
# - Synapse location and connectivity file compatible with NeuroSim
#
# Author: Robert Egger
#         Computational Neuroanatomy
#         Max Planck Institute for Biological Cybernetics
#         Tuebingen, Germany
#         Email: robert.egger@tuebingen.mpg.de
#===============================================================================

#===============================================================================
# Python standard library imports
#===============================================================================
from __future__ import absolute_import
import sys
import os.path
import glob
import time

#===============================================================================
# required imports
# numpy: tested with numpy v1.6.2 (not guaranteed to work with lower version)
# The singlecell_input_mapper module should automatically be loaded if its
# main folder is located in the same directory as this file. If not, you should
# add it to the system PYTHONPATH:
# export PYTHONPATH=/path/to/singlecell_input_mapper:$PYTHONPATH
#===============================================================================
import numpy as np
from . import singlecell_input_mapper as sim
import getting_started
#===============================================================================
# This is the only line that needs to be adapted to your system.
# Change the string 'prefix' to the folder where all anatomical data is
# located on your system (assuming you just unpack the data and do not change
# the directory structure)
#===============================================================================
prefix = os.path.join(getting_started.parent, 'barrel_cortex')

#===============================================================================
# If you change the directory structure of the anatomical input data,
# you need to update the following lines accordingly.
# Otherwise, you can leave everything from here on as is.
#===============================================================================
numberOfCellsSpreadsheetName = os.path.join(prefix, 'nrCells.csv')
connectionsSpreadsheetName = os.path.join(prefix, 'ConnectionsV8.csv')
ExPSTDensityName = os.path.join(prefix, 'PST/EXNormalizationPSTs.am')
InhPSTDensityName = os.path.join(prefix, 'PST/INHNormalizationPSTs.am')
boutonDensityFolderName = 'singleaxon_boutons_ascii'

exTypes = ('VPM', 'L2', 'L34', 'L4py', 'L4sp', 'L4ss', 'L5st', 'L5tt', 'L6cc',
           'L6ccinv', 'L6ct')
inhTypes = ('SymLocal1','SymLocal2','SymLocal3','SymLocal4','SymLocal5','SymLocal6',\
            'L1','L23Trans','L45Sym','L45Peak','L56Trans')


def map_singlecell_inputs(cellName, cellTypeName, nrOfSamples=50):
    if not (cellTypeName in exTypes) and not (cellTypeName in inhTypes):
        errstr = 'Unknown cell type %s!'
        raise TypeError(errstr)

    startTime = time.time()

    print('Loading cell morphology...')
    parser = sim.CellParser(cellName)
    parser.spatialgraph_to_cell()
    singleCell = parser.get_cell()

    print('Loading spreadsheets and bouton/PST densities...')
    print('    Loading numberOfCells spreadsheet {:s}'.format(
        numberOfCellsSpreadsheetName))
    numberOfCellsSpreadsheet = sim.read_celltype_numbers_spreadsheet(
        numberOfCellsSpreadsheetName)
    print('    Loading connections spreadsheet {:s}'.format(
        connectionsSpreadsheetName))
    connectionsSpreadsheet = sim.read_connections_spreadsheet(
        connectionsSpreadsheetName)
    print('    Loading PST density {:s}'.format(ExPSTDensityName))
    ExPSTDensity = sim.read_scalar_field(ExPSTDensityName)
    ExPSTDensity.resize_mesh()
    print('    Loading PST density {:s}'.format(InhPSTDensityName))
    InhPSTDensity = sim.read_scalar_field(InhPSTDensityName)
    InhPSTDensity.resize_mesh()
    boutonDensities = {}
    columns = list(numberOfCellsSpreadsheet.keys())
    preCellTypes = numberOfCellsSpreadsheet[columns[0]]

    for col in columns:
        boutonDensities[col] = {}
        for preCellType in preCellTypes:
            boutonDensities[col][preCellType] = []
            boutonDensityFolder = os.path.join(prefix, boutonDensityFolderName,
                                               col, preCellType)
            boutonDensityNames = glob.glob(
                os.path.join(boutonDensityFolder, '*'))
            print('    Loading {:d} bouton densities from {:s}'.format(
                len(boutonDensityNames), boutonDensityFolder))
            for densityName in boutonDensityNames:
                boutonDensity = sim.read_scalar_field(densityName)
                boutonDensity.resize_mesh()
                boutonDensities[col][preCellType].append(boutonDensity)

    inputMapper = sim.NetworkMapper(singleCell, cellTypeName, numberOfCellsSpreadsheet, connectionsSpreadsheet,\
                                    ExPSTDensity, InhPSTDensity)
    inputMapper.exCellTypes = exTypes
    inputMapper.inhCellTypes = inhTypes
    inputMapper.create_network_embedding(cellName,
                                         boutonDensities,
                                         nrOfSamples=nrOfSamples)

    endTime = time.time()
    duration = (endTime - startTime) / 60.0
    print('Runtime: {:.1f} minutes'.format(duration))


if __name__ == '__main__':
    if len(sys.argv) == 3:
        fname = sys.argv[1]
        cellTypeName = sys.argv[2]
        map_singlecell_inputs(fname, cellTypeName)
    else:
        print(
            'Usage: python map_singlecell_inputs.py [morphology filename] [postsynaptic cell type name]'
        )

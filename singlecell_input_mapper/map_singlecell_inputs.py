"""Map synapses onto a postsynaptic cell.

This module provides a full pipeline for creating anatomical realizations of the connectivity 
of individual neuron morphologies, based on methods and data presented in 
:cite:t:`Egger_Dercksen_Udvary_Hege_Oberlaender_2014`.
An anatomical realization refers to a set of synapses sampled from a probability distribution.

Inputs:

- Morphology of the post-synaptic neuron
- 3D PST densities for normalization of innervation calculations
- Number of cells per cell type in the brain area of interest.
- Connections spreadsheet containing PST length/area constants of 
  the post-synaptic cell for normalization.
- Presynaptic bouton densities of individual axon morphologies,
  sorted by anatomical area and cell type

This module then uses :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`
to assign synapses to a single post-synaptic cell morphology, based on the inputs mentioned above.
This happens according to the following pipeline:

1. The bouton density field is a scalar field with defined voxel resolution. This voxel resolution
   can reflect e.g. biological variability from animal to animal 
   (as is the case for which this package was developed), or measurement error.
2. Calculate the overlap between these voxels and the dendrites of the postsynaptic neuron morphology 
   using Liang-Barsky clipping :cite:`liang1984new`.
3. Calculate a synapse density field by multiplying the bouton density field with the PST density field
   at these voxels.
4. Normalize the synapse density field using cell-type specific PST length/area constraints and the number of 
   cells per cell type.
5. Poisson samples synapses from this density field and randomly assign them to the dendritic branch 
   that is contained within that voxel. This sample is called an "anatomical realization".
6. (optional) Repeat steps 4 and 5 to create a collection of anatomical realizations. 
   These collections can be investigated for variability in synapse number and location.
   Alternatively, the realization that is closest to the average is further used in modules like :py:mod:`simrun`.

Density meshes are accessed using :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`.
:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper` makes use of 
:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseDensity` for steps 2, 3 and 4,
and finalizes step 5 by itself.

Outputs:

- summary file containing information about number and presynaptic type
  and column of anatomical synapses
- AmiraMesh landmark file containing 3D synapse locations of anatomical
  synapses of each presynaptic type and column
- Synapse location and connectivity file compatible with :py:mod:`simrun`.

Author: 
    Robert Egger
    Computational Neuroanatomy
    Max Planck Institute for Biological Cybernetics
    Tuebingen, Germany
"""

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
prefix = os.path.join(os.path.dirname(getting_started.parent), 'barrel_cortex')

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


def map_singlecell_inputs(
    cellName, 
    cellTypeName, 
    nrOfSamples=50,
    numberOfCellsSpreadsheetName=numberOfCellsSpreadsheetName,
    connectionsSpreadsheetName=connectionsSpreadsheetName,
    ExPSTDensityName=ExPSTDensityName,
    InhPSTDensityName=InhPSTDensityName,
    boutonDensityFolderName=boutonDensityFolderName):
    """Map inputs to a single cell morphology.
    
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
        
    3. Creates a scalar field (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`)
       for each bouton density.
    4. Creates a :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper` object.
    5. Creates a network embedding for the cell using 
       :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper.create_network_embedding`.
    
    The naming of each anatomical area needs to be consistent between:
    
    - The number of cells per cell type spreadsheet
    - The bouton folders containing axon traces
    
    Args:
        cellName (str): 
            path to a .hoc file containing the morphology of the cell.
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
        None. Writes the results to disk.
    """
    if not (cellTypeName in exTypes) and not (cellTypeName in inhTypes):
        errstr = 'Unknown cell type %s!'
        raise TypeError(errstr)

    startTime = time.time()

    print('Loading cell morphology...')
    parser = sim.CellParser(cellName)
    parser.spatialgraph_to_cell()
    singleCell = parser.get_cell()  # This is a sim.Cell, not scp.cell

    # --------------------- Read in data ---------------------
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
    anatomical_areas = list(numberOfCellsSpreadsheet.keys())
    preCellTypes = numberOfCellsSpreadsheet[anatomical_areas[0]]

    # --------------------- Load bouton densities ---------------------
    for anatomical_area in anatomical_areas:
        # boutonDensities is a dictionary with anatomical areas as keys
        # and as value another dictionary mapping the presyn celltype to 
        # scalar fields of boutons
        boutonDensities[anatomical_area] = {}
        for preCellType in preCellTypes:
            boutonDensities[anatomical_area][preCellType] = []
            boutonDensityFolder = os.path.join(
                prefix, 
                boutonDensityFolderName,
                anatomical_area, 
                preCellType)
            boutonDensityNames = glob.glob(
                os.path.join(boutonDensityFolder, '*'))
            print('    Loading {:d} bouton densities from {:s}'.format(
                len(boutonDensityNames), boutonDensityFolder))
            for densityName in boutonDensityNames:
                boutonDensity = sim.read_scalar_field(densityName)
                boutonDensity.resize_mesh()
                boutonDensities[anatomical_area][preCellType].append(boutonDensity)

    inputMapper = sim.NetworkMapper(
        singleCell, 
        cellTypeName, 
        numberOfCellsSpreadsheet, 
        connectionsSpreadsheet,
        ExPSTDensity, 
        InhPSTDensity)
    inputMapper.exCellTypes = exTypes
    inputMapper.inhCellTypes = inhTypes
    inputMapper.create_network_embedding(
        cellName,
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

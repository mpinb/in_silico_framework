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

'''Create anatomical realizations of connectivity.
In contrast to :mod:`single_cell_parser.network_embedding`, 
this module does not handle the activity of presynaptic populations, but provides functionality to fully investigate the network connectivity.

'''
from __future__ import absolute_import
from typing import Dict
import os
import sys
import time
import numpy as np
from collections import defaultdict
from .cell import PointCell
from . import writer
from .synapse_mapper import SynapseMapper, SynapseDensity
from data_base.dbopen import dbopen
import logging
__author__ = 'Robert Egger'
__date__ = '2012-11-17'
logger = logging.getLogger("ISF").getChild(__name__)


class NetworkMapper:
    '''Connect presynaptic cells to a postsynaptic cell model.

    This class is used to create anatomical realizations of connectivity.
    Given a :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField` of boutons, 
    it computes all possible synapse densities that have non-zero overlap with every voxel this bouton field.
    These synapse density fields depend on the presence of post-synaptic dendrites in the bouton field,
    which in turn depends on the location and morphology of the post-syanptic neuron.
    The synapse density fields are further used as probability distributions to Poisson sample 
    mutiple realizations of synaptic connections between pre-synaptic cells, and the post-synaptic cell
    (see :func:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper.create_synapses`).
    
    See also:
        This is not the same class as :class:`single_cell_parser.network.NetworkMapper`.
        This class is specialized for anatomical reconstructions, 
        not synapse activations or simulation parameters.
    
    Attributes:
        cells (dict[str, dict[str, PointCell]]): 
            Presynaptic cells, ordered by anatomical area and cell type. 
            This attribute is filled by 
            :func:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper._create_presyn_cells`.
        connected_cells (dict): Indices of all active presynaptic cells, ordered by cell type.
        postCell (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): Reference to postsynaptic (multi-compartment) cell model.
        postCellType (str): Postsynaptic cell type.
    '''

    def __init__(
        self, 
        postCell, 
        postCellType, 
        cellTypeNumbersSpreadsheet,
        connectionsSpreadsheet, 
        exPST, 
        inhPST):
        '''        
        Args:
            postCell (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): The cell object to map synapses onto.
            postCellType (str): The type of the postsynaptic cell.
            cellTypeNumbersSpreadsheet (dict): Number of presynaptic cells per cell type and anatomical_area.
        '''
        self.cells: dict[str, dict[str, PointCell]] = {}
        self.connected_cells = {}
        self.exCellTypes = []
        self.inhCellTypes = []
        self.cellTypeNumbersSpreadsheet = cellTypeNumbersSpreadsheet
        self.connectionsSpreadsheet = connectionsSpreadsheet
        self.postCell = postCell
        self.postCellType = postCellType
        self.exPST = exPST
        self.inhPST = inhPST
        self.mapper = SynapseMapper(postCell)
        # seed = int(time.time())
        # self.ranGen = np.random.RandomState(seed)

    def create_network_embedding(
        self,
        postCellName,
        boutonDensities,
        nrOfSamples=50):
        '''Create a single network realization from a bouton density field.

        This is the main method to create anatomical realizations of connectivity.
        It creates :param:`nrOfSamples` network realizations, and saves the most representative
        realization to disk. The most representative realization is determined by comparing
        the distribution of anatomical parameters across the population of realizations using
        :func:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper._get_representative_sample`.

        Args:
            postCellName (str):
                Path to the postsynaptic :ref:`hoc_file_format` morphology file.
            boutonDensities (dict):
                Dictionary of bouton densities, ordered by anatomical area and cell type.
            nrOfSamples (int):
                Number of network realizations to create.
        
        Warning:
            Give this network realization a (somewhat) unique name!   
            Then save it at the same location as the anatomical realization
        
        Warning:
            Assumes path names to anatomical realization files are relative to the working directory. 
            These paths should be correct relative, or preferably absolute paths.
        
        Returns:
            None. Writes output files to disk.
        '''
        self._create_presyn_cells()
        anatomical_areas = list(self.cells.keys())
        preCellTypes = self.cells[anatomical_areas[0]]
        logger.info("Computing synapse densities")
        cellTypeSynapseDensities = self._precompute_anatomical_area_celltype_synapse_densities_vectorized(boutonDensities)
        sampleConnectivityData = []
        cellTypeSpecificPopulation = []
        for i in range(nrOfSamples):

            logger.info('Generating network embedding sample {:d} of {:d}'.format(i+1, nrOfSamples))
            self.postCell.remove_synapses('All')
            for anatomical_area in anatomical_areas:
                for preCellType in preCellTypes:
                    for preCell in self.cells[anatomical_area][preCellType]:
                        preCell.synapseList = None
            
            logger.debug("    Sample {:d} of {:d}: Creating anatomical realization...".format(i + 1, nrOfSamples))
            connectivityMap, connectedCells, connectedCellsPerStructure = \
                self._create_anatomical_realization(cellTypeSynapseDensities)
            logger.debug("    Sample {:d} of {:d}: Anatomical realization done.".format(i + 1, nrOfSamples))
            
            logger.debug("    Sample {:d} of {:d}: Computing summary tables...".format(i + 1, nrOfSamples))
            synapseLocations, cellSynapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable = \
                self._compute_summary_tables(connectedCells, connectedCellsPerStructure)
            logger.debug("    Sample {:d} of {:d}: Computing summary tables done".format(i + 1, nrOfSamples))

            connectivityData = connectivityMap, synapseLocations, \
                                cellSynapseLocations, cellTypeSummaryTable,\
                                anatomicalAreaSummaryTable
            sampleConnectivityData.append(connectivityData)
            cellTypeSpecificPopulation.append(cellTypeSummaryTable)
            logger.info('---------------------------')

        populationDistribution = self._compute_parameter_distribution(
            cellTypeSpecificPopulation)
        representativeIndex = self._get_representative_sample(
            cellTypeSpecificPopulation, populationDistribution)
        logger.info("Writing output files for representative sample (id={})".format(representativeIndex))
        (connectivityMap, 
         synapseLocations, 
         cellSynapseLocations, 
         cellTypeSummaryTable, 
         anatomicalAreaSummaryTable
            ) = sampleConnectivityData[representativeIndex]
        self._write_population_output_files(
            postCellName,
            populationDistribution,
            connectivityMap, 
            synapseLocations,
            cellSynapseLocations,
            cellTypeSummaryTable,
            anatomicalAreaSummaryTable)

        logger.info('Done generating network embedding!')
        logger.info('---------------------------')

    def create_network_embedding_for_simulations(
        self, 
        postCellName,
        boutonDensities,
        nrOfRealizations):
        '''Create multiple network realizations from a bouton density field.
        
        Main method used for creating fixed network connectivity for use in Monte Carlo simulations.
        Same principle as :func:`~create_network_embedding`, but rather than taking
        the most representative sample, this method saves all :param:`nrOfRealizations` network 
        realizations to allow investigating the effects of anatomical variability on neuron responses.

        Warning:
            Give this network realization a (somewhat) unique name!     
            Then save it at the same location as the anatomical realization
        
        Warning:
            Assumes path names to anatomical realization files are relative to the working directory. 
            These paths should be correct relative, or preferably absolute paths.
            
        Args:
            postCellName (str):
                Path to the postsynaptic :ref:`hoc_file_format` morphology file.
            boutonDensities (dict):
                Dictionary of bouton densities, ordered by anatomical area and cell type.
            nrOfRealizations (int):
                Number of network realizations to create.

        Returns:
            None. Writes output files to disk.
        '''
        self._create_presyn_cells()
        anatomical_areas = list(self.cells.keys())
        preCellTypes = self.cells[anatomical_areas[0]]
        cellTypeSynapseDensities = \
            self._precompute_anatomical_area_celltype_synapse_densities(
                boutonDensities)

        cellTypeSpecificPopulation = []
        for i in range(nrOfRealizations):
            logger.info('Creating realization {:d} of {:d}'.format(i + 1, nrOfRealizations))
            self.postCell.remove_synapses('All')
            for anatomical_area in anatomical_areas:
                for preCellType in preCellTypes:
                    for preCell in self.cells[anatomical_area][preCellType]:
                        preCell.synapseList = None

            connectivityMap, connectedCells, connectedCellsPerStructure = self._create_anatomical_realization(cellTypeSynapseDensities)
            self._generate_output_files(
                postCellName, 
                connectivityMap,
                connectedCells,
                connectedCellsPerStructure)
            _,  _,  cellTypeSummaryTable, _ = self._compute_summary_tables(connectedCells, connectedCellsPerStructure)
            cellTypeSpecificPopulation.append(cellTypeSummaryTable)
            logger.info('---------------------------')

    def create_network_embedding_from_synapse_densities(
        self, 
        postCellName,
        synapseDensities):
        '''Create a single network realization from pre-computed synapse densities.
        
        Useful for testing purposes.
        
        Warning:
            Give this network realization a (somewhat) unique name!     
            Then save it at the same location as the anatomical realization
        
        Warning:
            Assumes path names to anatomical realization files are relative to the working directory. 
            These paths should be correct relative, or preferably absolute paths.
        
        Args:
            postCellName (str):
                Path to the postsynaptic :ref:`hoc_file_format` morphology file.
            synapseDensities (dict):
                Dictionary of synapse densities, ordered by anatomical area and cell type.
        '''

        self._create_presyn_cells()
        anatomical_areas = list(self.cells.keys())
        preCellTypes = self.cells[anatomical_areas[0]]
        cellTypeSynapseDensities = synapseDensities
        for anatomical_area in anatomical_areas:
            for preCellType in preCellTypes:
                logger.debug('---------------------------')
                logger.debug('    Assigning synapses from cell type {:s} in anatomical_area {:s}'.
                      format(preCellType, anatomical_area))
                nrOfDensities = len(cellTypeSynapseDensities[anatomical_area][preCellType])
                if not nrOfDensities:
                    continue
                totalNumber = len(self.cells[anatomical_area][preCellType])
                count = 0
                for preCell in self.cells[anatomical_area][preCellType]:
                    count += 1
                    logger.debug('    Computing synapses for presynaptic cell {:d} of {:d}...\r'.format(count, totalNumber))  #, end=' ')
                    sys.stdout.flush()
                    densityID = np.random.randint(nrOfDensities)
                    synapseDensity = cellTypeSynapseDensities[anatomical_area][preCellType][
                        densityID]
                    self.mapper.synDist = synapseDensity
                    synapseType = '_'.join((preCellType, anatomical_area))
                    preCell.synapseList = self.mapper.create_synapses(
                        synapseType)
                    for newSyn in preCell.synapseList:
                        newSyn.preCell = preCell
                logger.debug('')

        connectivityMap, connectedCells, connectedCellsPerStructure = \
            self._create_anatomical_connectivity_map()
        
        self._generate_output_files(
            postCellName, 
            connectivityMap,
            connectedCells, 
            connectedCellsPerStructure)
        logger.info('---------------------------')

    def _precompute_anatomical_area_celltype_synapse_densities(self, boutonDensities):
        '''Compute synapse densities of all presynaptic cell types in all anatomical_areas
        
        Computes all possible synapse densities that have non-zero overlap
        with the current postynaptic neuron, and sorts them based on presynaptic anatomical_area and cell type

        Args:
            boutonDensities (Dict[str, Dict[str, List[:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`]]]):
                Dictionary of bouton densities, ordered by anatomical area and cell type.

        .. deprecated:: 0.5.0
           This has been deprecated in favor of :func:`_precompute_anatomical_area_celltype_synapse_densities_vectorized`

        :skip-doc:
        '''
        synapseDensities = {}
        synapseDensityComputation = SynapseDensity(
            self.postCell, 
            self.postCellType, 
            self.connectionsSpreadsheet,
            self.exCellTypes, 
            self.inhCellTypes, 
            self.exPST, 
            self.inhPST)
        anatomical_areas = list(boutonDensities.keys())
        preCellTypes = boutonDensities[anatomical_areas[0]]
        for anatomical_area in anatomical_areas:
            synapseDensities[anatomical_area] = {}
            for preCellType in preCellTypes:
                synapseDensities[anatomical_area][preCellType] = []
                logger.debug('Computing synapse densities from cell type {:s} in {:s}'.format(preCellType, anatomical_area))
                for boutons in boutonDensities[anatomical_area][preCellType]:
                    synapseDensities[anatomical_area][preCellType].append(
                        synapseDensityComputation.compute_synapse_density(
                            boutons, preCellType))
        return synapseDensities

    def _precompute_anatomical_area_celltype_synapse_densities_vectorized(self, boutonDensities):
        '''Compute synapse densities of all presynaptic cell types in all anatomical_areas
        
        Computes all possible synapse densities that have non-zero overlap
        with the current postynaptic neuron, and sorts them based on presynaptic anatomical_area and cell type

        Args:
            boutonDensities (Dict[str, Dict[str, :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`]]):
                Dictionary of bouton densities, ordered by anatomical area and cell type.
        '''
        synapseDensities = {}
        synapseDensityComputation = SynapseDensity(
            self.postCell, 
            self.postCellType, 
            self.connectionsSpreadsheet,
            self.exCellTypes, 
            self.inhCellTypes, 
            self.exPST, 
            self.inhPST)
        anatomical_areas = list(boutonDensities.keys())
        preCellTypes = boutonDensities[anatomical_areas[0]]
        for anatomical_area in anatomical_areas:
            synapseDensities[anatomical_area] = {}
            for preCellType in preCellTypes:
                synapseDensities[anatomical_area][preCellType] = []
                logger.debug('Computing synapse densities from cell type {:s} in {:s}'.format(preCellType, anatomical_area))
                for boutons in boutonDensities[anatomical_area][preCellType]:
                    synapseDensities[anatomical_area][preCellType].append(
                        synapseDensityComputation.compute_synapse_density_vectorized(boutons, preCellType))
        return synapseDensities

    def _create_presyn_cells(self):
        '''Creates presynaptic cells.

        Should be done before creating anatomical synapses.
        Fills the :attr:`~cells` attribute with a nested dictionary of presynaptic cells,
        ordered by anatomical area first, and cell type second.
        '''
        logger.info('---------------------------')
        cellIDs = 0
        anatomical_areas = list(self.cellTypeNumbersSpreadsheet.keys())
        for anatomical_area in anatomical_areas:
            cellTypes = list(self.cellTypeNumbersSpreadsheet[anatomical_area].keys())
            self.cells[anatomical_area] = {}
            for cellType in cellTypes:
                self.cells[anatomical_area][cellType] = []
                nrOfCellsPerType = self.cellTypeNumbersSpreadsheet[anatomical_area][cellType]
                for i in range(nrOfCellsPerType):
                    newCell = PointCell(anatomical_area, cellType)
                    self.cells[anatomical_area][cellType].append(newCell)
                    cellIDs += 1
                logger.debug('    Created {:d} presynaptic cells of type {:s} in anatomical_area {:s}'.format(nrOfCellsPerType, cellType, anatomical_area))
        logger.info('Created {:d} presynaptic cells in total'.format(cellIDs))
        logger.info('---------------------------')

    def _create_anatomical_realization(self, cellTypeSynapseDensities):
        '''Create a single anatomical realization of synapses.

        This is the main method for computing synapse/connectivity realization.
        Given one or more pre-computed density fields of synapses (see e.g. 
        :func:`~_precompute_anatomical_area_celltype_synapse_densities_vectorized`), this method 
        creates a :class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper`
        from this synapse density field, and assigns synapses.

        Returns anatomical connectivity map.
        '''
        anatomical_areas = list(self.cells.keys())
        preCellTypes = self.cells[anatomical_areas[0]]
        for anatomical_area in anatomical_areas:
            for preCellType in preCellTypes:
                nrOfDensities = len(cellTypeSynapseDensities[anatomical_area][preCellType])
                if not nrOfDensities:
                    continue

                logger.debug('---------------------------')
                logger.debug('Computed {:d} synapse densities of type {:s} in anatomical_area {:s}'.format(nrOfDensities, preCellType, anatomical_area))
                logger.debug('Assigning synapses from cell type {:s} in anatomical_area {:s}'.
                      format(preCellType, anatomical_area))
                totalNumber = len(self.cells[anatomical_area][preCellType])
                densityIDs = np.random.randint(0, nrOfDensities, totalNumber)
                count = 0
                skipCount = 0
                for i in range(totalNumber):
                    preCell = self.cells[anatomical_area][preCellType][i]
                    count += 1
                    logger.debug('    Computing synapses for presynaptic cell {:d} of {:d}...\r'.format(count, totalNumber))  #, end=' ')
                    # sys.stdout.flush()
                    densityID = densityIDs[i]
                    synapseDensity = cellTypeSynapseDensities[anatomical_area][preCellType][densityID]
                    if synapseDensity is None:
                        skipCount += 1
                        continue
                    self.mapper.synDist = synapseDensity
                    synapseType = '_'.join((preCellType, anatomical_area))
                    preCell.synapseList = self.mapper.create_synapses(synapseType)
                    for newSyn in preCell.synapseList:
                        newSyn.preCell = preCell
                logger.debug('')
                logger.debug('    Skipped {:d} empty synapse densities...'.format(skipCount))

        return self._create_anatomical_connectivity_map()

    def _create_anatomical_connectivity_map(self):
        '''Connects anatomical synapses to PointCells.
         
        Connections have anatomical constraints on connectivity.
        (i.e., convergence of presynaptic cell type).
        Creates three return values:
         
        1. An anatomical connectivity map:
            a list of connections between presynaptic cells and postsynaptic cell of the form
            (cell type, presynaptic cell index, synapse index):

            - cell type (str): string used for indexing point cells and synapses
            - presynaptic cell index (int): index of cell in list self.cells[cell type]
            - synapse index (int): index of synapse in list self.postCell.synapses[cell type]

        2. A dictionary of connected cells, ordered by cell type.
        3. A dictionary of connected cells per structure, ordered by cell type.
        
        Used to create anatomical realizations.
        
        Returns:
            tuple: the anatomical map, connected cells, and connected cells per structure
        '''
        logger.info('---------------------------')
        logger.info('Creating anatomical connectivity map for output...')

        anatomicalMap = []
        connectedCells = {}
        connectedCellsPerStructure = {}
        synapseTypes = list(self.postCell.synapses.keys())
        for synapseType in synapseTypes:
            nrOfSynapses = len(self.postCell.synapses[synapseType])
            for i in range(nrOfSynapses):
                self.postCell.synapses[synapseType][i].synapseID = i
        anatomical_areas = list(self.cells.keys())
        for anatomical_area in anatomical_areas:
            cellTypes = list(self.cells[anatomical_area].keys())
            for cellType in cellTypes:
                cellID = 0
                for cell in self.cells[anatomical_area][cellType]:
                    if not cell.synapseList:
                        continue
                    connectedStructures = []
                    for syn in cell.synapseList:
                        anatomicalConnection = (syn.preCellType, cellID,
                                                syn.synapseID)
                        anatomicalMap.append(anatomicalConnection)
                        synapseStructure = self.postCell.sections[syn.secID].label
                        if synapseStructure not in connectedStructures:
                            connectedStructures.append(synapseStructure)
                    if cell.synapseList[0].preCellType not in connectedCells:
                        connectedCells[syn.preCellType] = 1
                        connectedCellsPerStructure[syn.preCellType] = {}
                        connectedCellsPerStructure[syn.preCellType]['ApicalDendrite'] = 0
                        connectedCellsPerStructure[syn.preCellType]['Dendrite'] = 0
                        connectedCellsPerStructure[syn.preCellType]['Soma'] = 0
                    else:
                        connectedCells[cell.synapseList[0].preCellType] += 1
                    for synapseStructure in connectedStructures:
                        connectedCellsPerStructure[syn.preCellType][synapseStructure] += 1
                    cellID += 1
        logger.info('---------------------------')

        return anatomicalMap, connectedCells, connectedCellsPerStructure

    def _get_representative_sample(
        self, 
        realizationPopulation,
        populationDistribution):
        '''Determine which sample of a population of anatomical realizations
        is the most representative.
         
        Given a collection of anatomical parameters, takes all samples
        which have all features within +-2 SD of population mean, then sorts
        them by distance to population mean (in SD units) and chooses
        sample with smallest distance.
        
        Features used are:

        - cell type-specific total number of synapses.
        
        Returns:
            ID of the most representative sample.
        '''
        representativeID = None
        tmpID = None
        synapseNumberDistribution = []
        cellTypes = list(populationDistribution.keys())
        cellTypes.sort()
        for cellType in cellTypes:
            synapseNumberDistribution.append(
                populationDistribution[cellType][0])
        globalMinDist = 1e9
        inside2SDMinDist = 1e9
        for i in range(len(realizationPopulation)):
            sample = realizationPopulation[i]
            sampleSynapseNumbers = []
            for cellType in cellTypes:
                sampleSynapseNumbers.append(sample[cellType][0])
            distanceVector = self._compute_sample_distance(
                sampleSynapseNumbers, synapseNumberDistribution)
            distance2 = np.dot(distanceVector, distanceVector)
            inside2 = True
            for parameterDistance in distanceVector:
                if abs(parameterDistance) > 2.0:
                    inside2 = False
            if inside2 and distance2 < inside2SDMinDist:
                inside2SDMinDist = distance2
                representativeID = i
            if distance2 < globalMinDist:
                globalMinDist = distance2
                tmpID = i

        if representativeID is None:
            logger.info(
                'Could not find representative sample with all parameters within +-2 SD'
            )
            logger.info(
                'Choosing closest sample with minimum distance {:.1f} instead...'
                .format(np.sqrt(globalMinDist)))
            representativeID = tmpID
        else:
            logger.info(
                'Found representative sample with all parameters within +-2 SD')
            logger.info(
                'Closest sample within +-2 SD (ID {:d}) has minimum distance {:.1f} ...'
                .format(representativeID, np.sqrt(inside2SDMinDist)))
        logger.info('---------------------------')

        return representativeID

    def _compute_parameter_distribution(self, realizationPopulation):
        '''Compute mean +- SD of parameters for population of anatomical realizations.
        
        Using parameters in :attr:`cellTypeSummaryTable` on a per cell type basis:

        0.  nrOfSynapses
        1.  nrConnectedCells
        2.  nrPreCells
        3.  convergence
        4.  distanceMean
        5.  distanceSTD
        6.  cellTypeSynapsesPerStructure (dict: ApicalDendrite, BasalDendrite, Soma)
        7.  cellTypeConnectionsPerStructure (dict: ApicalDendrite, BasalDendrite, Soma)
        8.  cellTypeConvergencePerStructure (dict: ApicalDendrite, BasalDendrite, Soma)
        9.  cellTypeDistancesPerStructure (dict: ApicalDendrite, BasalDendrite)

        Returns:
            dict: dictionary organized the same way as :attr:`cellTypeSummaryTable`,
            but entries are tuples (mean, STD) of each parameter for
            given population of realizations.
        '''
        nrOfSamples = len(realizationPopulation)
        if not nrOfSamples:
            return None
        logger.info(
            'Computing parameter distribution for {:d} samples in population...'
            .format(nrOfSamples))
        populationDistribution = {}
        for cellType in list(realizationPopulation[0].keys()):
            populationDistribution[cellType] = []
            # unnamed parameters
            for i in range(6):
                populationValues = []
                for j in range(nrOfSamples):
                    populationValues.append(
                        realizationPopulation[j][cellType][i])
                populationMean = np.mean(populationValues)
                populationSTD = np.std(populationValues)
                parameterDistribution = populationMean, populationSTD
                populationDistribution[cellType].append(parameterDistribution)
            # named parameters apical/basal(/soma)
            for i in range(6, 10):
                populationDistribution[cellType].append({})
                if i < 9:
                    structures = 'ApicalDendrite', 'BasalDendrite', 'Soma'
                    for structure in structures:
                        populationValues = []
                        for j in range(nrOfSamples):
                            populationValues.append(realizationPopulation[j]
                                                    [cellType][i][structure])
                        populationMean = np.mean(populationValues)
                        populationSTD = np.std(populationValues)
                        parameterDistribution = populationMean, populationSTD
                        populationDistribution[cellType][i][
                            structure] = parameterDistribution
                else:
                    structures = 'ApicalDendrite', 'BasalDendrite'
                    for structure in structures:
                        populationMeanValues = []
                        populationSTDValues = []
                        for j in range(nrOfSamples):
                            populationMeanValues.append(
                                realizationPopulation[j][cellType][i][structure]
                                [0])
                            populationSTDValues.append(
                                realizationPopulation[j][cellType][i][structure]
                                [1])
                        populationMeanAvg = np.mean(populationMeanValues)
                        populationMeanSTD = np.std(populationMeanValues)
                        populationSTDAvg = np.mean(populationMeanValues)
                        populationSTDSTD = np.std(populationMeanValues)
                        parameterDistributionMean = populationMeanAvg, populationMeanSTD
                        parameterDistributionSTD = populationSTDAvg, populationSTDSTD
                        populationDistribution[cellType][i][
                            structure] = parameterDistributionMean, parameterDistributionSTD
        logger.info('---------------------------')

        return populationDistribution

    def _compute_sample_distance(
            self, 
            realizationSample,
            realizationPopulationDistribution):
        '''Compute the distance of network realization samples to the population mean.
         
        Given a sample distribution, calculate how far each parameter is from the population mean.
        Standardizes the distance vector by dividing it by the parameter's population-wide 
        standard deviation.

        Args:
            realizationSample (list): List of parameters for a single realization.
            realizationPopulationDistribution (list): List of parameters for the population of realizations.

        Returns:
            np.array: SD-normalized distance vector.
        '''
        distanceVec = np.zeros(len(realizationSample))
        for i in range(len(realizationSample)):
            sampleParameter = realizationSample[i]
            parameterMean = realizationPopulationDistribution[i][0]
            parameterSTD = realizationPopulationDistribution[i][1]
            if parameterSTD:
                distanceVec[i] = (sampleParameter -
                                  parameterMean) / parameterSTD
            else:
                distanceVec[i] = 0.0

        return distanceVec

    def _test_population_convergence(
        self, 
        nrOfSamples, 
        sampleConnectivityData,
        postCellName):
        '''Test how many samples are needed to get a representative sample.

        Tests how many network realizations need to be sampled in order
        to get a reasonable estimate of the variability of connectivity
        parameters.

        Args:
            nrOfSamples (int): Number of network realizations.
            sampleConnectivityData (list): List of network realizations.
            postCellName (str): Name of the postsynaptic cell model.
        '''
        population = [sampleConnectivityData[0][2]]
        sampleNumberSummary = {}
        sampleNumberFeatures = {}
        for i in range(1, nrOfSamples):
            populationSize = i + 1
            logger.info(
                'Computing parameter distribution for {:d} samples in population...'
                .format(populationSize))
            population.append(sampleConnectivityData[i][2])
            populationDistribution = self._compute_parameter_distribution(
                population)
            synapseNumberDistribution = []
            cellTypes = list(populationDistribution.keys())
            cellTypes.sort()
            for cellType in cellTypes:
                synapseNumberDistribution.append(
                    populationDistribution[cellType][0])
            sampleNumberFeatures[populationSize] = synapseNumberDistribution
            sampleDistanceVectors = []
            sampleDistance2 = []
            for sample in population:
                sampleSynapseNumbers = []
                for cellType in cellTypes:
                    sampleSynapseNumbers.append(sample[cellType][0])
                distanceVector = self._compute_sample_distance(
                    sampleSynapseNumbers, synapseNumberDistribution)
                distance2 = np.dot(distanceVector, distanceVector)
                sampleDistanceVectors.append(distanceVector)
                sampleDistance2.append(distance2)

            #===================================================================
            # calculate min distance^2, median distance^2 to mean, and number of
            # samples where all parameter are within +-1 or 2 SD of mean
            #===================================================================
            minDistance = np.min(sampleDistance2)
            medianDistance = np.median(sampleDistance2)
            inside1SD = 0
            inside2SD = 0
            for sampleVec in sampleDistanceVectors:
                inside1 = True
                inside2 = True
                for parameterDistance in sampleVec:
                    if abs(parameterDistance) > 1.0:
                        inside1 = False
                    if abs(parameterDistance) > 2.0:
                        inside2 = False
                if inside1:
                    inside1SD += 1
                if inside2:
                    inside2SD += 1
            sampleNumberSummary[
                populationSize] = minDistance, medianDistance, inside1SD, inside2SD

        sampleNumberDistributionName = postCellName[:-4]
        sampleNumberDistributionName += '_population_size_test_%03d_sample_distribution.csv' % nrOfSamples
        with dbopen(sampleNumberDistributionName, 'w') as outFile:
            header = 'population size\tminimum distance\tmedian distance\tsamples inside 1 SD\tsamples inside 2 SD\n'
            outFile.write(header)
            testSizes = list(sampleNumberSummary.keys())
            testSizes.sort()
            for testSize in testSizes:
                line = str(testSize)
                line += '\t'
                line += str(sampleNumberSummary[testSize][0])
                line += '\t'
                line += str(sampleNumberSummary[testSize][1])
                line += '\t'
                line += str(sampleNumberSummary[testSize][2])
                line += '\t'
                line += str(sampleNumberSummary[testSize][3])
                line += '\n'
                outFile.write(line)

        sampleNumberFeatureName = postCellName[:-4]
        sampleNumberFeatureName += '_population_size_test_%03d_sample_features.csv' % nrOfSamples
        with dbopen(sampleNumberFeatureName, 'w') as outFile:
            testSizes = list(sampleNumberFeatures.keys())
            testSizes.sort()
            nrOfFeatures = len(sampleNumberFeatures[testSizes[0]])
            header = 'population size'
            for i in range(nrOfFeatures):
                header += '\tfeature %02d mean' % (i + 1)
                header += '\tfeature %02d STD' % (i + 1)
            header += '\n'
            outFile.write(header)
            maxFeatures = {}
            for i in range(nrOfFeatures):
                maxMean = sampleNumberFeatures[testSizes[-1]][i][0]
                maxSTD = sampleNumberFeatures[testSizes[-1]][i][1]
                maxFeatures[i] = maxMean, maxSTD
            for testSize in testSizes:
                line = str(testSize)
                for i in range(nrOfFeatures):
                    maxMean, maxSTD = maxFeatures[i]
                    populationMean, populationSTD = sampleNumberFeatures[
                        testSize][i]
                    line += '\t'
                    line += str(populationMean / maxMean)
                    line += '\t'
                    line += str(populationSTD / maxSTD)
                line += '\n'
                outFile.write(line)
        logger.info('---------------------------')


    def _compute_summary_tables(self, connectedCells, connectedCellsPerStructure):
        """
        Same outputs as before, but structure names are inferred from
        self.postCell.sections[secID].label (no hardcoded Apical/Basal/Soma set).
        """

        logger.info('---------------------------')
        logger.info('Calculating results summary')
        logger.info('    Computing path length to soma for all synapses...')

        # --- Infer all structure labels that actually occur on the post cell ---
        # (keep deterministic order for nicer tables/logs)
        inferred_structures = sorted({sec.label for sec in self.postCell.sections})

        # --- Compute soma distances for every synapse ---
        for preCellType in list(self.postCell.synapses.keys()):
            for synapse in self.postCell.synapses[preCellType]:
                attachedSec = self.postCell.sections[synapse.secID]
                synapse.distanceToSoma = 0.0 if attachedSec.label == 'Soma' else \
                    self.postCell.distance_to_soma(attachedSec, synapse.x)

        synapseLocations = {}
        cellSynapseLocations = {}
        cellTypeSummaryTable = {}
        anatomicalAreaSummaryTable = {}

        anatomical_areas = list(self.cells.keys())
        for anatomical_area in anatomical_areas:
            cellTypes = list(self.cells[anatomical_area].keys())
            for preType in cellTypes:
                preCellType = preType + '_' + anatomical_area

                anatomicalAreaSummaryTable.setdefault(anatomical_area, {})
                synapseLocations.setdefault(anatomical_area, {})

                # Initialize per-celltype accumulator row once, with inferred structures
                if preType not in cellTypeSummaryTable:
                    # [nrOfSynapses, nrConnectedCells, nrPreCells, convergence, distanceMean, distanceSTD,
                    #  synapsesPerStructure, connectionsPerStructure, convergencePerStructure, distancesPerStructure]
                    syn_per_struct = {s: 0 for s in inferred_structures}
                    con_per_struct = {s: 0 for s in inferred_structures}
                    conv_per_struct = {s: 0.0 for s in inferred_structures}
                    dist_per_struct = {s: [[], -1] for s in inferred_structures}  # [list_of_distances, std_placeholder]
                    cellTypeSummaryTable[preType] = [
                        0, 0, 0, 0.0, [], -1, syn_per_struct, con_per_struct, conv_per_struct, dist_per_struct
                    ]

                # ---------- collect synapses ----------
                try:
                    syn_list = self.postCell.synapses[preCellType]
                except KeyError:
                    syn_list = []

                allSynapses = [syn.coordinates for syn in syn_list]
                cellSynapseLocations[preCellType] = [(syn.preCellType, syn.secID, syn.x) for syn in syn_list]

                # Per-structure synapse coordinate lists + counts/distances
                coords_by_struct = {s: [] for s in inferred_structures}
                count_by_struct = {s: 0 for s in inferred_structures}
                dist_by_struct = {s: [] for s in inferred_structures}

                tmpDistances = []
                for synapse in syn_list:
                    secLabel = self.postCell.sections[synapse.secID].label
                    # If some section label appears that's not in inferred_structures (shouldn't happen),
                    # create buckets on the fly.
                    if secLabel not in coords_by_struct:
                        coords_by_struct[secLabel] = []
                        count_by_struct[secLabel] = 0
                        dist_by_struct[secLabel] = []
                        # Also extend the cellTypeSummaryTable accumulators so later updates won't KeyError
                        cellTypeSummaryTable[preType][6].setdefault(secLabel, 0)
                        cellTypeSummaryTable[preType][7].setdefault(secLabel, 0)
                        cellTypeSummaryTable[preType][8].setdefault(secLabel, 0.0)
                        cellTypeSummaryTable[preType][9].setdefault(secLabel, [[], -1])

                    count_by_struct[secLabel] += 1
                    coords_by_struct[secLabel].append(synapse.coordinates)
                    dist_by_struct[secLabel].append(synapse.distanceToSoma)
                    tmpDistances.append(synapse.distanceToSoma)

                nrOfSynapses = len(syn_list)
                if sum(count_by_struct.values()) != nrOfSynapses:
                    raise RuntimeError('Logical error: Number of synapses does not add up')

                # distances overall
                if tmpDistances:
                    distanceMean = float(np.mean(tmpDistances))
                    distanceSTD = float(np.std(tmpDistances))
                else:
                    distanceMean = -1
                    distanceSTD = -1

                # ---------- connected-cells per structure (do not assume keys exist) ----------
                nrConnectedCells = connectedCells.get(preCellType, 0)
                ccps = connectedCellsPerStructure.get(preCellType, {})
                nrConnectedCellsByStruct = {s: ccps.get(s, 0) for s in count_by_struct.keys()}

                # ---------- per-structure distance stats ----------
                distancesPerStructure = {}
                for s, dists in dist_by_struct.items():
                    if dists:
                        distancesPerStructure[s] = (float(np.mean(dists)), float(np.std(dists)))
                    else:
                        distancesPerStructure[s] = (-1, -1)

                # ---------- anatomical_area + celltype table ----------
                nrPreCells = len(self.cells[anatomical_area][preType])
                convergence = float(nrConnectedCells) / float(nrPreCells) if nrPreCells else 0.0

                synapsesPerStructure = dict(count_by_struct)
                connectionsPerStructure = dict(nrConnectedCellsByStruct)
                convergencePerStructure = {
                    s: (float(connectionsPerStructure.get(s, 0)) / float(nrPreCells) if nrPreCells else 0.0)
                    for s in synapsesPerStructure.keys()
                }

                anatomicalAreaSummaryTable[anatomical_area][preType] = [
                    nrOfSynapses, nrConnectedCells, nrPreCells, convergence, distanceMean, distanceSTD,
                    synapsesPerStructure, connectionsPerStructure, convergencePerStructure, distancesPerStructure
                ]

                # ---------- synapse locations output ----------
                synapseLocations[anatomical_area][preType] = {'Total': allSynapses}
                for s in coords_by_struct.keys():
                    synapseLocations[anatomical_area][preType][s] = coords_by_struct[s]

                # ---------- accumulate into cellTypeSummaryTable ----------
                cellTypeSummaryTable[preType][0] += nrOfSynapses
                cellTypeSummaryTable[preType][1] += nrConnectedCells
                cellTypeSummaryTable[preType][2] += nrPreCells
                cellTypeSummaryTable[preType][4] += tmpDistances

                for s, n in synapsesPerStructure.items():
                    cellTypeSummaryTable[preType][6].setdefault(s, 0)
                    cellTypeSummaryTable[preType][6][s] += n

                for s, n in connectionsPerStructure.items():
                    cellTypeSummaryTable[preType][7].setdefault(s, 0)
                    cellTypeSummaryTable[preType][7][s] += n

                for s, dists in dist_by_struct.items():
                    cellTypeSummaryTable[preType][9].setdefault(s, [[], -1])
                    cellTypeSummaryTable[preType][9][s][0] += dists

        # --- finalize cellTypeSummaryTable means/stds ---
        for preType in list(cellTypeSummaryTable.keys()):
            nrConnectedCellsTotal = cellTypeSummaryTable[preType][1]
            nrPreCellsTotal = cellTypeSummaryTable[preType][2]
            cellTypeSummaryTable[preType][3] = float(nrConnectedCellsTotal) / float(nrPreCellsTotal) if nrPreCellsTotal else 0.0

            distancesTotal = cellTypeSummaryTable[preType][4]
            if distancesTotal:
                cellTypeSummaryTable[preType][4] = float(np.mean(distancesTotal))
                cellTypeSummaryTable[preType][5] = float(np.std(distancesTotal))
            else:
                cellTypeSummaryTable[preType][4] = -1
                cellTypeSummaryTable[preType][5] = -1

            # per-structure convergence + distance stats
            for s in list(cellTypeSummaryTable[preType][7].keys()):
                nconn = cellTypeSummaryTable[preType][7].get(s, 0)
                cellTypeSummaryTable[preType][8].setdefault(s, 0.0)
                cellTypeSummaryTable[preType][8][s] = float(nconn) / float(nrPreCellsTotal) if nrPreCellsTotal else 0.0

            for s, (dlist, _std_placeholder) in list(cellTypeSummaryTable[preType][9].items()):
                if dlist:
                    cellTypeSummaryTable[preType][9][s][0] = float(np.mean(dlist))
                    cellTypeSummaryTable[preType][9][s][1] = float(np.std(dlist))
                else:
                    cellTypeSummaryTable[preType][9][s][0] = -1
                    cellTypeSummaryTable[preType][9][s][1] = -1

        return synapseLocations, cellSynapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable


    def _write_landmark_files(
        self,
        synapseLocations, 
        id1, id2, 
        cellName, 
        dirName,
    ):
        """Write out landmark files for each synapse location.  
        
        This is used in :func:`_generate_output_files` to write out landmark files for each synapse location.

        Args:
            synapseLocations (dict): Dictionary of synapse locations.
            id1 (str): ID for the current date.
            id2 (str): ID for the current process.
            cellName (str): Name of the postsynaptic cell.
            dirName (str): Directory name for the output files.
        """
        totalDirName = dirName + 'total_synapses/'
        if not os.path.exists(totalDirName):
            os.makedirs(totalDirName)
        apicalDirName = dirName + 'apical_synapses/'
        if not os.path.exists(apicalDirName):
            os.makedirs(apicalDirName)
        basalDirName = dirName + 'basal_synapses/'
        if not os.path.exists(basalDirName):
            os.makedirs(basalDirName)
        somaDirName = dirName + 'soma_synapses/'
        if not os.path.exists(somaDirName):
            os.makedirs(somaDirName)
        anatomical_areas = list(self.cells.keys())
        for anatomical_area in anatomical_areas:
            cellTypes = list(self.cells[anatomical_area].keys())
            for preType in cellTypes:
                preCellType = preType + '_' + anatomical_area
                allSynapses = synapseLocations[anatomical_area][preType]['Total']
                totalLandmarkName = totalDirName + '_'.join(
                    (cellName, 'total_synapses', preCellType, id1, id2))
                writer.write_landmark_file(totalLandmarkName, allSynapses)
                apicalSynapses = synapseLocations[anatomical_area][preType][
                    'ApicalDendrite']
                apicalLandmarkName = apicalDirName + '_'.join(
                    (cellName, 'apical_synapses', preCellType, id1, id2))
                writer.write_landmark_file(apicalLandmarkName, apicalSynapses)
                basalSynapses = synapseLocations[anatomical_area][preType]['BasalDendrite']
                basalLandmarkName = basalDirName + '_'.join(
                    (cellName, 'basal_synapses', preCellType, id1, id2))
                writer.write_landmark_file(basalLandmarkName, basalSynapses)
                somaSynapses = synapseLocations[anatomical_area][preType]['Soma']
                somaLandmarkName = somaDirName + '_'.join(
                    (cellName, 'soma_synapses', preCellType, id1, id2))
                writer.write_landmark_file(somaLandmarkName, somaSynapses)

    def _generate_output_files(
            self, 
            postCellName, 
            connectivityMap,
            connectedCells, 
            connectedCellsPerStructure,
            writeLandmarkFiles=False):
        '''Generates all summary files and writes output files.

        Generates and writes out summary files using 
        :func:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_cell_synapse_locations`,
        :func:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_anatomical_realization_map`, and
        :func:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_sample_connectivity_summary`.

        Used by :func:`~create_network_embedding_for_simulations` and
        :func:`~create_network_embedding_from_synapse_densities` to write output files to disk.

        Args:
            postCellName (str): Path to the postsynaptic :ref:`hoc_file_format` file.
            connectivityMap (list): 
                Connections between presynaptic cells and postsynaptic cell of the form
                (cell type, presynaptic cell index, synapse index). 
                Created by :func:`_create_anatomical_connectivity_map`.
            connectedCells (dict): Dictionary of connected cells.
            connectedCellsPerStructure (dict): Dictionary of connected cells per structure.

        Returns:
            None. Writes output files to disk.
        '''

        id1 = time.strftime('%Y%m%d-%H%M')
        id2 = str(os.getpid())
        outNamePrefix = postCellName[:-4]
        cellName = postCellName[:-4].split('/')[-1]
        dirName = outNamePrefix + '_synapses_%s_%s/' % (id1, id2)
        if not os.path.exists(dirName):
            os.makedirs(dirName)

        (
            synapseLocations, 
            cellSynapseLocations, 
            cellTypeSummaryTable, 
            anatomicalAreaSummaryTable
        ) = self._compute_summary_tables(
            connectedCells, 
            connectedCellsPerStructure
        )

        logger.info('    Writing output files...')

        if writeLandmarkFiles:
            self._write_landmark_files(
                synapseLocations, id1, id2, cellName, dirName)

        synapseName = dirName + '_'.join((cellName, 'synapses', id1, id2))
        writer.write_cell_synapse_locations(
            synapseName, 
            cellSynapseLocations,
            self.postCell.id)
        anatomicalID = synapseName.split('/')[-1] + '.syn'
        writer.write_anatomical_realization_map(
            synapseName, 
            connectivityMap,
            anatomicalID)
        summaryName = dirName + '_'.join((cellName, 'summary', id1, id2))
        writer.write_sample_connectivity_summary(
            summaryName,
            cellTypeSummaryTable,
            anatomicalAreaSummaryTable)
        logger.info('---------------------------')

    def _write_population_output_files(
        self, 
        postCellName, 
        populationDistribution, 
        connectivityMap, 
        synapseLocations, 
        cellSynapseLocations,
        cellTypeSummaryTable, 
        anatomicalAreaSummaryTable,
        writeLandmarkFiles=False
        ):
        '''Writes output files for precomputed summary files.

        Used by :func:`_create_network_embedding` to write output files to disk.

        Args:
            postCellName (str): Path to the postsynaptic :ref:`hoc_file_format` file.
            populationDistribution (dict): Population distribution of anatomical parameters.
            connectivityMap (list): 
                Connections between presynaptic cells and postsynaptic cell of the form
                (cell type, presynaptic cell index, synapse index). 
                Created by :func:`_create_anatomical_connectivity_map`.
            synapseLocations (dict): Synapse locations.
            cellSynapseLocations (dict): Cell synapse locations.
            cellTypeSummaryTable (dict): Summary table of cell types.
            anatomicalAreaSummaryTable (dict): Summary table of anatomical areas.

        Returns:
            None. Writes output files to disk.
        '''
        id1 = time.strftime('%Y%m%d-%H%M')
        id2 = str(os.getpid())
        outNamePrefix = postCellName[:-4]
        cellName = postCellName[:-4].split('/')[-1]
        dirName = outNamePrefix + '_synapses_%s_%s/' % (id1, id2)
        if not os.path.exists(dirName):
            os.makedirs(dirName)

        logger.info('---------------------------')
        logger.info('Writing output files...')

        if writeLandmarkFiles:
            self._write_landmark_files(
                synapseLocations, id1, id2, cellName, dirName)

        synapseName = dirName + '_'.join((cellName, 'synapses', id1, id2))
        writer.write_cell_synapse_locations(
            synapseName, 
            synapses=cellSynapseLocations,
            cellID=self.postCell.id)
        anatomicalID = synapseName.split('/')[-1] + '.syn'
        writer.write_anatomical_realization_map(
            synapseName, 
            functionalMap=connectivityMap,
            anatomicalID=anatomicalID)
        summaryName = dirName + '_'.join((cellName, 'summary', id1, id2))
        writer.write_population_and_sample_connectivity_summary(
            fname=summaryName, 
            populationDistribution=populationDistribution, 
            cellTypeSummaryData=cellTypeSummaryTable,
            columnSummaryData=anatomicalAreaSummaryTable)
        #=======================================================================
        # Begin BB3D-specific information for making results available (keep!!!)
        #=======================================================================
        print()
        print("Directory Name is ", dirName)
        print("CSV file name is ", summaryName)
        print()
        #=======================================================================
        # End BB3D-specific information for making results available (keep!!!)
        #=======================================================================
        print('---------------------------')

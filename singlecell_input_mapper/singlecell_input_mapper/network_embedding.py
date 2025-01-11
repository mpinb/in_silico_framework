'''Create anatomical realizations of connectivity.
In contrast to :py:mod:`single_cell_parser.network_embedding`, 
this module does not handle the activity of presynaptic populations, but provides functionality to fully investigate the network connectivity.

'''
from __future__ import absolute_import
import os
import sys
import time
import numpy as np
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
    Given a :py:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField` of boutons, 
    it computes all possible synapse densities that have non-zero overlap with every voxel this bouton field.
    These synapse density fields depend on the presence of post-synaptic dendrites in the bouton field,
    which in turn depends on the location and morphology of the post-syanptic neuron.
    The synapse density fields are further used as probability distributions to Poisson sample 
    mutiple realizations of synaptic connections between pre-synaptic cells, and the post-synaptic cell
    (see :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper.create_synapses`).
    
    See also:
        This is not the same class as :py:class:`single_cell_parser.network.NetworkMapper`.
        This class is specialized for anatomical reconstructions, 
        not synapse activations or simulation parameters.
    
    Attributes:
        cells (dict): 
            Presynaptic cells, ordered by anatomical area and cell type. 
            This attribute is filled by 
            :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper._create_presyn_cells`.
        connected_cells (dict): Indices of all active presynaptic cells, ordered by cell type.
        postCell (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): Reference to postsynaptic (multi-compartment) cell model.
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
            postCell (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): The cell object to map synapses onto.
            postCellType (str): The type of the postsynaptic cell.
            cellTypeNumbersSpreadsheet (dict): Number of presynaptic cells per cell type and anatomical_area.
        '''
        self.cells = {}
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
        It creates :paramref:`nrOfSamples` network realizations, and saves the most representative
        realization to disk. The most representative realization is determined by comparing
        the distribution of anatomical parameters across the population of realizations using
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper._get_representative_sample`.

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
        cellTypeSynapseDensities = self._precompute_anatomical_area_celltype_synapse_densities(
            boutonDensities)
        sampleConnectivityData = []
        cellTypeSpecificPopulation = []
        for i in range(nrOfSamples):
            logger.info('Generating network embedding sample {:d}'.format(i))
            self.postCell.remove_synapses('All')
            for anatomical_area in anatomical_areas:
                for preCellType in preCellTypes:
                    for preCell in self.cells[anatomical_area][preCellType]:
                        preCell.synapseList = None
            connectivityMap, connectedCells, connectedCellsPerStructure = \
                self._create_anatomical_realization(cellTypeSynapseDensities)
            (
                synapseLocations,
                cellSynapseLocations, 
                cellTypeSummaryTable, 
                anatomicalAreaSummaryTable
            ) = self._compute_summary_tables(
                connectedCells, 
                connectedCellsPerStructure
            )
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

        #        for testing convergence:
        #        self._test_population_convergence(nrOfSamples, sampleConnectivityData, postCellName)

        #        for testing basic functionality:
        #        connectivityMap, synapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable = sampleConnectivityData[0]
        #        self._write_output_files(postCellName, connectivityMap, synapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable)

        logger.info('Done generating network embedding!')
        logger.info('---------------------------')

    def create_network_embedding_for_simulations(
        self, 
        postCellName,
        boutonDensities,
        nrOfRealizations):
        '''Create multiple network realizations from a bouton density field.
        
        Main method used for creating fixed network connectivity for use in Monte Carlo simulations.
        Same principle as :py:meth:`~create_network_embedding`, but rather than taking
        the most representative sample, this method saves all :paramref:`nrOfRealizations` network 
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
            logger.info('Creating realization {:d} of {:d}'.format(
                i + 1, nrOfRealizations))
            self.postCell.remove_synapses('All')
            for anatomical_area in anatomical_areas:
                for preCellType in preCellTypes:
                    for preCell in self.cells[anatomical_area][preCellType]:
                        preCell.synapseList = None
            # for anatomical_area in anatomical_areas:
            #     for preCellType in preCellTypes:
            #         nrOfDensities = len(cellTypeSynapseDensities[anatomical_area][preCellType])
            #         if not nrOfDensities:
            #             continue
            #         #=======================================================================
            #         # for testing purposes: write 3D synapse density
            #         #=======================================================================
            ##          for structure in self.postCell.structures.keys():
            ##              for i in range(nrOfDensities):
            ##                  outDensity = cellTypeSynapseDensities[anatomical_area][preCellType][i][structure]
            ##                  outNamePrefix = postCellName[:-4]
            ##                  synapseDensityName = '_'.join((outNamePrefix,'synapse_density',structure,anatomical_area,preCellType,str(i)))
            ##                  writer.write_scalar_field(synapseDensityName, outDensity)

            #         print '---------------------------'
            #         print 'Computed %d synapse densities of type %s in anatomical_area %s!' % (nrOfDensities,preCellType,anatomical_area)
            #         print 'Assigning synapses from cell type %s in anatomical_area %s' % (preCellType, anatomical_area)
            #         totalNumber = len(self.cells[anatomical_area][preCellType])
            #         densityIDs = np.random.randint(0, nrOfDensities, totalNumber)
            #         count = 0
            #         skipCount = 0
            #         for i in range(totalNumber):
            #             preCell = self.cells[anatomical_area][preCellType][i]
            #             count += 1
            #             print '    Computing synapses for presynaptic cell %d of %d...\r' %  (count,totalNumber),
            #             sys.stdout.flush()
            #             densityID = densityIDs[i]
            #             synapseDensity = cellTypeSynapseDensities[anatomical_area][preCellType][densityID]
            #             if synapseDensity is None:
            #                 skipCount += 1
            #                 continue
            #             self.mapper.synDist = synapseDensity
            #             synapseType = '_'.join((preCellType,anatomical_area))
            #             preCell.synapseList = self.mapper.create_synapses(synapseType)
            #             for newSyn in preCell.synapseList:
            #                 newSyn.preCell = preCell
            #         print ''
            #         print '    Skipped %d empty synapse densities...' % skipCount

            # connectivityMap, connectedCells, connectedCellsPerStructure = self._create_anatomical_connectivity_map()
            connectivityMap, connectedCells, connectedCellsPerStructure = \
                self._create_anatomical_realization(cellTypeSynapseDensities)
            self._generate_output_files(
                postCellName, 
                connectivityMap,
                connectedCells,
                connectedCellsPerStructure)
            (synapseLocations,  # unused 
             cellSynapseLocations,  # unused
             cellTypeSummaryTable, 
             anatomicalAreaSummaryTable  # unused
             ) = self._compute_summary_tables(
                connectedCells, connectedCellsPerStructure)
            cellTypeSpecificPopulation.append(cellTypeSummaryTable)
            logger.info('---------------------------')

        # print '    Writing output files...'
        # populationDistribution = self._compute_parameter_distribution(cellTypeSpecificPopulation)
        # outNamePrefix = postCellName[:-4]
        # summaryName = outNamePrefix + '_synapses_%d_realizations_summary' % nrOfRealizations
        # writer.write_population_connectivity_summary(summaryName, populationDistribution)

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
                logger.info('---------------------------')
                logger.info('Assigning synapses from cell type {:s} in anatomical_area {:s}'.
                      format(preCellType, anatomical_area))
                nrOfDensities = len(cellTypeSynapseDensities[anatomical_area][preCellType])
                if not nrOfDensities:
                    continue
                totalNumber = len(self.cells[anatomical_area][preCellType])
                count = 0
                for preCell in self.cells[anatomical_area][preCellType]:
                    count += 1
                    logger.info(
                        '    Computing synapses for presynaptic cell {:d} of {:d}...\r'
                        .format(count, totalNumber))  #, end=' ')
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
                logger.info('')

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
                logger.info('---------------------------')
                logger.info(
                    'Computing synapse densities from cell type %s in anatomical_area {:s}'
                    .format(preCellType, anatomical_area))
                for boutons in boutonDensities[anatomical_area][preCellType]:
                    synapseDensities[anatomical_area][preCellType].append(
                        synapseDensityComputation.compute_synapse_density(
                            boutons, preCellType))
        logger.info('---------------------------')
        return synapseDensities

    def _create_presyn_cells(self):
        '''Creates presynaptic cells.

        Should be done before creating anatomical synapses.
        Fills the :py:attr:`~cells` attribute with a nested dictionary of presynaptic cells,
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
                nrOfCellsPerType = self.cellTypeNumbersSpreadsheet[anatomical_area][
                    cellType]
                for i in range(nrOfCellsPerType):
                    newCell = PointCell(anatomical_area, cellType)
                    self.cells[anatomical_area][cellType].append(newCell)
                    cellIDs += 1
                logger.info(
                    '    Created {:d} presynaptic cells of type {:s} in anatomical_area {:s}'
                    .format(nrOfCellsPerType, cellType, anatomical_area))
        logger.info('Created {:d} presynaptic cells in total'.format(cellIDs))
        logger.info('---------------------------')

    def _create_anatomical_realization(self, cellTypeSynapseDensities):
        '''Create a single anatomical realization of synapses.

        This is the main method for computing synapse/connectivity realization.
        Given one or more pre-computed density fields of synapses (see e.g. 
        :py:meth:`~_precompute_anatomical_area_celltype_synapse_densities`), this method 
        creates a :py:class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper`
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
                #=======================================================================
                # for testing purposes: write 3D synapse density
                #=======================================================================


                # for structure in self.postCell.structures.keys():
                #     for i in range(nrOfDensities):
                #         outDensity = cellTypeSynapseDensities[anatomical_area][preCellType][i][structure]
                #         outNamePrefix = postCellName[:-4]
                #         synapseDensityName = '_'.join((outNamePrefix,'synapse_density',structure,anatomical_area,preCellType,str(i)))
                #         writer.write_scalar_field(synapseDensityName, outDensity)

                logger.info('---------------------------')
                logger.info(
                    'Computed {:d} synapse densities of type {:s} in anatomical_area {:s}!'
                    .format(nrOfDensities, preCellType, anatomical_area))
                logger.info('Assigning synapses from cell type {:s} in anatomical_area {:s}'.
                      format(preCellType, anatomical_area))
                totalNumber = len(self.cells[anatomical_area][preCellType])
                densityIDs = np.random.randint(0, nrOfDensities, totalNumber)
                count = 0
                skipCount = 0
                for i in range(totalNumber):
                    preCell = self.cells[anatomical_area][preCellType][i]
                    count += 1
                    logger.info(
                        '    Computing synapses for presynaptic cell {:d} of {:d}...\r'
                        .format(count, totalNumber))  #, end=' ')
                    sys.stdout.flush()
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
                logger.info('')
                logger.info('    Skipped {:d} empty synapse densities...'.format(skipCount))

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
        
        Using parameters in :py:attr:`cellTypeSummaryTable` on a per cell type basis:

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
            dict: dictionary organized the same way as :py:attr:`cellTypeSummaryTable`,
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

    def _compute_summary_tables(
            self, 
            connectedCells,
            connectedCellsPerStructure):
        '''Computes all summary data.

        Compute the following summary data:

        - numbers of synapses per cell type/anatomical_area,
        - distance of synapses to soma, convergence etc.

        Used by :py:meth:`~create_network_embedding` and 
        :py:meth:`~create_network_embedding_for_simulations`.

        Args:
            connectedCells (dict): Dictionary of connected cells.
            connectedCellsPerStructure (dict): Dictionary of connected cells per structure.
        
        Returns: 
            tuple: synapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable
        '''
        logger.info('---------------------------')
        logger.info('Calculating results summary')
        logger.info('    Computing path length to soma for all synapses...')
        for preCellType in list(self.postCell.synapses.keys()):
            for synapse in self.postCell.synapses[preCellType]:
                attachedSec = self.postCell.sections[synapse.secID]
                if attachedSec.label == 'Soma':
                    dist = 0.0
                else:
                    dist = self.postCell.distance_to_soma(
                        attachedSec, synapse.x)
                synapse.distanceToSoma = dist

        synapseLocations = {}
        cellSynapseLocations = {}
        cellTypeSummaryTable = {}
        anatomicalAreaSummaryTable = {
        }  # note- this could probably be tidied using I.defaultdict
        anatomical_areas = list(self.cells.keys())
        for anatomical_area in anatomical_areas:
            cellTypes = list(self.cells[anatomical_area].keys())
            for preType in cellTypes:
                preCellType = preType + '_' + anatomical_area
                if anatomical_area not in anatomicalAreaSummaryTable:
                    anatomicalAreaSummaryTable[anatomical_area] = {}
                if anatomical_area not in synapseLocations:
                    synapseLocations[anatomical_area] = {}
                if preType not in cellTypeSummaryTable:
                    #                    [nrOfSynapses,nrConnectedCells,nrPreCells,convergence,distanceMean,distanceSTD]
                    cellTypeSummaryTable[preType] = [0, 0, 0, 0.0, [], -1]
                    cellTypeSynapsesPerStructure = {}
                    cellTypeSynapsesPerStructure['ApicalDendrite'] = 0
                    cellTypeSynapsesPerStructure['BasalDendrite'] = 0
                    cellTypeSynapsesPerStructure['Soma'] = 0
                    cellTypeConnectionsPerStructure = {}
                    cellTypeConnectionsPerStructure['ApicalDendrite'] = 0
                    cellTypeConnectionsPerStructure['BasalDendrite'] = 0
                    cellTypeConnectionsPerStructure['Soma'] = 0
                    cellTypeConvergencePerStructure = {}
                    cellTypeConvergencePerStructure['ApicalDendrite'] = 0.0
                    cellTypeConvergencePerStructure['BasalDendrite'] = 0.0
                    cellTypeConvergencePerStructure['Soma'] = 0.0
                    cellTypeDistancesPerStructure = {}
                    cellTypeDistancesPerStructure['ApicalDendrite'] = [[], -1]
                    cellTypeDistancesPerStructure['BasalDendrite'] = [[], -1]
                    cellTypeSummaryTable[preType].append(
                        cellTypeSynapsesPerStructure)
                    cellTypeSummaryTable[preType].append(
                        cellTypeConnectionsPerStructure)
                    cellTypeSummaryTable[preType].append(
                        cellTypeConvergencePerStructure)
                    cellTypeSummaryTable[preType].append(
                        cellTypeDistancesPerStructure)
                try:
                    allSynapses = [
                        syn.coordinates
                        for syn in self.postCell.synapses[preCellType]
                    ]
                    cellSynapseLocations[preCellType] = [
                        (syn.preCellType, syn.secID, syn.x)
                        for syn in self.postCell.synapses[preCellType]
                    ]
                    apicalSynapses = []
                    basalSynapses = []
                    somaSynapses = []
                    nrOfSynapses = len(self.postCell.synapses[preCellType])
                    nrConnectedCells = connectedCells[preCellType]
                    nrConnectedCellsApical = connectedCellsPerStructure[
                        preCellType]['ApicalDendrite']
                    nrConnectedCellsBasal = connectedCellsPerStructure[
                        preCellType]['Dendrite']
                    nrConnectedCellsSoma = connectedCellsPerStructure[
                        preCellType]['Soma']
                    nrOfApicalSynapses = 0
                    nrOfBasalSynapses = 0
                    nrOfSomaSynapses = 0
                    tmpDistances = []
                    tmpDistancesApical = []
                    tmpDistancesBasal = []
                    for synapse in self.postCell.synapses[preCellType]:
                        secLabel = self.postCell.sections[synapse.secID].label
                        if secLabel == 'ApicalDendrite':
                            nrOfApicalSynapses += 1
                            tmpDistancesApical.append(synapse.distanceToSoma)
                            apicalSynapses.append(synapse.coordinates)
                        if secLabel == 'Dendrite':
                            nrOfBasalSynapses += 1
                            tmpDistancesBasal.append(synapse.distanceToSoma)
                            basalSynapses.append(synapse.coordinates)
                        if secLabel == 'Soma':
                            nrOfSomaSynapses += 1
                            somaSynapses.append(synapse.coordinates)
                        tmpDistances.append(synapse.distanceToSoma)
                    distanceMean = np.mean(tmpDistances)
                    distanceSTD = np.std(tmpDistances)
                    if len(tmpDistancesApical):
                        distanceApicalMean = np.mean(tmpDistancesApical)
                        distanceApicalSTD = np.std(tmpDistancesApical)
                    else:
                        distanceApicalMean = -1
                        distanceApicalSTD = -1
                    if len(tmpDistancesBasal):
                        distanceBasalMean = np.mean(tmpDistancesBasal)
                        distanceBasalSTD = np.std(tmpDistancesBasal)
                    else:
                        distanceBasalMean = -1
                        distanceBasalSTD = -1
                except KeyError:
                    allSynapses = []
                    cellSynapseLocations[preCellType] = []
                    apicalSynapses = []
                    basalSynapses = []
                    somaSynapses = []
                    nrOfSynapses = 0
                    nrConnectedCells = 0
                    nrConnectedCellsApical = 0
                    nrConnectedCellsBasal = 0
                    nrConnectedCellsSoma = 0
                    nrOfApicalSynapses = 0
                    nrOfBasalSynapses = 0
                    nrOfSomaSynapses = 0
                    tmpDistances = []
                    tmpDistancesApical = []
                    tmpDistancesBasal = []
                    distanceMean = -1
                    distanceSTD = -1
                    distanceApicalMean = -1
                    distanceApicalSTD = -1
                    distanceBasalMean = -1
                    distanceBasalSTD = -1
                if nrOfApicalSynapses + nrOfBasalSynapses + nrOfSomaSynapses != nrOfSynapses:
                    errstr = 'Logical error: Number of synapses does not add up'
                    raise RuntimeError(errstr)
                logger.info('    Created {:d} synapses of type {:s}!'.format(
                    nrOfSynapses, preCellType))
                #===============================================================
                # anatomical_area- and cell type-specific data
                #===============================================================
                nrPreCells = len(self.cells[anatomical_area][preType])
                synapsesPerStructure = {}
                synapsesPerStructure['ApicalDendrite'] = nrOfApicalSynapses
                synapsesPerStructure['BasalDendrite'] = nrOfBasalSynapses
                synapsesPerStructure['Soma'] = nrOfSomaSynapses
                connectionsPerStructure = {}
                connectionsPerStructure[
                    'ApicalDendrite'] = nrConnectedCellsApical
                connectionsPerStructure['BasalDendrite'] = nrConnectedCellsBasal
                connectionsPerStructure['Soma'] = nrConnectedCellsSoma
                convergence = float(nrConnectedCells) / float(nrPreCells)
                convergencePerStructure = {}
                convergencePerStructure['ApicalDendrite'] = float(
                    nrConnectedCellsApical) / float(nrPreCells)
                convergencePerStructure['BasalDendrite'] = float(
                    nrConnectedCellsBasal) / float(nrPreCells)
                convergencePerStructure['Soma'] = float(
                    nrConnectedCellsSoma) / float(nrPreCells)
                distancesPerStructure = {}
                distancesPerStructure[
                    'ApicalDendrite'] = distanceApicalMean, distanceApicalSTD
                distancesPerStructure[
                    'BasalDendrite'] = distanceBasalMean, distanceBasalSTD
                anatomicalAreaSummaryTable[anatomical_area][preType] = [
                    nrOfSynapses, nrConnectedCells, nrPreCells, convergence,
                    distanceMean, distanceSTD
                ]
                anatomicalAreaSummaryTable[anatomical_area][preType].append(synapsesPerStructure)
                anatomicalAreaSummaryTable[anatomical_area][preType].append(connectionsPerStructure)
                anatomicalAreaSummaryTable[anatomical_area][preType].append(convergencePerStructure)
                anatomicalAreaSummaryTable[anatomical_area][preType].append(distancesPerStructure)
                #                totalLandmarkName = totalDirName + '_'.join((cellName,'total_synapses',preCellType,id1,id2))
                #                writer.write_landmark_file(totalLandmarkName, allSynapses)
                #                apicalLandmarkName = apicalDirName + '_'.join((cellName,'apical_synapses',preCellType,id1,id2))
                #                writer.write_landmark_file(apicalLandmarkName, apicalSynapses)
                #                basalLandmarkName = basalDirName + '_'.join((cellName,'basal_synapses',preCellType,id1,id2))
                #                writer.write_landmark_file(basalLandmarkName, basalSynapses)
                #                somaLandmarkName = somaDirName + '_'.join((cellName,'soma_synapses',preCellType,id1,id2))
                #                writer.write_landmark_file(somaLandmarkName, somaSynapses)
                synapseLocations[anatomical_area][preType] = {}
                synapseLocations[anatomical_area][preType]['Total'] = allSynapses
                synapseLocations[anatomical_area][preType][
                    'ApicalDendrite'] = apicalSynapses
                synapseLocations[anatomical_area][preType]['BasalDendrite'] = basalSynapses
                synapseLocations[anatomical_area][preType]['Soma'] = somaSynapses
                #===============================================================
                # cell type-specific data summary
                #===============================================================
                cellTypeSummaryTable[preType][0] += nrOfSynapses
                cellTypeSummaryTable[preType][1] += nrConnectedCells
                cellTypeSummaryTable[preType][2] += nrPreCells
                cellTypeSummaryTable[preType][4] += tmpDistances
                cellTypeSummaryTable[preType][6][
                    'ApicalDendrite'] += nrOfApicalSynapses
                cellTypeSummaryTable[preType][6][
                    'BasalDendrite'] += nrOfBasalSynapses
                cellTypeSummaryTable[preType][6]['Soma'] += nrOfSomaSynapses
                cellTypeSummaryTable[preType][7][
                    'ApicalDendrite'] += nrConnectedCellsApical
                cellTypeSummaryTable[preType][7][
                    'BasalDendrite'] += nrConnectedCellsBasal
                cellTypeSummaryTable[preType][7]['Soma'] += nrConnectedCellsSoma
                cellTypeSummaryTable[preType][9]['ApicalDendrite'][
                    0] += tmpDistancesApical
                cellTypeSummaryTable[preType][9]['BasalDendrite'][
                    0] += tmpDistancesBasal

        for preType in list(cellTypeSummaryTable.keys()):
            nrConnectedCellsTotal = cellTypeSummaryTable[preType][1]
            nrPreCellsTotal = cellTypeSummaryTable[preType][2]
            cellTypeSummaryTable[preType][3] = float(
                nrConnectedCellsTotal) / float(nrPreCellsTotal)
            distancesTotal = cellTypeSummaryTable[preType][4]
            if len(distancesTotal):
                cellTypeSummaryTable[preType][4] = np.mean(distancesTotal)
                cellTypeSummaryTable[preType][5] = np.std(distancesTotal)
            else:
                cellTypeSummaryTable[preType][4] = -1
                cellTypeSummaryTable[preType][5] = -1
            nrConnectedCellsApical = cellTypeSummaryTable[preType][7][
                'ApicalDendrite']
            cellTypeSummaryTable[preType][8]['ApicalDendrite'] = float(
                nrConnectedCellsApical) / float(nrPreCellsTotal)
            nrConnectedCellsBasal = cellTypeSummaryTable[preType][7][
                'BasalDendrite']
            cellTypeSummaryTable[preType][8]['BasalDendrite'] = float(
                nrConnectedCellsBasal) / float(nrPreCellsTotal)
            nrConnectedCellsSoma = cellTypeSummaryTable[preType][7]['Soma']
            cellTypeSummaryTable[preType][8]['Soma'] = float(
                nrConnectedCellsSoma) / float(nrPreCellsTotal)
            distancesApical = cellTypeSummaryTable[preType][9][
                'ApicalDendrite'][0]
            if len(distancesApical):
                cellTypeSummaryTable[preType][9]['ApicalDendrite'][0] = np.mean(
                    distancesApical)
                cellTypeSummaryTable[preType][9]['ApicalDendrite'][1] = np.std(
                    distancesApical)
            else:
                cellTypeSummaryTable[preType][9]['ApicalDendrite'][0] = -1
                cellTypeSummaryTable[preType][9]['ApicalDendrite'][1] = -1
            distancesBasal = cellTypeSummaryTable[preType][9]['BasalDendrite'][
                0]
            if len(distancesBasal):
                cellTypeSummaryTable[preType][9]['BasalDendrite'][0] = np.mean(
                    distancesBasal)
                cellTypeSummaryTable[preType][9]['BasalDendrite'][1] = np.std(
                    distancesBasal)
            else:
                cellTypeSummaryTable[preType][9]['BasalDendrite'][0] = -1
                cellTypeSummaryTable[preType][9]['BasalDendrite'][1] = -1

        return synapseLocations, cellSynapseLocations, cellTypeSummaryTable, anatomicalAreaSummaryTable

    def _generate_output_files(
            self, 
            postCellName, 
            connectivityMap,
            connectedCells, 
            connectedCellsPerStructure):
        '''Generates all summary files and writes output files.

        Generates and writes out summary files using 
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_cell_synapse_locations`,
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_anatomical_realization_map`, and
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.writer.write_sample_connectivity_summary`.

        Used by :py:meth:`~create_network_embedding_for_simulations` and
        :py:meth:`~create_network_embedding_from_synapse_densities` to write output files to disk.

        Args:
            postCellName (str): Path to the postsynaptic :ref:`hoc_file_format` file.
            connectivityMap (list): 
                Connections between presynaptic cells and postsynaptic cell of the form
                (cell type, presynaptic cell index, synapse index). 
                Created by :py:meth:`_create_anatomical_connectivity_map`.
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
        anatomicalAreaSummaryTable
        ):
        '''Writes output files for precomputed summary files.

        Used by :py:meth:`_create_network_embedding` to write output files to disk.

        Args:
            postCellName (str): Path to the postsynaptic :ref:`hoc_file_format` file.
            populationDistribution (dict): Population distribution of anatomical parameters.
            connectivityMap (list): 
                Connections between presynaptic cells and postsynaptic cell of the form
                (cell type, presynaptic cell index, synapse index). 
                Created by :py:meth:`_create_anatomical_connectivity_map`.
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

        logger.info('---------------------------')
        logger.info('Writing output files...')

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
        writer.write_population_and_sample_connectivity_summary(
            summaryName, 
            populationDistribution, 
            cellTypeSummaryTable,
            anatomicalAreaSummaryTable)
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

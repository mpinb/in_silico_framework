'''Connect and activate presynaptic neuron populations.

This module either creates or reads in an existing network realization, and connects the synapses
to presynaptic cells with known cell type and activity patterns. A network realization 
(or anatomical realization) with known presynaptic origin is referred to as a functional realization.
The result of a network activation is a :ref:`syn_activation_format` file.

Reading existing network realizations
-------------------------------------
Network realizations that have been created with :py:mod:`~singlecell_input_mapper`'s :py:mod:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding`
can be read in here using the method :py:meth:`create_saved_network2`. 
This approach allows for the most fine-grained control over the network realization, as it offloads all the network embedding details to the specialized
:py:mod:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding` module.

Creating new network realizations
---------------------------------
Creating a new network realization from scratch can be done using the ``convergence`` parameter in the
:ref:`network_parameters_format` file.
Convergence is the probability of a connection existing between the :py:class:`~single_cell_parser.cell.Cell` and a presynaptic cell.
It is specific for each presynaptic cell type, and depends on the postsynaptic cell type.
This approach is used by :py:meth:`~single_cell_parser.network_mapper.NetworkMapper.create_functional_realization`
and :py:meth:`~single_cell_parser.network_mapper.NetworkMapper.create_network`.

See also:
    :py:mod:`~singlecell_input_mapper.singlecell_input_mapper`.
'''

import os
import time
from collections import Sequence
import numpy as np
from .cell import PointCell, SpikeTrain
from . import reader
from . import writer
from .synapse_mapper import SynapseMapper
#import synapse
from neuron import h
import six
import math
import logging

from . import network_modify_functions

__author__  = "Robert Egger"
__credits__ = ["Robert Egger", "Arco Bast"]

logger = logging.getLogger("ISF").getChild(__name__)

class NetworkMapper:
    '''Map active presynaptic cells to a multi-compartmental neuron model.
    
    See also:
        This is not the same class as :py:class:`singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`.
        This class is specialized for synapse activations and simulation control and re-creating already existing network realizations, 
        not for creating such anatomical network realizations from empirical data.
    
    Attributes:
        cells (dict): dictionary holding all presynaptic cells ordered by cell type.
        connected_cells (dict): dictionary holding indices of all active presynaptic cells ordered by cell type.
        postCell (:py:class:`~single_cell_parser.cell.Cell`): reference to postsynaptic (multi-compartment) cell model.
        nwParam (:py:class:`~sumatra.parameters.NTParameterSet`): network parameter set (see :ref:`network_parameters_format` for more info).
        simParam (:py:class:`~sumatra.parameters.NTParameterSet`): simulation parameter set.
    '''

    def __init__(self, postCell, nwParam, simParam=None):
        '''Initialize NetworkMapper.      

        Args:
            postCell (:py:class:`~single_cell_parser.cell.Cell`): The cell to map synapses onto.
            nwParam (:py:class:`~sumatra.parameters.NTParameterSet`): The network parameter set (see :ref:`network_parameters_format` for more info).
            simParam (:py:class:`~sumatra.parameters.NTParameterSet`): The simulation parameter set. Default: None.
        '''
        self.cells = {}
        self.connected_cells = {}
        self.postCell = postCell
        self.nwParam = nwParam
        self.simParam = simParam
        postCell.network_param = nwParam
        postCell.network_sim_param = simParam

    def create_network(self, synWeightName=None, change=None):
        '''Set up a network from network parameters. 

        Here, these synapses can then be connected to activity sources and activated.

        Steps:

        1. Assign anatomical synapses to postsynaptic cell using :py:meth:`~_assign_anatomical_synapses`.
        2. Create presynaptic cells for these synapses using :py:meth:`~_create_presyn_cells` (multiple synapses can originate from the same presynaptic cell).
        3. Generate activation patters for each presynaptic cell, depending on whether they are a :py:class:`~single_cell_parser.cell.PointCell` or :py:class:`~single_cell_parser.cell.SpikeTrain` using :py:meth:`_activate_presyn_cells`.
        4. Connect the presynaptic cells to the anatomical synapses using :py:meth:`~_connect_functional_synapses`.
        5. Connect to spike train sources using :py:meth:`_connect_spike_trains`.

        Args:
            synWeightName (str): Name of the file containing the synapse weights. Default: None.
            change (float): Change in presynaptic release probability. Default: None.

        Returns:
            None. Updates the class attributes (in contrast to :py:meth:`~create_functional_realization, which writes to disk`).
        '''
        logger.info('***************************')
        logger.info('creating network')
        logger.info('***************************')
        self._assign_anatomical_synapses()
        self._create_presyn_cells()
        self._activate_presyn_cells()
        self._connect_functional_synapses()
        spikeTrainWeights = None
        if synWeightName:
            spikeTrainWeights, locations = reader.read_synapse_weight_file(
                synWeightName)
        # awkward temporary implementation of prelease change during simulation time window
        self._connect_spike_trains(spikeTrainWeights, change)
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def create_saved_network2(self, synWeightName=None, full_network=False):
        '''Recreate a saved network embedding and activate it.

        Commonly used to assign synapse locations that have been previously generated
        with :py:mod:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding`.

        Here, these synapses can then be connected to activity sources and activated.
        This is the most recent version where point cells and spike trains can be integrated into the same presynaptic cell
        
        Steps:

        1. Assigns anatomical synapses to postsynaptic cell using :py:meth:`~_assign_anatomical_synapses`.
        2. Creates presynaptic cells for these synapses using :py:meth:`~_create_presyn_cells` (multiple synapses can originate from the same presynaptic cell).
        3. Generates activation patters for each presynaptic cell, depending on whether they are a :py:class:`~single_cell_parser.cell.PointCell` or :py:class:`~single_cell_parser.cell.SpikeTrain` using :py:meth:`_activate_presyn_cells`.
        4. Connects the presynaptic cells to the anatomical synapses using :py:meth:`~_map_complete_anatomical_realization`.
        5. Applies network modify functions (if any) using :py:meth:`_apply_network_modification_functions`.

        Args:
            synWeightName (str): 
                Name of the file containing the synapse weights. Default: None.
            full_network (bool): 
                If True, all synapses are created, even if they were not active. 
                If False, only recreates the synapses that were active, and re-assigns their IDs to be sequential.
                Default: False.
        
        '''
        logger.info('***************************')
        logger.info('creating saved network')
        logger.info('***************************')
        
        self._assign_anatomical_synapses()
        self._create_presyn_cells()
        self._activate_presyn_cells()
        
        weights = None
        if synWeightName:
            weights, locations = reader.read_synapse_weight_file(synWeightName)
        self._map_complete_anatomical_realization(
            weights,
            full_network=full_network)
        self._apply_network_modify_functions()
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def reconnect_saved_synapses(self, synInfoName, synWeightName=None, include_silent_synapses = False):
        '''Set up a network from a saved :ref:`syn_activation_format` file.

        This method does not only create the synapse locations from previously saved files,
        but also activates them according to the saved activation times.
        This is in contrast to e.g. :py:meth:`~create_saved_network2`, which generates
        the activations from scratch.
        
        Args:
            synInfoName (str): 
                Name of the :ref:`syn_activation_format` file.
            synWeightName (str, optional): 
                Name of the file containing the synapse weights. Default: None.
            include_silent_synapses: 
                Also create synapses that were not active. 
                This maintains the synapse id, but maybe slightly slower.

        .. deprecated:: 0.1
           The ``synWeightName`` argument is deprecated.
        '''
        logger.info('***************************')
        logger.info('creating saved network and')
        logger.info('activating synapses with saved times')
        logger.info('***************************')
        
        weights = None
        locations = None
        if synWeightName:
            weights, locations = reader.read_synapse_weight_file(synWeightName)
        
        if isinstance(synInfoName, str):
            synInfo = reader.read_synapse_activation_file(synInfoName)
        else:
            synInfo = synInfoName
        if include_silent_synapses:
            def complete_syn(syn):
                "adds synapses that do not have any activity back in such that synapse ID matches the id of the synapse"
                syn_out = {}
                for syntype in syn:
                    syn_out[syntype] = []
                    syn_id = 0
                    syn_index = 0
                    while True:
                        try:
                            s = syn[syntype][syn_id]
                        except IndexError:
                            break
                        if syn_index < s[0]:
                            syn_out[syntype].append([syn_index, -1, -1, [], -1])
                            syn_index += 1
                        else:
                            syn_out[syntype].append(s)
                            syn_id += 1 
                            syn_index += 1
                return syn_out
            synInfo = complete_syn(synInfo)
        synTypes = list(synInfo.keys())
        for synType in synTypes:
            logger.info(
                'Creating synapses and activation times for cell type {:s}'.
                format(synType))
            synParameters = self.nwParam[synType].synapses
            for receptorType in list(synParameters.receptors.keys()):
                if 'weightDistribution' in synParameters.receptors[
                        receptorType]:
                    weightStr = synParameters.receptors[
                        receptorType].weightDistribution
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution {:s}'
                        .format(receptorType, weightStr))
                else:
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution uniform'
                        .format(receptorType))
            # for syn in synInfo[synType]:
            for i in range(len(synInfo[synType])):
                syn = synInfo[synType][i]
                synID, secID, ptID, synTimes, somaDist = syn
                #                logger.info '\tactivating synapse of type %s' % synType
                #                logger.info '\tsecID: %d' % secID
                #                logger.info '\tptID: %d' % ptID
                #                logger.info '\ttimes: %s' % ','.join([str(t) for t in synTimes])
                newCell = PointCell(synTimes)
                newCell.play()
                if synType not in self.cells:
                    self.cells[synType] = []
                self.cells[synType].append(newCell)
                synx = self.postCell.sections[secID].relPts[ptID]
                newSyn = self.postCell.add_synapse(secID, ptID, synx, synType)
                if weights:
                    # Reading in weights from a synapse weight file
                    # DEPRECATED
                    newSyn.weight = weights[synType][synID]
                    #===========================================================
                    # testLoc = locations[synType][synID]
                    # if testLoc[0] != secID or testLoc[1] != ptID:
                    #    errstr = 'secID %d != secID %d --- ptID %d != ptID %d' % (testLoc[0], secID, testLoc[1], ptID)
                    #    raise RuntimeError(errstr)
                    #===========================================================
                else:
                    # Getting the weights from the network parameters
                    for recepStr in list(synParameters.receptors.keys()):
                        receptor = synParameters.receptors[recepStr]
                        self._assign_synapse_weights(receptor, recepStr, newSyn)
                activate_functional_synapse(
                    newSyn,
                    self.postCell,
                    newCell,
                    synParameters,
                    forceSynapseActivation=True)
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def create_functional_realization(self):
        '''Create a new functional connectivity realization from an existing network parameter file based on ``convergence``.

        Network parameterfiles already have backlinks to :ref:`con_file_format` files,
        which contain the anatomical realization of the network.
        This method creates its own realizations based on the ``convergence`` parameter in the network parameters,
        and saves the resulting :ref:`con_file_format` file and adapted network parameter file in the working directory.
        It does not assign activity to these presynaptic cells.

        See also:
            :py:meth:`_create_functional_connectivity_map` on how the ``convergence`` parameter is used
            for anatomical realizations.

        Attention:
            Give this functional realization a (somewhat) unique name!   
            then save it at the same location as the anatomical realization,  
            and create a network parameter file with the anatomical and       
            corresponding functional realizations already in it.
                 
        Attention: 
            Assumes path names to anatomical realization files     
            work from the working directory! So they should be correct relative, or
            preferably absolute paths.

        Returns:
            None. Writes the resulting :ref:`con_file_format` files and adapted 
            :ref:`network_parameters_format` file to disk (in contrast to :py:meth:`~create_network`).
        '''
        allParam = self.nwParam
        self.nwParam = allParam.network
        self._assign_anatomical_synapses()  # reads .syn
        self._create_presyn_cells()
        functionalMap = self._create_functional_connectivity_map()  # uses convergence
        id1 = time.strftime('%Y%m%d-%H%M')
        id2 = str(os.getpid())
        for synType in functionalMap:
            tmpName = self.nwParam[synType].synapses.distributionFile
            splitName = tmpName.split('/')
            anatomicalID = splitName[-1]
            outName = tmpName[:-4]
            outName += '_functional_map_%s_%s.con' % (id1, id2)
            # write .con file
            writer.write_functional_realization_map(
                outName,
                functionalMap[synType],
                anatomicalID)
            allParam.network[synType].synapses.connectionFile = outName
        paramName = allParam.info.name
        paramName += '_functional_map_%s_%s.param' % (id1, id2)
        allParam.info.name += '_functional_map_%s_%s' % (id1, id2)
        allParam.save(paramName)

    def re_init_network(self, replayMode=False):
        """Reinitialize the network for a new simulation run.

        Sets all the presynaptic cells to ``off``.

        See also:
            :py:meth:`~single_cell_parser.cell.Cell.turn_off` for more information on turning cells off.
        
        Args:
            replayMode (bool): 
                Whether or not to destroy the presynaptic cells as well. Default: False.
                Set to False if you want to keep the presynaptic cells for a new simulation run.
                Set to True if you want to recreate a new network realization (not taken care of in this function)."""
        for synType in list(self.cells.keys()):
            for cell in self.cells[synType]:
                cell.turn_off()
                # cell.synapseList = None
            if replayMode:
                self.cells[synType] = []

    # Private methods
    
    def _assign_anatomical_synapses(self):
        '''Assigns synapses to postsynaptic cell from :ref:`syn_file_format` files.

        Fetches the correct :ref:`syn_file_format` files from the network parameters.
        Assigns all synapses from these files to the postsynaptic cell.
        
        This is the first step in creating a functional network.
        '''
        loadSynapses = False
        for preType in list(self.nwParam.keys()):
            if preType not in self.postCell.synapses:
                loadSynapses = True
                break
        if loadSynapses:
            for preType in list(self.nwParam.keys()):
                if preType == 'network_modify_functions':  # not a synapse type
                    continue
                logger.info(
                    'mapping anatomical synapse locations for cell type {:s}'.
                    format(preType))
                synapseFName = self.nwParam[preType].synapses.distributionFile
                # ready .syn file
                synDist = reader.read_synapse_realization(synapseFName)
                #                TODO: implement fix that allows mapping of synapses of different
                #                types from the same file in addition to the current setup.
                #                Possible fix follows:
                for synType in list(synDist.keys()):
                    if synType in self.postCell.synapses:
                        synDist.pop(synType)
                    else:
                        logger.info(
                            'mapping anatomical synapse locations for cell type {:s}'
                            .format(synType))
                mapper = SynapseMapper(self.postCell, synDist)
                mapper.map_synapse_realization()
            logger.info('---------------------------')
        else:
            logger.info('anatomical synapse locations already mapped')
            logger.info('---------------------------')

    def _apply_network_modify_functions(self):
        """Apply network modify functions to the network.
        
        Network modify functions can be found in the module :py:mod:`~single_cell_parser.network_modify_functions`,
        and always take the arguments :paramref:`postCell` and a :py:class:`~single_cell_parser.network.NetworkMapper` object.
        """
        if 'network_modify_functions' in list(self.nwParam.keys()):
            logger.info('***************************')
            logger.info('applying network modify functions')
            logger.info('***************************')
            dict_ = self.nwParam.network_modify_functions
            for funname, params in six.iteritems(dict_):
                fun = network_modify_functions.get(funname)
                logger.info('applying', funname, 'with parameters', params)
                fun(self.postCell, self, **params)

    def _create_presyn_cells(self):
        '''Creates presynaptic cells.
        
        This is the second step in creating a functional network with :py:meth:`create_saved_network2`.
        The synapses should already be created in :py:meth:`_assign_anatomical_synapses` (step 1).
        
        Network parameters contains information on how many presynaptic cells per synapse type there are.
        This method simply creates these cells as :py:class:`~single_cell_parser.cell.PointCell`s, but provides no further configuration
        to these :py:class:`~single_cell_parser.cell.PointCell` objects.
        '''
        # Check if new cells need to be constructed
        createCells = False
        for preType in list(self.nwParam.keys()):
            if preType not in self.cells:
                createCells = True
                break
        
        # Create PointCells to connect to synapses later on.
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            nrOfCells = self.nwParam[synType].cellNr
            logger.info('creating {:d} PointCells for cell type {:s}'.format(nrOfCells, synType))
            if createCells:
                self.cells[synType] = [PointCell() for n in range(nrOfCells)]

            # ----- Everything after this is just for verbose output -----
            
            # singlecell_input_mapper.singlecell_input_mapper.network_embedding if self.nwParam[synType].celltype == 'pointcell':
            #      nrOfCells = self.nwParam[synType].cellNr
            #      logger.info 'creating %d PointCells for cell type %s' % (nrOfCells, synType)
            #      if createCells:
            #          self.cells[synType] = [PointCell() for n in xrange(nrOfCells)]
            #  elif self.nwParam[synType].celltype == 'spiketrain':
            #      nrOfSyns = len(self.postCell.synapses[synType])
            #      nrOfCells = self.nwParam[synType].cellNr
            #      logger.info 'creating %d SpikeTrains for cell type %s' % (nrOfCells, synType)
            #      if createCells:
            #           self.cells[synType] = [SpikeTrain() for n in xrange(nrOfCells)]
            #          self.cells[synType] = [PointCell() for n in xrange(nrOfCells)]
            #  else:
            #      errstr = 'Spike source \"%s\" for cell type %s not implemented!' % (self.nwParam[synType].celltype, synType)
            #      raise NotImplementedError(errstr)
            
            # This is just for output, no actual attributes get updated.
            for receptorType in list(self.nwParam[synType].synapses.receptors.keys()):
                # e.g. "glutamate_syn"
                if 'weightDistribution' in self.nwParam[synType].synapses.receptors[receptorType]:
                    weightStr = self.nwParam[synType].synapses.receptors[receptorType].weightDistribution
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution {:s}'
                        .format(receptorType, weightStr))
                else:
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution uniform'
                        .format(receptorType))
        logger.info('---------------------------')

    def _activate_presyn_cells(self):
        '''Create PointCell or SpikeTrain activation patters for each presynaptic cell.

        This is the third step in creating a functional network with :py:meth:`create_saved_network2`.
        The synapses should already be created in :py:meth:`_assign_anatomical_synapses` (step 1) and 
        the presynaptic cells in :py:meth:`_create_presyn_cells` (step 2).
        
        Depending on the cell type of a synapse, this method creates activation patterns for each presynaptic cell:

        1. For :py:class:`~single_cell_parser.cell.PointCell`: see :py:meth:`_create_pointcell_activities`
        2. For :py:class:`~single_cell_parser.cell.SpikeTrain`: see :py:meth:`_create_spiketrain_activities`
        '''
        for synType in list(self.nwParam.keys()):  
            # contains list of celltypes in network: 
            # ['L45Peak_D1', 'L45Peak_D2', 'L5tt_B3', 'L45Peak_Delta', 'L2_C1', 'L6ct_E3' ...]
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if self.nwParam[synType].celltype == 'pointcell':
                self._create_pointcell_activities(synType, self.nwParam[synType])
                """old code:
                # nrOfCells = self.nwParam[synType].cellNr
                # active, = np.where(np.random.uniform(size=nrOfCells) < self.nwParam[synType].activeFrac)
                # try:
                #     dist = self.nwParam[synType].distribution
                # except AttributeError:
                #     logger.info 'WARNING: Could not find attribute \"distribution\" for \"pointcell\" of cell type %s.' % synType
                #     logger.info '         Support of \"pointcell\" without this attribute is deprecated.'
                #     dist = 'normal'
                # if dist == 'normal':
                #     mean = self.nwParam[synType].spikeT
                #     sigma = self.nwParam[synType].spikeWidth
                #     try:
                #         offset = self.nwParam[synType].offset
                #     except AttributeError:
                #         logger.info 'WARNING: Could not find attribute \"offset\" for \"pointcell\" of cell type %s.' % synType
                #         logger.info '         Support of \"pointcell\" without this attribute is deprecated.'
                #         offset = 10.0
                #     spikeTimes = offset + mean + sigma*np.random.randn(len(active))
                # elif dist == 'uniform':
                #     window = self.nwParam[synType].window
                #     offset = self.nwParam[synType].offset
                #     spikeTimes = offset + window*np.random.rand(len(active))
                # elif dist == 'lognormal':
                #     mu = self.nwParam[synType].mu
                #     sigma = self.nwParam[synType].sigma
                #     offset = self.nwParam[synType].offset
                #     spikeTimes = offset + np.random.lognormal(mu, sigma, len(active))
                # else:
                #     errstr = 'Unknown spike time distribution: %s' % dist
                #     raise RuntimeError(errstr)
                # logger.info 'initializing spike times for cell type %s' % (synType)
                # for i in range(len(active)):
                #     if spikeTimes[i] < 0.1:
                #         spikeTimes[i] = 0.1
                #     self.cells[synType][active[i]].append(spikeTimes[i])
                #      self.cells[synType][active[i]].play()
                #      self.cells[synType][active[i]].playing = True
                #      logger.info 'Presynaptic cell %d active at time %.1f' % (i+1, spikeTimes[i])
                """
            elif self.nwParam[synType].celltype == 'spiketrain':
                self._create_spiketrain_activities(synType, self.nwParam[synType])
                """old code:
#                interval = self.nwParam[synType].interval
#                noise = 1.0
#                start = 0.0
#                stop = -1.0
#                nSpikes = None
#                try:
#                    noise = self.nwParam[synType].noise
#                    start = self.nwParam[synType].start
#                except AttributeError:
#                    logger.info 'WARNING: Could not find attributes \"noise\" or \"start\" for \"spiketrain\" of cell type %s.' % synType
#                    logger.info '         Support of \"spiketrains\" without these attributes is deprecated.'
##                optional argument: nr. of spikes
#                try:
#                    nSpikes = self.nwParam[synType].nspikes
#                except AttributeError:
#                    pass
#                if self.simParam is not None:
#                    stop = self.simParam.tStop
#                logger.info 'initializing spike trains with mean rate %.2f Hz for cell type %s' % (1000.0/interval, synType)
#                for cell in self.cells[synType]:
#                    cell.compute_spike_train_times(interval, noise, start, stop, nSpikes)
##                    cell.set_interval(interval)
##                    cell.set_noise(noise)
##                    cell.set_start(start)
##                    cell.set_stop(stop)
##                    cell.compute_spike_times(nSpikes)
##                    cell.play()
##                    cell.playing = True
            """
            else:
                try:  
                    # seems to be build for the case where self.nwParam[synType].celltype 
                    # contains the actual celltypes instead of being one
                    cellTypes = list(self.nwParam[synType].celltype.keys())
                    for cellType in cellTypes:
                        if cellType == "spiketrain":
                            networkParameters = self.nwParam[
                                synType].celltype.spiketrain
                            self._create_spiketrain_activities(
                                synType, networkParameters)
                        elif cellType == "pointcell":
                            networkParameters = self.nwParam[
                                synType].celltype.pointcell
                            self._create_pointcell_activities(
                                synType, networkParameters)
                        else:
                            errstr = 'Cell type \"%s\" not implemented as spike source!'
                            raise RuntimeError(errstr)
                except AttributeError:
                    pass
        logger.info('---------------------------')

    def _create_spiketrain_activities(
            self, 
            preCellType, 
            networkParameters):
        '''Create spike train times based on the network parameters spiketrain keywords.

        Uses :py:meth:`~single_cell_parser.cell.PointCell.compute_spike_train_times` to calculate
        spike times based on the network parameter keys "noise", "start", "interval", "nspikes".
        See :ref:`network_parameters_format` for more information.
        '''
        interval = networkParameters.interval
        noise = 1.0
        start = 0.0
        stop = -1.0
        nSpikes = None
        try:
            noise = networkParameters.noise
            start = networkParameters.start
        except AttributeError:
            logger.error('Could not find attributes \"noise\" or \"start\" for \"spiketrain\" of cell type {:s}.'.format(preCellType))
            logger.error('         Support of \"spiketrains\" without these attributes is deprecated.')
        try:
            nSpikes = networkParameters.nspikes
        except AttributeError:
            pass
        if self.simParam is not None:
            stop = self.simParam.tStop
        logger.info('initializing spike trains with mean rate {:.2f} Hz for cell type {:s}'.format(1000.0 / interval, preCellType))
        for cell in self.cells[preCellType]:
            cell.compute_spike_train_times(
                interval,
                noise,
                start,
                stop,
                nSpikes,
                spike_source='poissontrain')

    def _create_pointcell_activities(self, preCellType, networkParameters):
        '''Create point cell spike times based on the network parameters ``distribution`` keyword.

        Depending on the ``distribution`` given by :paramref:`networkParameters`, this method creates
        spike times for each presynaptic cell of type :paramref:`preCellType`.

        The following spike time distributions are supported, and require the following parameters:
        
        .. list-table:: Spike Time Distributions
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
           * - "PSTH_poissontrain" (deprecated)
             - "intervals", "rates", "offset"
           * - "PSTH_poissontrain_v2"
             - "bins", "rates", "offset"
           * - "poissontrain_modulated"
             - "rate_before_t_offset", "mean_rate", "max_modulation", "modulation_frequency", "bin_size", "phase_distribution", "offset"

        See :ref:`network_parameters_format` for more information on the network parameter file format.

        Args:
            preCellType (str): The presynaptic cell type.
            networkParameters (:py:class:`~sumatra.parameters.NTParameterSet`): The network parameters for the presynaptic cell type.

        Returns:
            None
        '''
        nrOfCells = len(self.cells[preCellType])
        try:
            dist = networkParameters.distribution
        except AttributeError:
            logger.warning('Could not find attribute \"distribution\" for \"pointcell\" of cell type {:s}.'.format(preCellType))
            logger.warning('         Support of \"pointcell\" without this attribute is deprecated.')
            dist = 'normal'
        if dist == 'normal':
            active, = np.where(np.random.uniform(size=nrOfCells) < networkParameters.activeFrac)
            mean = networkParameters.spikeT
            sigma = networkParameters.spikeWidth
            try:
                offset = networkParameters.offset
            except AttributeError:
                logger.warning('Could not find attribute \"offset\" for \"pointcell\" of cell type {:s}.'.format(preCellType))
                logger.warning('         Support of \"pointcell\" without this attribute is deprecated.')
                offset = 10.0
            spikeTimes = offset + mean + sigma * np.random.randn(len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(
                    spikeTimes[i], spike_source='pointcell_normal')
        
        elif dist == 'uniform':
            active, = np.where(np.random.uniform(size=nrOfCells) < networkParameters.activeFrac)
            window = networkParameters.window
            offset = networkParameters.offset
            spikeTimes = offset + window * np.random.rand(len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(
                    spikeTimes[i], spike_source='pointcell_uniform')
        
        elif dist == 'lognormal':
            active, = np.where(np.random.uniform(size=nrOfCells) < networkParameters.activeFrac)
            mu = networkParameters.mu
            sigma = networkParameters.sigma
            offset = networkParameters.offset
            spikeTimes = offset + np.random.lognormal(mu, sigma, len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(spikeTimes[i], spike_source='pointcell_lognormal')
        
        elif dist == 'PSTH':
            bins = networkParameters.intervals
            probabilities = networkParameters.probabilities
            offset = networkParameters.offset
            if len(bins) != len(probabilities):
                errstr = 'Time bins and probabilities of PSTH for cell type %s have unequal length! ' % preCellType
                errstr += 'len(bins) = %d - len(probabilities) = %d' % (len(bins), len(probabilities))
                raise RuntimeError(errstr)
            for i in range(len(bins)):  ##fill all cells bin after bin
                tBegin, tEnd = bins[i]
                spikeProb = probabilities[i]
                active, = np.where(
                    np.random.uniform(size=nrOfCells) < spikeProb)
                spikeTimes = offset + tBegin + (
                    tEnd - tBegin) * np.random.uniform(size=len(active))
                for j in range(len(active)):
                    self.cells[preCellType][active[j]].append(
                        spikeTimes[j], spike_source='pointcell_PSTH')
        
        elif dist == 'PSTH_absolute_number':
            bins = networkParameters.intervals
            number_active_synapses = networkParameters.number_active_synapses
            offset = networkParameters.offset
            if len(bins) != len(number_active_synapses):
                errstr = 'Time bins and probabilities of PSTH for cell type {} have unequal length! len(bins) = {} - len(probabilities) = {}'.format(preCellType, len(bins), len(probabilities))
                raise RuntimeError(errstr)
            for i in range(len(bins)):  ##fill all cells bin after bin
                tBegin, tEnd = bins[i]
                nas = number_active_synapses[i]
                try:
                    active = np.random.choice(
                        list(range(nrOfCells)), nas, replace=False
                    )  # np.where(np.random.uniform(size=nrOfCells) < spikeProb)
                except ValueError:
                    logger.warning('Number of active synapses larger than number of synapses! ')
                    logger.warning('Switching from drawing without replacement to drawing with replacement.')
                    
                    active = np.random.choice(
                        list(range(nrOfCells)),
                        nas,
                        replace=True)
                spikeTimes = offset + tBegin + (
                    tEnd - tBegin) * np.random.uniform(size=len(active))
                for j in range(len(active)):
                    self.cells[preCellType][active[j]].append(
                        spikeTimes[j],
                        spike_source='pointcell_PSTH_absolute_number')
        
        elif dist == 'PSTH_poissontrain':
            logger.warning('PSTH_poissontrain is deprecated! Use PSTH_poissontrain_v2 instead!')
            bins = networkParameters.intervals
            rates = networkParameters.rates
            offset = networkParameters.offset
            noise = 1.0
            start = 0.0
            stop = -1.0
            nSpikes = None
            if len(bins) != len(rates):
                errstr = 'Time bins and rates of PSTH_poissontrain for cell type %s have unequal length! ' % preCellType
                errstr += 'len(bins) = %d - len(rates) = %d' % (len(bins),
                                                                len(rates))
                raise RuntimeError(errstr)

            for i in range(len(bins)):  ##fill all cells bin after bin
                tBegin, tEnd = bins[i]
                try:
                    interval = 1000. / rates[i]
                except ZeroDivisionError:
                    continue
                logger.info(
                    'initializing spike trains with mean rate {:.2f} Hz for cell type {:s}'
                    .format(1000.0 / interval, preCellType))
                for cell in self.cells[preCellType]:
                    #logger.info 'calling compute_spike_train_times with',  'interval', \
                    #interval, 'noise', noise, 'tBegin', tBegin, 'tEnd', tEnd, \
                    #'nSpikes', nSpikes
                    # self.append(tSpike, spike_source = spike_source)
                    cell.compute_spike_train_times(
                        interval,
                        noise,
                        tBegin,
                        tEnd,
                        nSpikes,
                        spike_source='pointcell_PSTH_poissontrain')
        
        elif dist == 'PSTH_poissontrain_v2':
            bins = networkParameters.bins
            rates = networkParameters.rates
            offset = networkParameters.offset
            noise = 1.0
            start = 0.0
            stop = -1.0
            nSpikes = None
            if len(bins) != len(rates) + 1:
                errstr = 'Time bins must be one element longer than rates!'
                errstr += 'len(bins) = %d - len(rates) = %d' % (len(bins),
                                                                len(rates))
                raise RuntimeError(errstr)

            for cell in self.cells[preCellType]:
                spikeTimes = sample_times_from_rates(bins, rates)
                for spike_time in spikeTimes:
                    cell.append(spike_time, spike_source='PSTH_poissontrain_v2')

        elif dist == 'poissontrain_modulated':
            # Generates poisson train activity from a modulated PSTH
            # from a mean activity, a modulation, and different cells in the population have different modulation phases.
            # The distribution of cells phases is defined as uniform/normal, etc
            rate_before_t_offset = networkParameters.rate_before_t_offset
            mean_rate = networkParameters.mean_rate
            M = networkParameters.max_modulation
            freq = networkParameters.modulation_frequency  # Hz
            bin_size = networkParameters.bin_size
            phase_distribution = networkParameters.phase_distribution
            tStop = self.simParam.tStop
            offset = networkParameters.offset

            duration = tStop - offset
            n_bins = math.ceil(duration / bin_size)
            bins = np.arange(0, duration + bin_size, bin_size)
            bins = bins + offset
            bins[0] = 0
            bins[-1] = tStop

            cycle_duration = 1000 / freq  # ms
            n_cycles = duration / cycle_duration

            if phase_distribution == 'uniform':
                phase = np.random.uniform(0, 2 * np.pi,
                                       len(self.cells[preCellType]))
            elif phase_distribution == 'normal':
                mean_phase = networkParameters.mean_phase
                std_phase = networkParameters.std_phase
                phase = np.random.normal(mean_phase, std_phase,
                                         len(self.cells[preCellType]))
            else:
                phase = np.zeros(len(self.cells[preCellType]))
            
            for i,cell in enumerate(self.cells[preCellType]):
                rates = np.full(n_bins,mean_rate)*(1+ M*np.sin(np.linspace(0,2*np.pi*n_cycles,n_bins)+phase[i]))
                rates[0] = rate_before_t_offset
                spikeTimes = sample_times_from_rates(bins, rates)
                for spike_time in spikeTimes:
                    cell.append(spike_time, spike_source='poissontrain_modulated')

        else:
            errstr = 'Unknown spike time distribution: %s' % dist
            raise RuntimeError(errstr)
        logger.info(
            'initializing spike times for cell type {:s}'.format(preCellType))

    def _connect_functional_synapses(self):
        '''Connects anatomical synapses to spike generators (PointCells).
         
        This connection is according to physiological and/or anatomical constraints
        on connectivity (i.e., convergence of presynaptic cell type)

        Used in :py:meth:`~create_network`. 
        To recreate network embeddings that have been created with :py:mod:`singlecell_input_mapper.singlecell_input_mapper`,
        use :py:meth:`~create_saved_network_2` instead, which connects synapses using :py:meth:`~_map_complete_anatomical_realization` instead
        of this method
        '''
        synapses = self.postCell.synapses
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if not self.nwParam[synType].celltype == 'pointcell':
                continue
            logger.info(
                'setting up functional connectivity for cell type {:s}'.format(
                    synType))
            activeSyn = 0
            connectedCells = set()
            nrPreCells = len(self.cells[synType])
            convergence = self.nwParam[synType].convergence
            # array with indices of presynaptic cells connected to postsynaptic cell
            connected = []
            # if there are synapses there have to be presynaptic neurons...
            while not len(connected):
                connected, = np.where(
                    np.random.uniform(size=nrPreCells) < convergence)
            # array with indices of presynaptic cell assigned to each synapse
            # each connected presynaptic cell has at least 1 synapse by definition
            if len(synapses[synType]) < len(connected):
                # this should not be the anatomical reality, but for completeness...
                connectionIndex = np.random.randint(len(connected),
                                                    size=len(synapses[synType]))
            else:
                connectionIndex = list(np.random.permutation(len(connected)))
                for i in range(len(connected), len(synapses[synType])):
                    connectionIndex.append(np.random.randint(len(connected)))
            for i in range(len(connectionIndex)):
                con = connected[connectionIndex[i]]
                preSynCell = self.cells[synType][con]
                connectedCells.add(con)
                syn = synapses[synType][i]
                synParameters = self.nwParam[synType].synapses
                for recepStr in list(synParameters.receptors.keys()):
                    receptor = synParameters.receptors[recepStr]
                    self._assign_synapse_weights(receptor, recepStr, syn)
                if preSynCell.is_active():
                    if not syn.pruned:
                        activate_functional_synapse(syn, self.postCell,
                                                    preSynCell, synParameters)
                    if syn.is_active():
                        activeSyn += 1
                    preSynCell._add_synapse_pointer(syn)
            self.connected_cells[synType] = connectedCells
            logger.info('    connected cells: {:d}'.format(len(connectedCells)))
            logger.info('    active {:s} synapses: {:d}'.format(
                synType, activeSyn))
        logger.info('---------------------------')

    def _create_functional_connectivity_map(self):
        '''Connect functional anatomical synapses based on ``convergence``.
         
        Synapses are connected here to spike generators (:py:class:`~PointCell` objects) according to physiological
        and/or anatomical constraints on connectivity (i.e., convergence of presynaptic cell type).
        Used to create fixed functional realization.
        Used in :py:meth:`~create_functional_realization`
        
        Returns:
            dict: 
                A dictionary with synapse types as keys. 
                Values are 3-tuples of (cell type, presynaptic cell index, synapse index).
                cell type: string used for indexing point cells and synapses
                presynaptic cell index: index of cell in list ``self.cells[cell type]``
                synapse index: index of synapse in list ``self.postCell.synapses[cell type]``
        '''
        #        visTest = {} # dict holding (cell type, cell, synapse) pairs for simple visualization test

        functionalMap = {}
        synapses = self.postCell.synapses
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if not self.nwParam[synType].celltype == 'pointcell':
                continue
            logger.info('creating functional connectivity map for cell type {:s}'.
                     format(synType))
            nrPreCells = len(self.cells[synType])
            convergence = self.nwParam[synType].convergence
            # array with indices of presynaptic cells connected to postsynaptic cell
            connected = []
            # if there are synapses there have to be presynaptic neurons...
            while not len(connected):
                connected, = np.where(
                    np.random.uniform(size=nrPreCells) < convergence)
            # array with indices of presynaptic cell assigned to each synapse
            # each connected presynaptic cell has at least 1 synapse by definition
            if len(synapses[synType]) < len(connected):
                # this should not be the anatomical reality, but for completeness...
                connectionIndex = np.random.randint(len(connected),
                                                    size=len(synapses[synType]))
            else:
                connectionIndex = list(np.random.permutation(len(connected)))
                for i in range(len(connected), len(synapses[synType])):
                    connectionIndex.append(np.random.randint(len(connected)))
            for i in range(len(connectionIndex)):
                con = connected[connectionIndex[i]]
                funCon = (synType, con, i)
                if synType not in functionalMap:
                    functionalMap[synType] = []
                functionalMap[synType].append(funCon)
               # if synType not in visTest.keys():
               #     visTest[synType] = []
               # visTest[synType].append((synType, con, i))

        # functional_connectivity_visualization(visTest, self.postCell)
        return functionalMap

    def _map_functional_realization(self, weights=None):
        '''Connects anatomical synapses to spike generators (PointCells).
         
        This happens consistent to empirical constraints from a functional realization file.

        .. deprecated: 0.1.0
           This method is used in the deprecated method :py:meth:`create_saved_network`.
           Please use :py:meth:`~create_saved_network2` instead, which uses :py:meth:`~_map_complete_anatomical_realization` to connect synapses.
        '''
        #        visTest = {} # dict holding (cell type, cell, synapse) pairs for simple visualization test

        synapses = self.postCell.synapses
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if not self.nwParam[synType].celltype == 'pointcell':
                continue
            logger.info(
                'setting up functional connectivity for cell type {:s}'.format(
                    synType))
            activeSyn = 0
            connectedCells = set()
            funcMapName = self.nwParam[synType].synapses.connectionFile
            connections, anatomicalID = reader.read_functional_realization_map(
                funcMapName)
            functionalMap = connections[synType]
            anatomicalRealizationName = self.nwParam[
                synType].synapses.distributionFile.split('/')[-1]
            #if anatomicalID != anatomicalRealizationName:
            #    errstr = 'Functional mapping %s does not correspond to anatomical realization %s' \
            #    % (anatomicalID, anatomicalRealizationName)
            #    raise RuntimeError(errstr)
            for con in functionalMap:
                cellType, cellID, synID = con
                if cellType != synType:
                    errstr = 'Functional map cell type %s does not correspond to synapse type %s' % (
                        cellType, synType)
                    raise RuntimeError(errstr)
                preSynCell = self.cells[synType][cellID]
                connectedCells.add(cellID)
                #                if cellType not in visTest.keys():
                #                    visTest[cellType] = []
                #                visTest[cellType].append((cellType, cellID, synID))
                syn = synapses[synType][synID]
                synParameters = self.nwParam[synType].synapses
                if weights:
                    syn.weight = weights[synType][synID]
                else:
                    for recepStr in list(synParameters.receptors.keys()):
                        receptor = synParameters.receptors[recepStr]
                        self._assign_synapse_weights(receptor, recepStr, syn)
                if preSynCell.is_active():
                    if not syn.pruned:
                        activate_functional_synapse(syn, self.postCell,
                                                    preSynCell, synParameters)
                    if syn.is_active():
                        activeSyn += 1
                    preSynCell._add_synapse_pointer(syn)
            self.connected_cells[synType] = connectedCells
            logger.info('    connected cells: {:d}'.format(len(connectedCells)))
            logger.info('    active %s synapses: {:d}'.format(synType, activeSyn))
        logger.info('---------------------------')

        # functional_connectivity_visualization(visTest, self.postCell)

    def _map_complete_anatomical_realization(
        self,
        weights=None,
        full_network=False
        ):
        '''Connect synapses to active presynaptic cells.

        This is step 4 in the creation of a saved network using :py:meth:`create_saved_network2`.
        The synapses should already be created in :py:meth:`_assign_anatomical_synapses` (step 1),
        the presynaptic cells have been created in :py:meth:`_create_presyn_cells` (step 2),
        and their activity should have been generated in :py:meth:`_activate_presyn_cells` (step 3).
        
        Assigns synapse weights using :py:meth:`~_assign_synapse_weights` and connect synapses to presynaptic cells with defined activity.
        
        Args:
            weights (dict | None, optional): 
                pecific weights for each synapse type.
                Default: None, in which case they are read from the :ref:`network_parameters_format`.
            full_network (bool): Defines which cell IDS to use.
                If True: (non-sequential) cell ids from the network embedding are used. 
                If False, single_cell network embedding from single_cell_input_mapper is used, in which cell ids are sequential.
        '''
        previousConnectionFile = ''
        synapses = self.postCell.synapses
        # previousConnections = {}
        # previousAnatomicalID = None
        totalConnectedCells = 0
        totalActiveSyns = 0

        for synType in list(self.nwParam.keys()):
            # Iterate synapse types / presynaptic cell types in network.
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if full_network:
                synapse_counter = 0 # Sequential counter
            
            # 1. Load .con file for current synapse type
            funcMapName = self.nwParam[synType].synapses.connectionFile
            if funcMapName != previousConnectionFile:
                logger.info('loading anatomical connectivity file {:s}'.format(funcMapName))
                connections, anatomicalID = reader.read_functional_realization_map(funcMapName)
                previousConnectionFile = funcMapName
            else:
                logger.info('anatomical connectivity file already loaded')
                # connections, anatomicalID = previousConnections, previousAnatomicalID
            
            # 2. Connect synapses
            
            logger.info('setting up functional connectivity for cell type %s'.format(synType))
            activeSyn = 0
            connectedCells = set()
            
            try:
                functionalMap = connections[synType]
            except KeyError:  
                # there are celltypes in the network param file that aren't in the con file
                logger.info('skipping {}, which occurs in network parameters, but not confile'.format(synType))
                continue
            logger.info('including {}'.format(synType))
            
            anatomicalRealizationName = self.nwParam[synType].synapses.distributionFile.split('/')[-1]
            if anatomicalID != anatomicalRealizationName:
                errstr = 'Functional mapping %s does not correspond to anatomical realization %s' % (anatomicalID, anatomicalRealizationName)
                # raise RuntimeError(errstr)
            
            # Connect synapses to presynaptic cells
            def log_cell_count(nwparam, cells):
                if nwparam[synType].celltype == 'pointcell':
                    nrOfSyns = len(synapses[synType])
                    nrOfCells = len(cells[synType])
                    logger.info('activating point cells for cell type {:s}: {:d} synapses, {:d} presynaptic cells'.format(synType, nrOfSyns, nrOfCells))
                elif nwparam[synType].celltype == 'spiketrain':
                    nrOfSyns = len(synapses[synType])
                    nrOfCells = len(cells[synType])
                    logger.info('activating spike trains for cell type {:s}: {:d} synapses, {:d} presynaptic cells'.format(synType, nrOfSyns, nrOfCells))
                else:
                    try:
                        spikeSourceType = list(nwparam[synType].celltype.keys())
                        if len(spikeSourceType) == 2:
                            nrOfSyns = len(synapses[synType])
                            nrOfCells = len(cells[synType])
                            logger.info('activating mixed spike trains/point cells for cell type {:s}: {:d} synapses, {:d} presynaptic cells'.format(synType, nrOfSyns, nrOfCells))
                    except AttributeError:
                        pass
            log_cell_count(self.nwParam, self.cells)
            
            for con in functionalMap:
                cellType, cellID, synID = con
                if cellType != synType:
                    errstr = 'Functional map cell type %s does not correspond to synapse type %s' % (cellType, synType)
                    raise RuntimeError(errstr)

                # Fetch presynaptic cell from list of unconfigured PointCells
                # These are initialized in _create_presyn_cells
                if not full_network:
                    preSynCell = self.cells[synType][cellID]
                    connectedCells.add(cellID)
                    syn = synapses[synType][synID]
                else:
                    connectedCells.add(cellID)
                    # Consecutive cell indices
                    cell_index = len(connectedCells) - 1
                    preSynCell = self.cells[synType][cell_index]
                    syn = synapses[synType][synapse_counter]
                    synapse_counter += 1

                # if cellType not in visTest.keys():
                #      visTest[cellType] = []
                #  visTest[cellType].append((cellType, cellID, synID))

                synParameters = self.nwParam[synType].synapses
                if weights:
                    syn.weight = weights[synType][synID]
                else:
                    for recepStr in list(synParameters.receptors.keys()):
                        receptor = synParameters.receptors[recepStr]
                        self._assign_synapse_weights(receptor, recepStr, syn)
                if preSynCell.is_active():
                    if not syn.pruned:
                        activate_functional_synapse(syn, self.postCell,preSynCell, synParameters)
                    if syn.is_active():
                        activeSyn += 1
                    preSynCell._add_synapse_pointer(syn)
            self.connected_cells[synType] = connectedCells

            # previousConnections = connections
            # previousAnatomicalID = anatomicalID
            totalConnectedCells += len(connectedCells)
            totalActiveSyns += activeSyn
            logger.info('    connected cells: {:d}'.format(len(connectedCells)))
            logger.info('    active {:s} synapses: {:d}'.format(
                synType, activeSyn))
        logger.info('---------------------------')
        logger.info('total connected cells: {:d}'.format(totalConnectedCells))
        logger.info('total active synapses: {:d}'.format(totalActiveSyns))
        logger.info('---------------------------')

    def _assign_synapse_weights(self, receptor, recepStr, syn):
        """Assign synapse weights according to distribution specified in network parameters.
        
        Args:
            receptor (:py:class:`~sumatra.parameters.NTParameterSet`): Receptor parameters from network parameter file.
            recepStr (str): Receptor name.
            syn (Synapse): Synapse object.
        """
        if syn.weight is None:
            syn.weight = {}
        if recepStr not in syn.weight:
            syn.weight[recepStr] = []
        if "weightDistribution" in receptor:
            if receptor["weightDistribution"] == "lognormal":
                if isinstance(receptor.weight, Sequence):
                    for i in range(len(receptor.weight)):
                        mean = receptor.weight[i]
                        std = mean**2
                        sigma = np.sqrt(np.log(1 + std**2 / mean**2))
                        mu = np.log(mean) - 0.5 * sigma**2
                        gmax = np.random.lognormal(mu, sigma)
                        syn.weight[recepStr].append(gmax)
                        #logger.info '    weight[%d] = %.2f' % (i, syn.weight[recepStr][-1])
                else:
                    mean = receptor.weight
                    std = mean**2
                    sigma = np.sqrt(np.log(1 + std**2 / mean**2))
                    mu = np.log(mean) - 0.5 * sigma**2
                    gmax = np.random.lognormal(mu, sigma)
                    syn.weight[recepStr].append(gmax)
                    #logger.info '    weight = %.2f' % (syn.weight[recepStr][-1])
            else:
                distStr = receptor["weightDistribution"]
                errstr = 'Synaptic weight distribution %s not implemented yet!' % distStr
                raise NotImplementedError(errstr)
        else:
            if isinstance(receptor.weight, Sequence):
                for i in range(len(receptor.weight)):
                    syn.weight[recepStr].append(receptor.weight[i])
            else:
                syn.weight[recepStr].append(receptor.weight)

    def _connect_spike_trains(self, weights=None, change=None):
        '''Connects synapses with spike generators.
         
        Spike trains are activity sources with given mean spike rate (SpikeTrains).
        All synapses are independent.

        Used in :py:meth:`create_network`.
        '''
        synapses = self.postCell.synapses
        if change is not None:
            tChange, changeParam = change
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if not self.nwParam[synType].celltype == 'spiketrain':
                continue
            nrOfSyns = len(synapses[synType])
            nrOfCells = len(self.cells[synType])
            logger.info('activating spike trains for cell type {:s}: {:d} synapses, {:d} presynaptic cells'.format(synType, nrOfSyns, nrOfCells))
            for i in range(len(synapses[synType])):
                syn = synapses[synType][i]
                synParameters = self.nwParam[synType].synapses
                preSynCell = self.cells[synType][i]
                if weights:
                    syn.weight = weights[synType][i]
                else:
                    for recepStr in list(synParameters.receptors.keys()):
                        receptor = synParameters.receptors[recepStr]
                        self._assign_synapse_weights(receptor, recepStr, syn)
                if change is None:
                    activate_functional_synapse(syn, self.postCell, preSynCell,
                                                synParameters)
                else:
                    activate_functional_synapse(syn, self.postCell, preSynCell,
                                                synParameters, tChange,
                                                changeParam[synType].synapses)
        logger.info('---------------------------')

    # Deprecated methods
    
    def create_saved_network(self, synWeightName=None):
        '''Recreate a saved network embedding and activate it.

        .. deprecated:: 0.1.0
            Point cells and spike trains are separate entities in this version.
            Please use :py:meth:`create_saved_network2` instead, which is
            the most recent version, where point cells and spike trains can 
            be integrated into the same presynaptic cell.

        Commonly used to assign synapse locations that have been previously generated
        with :py:mod:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding`.

        Here, these synapses can then be connected to activity sources and activated.
        
        Steps:

        1. Assign anatomical synapses to postsynaptic cell using :py:meth:`~_assign_anatomical_synapses`.
        2. Create presynaptic cells for these synapses using :py:meth:`~_create_presyn_cells` (multiple synapses can originate from the same presynaptic cell).
        3. Generate activation patters for each presynaptic cell, depending on whether they are a :py:class:`PointCell` or :py:class:`SpikeTrain` using :py:meth:`_activate_presyn_cells`.
        4. Connect the presynaptic cells to the anatomical synapses using :py:meth:`~_map_functional_realization`.
        5. Connect to spike train sources using :py:meth:`_connect_spike_trains`.

        Args:
            synWeightName (str): Name of the file containing the synapse weights. Default: None.
            full_network (bool): 
                If True, all synapses are created, even if they were not active. 
                If False, only recreates the synapses that were active, and re-assigns their IDs to be sequential.
                Default: False.
        '''
        logger.info('***************************')
        logger.info('creating saved network')
        logger.info('***************************')
        self._assign_anatomical_synapses()
        self._create_presyn_cells()
        self._activate_presyn_cells()
        weights = None
        if synWeightName:
            weights, locations = reader.read_synapse_weight_file(synWeightName)
        # These are different from the ones in create_saved_network2
        self._map_functional_realization(weights)
        self._connect_spike_trains(weights)
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def reconnect_network(self):
        '''Re-generate activity and connectivity patterns for a network.

        .. deprecated:: 0.1.0
            This method still uses the deprecated methods :py:meth:`~_connect_functional_synapses` 
            and :py:meth:`~_connect_spike_trains`, instead of :py:meth:`~_map_complete_synapse_realization`.
        '''
        logger.info('***************************')
        logger.info('re-configuring network')
        logger.info('***************************')
        self._activate_presyn_cells()
        self._connect_functional_synapses()
        self._connect_spike_trains()
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')


def activate_functional_synapse(
        syn,
        cell,
        preSynCell,
        synParameters,
        tChange=None,
        synParametersChange=None,
        forceSynapseActivation=False,
        releaseTimes=None):
    '''Activate a single synapse.

    This method simulates the activation of a single synapse onto a biophysically detailed neuron model using NEURON.

    The activation times for the synapse can be passed explicitly, or generated in case :paramref:`releaseTimes` is ``None``.
    In the latter case, this method generates release times based on the synapse's release probability from :paramref:`synParameters`,
    and spike times of :paramref:`preSyncell`.
    
    If they need to be generated (default behavior), the release times are calculated from the ``releaseProb`` keyword in the synapse parameter file.
    If the ``releaseProb`` is not given, or set to ``'dynamic'``, the synapse is assumed to release each time the presynaptic cell spikes.
    
    Attention: 
        This implementation expects all presynaptic spike times to be pre-computed.
        It can thus not be used in recurrent network models at this point.
        
    Args:
        syn (:py:class:`~single_cell_parser.synapse.Synapse`): Synapse object.
        cell (:py:class:`~single_cell_parser.cell.Cell`): Postsynaptic cell.
        preSynCell (:py:class:`~single_cell_parser.cell.PointCell`): Presynaptic cell.
        synParameters (:py:class:`~sumatra.parameters.NTParameterSet`): Synapse parameters, see also the ``synapses.rerceptors.<syn_type>`` key in the :ref:`network_parameters_format` file.
        tChange (float): Time at which the synapse parameters change (e.g. the release probability due to a spike).
        synParametersChange (:py:class:`~sumatra.parameters.NTParameterSet`): Synapse parameters after change (including e.g. the release probability).
        forceSynapseActivation (bool): If True, the synapse is activated regardless of the release probability.
        releaseTimes (list):
            List of synaptic release times.
            If None, the release times are generated from the :paramref:`synapseParameters`'s ``releaseProb`` keyword,
            If None and ``releaseprob`` does not appear in :paramref:`synapseParameters`, the release probability is assumed to equal 1,
            and synapse release times equal presynaptic spike times without delay.
    '''
    #     try:
    #         conductance_delay = synParameters.delay
    #     except KeyError:
    #         conductance_delay = 0.0
    conductance_delay = 0.0

    if releaseTimes is None:
        releaseTimes = []
        if 'releaseProb' in synParameters and synParameters.releaseProb != 'dynamic':
            release_prob = synParameters.releaseProb
            if tChange is not None:
                release_prob_change = synParametersChange.releaseProb
            for t in preSynCell.spikeTimes:
                if tChange is not None:
                    if t >= tChange:
                        if np.random.rand() < release_prob_change:  
                            # change parameters within simulation time
                            releaseTimes.append(t + conductance_delay)
                        continue
                if np.random.rand() < release_prob or forceSynapseActivation:
                    releaseTimes.append(t + conductance_delay)
        else:
            releaseTimes = [
                t + conductance_delay for t in preSynCell.spikeTimes
            ]
            spike_source = preSynCell.spike_source
    else:
        pass
        #logger.info "releaseTimes have been explicitly set", releaseTimes

    if not len(releaseTimes):
        return
    releaseTimes.sort()
    releaseSite = PointCell(releaseTimes)
    releaseSite.spike_source = preSynCell.spike_source
    syn.spike_source = preSynCell.spike_source

    releaseSite.play()
    receptors = synParameters.receptors
    syn.activate_hoc_syn(releaseSite, preSynCell, cell, receptors)
    if 'releaseProb' in synParameters and synParameters.releaseProb == 'dynamic':
        syn.hocRNG = h.Random(int(1000000 * np.random.rand()))
        syn.hocRNG.negexp(1)
#    set properties for all receptors here
    for recepStr in list(receptors.keys()):
        recep = receptors[recepStr]
        for param in list(recep.parameter.keys()):
            #            try treating parameters as hoc range variables,
            #            then as hoc global variables
            try:
                # e.g. syn.receptors['glutamate_syn'].decayampa = 1.0
                paramStr = 'syn.receptors[\'' + recepStr + '\'].'
                paramStr += param + '=' + str(recep.parameter[param])
                exec(paramStr)
            except LookupError:
                paramStr = param + '_' + recepStr + '='
                paramStr += str(recep.parameter[param])
                h(paramStr)
        if 'releaseProb' in synParameters and synParameters.releaseProb == 'dynamic':
            paramStr = 'syn.receptors[\'' + recepStr + '\'].setRNG(syn.hocRNG)'
            exec(paramStr)


# backup by arco
# def activate_functional_synapse(syn, cell, preSynCell, synParameters, tChange=None, synParametersChange=None):
#     '''Default method to activate single synapse.
#     Currently, this implementation expects all presynaptic spike
#     times to be pre-computed; can thus not be used in recurrent
#     network models at this point.'''
#     releaseTimes = []
#     if synParameters.has_key('releaseProb') and synParameters.releaseProb != 'dynamic':
#         prel = synParameters.releaseProb
#         if tChange is not None:
#             prelChange = synParametersChange.releaseProb
#         for t in preSynCell.spikeTimes:
#             if tChange is not None:
#                 if t >= tChange:
#                     if np.random.rand() < prelChange:
#                         releaseTimes.append(t)
#                     continue
#             if np.random.rand() < prel:
#                 releaseTimes.append(t)
#     else:
#         releaseTimes = preSynCell.spikeTimes[:]
#     if not len(releaseTimes):
#         return
#     releaseTimes.sort()
#     releaseSite = PointCell(releaseTimes)
#     releaseSite.play()
#     receptors = synParameters.receptors
#     syn.activate_hoc_syn(releaseSite, preSynCell, cell, receptors)
#     if synParameters.has_key('releaseProb') and synParameters.releaseProb == 'dynamic':
#         syn.hocRNG = h.Random(int(1000000*np.random.rand()))
#         syn.hocRNG.negexp(1)
# #    set properties for all receptors here
#     for recepStr in receptors.keys():
#         recep = receptors[recepStr]
#         for param in recep.parameter.keys():
# #            try treating parameters as hoc range variables,
# #            then as hoc global variables
#             try:
#                 paramStr = 'syn.receptors[\'' + recepStr + '\'].'
#                 paramStr += param + '=' + str(recep.parameter[param])
#                 exec(paramStr)
#             except LookupError:
#                 paramStr = param + '_' + recepStr + '='
#                 paramStr += str(recep.parameter[param])
#                 h(paramStr)
#         if synParameters.has_key('releaseProb') and synParameters.releaseProb == 'dynamic':
#             paramStr = 'syn.receptors[\'' + recepStr + '\'].setRNG(syn.hocRNG)'
#             exec(paramStr)


def functional_connectivity_visualization(functionalMap, cell):
    """Visualize functional connectivity.

    Left undocumented, as this seems to be a specific testing/convenience method.
    
    :skip-doc:
    """
    nrL4ssCells = 3168
    nrL1Cells = 104

    L4origin = np.array([-150, -150, 0])
    #    L4colSpacing = np.array([1,0,0])
    #    L4rowSpacing = np.array([0,30,0])
    L4rowSpacing = np.array([1, 0, 0])
    L4colSpacing = np.array([0, 30, 0])
    L1origin = np.array([-550, -150, 700])
    L1colSpacing = np.array([30, 0, 0])
    L1rowSpacing = np.array([0, 30, 0])

    rows = 10
    L4cols = nrL4ssCells // rows
    L1cols = nrL1Cells // rows

    L4grid = {}
    L1grid = {}

    for i in range(nrL4ssCells):
        #        row = i//rows
        #        col = i - row*L4cols
        col = i // L4cols
        row = i - col * L4cols
        #        logger.info 'row = %d' % row
        #        logger.info 'col = %d' % col
        cellPos = L4origin + row * L4rowSpacing + col * L4colSpacing
        L4grid[i] = cellPos
    for i in range(nrL1Cells):
        row = i // rows
        col = i - row * L1cols
        cellPos = L1origin + row * L1rowSpacing + col * L1colSpacing
        L1grid[i] = cellPos

    L4map = {}
    L1map = {}

    for con in functionalMap['L4ssD2']:
        cellType, cellID, synID = con
        synPos = cell.synapses[cellType][synID].coordinates
        if cellID not in list(L4map.keys()):
            L4map[cellID] = []
        L4map[cellID].append((L4grid[cellID], synPos))
    for i in range(nrL4ssCells):
        if i not in list(L4map.keys()):
            L4map[i] = [(L4grid[i], L4grid[i])]
    for con in functionalMap['L1D1']:
        cellType, cellID, synID = con
        synPos = cell.synapses[cellType][synID].coordinates
        if cellID not in list(L1map.keys()):
            L1map[cellID] = []
        L1map[cellID].append((L1grid[cellID], synPos))
    for i in range(nrL1Cells):
        if i not in list(L1map.keys()):
            L1map[i] = [(L1grid[i], L1grid[i])]

    writer.write_functional_map('L4ss_func_map3.am', L4map)
    writer.write_functional_map('L1_func_map3.am', L1map)


def sample_times_from_rates(bins, rate):
    """Sample spike times from spike rates.
    
    Used in :py:meth:`~_create_presyn_cells` to generate spike times for a Poisson spike train."""
    cum_bin_width_weighted_with_rate = np.cumsum(np.diff(bins) * rate)
    cum_bin_width = np.cumsum(np.diff(bins))

    # generate a poisson spike train, add additional spikes until length is sufficient to fill all bins
    size = int(np.ceil(cum_bin_width_weighted_with_rate.max() * 1.)) + 1
    inter_spike_intervals = np.random.exponential(
        1000, size=size)  # 1000 corresponds to 1Hz, since time is in ms
    while sum(inter_spike_intervals) <= max(cum_bin_width_weighted_with_rate):
        inter_spike_intervals2 = np.random.exponential(1000, size=size)
        inter_spike_intervals = np.concatenate(
            [inter_spike_intervals, inter_spike_intervals2])
    constant_rate_spikes = np.cumsum(inter_spike_intervals)

    # warp time axis such that constant_rate_spikes transform into the time dependent rate
    spikes = np.interp(constant_rate_spikes,
                       [0] + list(cum_bin_width_weighted_with_rate),
                       [0] + list(cum_bin_width),
                       right=np.nan,
                       left=np.nan)

    # shift bins such that they start when first interval stats
    spikes = spikes + bins[0]

    return spikes[~np.isnan(spikes)]

'''
Created on Nov 17, 2012

@author: regger
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

logger = logging.getLogger("ISF").getChild(__name__)

from . import network_modify_functions


class NetworkMapper:
    '''
    Handles connectivity of presynaptic populations
    to multi-compartmental neuron model.
    Also handles activity of presynaptic populations.
    '''

    def __init__(self, postCell, nwParam, simParam=None):
        '''
        dictionary holding all presynaptic cells
        ordered by cell type
        self.cells = {}
        
        dictionary holding indices of
        all active presynaptic cells
        ordered by cell type
        self.connected_cells = {}
        
        reference to postsynaptic (multi-compartment) cell model
        self.postCell = postCell
        
        network parameter set (i.e., parameters.network.pre)
        self.nwParam = nwParam
        
        Args:
            postCell (:class:`single_cell_parser.cell.Cell`): The cell to map synapses onto.
            nwParam (:class:`sumatra.parameters.NTParameterSet`): The network parameter set.
            simParam (:class:`sumatra.parameters.NTParameterSet`): The simulation parameter set. Default: None.
        '''
        self.cells = {}
        self.connected_cells = {}
        self.postCell = postCell
        self.nwParam = nwParam
        self.simParam = simParam
        postCell.network_param = nwParam
        postCell.network_sim_param = simParam

    def create_network(self, synWeightName=None, change=None):
        '''
        Public interface
        Only call this function, it automatically
        takes care of setting up the network correctly.
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

    def create_saved_network(self, synWeightName=None):
        '''
        Public interface
        Used for re-creating network from anatomical
        and functional connection files
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
        self._map_functional_realization(weights)
        self._connect_spike_trains(weights)
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def create_saved_network2(self, synWeightName=None, full_network=False):
        '''
        Public interface
        Used for re-creating network from anatomical
        location and connection files.
        This is the better, up-to-date version where
        point cells and spike trains can be integrated
        into the same presynaptic cell
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

    import six

    def _apply_network_modify_functions(self):
        if 'network_modify_functions' in list(self.nwParam.keys()):
            logger.info('***************************')
            logger.info('applying network modify functions')
            logger.info('***************************')
            dict_ = self.nwParam.network_modify_functions
            for funname, params in six.iteritems(dict_):
                fun = network_modify_functions.get(funname)
                logger.info('applying', funname, 'with parameters', params)
                fun(self.postCell, self, **params)

    def reconnect_saved_synapses(self, synInfoName, synWeightName=None):
        '''
        Public interface
        used for setting up saved synapse
        locations and activation times
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
#            for syn in synInfo[synType]:
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
                    newSyn.weight = weights[synType][synID]
                    #===========================================================
                    # testLoc = locations[synType][synID]
                    # if testLoc[0] != secID or testLoc[1] != ptID:
                    #    errstr = 'secID %d != secID %d --- ptID %d != ptID %d' % (testLoc[0], secID, testLoc[1], ptID)
                    #    raise RuntimeError(errstr)
                    #===========================================================
                else:
                    for recepStr in list(synParameters.receptors.keys()):
                        receptor = synParameters.receptors[recepStr]
                        self._assign_synapse_weights(receptor, recepStr, newSyn)
                activate_functional_synapse(newSyn,
                                            self.postCell,
                                            newCell,
                                            synParameters,
                                            forceSynapseActivation=True)
        logger.info('***************************')
        logger.info('network complete!')
        logger.info('***************************')

    def reconnect_network(self):
        '''
        Public interface
        used for re-configuring functional connectivity
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

    def create_functional_realization(self):
        '''
        Public interface:
        used for creating fixed functional connectivity.
        
        Give this functional realization a (somewhat) unique name!!!!     
        then save it at the same location as the anatomical realization,  
        and create a network parameter file with the anatomical and       
        corresponding functional realizations already in it               
        IMPORTANT: assumes path names to anatomical realization files     
        work from the working directory! so should be correct relative, or
        preferably absolute paths.
        Saves parameter file in working directory.
        '''
        allParam = self.nwParam
        self.nwParam = allParam.network
        self._assign_anatomical_synapses()
        self._create_presyn_cells()
        functionalMap = self._create_functional_connectivity_map()
        id1 = time.strftime('%Y%m%d-%H%M')
        id2 = str(os.getpid())
        for synType in functionalMap:
            tmpName = self.nwParam[synType].synapses.distributionFile
            splitName = tmpName.split('/')
            anatomicalID = splitName[-1]
            outName = tmpName[:-4]
            outName += '_functional_map_%s_%s.con' % (id1, id2)
            writer.write_functional_realization_map(outName,
                                                    functionalMap[synType],
                                                    anatomicalID)
            allParam.network[synType].synapses.connectionFile = outName
        paramName = allParam.info.name
        paramName += '_functional_map_%s_%s.param' % (id1, id2)
        allParam.info.name += '_functional_map_%s_%s' % (id1, id2)
        allParam.save(paramName)

    def re_init_network(self, replayMode=False):
        for synType in list(self.cells.keys()):
            for cell in self.cells[synType]:
                cell.turn_off()
#                cell.synapseList = None
            if replayMode:
                self.cells[synType] = []

    def _assign_anatomical_synapses(self):
        '''
        Creates anatomical synapses. This should be done first.
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

    def _create_presyn_cells(self):
        '''
        Creates presynaptic cells.
        Should be done after creating anatomical synapses.
        '''
        createCells = False
        for preType in list(self.nwParam.keys()):
            if preType not in self.cells:
                createCells = True
                break
        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            nrOfCells = self.nwParam[synType].cellNr
            logger.info('creating {:d} PointCells for cell type {:s}'.format(
                nrOfCells, synType))
            if createCells:
                self.cells[synType] = [PointCell() for n in range(nrOfCells)]
#            if self.nwParam[synType].celltype == 'pointcell':
#                nrOfCells = self.nwParam[synType].cellNr
#                logger.info 'creating %d PointCells for cell type %s' % (nrOfCells, synType)
#                if createCells:
#                    self.cells[synType] = [PointCell() for n in xrange(nrOfCells)]
#            elif self.nwParam[synType].celltype == 'spiketrain':
#                nrOfSyns = len(self.postCell.synapses[synType])
#                nrOfCells = self.nwParam[synType].cellNr
#                logger.info 'creating %d SpikeTrains for cell type %s' % (nrOfCells, synType)
#                if createCells:
##                    self.cells[synType] = [SpikeTrain() for n in xrange(nrOfCells)]
#                    self.cells[synType] = [PointCell() for n in xrange(nrOfCells)]
#            else:
#                errstr = 'Spike source \"%s\" for cell type %s not implemented!' % (self.nwParam[synType].celltype, synType)
#                raise NotImplementedError(errstr)
            for receptorType in list(
                    self.nwParam[synType].synapses.receptors.keys()):
                if 'weightDistribution' in self.nwParam[
                        synType].synapses.receptors[receptorType]:
                    weightStr = self.nwParam[synType].synapses.receptors[
                        receptorType].weightDistribution
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution {:s}'
                        .format(receptorType, weightStr))
                else:
                    logger.info(
                        '\tAttached {:s} receptor with weight distribution uniform'
                        .format(receptorType))
        logger.info('---------------------------')

    def _activate_presyn_cells(self):
        '''
        Activates presynaptic cells.
        Should be done after creating presynaptic cells.
        TODO: PointCells are only useable with one spike currently.
        '''
        for synType in list(
                self.nwParam.keys()
        ):  ## contains list of celltypes in network: ['L45Peak_D1', 'L45Peak_D2', 'L5tt_B3', 'L45Peak_Delta', 'L2_C1', 'L6ct_E3' ...]
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if self.nwParam[synType].celltype == 'pointcell':
                self._create_pointcell_activities(synType,
                                                  self.nwParam[synType])
#                nrOfCells = self.nwParam[synType].cellNr
#                active, = np.where(np.random.uniform(size=nrOfCells) < self.nwParam[synType].activeFrac)
#                try:
#                    dist = self.nwParam[synType].distribution
#                except AttributeError:
#                    logger.info 'WARNING: Could not find attribute \"distribution\" for \"pointcell\" of cell type %s.' % synType
#                    logger.info '         Support of \"pointcell\" without this attribute is deprecated.'
#                    dist = 'normal'
#                if dist == 'normal':
#                    mean = self.nwParam[synType].spikeT
#                    sigma = self.nwParam[synType].spikeWidth
#                    try:
#                        offset = self.nwParam[synType].offset
#                    except AttributeError:
#                        logger.info 'WARNING: Could not find attribute \"offset\" for \"pointcell\" of cell type %s.' % synType
#                        logger.info '         Support of \"pointcell\" without this attribute is deprecated.'
#                        offset = 10.0
#                    spikeTimes = offset + mean + sigma*np.random.randn(len(active))
#                elif dist == 'uniform':
#                    window = self.nwParam[synType].window
#                    offset = self.nwParam[synType].offset
#                    spikeTimes = offset + window*np.random.rand(len(active))
#                elif dist == 'lognormal':
#                    mu = self.nwParam[synType].mu
#                    sigma = self.nwParam[synType].sigma
#                    offset = self.nwParam[synType].offset
#                    spikeTimes = offset + np.random.lognormal(mu, sigma, len(active))
#                else:
#                    errstr = 'Unknown spike time distribution: %s' % dist
#                    raise RuntimeError(errstr)
#                logger.info 'initializing spike times for cell type %s' % (synType)
#                for i in range(len(active)):
#                    if spikeTimes[i] < 0.1:
#                        spikeTimes[i] = 0.1
#                    self.cells[synType][active[i]].append(spikeTimes[i])
##                    self.cells[synType][active[i]].play()
##                    self.cells[synType][active[i]].playing = True
##                    logger.info 'Presynaptic cell %d active at time %.1f' % (i+1, spikeTimes[i])
            elif self.nwParam[synType].celltype == 'spiketrain':
                self._create_spiketrain_activities(synType,
                                                   self.nwParam[synType])
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
            else:
                try:  ##seems to be build for the case, that self.nwParam[synType].celltype contains the actual celltypes instead of beeing one
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

    def _create_spiketrain_activities(self, preCellType, networkParameters):
        '''
        Create spike train times with parameters
        given by networkParameters
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
            logger.info(
                'WARNING: Could not find attributes \"noise\" or \"start\" for \"spiketrain\" of cell type {:s}.'
                .format(preCellType))
            logger.info(
                '         Support of \"spiketrains\" without these attributes is deprecated.'
            )
        try:
            nSpikes = networkParameters.nspikes
        except AttributeError:
            pass
        if self.simParam is not None:
            stop = self.simParam.tStop
        logger.info(
            'initializing spike trains with mean rate {:.2f} Hz for cell type {:s}'
            .format(1000.0 / interval, preCellType))
        for cell in self.cells[preCellType]:
            cell.compute_spike_train_times(interval,
                                           noise,
                                           start,
                                           stop,
                                           nSpikes,
                                           spike_source='poissontrain')

    def _create_pointcell_activities(self, preCellType, networkParameters):
        '''
        Create point cell spike times with
        parameters for certain implemented
        distributions given by networkParameters
        '''
        nrOfCells = len(self.cells[preCellType])
        try:
            dist = networkParameters.distribution
        except AttributeError:
            logger.info(
                'WARNING: Could not find attribute \"distribution\" for \"pointcell\" of cell type {:s}.'
                .format(preCellType))
            logger.info(
                '         Support of \"pointcell\" without this attribute is deprecated.'
            )
            dist = 'normal'
        if dist == 'normal':
            active, = np.where(
                np.random.uniform(
                    size=nrOfCells) < networkParameters.activeFrac)
            mean = networkParameters.spikeT
            sigma = networkParameters.spikeWidth
            try:
                offset = networkParameters.offset
            except AttributeError:
                logger.info(
                    'WARNING: Could not find attribute \"offset\" for \"pointcell\" of cell type {:s}.'
                    .format(preCellType))
                logger.info(
                    '         Support of \"pointcell\" without this attribute is deprecated.'
                )
                offset = 10.0
            spikeTimes = offset + mean + sigma * np.random.randn(len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(
                    spikeTimes[i], spike_source='pointcell_normal')
        elif dist == 'uniform':
            active, = np.where(
                np.random.uniform(
                    size=nrOfCells) < networkParameters.activeFrac)
            window = networkParameters.window
            offset = networkParameters.offset
            spikeTimes = offset + window * np.random.rand(len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(
                    spikeTimes[i], spike_source='pointcell_uniform')
        elif dist == 'lognormal':
            active, = np.where(
                np.random.uniform(
                    size=nrOfCells) < networkParameters.activeFrac)
            mu = networkParameters.mu
            sigma = networkParameters.sigma
            offset = networkParameters.offset
            spikeTimes = offset + np.random.lognormal(mu, sigma, len(active))
            for i in range(len(active)):
                if spikeTimes[i] < 0.1:
                    spikeTimes[i] = 0.1
                self.cells[preCellType][active[i]].append(
                    spikeTimes[i], spike_source='pointcell_lognormal')
        elif dist == 'PSTH':
            bins = networkParameters.intervals
            probabilities = networkParameters.probabilities
            offset = networkParameters.offset
            if len(bins) != len(probabilities):
                errstr = 'Time bins and probabilities of PSTH for cell type %s have unequal length! ' % preCellType
                errstr += 'len(bins) = %d - len(probabilities) = %d' % (
                    len(bins), len(probabilities))
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
                errstr = 'Time bins and probabilities of PSTH for cell type %s have unequal length! ' % preCellType
                errstr += 'len(bins) = %d - len(probabilities) = %d' % (
                    len(bins), len(probabilities))
                raise RuntimeError(errstr)
            for i in range(len(bins)):  ##fill all cells bin after bin
                tBegin, tEnd = bins[i]
                nas = number_active_synapses[i]
                try:
                    active = np.random.choice(
                        list(range(nrOfCells)), nas, replace=False
                    )  # np.where(np.random.uniform(size=nrOfCells) < spikeProb)
                except ValueError:
                    logger.info(
                        'Number of active synapses larger than number of synapses! '
                    )
                    logger.info(
                        'Switching from drawing without replacement to drawing with replacement.'
                    )
                    active = np.random.choice(list(range(nrOfCells)),
                                              nas,
                                              replace=True)
                spikeTimes = offset + tBegin + (
                    tEnd - tBegin) * np.random.uniform(size=len(active))
                for j in range(len(active)):
                    self.cells[preCellType][active[j]].append(
                        spikeTimes[j],
                        spike_source='pointcell_PSTH_absolute_number')
        elif dist == 'PSTH_poissontrain':
            logger.info(
                'PSTH_poissontrain is deprecated! Use PSTH_poissontrain_v2 instead!'
            )
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
                phase = random.uniform(0, 2 * np.pi,
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
                    cell.append(spike_time,
                                spike_source='poissontrain_modulated')

        else:
            errstr = 'Unknown spike time distribution: %s' % dist
            raise RuntimeError(errstr)
        logger.info(
            'initializing spike times for cell type {:s}'.format(preCellType))

    def _connect_functional_synapses(self):
        '''
        Connects anatomical synapses to spike
        generators (PointCells) according to physiological
        and/or anatomical constraints on connectivity
        (i.e., convergence of presynaptic cell type)
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
        '''
        Connects anatomical synapses to spike
        generators (PointCells) according to physiological
        and/or anatomical constraints on connectivity
        (i.e., convergence of presynaptic cell type).
        Used to create fixed functional realization.
        Returns list of functional connections, where
        each functional connection is a tuple
        (cell type, presynaptic cell index, synapse index).
        cell type - string used for indexing point cells and synapses
        presynaptic cell index - index of cell in list self.cells[cell type]
        synapse index - index of synapse in list self.postCell.synapses[cell type]
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
#                if synType not in visTest.keys():
#                    visTest[synType] = []
#                visTest[synType].append((synType, con, i))

#        functional_connectivity_visualization(visTest, self.postCell)
        return functionalMap

    def _map_functional_realization(self, weights=None):
        '''
        Connects anatomical synapses to spike
        generators (PointCells) according to functional
        realization file.
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

#        functional_connectivity_visualization(visTest, self.postCell)

    def _connect_spike_trains(self, weights=None, change=None):
        '''
        Connects spike generators with given
        mean spike rate (SpikeTrains) to synapse locations.
        All synapses are independent.
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
            logger.info(
                'activating spike trains for cell type {:s}: {:d} synapses, {:d} presynaptic cells'
                .format(synType, nrOfSyns, nrOfCells))
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

    def _map_complete_anatomical_realization(
        self,
        weights=None,
        full_network=False):
        '''Connect anatomical synapses of :paramref:`~postCell` to spike generators according to anatomical
        connection file.
        
        Spike generators may be PointCells, or SpikeTrains.
        
        Args:
            weights (dict): Weights for each synapse type.
            full_network (bool): Defines which cell IDS to use.
                If True: (non-sequential) cell ids from the network embedding are used. 
                If False, single_cell network embedding from single_cell_input_mapper 
                is used, in which cell ids are sequential.
        '''
        previousConnectionFile = ''
        synapses = self.postCell.synapses
        # previousConnections = {}
        # previousAnatomicalID = None
        totalConnectedCells = 0
        totalActiveSyns = 0

        for synType in list(self.nwParam.keys()):
            if synType == 'network_modify_functions':  # not a synapse type
                continue
            if full_network:
                # Sequential counter
                synapse_counter = 0
            
            funcMapName = self.nwParam[synType].synapses.connectionFile
           
            # 1. Load anatomical connectivity file  -------------------------------------------
            if funcMapName != previousConnectionFile:
                logger.info('loading anatomical connectivity file {:s}'.format(
                    funcMapName))
                connections, anatomicalID = reader.read_functional_realization_map(
                    funcMapName)
                previousConnectionFile = funcMapName
            else:
                logger.info('anatomical connectivity file already loaded')
                # connections, anatomicalID = previousConnections, previousAnatomicalID
            
            # 2. Connect synapses -------------------------------------------------------------
            logger.info('setting up functional connectivity for cell type %s'.format(synType))
            activeSyn = 0
            connectedCells = set()
            
            try:
                functionalMap = connections[synType]
            except KeyError:  # if there are celltypes in the network param file that aren't in the functional map (con file)
                logger.info(
                    'skipping {}, which occurs in network parameters, but not confile'.
                    format(synType))
                continue
            logger.info('including {}'.format(synType))
            anatomicalRealizationName = self.nwParam[synType].synapses.distributionFile.split('/')[-1]
            if anatomicalID != anatomicalRealizationName:
                errstr = 'Functional mapping %s does not correspond to anatomical realization %s' \
                % (anatomicalID, anatomicalRealizationName)
                #raise RuntimeError(errstr)
            
            ## 2.1 Connect synapses to presynaptic cells --------------------------------------
            # Simply count the amount of cells for logger output
            if self.nwParam[synType].celltype == 'pointcell':
                nrOfSyns = len(synapses[synType])
                nrOfCells = len(self.cells[synType])
                logger.info(
                    'activating point cells for cell type {:s}: {:d} synapses, {:d} presynaptic cells'
                    .format(synType, nrOfSyns, nrOfCells))
            elif self.nwParam[synType].celltype == 'spiketrain':
                nrOfSyns = len(synapses[synType])
                nrOfCells = len(self.cells[synType])
                logger.info(
                    'activating spike trains for cell type {:s}: {:d} synapses, {:d} presynaptic cells'
                    .format(synType, nrOfSyns, nrOfCells))
            else:
                try:
                    spikeSourceType = list(
                        self.nwParam[synType].celltype.keys())
                    if len(spikeSourceType) == 2:
                        nrOfSyns = len(synapses[synType])
                        nrOfCells = len(self.cells[synType])
                        logger.info(
                            'activating mixed spike trains/point cells for cell type {:s}: {:d} synapses, {:d} presynaptic cells'
                            .format(synType, nrOfSyns, nrOfCells))
                except AttributeError:
                    pass
            
            # Connect them, depending on the cell type
            for con in functionalMap:
                cellType, cellID, synID = con
                if cellType != synType:
                    errstr = 'Functional map cell type %s does not correspond to synapse type %s' % (
                        cellType, synType)
                    raise RuntimeError(errstr)

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
                        activate_functional_synapse(
                            syn, 
                            self.postCell,
                            preSynCell, 
                            synParameters
                            )
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
            receptor (dict): Receptor parameters from network parameter file.
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


def activate_functional_synapse(
        syn,
        cell,
        preSynCell,
        synParameters,
        tChange=None,
        synParametersChange=None,
        forceSynapseActivation=False,
        releaseTimes=None):
    '''Default method to activate single synapse.
    Currently, this implementation expects all presynaptic spike
    times to be pre-computed; can thus not be used in recurrent
    network models at this point.'''
    #     try:
    #         conductance_delay = synParameters.delay
    #     except KeyError:
    #         conductance_delay = 0.0
    conductance_delay = 0.0

    if releaseTimes is None:
        releaseTimes = []
        if 'releaseProb' in synParameters and synParameters.releaseProb != 'dynamic':
            prel = synParameters.releaseProb
            if tChange is not None:
                prelChange = synParametersChange.releaseProb
            for t in preSynCell.spikeTimes:
                if tChange is not None:
                    if t >= tChange:
                        if np.random.rand(
                        ) < prelChange:  ##change parameters within simulation time
                            releaseTimes.append(t + conductance_delay)
                        continue
                if np.random.rand() < prel or forceSynapseActivation:
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
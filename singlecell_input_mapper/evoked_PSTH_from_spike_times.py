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
Create PSTHs from spike times.

Attention:
    This module is specific to the data gathering process and file formats used by the `Oberlaender lab in Bonn <https://mpinb.mpg.de/en/research-groups/groups/in silico-brain-sciences/research-focus-ibs.html>`_.
    If you are in the process of adapting this module to your own data, please focus on the output format of each method, rather than trying to apply these blindly to your files.
"""
import sys
import numpy as np
import os, os.path
import glob
from data_base.dbopen import dbopen

# anatomical PC + surround columns (3x3)
# ranging from (potentially) 1-9, starting at row-1, arc-1,
# then increasing by arc and then by row up to row+1, arc+1
# e.g. for C2: B1=1, B2=2, B3=3, C1=4, C2=5, C3=6, D1=7, D2=8, D3=9
surroundColumns = {'A1': {'Alpha': 4, 'A1': 5, 'A2': 6, 'B1': 8, 'B2': 9},\
                   'A2': {'A1': 4, 'A2': 5, 'A3': 6, 'B1': 7, 'B2': 8, 'B3': 9},\
                   'A3': {'A2': 4, 'A3': 5, 'A4': 6, 'B2': 7, 'B3': 8, 'B4': 9},\
                   'A4': {'A3': 4, 'A4': 5, 'B3': 7, 'B4': 8},\
                   'Alpha': {'Alpha': 5, 'A1': 6, 'Beta': 8, 'B1': 9},\
                   'B1': {'Alpha': 1, 'A1': 2, 'A2': 3, 'Beta': 4, 'B1': 5, 'B2': 6, 'C1': 8, 'C2': 9},\
                   'B2': {'A1': 1, 'A2': 2, 'A3': 3, 'B1': 4, 'B2': 5, 'B3': 6, 'C1': 7, 'C2': 8, 'C3': 9},\
                   'B3': {'A2': 1, 'A3': 2, 'A4': 3, 'B2': 4, 'B3': 5, 'B4': 6, 'C2': 7, 'C3': 8, 'C4': 9},\
                   'B4': {'A3': 1, 'A4': 2, 'B3': 4, 'B4': 5, 'C3': 7, 'C4': 8},\
                   'Beta': {'Alpha': 2, 'Beta': 5, 'B1': 6, 'Gamma': 8, 'C1': 9},\
                   'C1': {'Beta': 1, 'B1': 2, 'B2': 3, 'Gamma': 4, 'C1': 5, 'C2': 6, 'D1': 8, 'D2': 9},\
                   'C2': {'B1': 1, 'B2': 2, 'B3': 3, 'C1': 4, 'C2': 5, 'C3': 6, 'D1': 7, 'D2': 8, 'D3': 9},\
                   'C3': {'B2': 1, 'B3': 2, 'B4': 3, 'C2': 4, 'C3': 5, 'C4': 6, 'D2': 7, 'D3': 8, 'D4': 9},\
                   'C4': {'B3': 1, 'B4': 2, 'C3': 4, 'C4': 5, 'D3': 7, 'D4': 8},\
                   'Gamma': {'Beta': 2, 'Gamma': 5, 'C1': 6, 'Delta': 8, 'D1': 9},\
                   'D1': {'Gamma': 1, 'C1': 2, 'C2': 3, 'Delta': 4, 'D1': 5, 'D2': 6, 'E1': 8, 'E2': 9},\
                   'D2': {'C1': 1, 'C2': 2, 'C3': 3, 'D1': 4, 'D2': 5, 'D3': 6, 'E1': 7, 'E2': 8, 'E3': 9},\
                   'D3': {'C2': 1, 'C3': 2, 'C4': 3, 'D2': 4, 'D3': 5, 'D4': 6, 'E2': 7, 'E3': 8, 'E4': 9},\
                   'D4': {'C3': 1, 'C4': 2, 'D3': 4, 'D4': 5, 'E3': 7, 'E4': 8},\
                   'Delta': {'Gamma': 2, 'Delta': 5, 'D1': 6, 'E1': 9},\
                   'E1': {'Delta': 1, 'D1': 2, 'D2': 3, 'E1': 5, 'E2': 6},\
                   'E2': {'D1': 1, 'D2': 2, 'D3': 3, 'E1': 4, 'E2': 5, 'E3': 6},\
                   'E3': {'D2': 1, 'D3': 2, 'D4': 3, 'E2': 4, 'E3': 5, 'E4': 6},\
                   'E4': {'D3': 1, 'D4': 2, 'E3': 4, 'E4': 5}}
index2WhiskerLUT = {1: 'B1', 2: 'B2', 3: 'B3',\
            4: 'C1', 5: 'C2', 6: 'C3',\
            7: 'D1', 8: 'D2', 9: 'D3'}


def create_average_celltype_PSTH_from_clusters(cellTypeFolder, outFileName):
    '''Loads cluster recording files and writes out the average ongoing activity for a given cell type.
        
    Args:
        cellTypeFolder (str): 
            The folder containing the .cluster recording files of spike times. 
            Each file in this folder should contain the spike times of a single cell under a specific experimental condition (e.g. deflecting a single whisker).
        outFileName (str): The name of the output file.
        
    Returns:
        None. Writes the average ongoing activity to the output file.
    
    Example:
        >>> create_average_celltype_PSTH_from_clusters(
            'getting_started/example_data/functional_constraints/evoked_activity/L5tt/L5tt_84', 
            'L5_PSTH_UpState.param')
        {
            "getting_started/example_data/functional_constraints/evoked_activity/L5tt/L5tt_84_B1": {
                "distribution": "PSTH",
                "intervals": [(6.0,7.0)],
                "probabilities": [0.0216],
            },
            "getting_started/example_data/functional_constraints/evoked_activity/L5tt/L5tt_84_B2": {
                ...
            },
        }
    '''
    UpDownStateCorrection = 0.4571  # TODO: what is this magic number
    stimulusOnset = 145.0
    ongoingBegin = 20.0  # 100ms pre-stimulus
    ongoingDur = 100.0
    #    ongoingBegin = 0.0 # 100ms pre-stimulus
    PSTHEnd = 195.0  # 0-50ms here
    # load all spike time files for all whiskers of all recorded cells
    
    print('Calculating average evoked PSTH for all cells in folder {:s}'.format(cellTypeFolder))
    
    # Recursively get all .cluster1 files in a directory
    fnames = []
    scan_directory(cellTypeFolder, fnames, '.cluster1')
    
    # gather spike times per cell for each round of trials.
    cellSpikeTimes = {}
    for fname in fnames:
        whiskerSpikeTimes = load_cluster_trials(fname)
        splitName = fname.split('/')
        trialName = splitName[-1]
        cellName = splitName[-2]
        if cellName not in cellSpikeTimes:
            cellSpikeTimes[cellName] = {}
        cellSpikeTimes[cellName][trialName] = whiskerSpikeTimes
    
    # calculate spontaneous activity, i.e. all spikes that are
    # 100ms pre-stim across all cells, whiskers, trials
    rates = []
    for cell in cellSpikeTimes:
        ongoingSpikes = 0.0
        ongoingTrials = 0.0
        #        PW = ''
        #        for whisker in cellSpikeTimes[cell]:
        #            if 'PW' in whisker:
        #                splitName = whisker.split('_')
        #                PW = splitName[0]
        for whisker in cellSpikeTimes[cell]:
            #            splitName = whisker.split('_')
            #            whiskerName = splitName[0]
            #            if whiskerName in surroundColumns[PW]:
            #            print whiskerName
            for trial in cellSpikeTimes[cell][whisker]:
                ongoingTrials += 1
                for t in cellSpikeTimes[cell][whisker][trial]:
                    if ongoingBegin <= t < ongoingBegin + ongoingDur:
                        ongoingSpikes += 1
                        # if '85' in cell:
                        #     print t
        spontRate = ongoingSpikes / ongoingTrials * 0.01  # per ms
        rates.append(spontRate)
        print('\tcell name: {:s}'.format(cell))
        print('\tSpontaneous firing rate = {:.2f} Hz'.format(spontRate *1000.0))
        # print '\tongoing spikes: %.0f' % (ongoingSpikes)
        # print '\tongoing trials: %.0f' % (ongoingTrials)
    avgRate = np.mean(rates)
    print('Average spontaneous firing rate = {:.2f} Hz'.format(avgRate *1000.0))
    
    # collect all spike times and repetitions 0-50ms post-stimulus PW-aligned
    trialsPerWhisker = dict([(i, 0) for i in range(1, 10)])
    spikesPerWhisker = dict([(i, []) for i in range(1, 10)])
    for cell in cellSpikeTimes:
        PW = ''
        for whisker in cellSpikeTimes[cell]:
            if 'PW' in whisker:
                splitName = whisker.split('_')
                PW = splitName[0]
        for whisker in cellSpikeTimes[cell]:
            splitName = whisker.split('_')
            whiskerName = splitName[0]
            if whiskerName in surroundColumns[PW]:
                tmpSpikes = 0
                tmpTrials = 0
                col = surroundColumns[PW][whiskerName]
                for trial in cellSpikeTimes[cell][whisker]:
                    trialsPerWhisker[col] += 1
                    tmpTrials += 1
                    for t in cellSpikeTimes[cell][whisker][trial]:
                        if stimulusOnset <= t < PSTHEnd:
                            spikesPerWhisker[col].append(t)
                            tmpSpikes += 1
                if col == 5:
                    print(cell)
                    print('PW: ', PW)
                    print('APs per stim: ', float(tmpSpikes) / tmpTrials)
    # create 1ms resolution PSTH per whisker and subtract
    # spontaneous activity per 1ms bin
    numberOfBins = 50
    PSTHrange = (stimulusOnset, PSTHEnd)
    whiskerPSTH = {}
    for col in spikesPerWhisker:
        nrOfTrials = trialsPerWhisker[col]
        hist, bins = np.histogram(spikesPerWhisker[col], numberOfBins,
                                  PSTHrange)
        #        hist = 1.0/nrOfTrials*hist - avgRate
        hist = UpDownStateCorrection * (1.0 / nrOfTrials * hist - avgRate)
        whiskerPSTH[col] = hist, bins
        print('whisker: ', index2WhiskerLUT[col])
        print('sum PSTH: ', np.sum(hist))

    whiskers = list(whiskerPSTH.keys())
    whiskers.sort()
    
    with dbopen(outFileName, 'w') as PSTHFile:
        PSTHFile.write('{\n')
        for whisker in whiskers:
            intervals = []
            probabilities = []
            PSTH = whiskerPSTH[whisker]
            prefix = '\"%s_%s\"' % (cellTypeFolder, index2WhiskerLUT[whisker])
            prefix += ': {\n  \"distribution\": \"PSTH\",\n'
            prefix += '  \"intervals\": ['
            PSTHFile.write(prefix)
            if PSTH is not None:
                hist, bins = PSTH
                for i in range(len(hist)):
                    interval = bins[i], bins[i + 1]
                    prob = hist[i]
                    if prob > 0:
                        intervals.append(interval)
                        probabilities.append(prob)
            line = ''
            for interval in intervals:
                line += '(%.1f,%.1f),' % (interval[0] - stimulusOnset,
                                          interval[1] - stimulusOnset)
            line = line[:-1] + '],\n'
            line += '  \"probabilities\": ['
            PSTHFile.write(line)
            line = ''
            for prob in probabilities:
                line += '%.4f,' % prob
            line = line[:-1] + '],\n},\n'
            PSTHFile.write(line)
        PSTHFile.write('}')


#    # collect all spike times and repetitions
#    # 0-50ms for B2 only (for L5tt experiments)
#    trialsPerB2 = 0
#    spikesPerB2 = 0
#    for cell in cellSpikeTimes:
#        for whisker in cellSpikeTimes[cell]:
#            splitName = whisker.split('_')
#            whiskerName = splitName[0]
#            if whiskerName == 'D4':
#                tmpSpikes = 0
#                tmpTrials = 0
#                for trial in cellSpikeTimes[cell][whisker]:
#                    trialsPerB2 += 1
#                    tmpTrials += 1
#                    for t in cellSpikeTimes[cell][whisker][trial]:
#                        if stimulusOnset <= t < PSTHEnd:
#                            spikesPerB2 += 1
#                            tmpSpikes += 1
#                print cell
#                print 'D4:'
#                print 'APs per stim: ', float(tmpSpikes)/tmpTrials
#    # create 1ms resolution PSTH per whisker and subtract
#    # spontaneous activity per 1ms bin
#    spikeProb = float(spikesPerB2)/trialsPerB2
#    spikeProb -= avgRate*50.0
#    print 'D4:'
#    print 'AP per stim: ', spikeProb


def create_evoked_PSTH(spikeTimesName, cellType, ongoingRate, outFileName):
    """Reads in spike times and creates a PSTH for evoked activity for each whisker.
    
    Args:
        spikeTimesName (str): Filepath of the .cluster file containing spike time recordings.
        cellType (str): Cell type.
        ongoingRate (float): The ongoing firing rate for this cell type.
        outFileName (str): Filename to write to.
    
    Example:
        >>> create_evoked_PSTH(
            'getting_started/example_data/functional_constraints/evoked_activity/L5tt/L5tt_84/C1_040929-129-ctx.cluster1', 
            cellType='L5tt', 
            ongoingrate=2.64, 
            outFileName='PSTH.param')
        >>> with open('PSTH.param', 'r) as f:
        ...     content = f.readlines()
        >>> print(content)
        {
            "L5tt_B1": {
                "distribution": "PSTH",
                "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
                "probabilities": [-0.0000,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,0.0227,-0.0000,0.0227,0.0227,0.0227,-0.0000,-0.0000,-0.0000,-0.0000],
            },
            "L5tt_B2": {
                "distribution": "PSTH",
                "intervals": [(0.0,1.0),(1.0,2.0),(2.0,3.0),(3.0,4.0),(4.0,5.0),(5.0,6.0),(6.0,7.0),(7.0,8.0),(8.0,9.0),(9.0,10.0),(10.0,11.0),(11.0,12.0),(12.0,13.0),(13.0,14.0),(14.0,15.0),(15.0,16.0),(16.0,17.0),(17.0,18.0),(18.0,19.0),(19.0,20.0),(20.0,21.0),(21.0,22.0),(22.0,23.0),(23.0,24.0),(24.0,25.0),(25.0,26.0),(26.0,27.0),(27.0,28.0),(28.0,29.0),(29.0,30.0),(30.0,31.0),(31.0,32.0),(32.0,33.0),(33.0,34.0),(34.0,35.0),(35.0,36.0),(36.0,37.0),(37.0,38.0),(38.0,39.0),(39.0,40.0),(40.0,41.0),(41.0,42.0),(42.0,43.0),(43.0,44.0),(44.0,45.0),(45.0,46.0),(46.0,47.0),(47.0,48.0),(48.0,49.0),(49.0,50.0)],
                "probabilities": [0.1363,0.0227,0.0227,0.0227,0.0909,0.0909,0.1136,0.0227,0.0227,0.0227,0.0227,0.0227,0.0454,0.0454,0.0227,0.0682,0.0909,0.0454,0.0454,0.0227,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000,-0.0000],
            },
            "L5tt_B3": {...},
            ...
        }
        """
    print('*************')
    print(
        'creating evoked PSTH from spike times in {:s}'.format(spikeTimesName))
    print('*************')

    whiskerSpikeTimes, whiskerDeflectionTrials = load_spike_times(
        spikeTimesName)
    whiskers = list(whiskerSpikeTimes.keys())
    whiskers.sort()
    whiskerPSTH = {}
    numberOfBins = 50
    #numberOfBins = 5
    PSTHrange = (0, 50)
    ongoingCorrection = ongoingRate * 0.001
    #ongoingCorrection = ongoingRate*0.01
    for whisker in whiskers:
        hist, bins = np.histogram(whiskerSpikeTimes[whisker], numberOfBins,
                                  PSTHrange)
        norm = float(whiskerDeflectionTrials[whisker])
        if norm:
            hist = 1.0 / norm * hist
            hist = hist - ongoingCorrection
            whiskerPSTH[whisker] = hist, bins
        else:
            whiskerPSTH[whisker] = None

    with dbopen(outFileName, 'w') as PSTHFile:
        PSTHFile.write('{\n')
        for whisker in whiskers:
            intervals = []
            probabilities = []
            PSTH = whiskerPSTH[whisker]
            prefix = '\"%s_%s\"' % (cellType, whisker)
            prefix += ': {\n  \"distribution\": \"PSTH\",\n'
            prefix += '  \"intervals\": ['
            PSTHFile.write(prefix)
            if PSTH is not None:
                hist, bins = PSTH
                for i in range(len(hist)):
                    interval = bins[i], bins[i + 1]
                    prob = hist[i]
                    if 1:  #prob > 0:
                        intervals.append(interval)
                        probabilities.append(prob)
            line = ''
            for interval in intervals:
                line += '(%.1f,%.1f),' % (interval[0], interval[1])
            line = line[:-1] + '],\n'
            line += '  \"probabilities\": ['
            PSTHFile.write(line)
            line = ''
            for prob in probabilities:
                line += '%.4f,' % prob
            line = line[:-1] + '],\n},\n'
            PSTHFile.write(line)
        PSTHFile.write('}')


def load_spike_times(spikeTimesName):
    """Reads in .cluster files containing spike time recordings
    
    Args;
        spikeTimesname (str): Name of the .cluster file.
        
    Returns:
        tuple: Tuple of 2 dictioinaries.
        The first contains the spike times per whisker.
        The second contains the amount of trials per whisker.
    
    """
    whiskers = {0: 'B1', 1: 'B2', 2: 'B3',\
                3: 'C1', 4: 'C2', 5: 'C3',\
                6: 'D1', 7: 'D2', 8: 'D3'}
    whiskerDeflectionTrials = {'B1': 0, 'B2': 0, 'B3': 0,\
                                'C1': 0, 'C2': 0, 'C3': 0,\
                                'D1': 0, 'D2': 0, 'D3': 0}
    whiskerSpikeTimes = {'B1': [], 'B2': [], 'B3': [],\
                        'C1': [], 'C2': [], 'C3': [],\
                        'D1': [], 'D2': [], 'D3': []}
    with dbopen(spikeTimesName, 'r') as spikeTimesFile:
        lineCnt = 0
        for line in spikeTimesFile:
            if line:
                lineCnt += 1
            if lineCnt <= 1:
                continue
            splitLine = line.strip().split('\t')
            for i in range(len(splitLine)):
                t = float(splitLine[i])
                whisker = whiskers[i]
                if np.isnan(t):
                    whiskerDeflectionTrials[whisker] += 1
                    continue
                # Use -1 as marker for non-stimulated trials
                if t < 0:
                    continue
                whiskerDeflectionTrials[whisker] += 1
                whiskerSpikeTimes[whisker].append(t)

    return whiskerSpikeTimes, whiskerDeflectionTrials


def load_cluster_trials(fname):
    """Reads in a cluster file and returns a dictionary with the spike times for each trial.
    
    Args:
        fname (str): The name of the .cluster file.
        
    Returns:
        dict: A dictionary with the spike times for each trial.
        
    Example:
        >>> load_cluster_trials('getting_started/example_data/functional_constraints/evoked_activity/L5tt/L5tt_84/C1_040929-129-ctx.cluster1')
        {
            0: [87.80000000000001, 138.70000000000002, 151.6, 430.40000000000003, 471.1, 478.90000000000003], 
            1: [], 
            2: [], 
            3: [], 
            4: [129.9, 265.7, 269.7], 
            5: [283.8, 290.1, 459.20000000000005], 
            6: [13.100000000000001, 90.10000000000001, 95.0, 387.90000000000003], 
            7: [], 
            8: [], 
            9: [], 
            10: [], 
            11: [], 
            12: [320.6], 
            13: [34.0], 
            14: [], 
            15: [110.80000000000001, 464.0], 
            16: [317.5, 409.1, 483.90000000000003], 
            17: [65.5], 
            18: [43.6], 
            19: []}
    """
    data = np.loadtxt(fname, unpack=True)
    trialNumber = data[1]
    spikeTimes = data[3]
    spikeTimes = 0.1 * spikeTimes  # CDK files in 0.1ms
    trialsSpikeTimes = {}
    for i in range(len(trialNumber)):
        nr = int(trialNumber[i])
        if nr not in trialsSpikeTimes:
            trialsSpikeTimes[nr] = []
        t = spikeTimes[i]
        if t > 0.0:
            trialsSpikeTimes[nr].append(t)

    return trialsSpikeTimes


def scan_directory(path, fnames, suffix):
    """Recursively scans a directory for files with a specific suffix.
    
    Args:
        path (str): The path of the directory to scan.
        fnames (list): A list to store the file names.
        suffix (str): The suffix of the files to look for.
    
    Returns:
        None. Updates :paramref:`fnames` in place.
    """
    for fname in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(fname):
            scan_directory(fname, fnames, suffix)
        elif fname.endswith(suffix):
            fnames.append(fname)
        else:
            continue


if __name__ == '__main__':
    if len(sys.argv) == 5:
        spikeTimesName = sys.argv[1]
        cellType = sys.argv[2]
        ongoingRate = float(sys.argv[3])
        outFileName = sys.argv[4]
        create_evoked_PSTH(spikeTimesName, cellType, ongoingRate, outFileName)
    elif len(sys.argv) == 3:
        folderName = sys.argv[1]
        outFileName = sys.argv[2]
        create_average_celltype_PSTH_from_clusters(folderName, outFileName)
    else:
        print(
            'parameters: [spikeTimesName] [cellType] [ongoingRate (Hz)] [outFileName]'
        )

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
from data_base.dbopen import dbopen

__author__  = 'Robert Egger'
__date__    = '2012-03-08'

def read_synapse_weight_file(fname):
    '''Reads list of all anatomical synapses and their maximum conductance values.
    
    Args: 
        fname (str): 
            Synapse weight filename. 
            See: :func:`~single_cell_parser.writer.write_synapse_weight_file`.
    
    Returns: 
        tuple: two dictionaries with cell types as keys, ordered the same as the anatomical synapses:
        1st with section ID and pt ID, 2nd with synaptic weights, coded as dictionaries
        (keys=receptor strings) containing weights: (gmax_0, gmax_1, ... , gmax_n)
    '''
    #    logger.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    #    logger.info 'reading synapse strength file'
    #    logger.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    synWeights, synLocations = {}, {}
    lineCnt = 0
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            if not lineCnt:
                lineCnt += 1
                continue
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            cellType = splitLine[0]
            synID = int(splitLine[1])
            secID = int(splitLine[2])
            ptID = int(splitLine[3])
            receptorType = splitLine[4]
            synWeightList = []
            synWeightsStr = splitLine[5].split(',')
            for gStr in synWeightsStr:
                if gStr:
                    synWeightList.append(float(gStr))
            if cellType not in synLocations:
                synLocations[cellType] = {}
            synLocations[cellType][synID] = (secID, ptID)
            if cellType not in synWeights:
                synWeights[cellType] = []
            if len(synWeights[cellType]) < synID + 1:
                synWeights[cellType].append({})
            synWeights[cellType][synID][receptorType] = synWeightList
            lineCnt += 1
    return synWeights, synLocations

def read_synapse_activation_file(fname):
    '''Reads list of all functional synapses and their activation times.

    .. deprecated::
        This format is now commonly a pandas or dask dataframe.
        They can still be explicitly read with this function
        using Python's ``open()`` and ``read()`` capabilities, but this is not recommended, or efficient.
    
    
    In contrast to :func:`~single_cell_parser.reader.read_complete_synapse_activation_file`, this reader does not return the structure label.
    
    Args:
        fname (str): 
            Filename of a synapse activation file.
            Such a file can be generated with :func:`single_cell_parser.analyze.synanalysis.comute_synapse_distances_times`.
    
    Returns: 
        dictionary with cell types as keys and list of synapse locations and activation times, coded as tuples: (synapse ID, section ID, section pt ID, [t1, t2, ... , tn])
    '''
    #    logger.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    #    logger.info 'reading synapse activation file'
    #    logger.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    synapses = {}
    lineCnt = 0
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            if not lineCnt:
                lineCnt += 1
                continue
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            #===================================================================
            # clunky support for analysis of old format synapse activation files...
            #===================================================================
            old = False
            if len(splitLine) == 6:
                old = True
            if old:
                cellType = splitLine[0]
                synID = -1
                somaDist = float(splitLine[1])
                secID = int(splitLine[2])
                ptID = int(splitLine[3])
            if not old:
                cellType = splitLine[0]
                synID = int(splitLine[1])
                somaDist = float(splitLine[2])
                secID = int(splitLine[3])
                ptID = int(splitLine[4])
            synTimes = []
            synTimesStr = splitLine[-1].split(',')
            for tStr in synTimesStr:
                if tStr:
                    synTimes.append(float(tStr))
            if cellType not in synapses:
                synapses[cellType] = [(synID, secID, ptID, synTimes, somaDist)]
            else:
                synapses[cellType].append(
                    (synID, secID, ptID, synTimes, somaDist))
            lineCnt += 1
    return synapses


def read_complete_synapse_activation_file(fname):
    '''Reads list of all functional synapses and their activation times.
    
    This reader also returns "structure label" in addition to the columns of :func:`read_synapse_activation_file`.

    .. deprecated::
        This format is now commonly a pandas or dask dataframe.
        They can still be explicitly read with this function
        using Python's ``open()`` and ``read()`` capabilities, but this is not recommended, or efficient.
    
    
    Args: 
        fname (str): 
            Filename of a synapse activation file.
            Such a file can be generated with :func:`single_cell_parser.analyze.synanalysis.comute_synapse_distances_times`.
    
    Returns: 
        dict: A dictionary with cell types as keys and list of synapse locations and activation times, coded as tuples: (synapse ID, soma distance, section ID, point ID, structure label, [t1, t2, ... , tn])
    '''
    synapses = {}
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            splitLine = line.split('\t')
            cellType = splitLine[0]
            synID = int(splitLine[1])
            somaDist = float(splitLine[2])
            secID = int(splitLine[3])
            ptID = int(splitLine[4])
            structure = splitLine[5]
            synTimes = []
            synTimesStr = splitLine[6].split(',')
            for tStr in synTimesStr:
                if tStr:
                    synTimes.append(float(tStr))
            if cellType not in synapses:
                synapses[cellType] = [(
                    synID, somaDist, secID, ptID, structure, synTimes)]
            else:
                synapses[cellType].append(
                    (synID, somaDist, secID, ptID, structure, synTimes))

    return synapses


def read_spike_times_file(fname):
    '''Reads all trials and spike times within these trials.

    .. deprecated::
        This format is now commonly a pandas or dask dataframe.
        They can still be explicitly read with this function
        using Python's ``open()`` and ``read()`` capabilities, but this is not recommended, or efficient.
    
    
    Args:
        fname (str): 
            file of format:
            trial nr.   activation times (comma-separated list or empty)

    Raises:
        RuntimeError: If a trial number is found twice in the file
    
    Returns:
        dict: Dictionary with trial numbers as keys (integers), and tuples of spike times in each trial as values
    
    Example:

        >>> spike_file
        # Spike times file
        # trial nr.   activation times (ms)
        1   100.2,698.1
        2   100.2,698.1,1000.0
        ...
        >>> read_spike_times_file(spike_file)
        {
            1: (100.2, 698.1),
            2: (100.2, 698.1, 1000.0),
            ...
        }
    '''
    spikeTimes = {}
    with dbopen(fname, 'r') as spikeTimeFile:
        for line in spikeTimeFile:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            splitLine = line.split('\t')
            trial = int(splitLine[0])
            tmpTimes = []
            if len(splitLine) > 1:
                spikeTimesStr = splitLine[1].split(',')
                for tStr in spikeTimesStr:
                    if tStr:
                        tmpTimes.append(float(tStr))
            if trial not in spikeTimes:
                spikeTimes[trial] = tuple(tmpTimes)
            else:
                errstr = 'Error reading spike times file: duplicate trial number (trial %d)' % trial
                raise RuntimeError(errstr)

    return spikeTimes


def write_all_traces(fname, t, vTraces):
    """Write out a list of voltage traces.

    Args:
        fname (str): The name of the file to write to.
        t (list): The time points of the voltage traces.
        vTraces (list): A list of voltage traces.

    Returns:
        None. Writes out the voltage traces to :param:`fname`.
    
    Example:

        >>> t = [0.0, 0.1, 0.2]
        >>> vTraces = [[-65.0, -64.9, -64.8], [-70.0, -69.9, -69.8]]
        >>> write_all_traces('voltage_traces.dat', t, vTraces)
    """
    with dbopen(fname, 'w') as outputFile:
        header = 't'
        for i in range(len(vTraces)):
            header += '\tVm run %02d' % i
        header += '\n'
        outputFile.write(header)
        for i in range(len(t)):
            line = str(t[i])
            for j in range(len(vTraces)):
                line += '\t'
                line += str(vTraces[j][i])
            line += '\n'
            outputFile.write(line)



def write_synapse_activation_file(
    fname=None,
    cell=None,
    synTypes=None,
    synDistances=None,
    synTimes=None,
    activeSyns=None):
    """Write out a :ref:`syn_activation_format` file.

    Used in :func:`~single_cell_parser.analyze.synanalysis.compute_synapse_distances_times` 
    to write out a synapse activation file.

    The following information is saved:

    - synapse type: to which presynaptic cell type this synapse belongs to.
    - synapse ID: unique identifier for the synapse.
    - soma distance: distance from the synapse to the soma.
    - section ID: ID of the section of the postsynaptic cell that contains this synapse.
    - section pt ID: ID of the point in the section that contains this synapse.
    - dendrite label: label of the dendrite that contains this synapse.
    - activation times: times at which the synapse was active (ms).

    Args:
        fname (str): The output file name as a ful path, including the file extension. Preferably unique (see e.g. :func:`~simrun.generate_synapse_activations._evoked_activity` for the generation of unique syapse activation filenames)
        cell (:class:`single_cell_parser.cell.Cell`): Cell object.
        synTypes (list): list of synapse types.
        synDistances (dict): dictionary of synapse distances per synapse type.
        synTimes (dict): dictionary of synapse activation times per synapse type. Values are a list of the activation times for each synapse within that type.
        activeSyns (dict): dictionary of active synapses per synapse type. Values are a list of booleans indicating whether each synapse of that type is active.

    Returns:
        None. Writes out the synapse activation file to :param:`fname`.

    Example:
        
        >>> synTypes = ['cell_type_1']  # 1 synapse type
        >>> synTimes = {'cell_type_1': [[0.1, 0.2, 0.3], [0.15, 0.25, 0.35], [0.2, 0.3, 0.4]]}  # 3 synapses of that type
        >>> synDistances = {'cell_type_1': [150.0, 200.0, 250.0]}
        >>> activeSyns = {'cell_type_1': [True, True, True]}  # all 3 synapses are active
        >>> write_synapse_activation_file(
        ...     'synapse_activation.csv', 
        ...     cell, 
        ...     synTypes, 
        ...     synDistances, 
        ...     synTimes, 
        ...     activeSyns
        ... )

    """
    if fname is None or cell is None or synTypes is None or synDistances is None or synTimes is None or activeSyns is None:
        err_str = 'Incomplete data! Cannot write functional realization file'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# synapse type\t'
        header += 'synapse ID\t'
        header += 'soma distance\t'
        header += 'section ID\t'
        header += 'section pt ID\t'
        header += 'dendrite label\t'
        header += 'activation times\n'
        outputFile.write(header)
        for synType in synTypes:
            for i in range(len(cell.synapses[synType])):
                if not activeSyns[synType][i]:
                    continue
                secID = cell.synapses[synType][i].secID
                ptID = cell.synapses[synType][i].ptID
                dendLabel = cell.sections[secID].label
                line = synType
                line += '\t'
                line += str(i)
                line += '\t'
                line += str(synDistances[synType][i])
                line += '\t'
                line += str(secID)
                line += '\t'
                line += str(ptID)
                line += '\t'
                line += str(dendLabel)
                line += '\t'
                for t in synTimes[synType][i]:
                    line += str(t)
                    line += ','
                line += '\n'
                outputFile.write(line)


def write_synapse_weight_file(fname=None, cell=None):
    """Write out a synapse weight file.
    
    This file contains the following information:
    
    - synapse type
    - synapse ID
    - section ID
    - section pt ID
    - receptor type
    - synapse weights
    
    Args:
        fname (str): The name of the file to write to.
        cell (:class:`single_cell_parser.cell.Cell`): The cell object, containing synapses.
    
    Returns:
        None. Writes out the synapse weight file to :param:`fname`.
        
    """
    if fname is None or cell is None:
        err_str = 'Incomplete data! Cannot write functional realization file'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# synapse type\t'
        header += 'synapse ID\t'
        header += 'section ID\t'
        header += 'section pt ID\t'
        header += 'receptor type\t'
        header += 'synapse weights\n'
        outputFile.write(header)
        for synType in list(cell.synapses.keys()):
            for i in range(len(cell.synapses[synType])):
                for recepStr in list(cell.synapses[synType][i].weight.keys()):
                    secID = cell.synapses[synType][i].secID
                    ptID = cell.synapses[synType][i].ptID
                    line = synType
                    line += '\t'
                    line += str(i)
                    line += '\t'
                    line += str(secID)
                    line += '\t'
                    line += str(ptID)
                    line += '\t'
                    line += recepStr
                    line += '\t'
                    for g in cell.synapses[synType][i].weight[recepStr]:
                        line += str(g)
                        line += ','
                    line += '\n'
                    outputFile.write(line)


def write_PSTH(fname=None, PSTH=None, bins=None):
    '''Write PSTH and time bins of PSTH, 
    
    Bins contain left and right end of each bin, i.e. ``len(bins) = len(PSTH) + 1``

    Args:
        fname (str): The name of the file to write to.
        PSTH (list): A list of PSTH values.
        bins (list): A list of time bins, including begin and end
        
    Returns:
        None. Writes out the PSTH file to :param:`fname`.

    Example:

        >>> PSTH = [1, 1, 2]
        >>> bins = [0.0, 0.1, 0.2, 0.3]
        >>> write_PSTH('PSTH.param', PSTH, bins)
        >>> PSTH.param
        # bin begin	bin end	APs/trial/bin
        0.0	0.1	1
        0.1	0.2	1
        0.2	0.3	2
    '''
    if fname is None or PSTH is None or bins is None:
        err_str = 'Incomplete data! Cannot write PSTH'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# bin begin\t'
        header += 'bin end\t'
        header += 'APs/trial/bin\n'
        outputFile.write(header)
        for i in range(len(PSTH)):
            line = str(bins[i])
            line += '\t'
            line += str(bins[i + 1])
            line += '\t'
            line += str(PSTH[i])
            line += '\n'
            outputFile.write(line)


def write_spike_times_file(fname=None, spikeTimes=None):
    '''Write trial numbers and all spike times in each trial (may be empty).

    Args:
        fname (str): The name of the file to write to.
        spikeTimes (dict): A dictionary with trial numbers as keys (int) and tuples of spike times in each trial as values.
    
    Returns:
        None. Writes out the spike times file to :param:`fname`.

    Example:

        >>> spikeTimes = {0: [0.1, 0.2, 0.3], 1: [], 2: [0.2, 0.3]}
        >>> write_spike_times_file('spike_times.param', spikeTimes)
        >>> spike_times.param
        # trial	spike times
        0	0.1,0.2,0.3,
        1	
        2	0.2,0.3,
    '''
    if fname is None or spikeTimes is None:
        err_str = 'Incomplete data! Cannot write spike times file'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outFile:
        header = '# trial\tspike times\n'
        outFile.write(header)
        trials = list(spikeTimes.keys())
        trials.sort()
        for trial in trials:
            line = str(trial)
            line += '\t'
            for tSpike in spikeTimes[trial]:
                line += str(tSpike)
                line += ','
            line += '\n'
            outFile.write(line)


def write_presynaptic_spike_times(fname=None, cells=None):
    '''Write cell type, presynaptic cell ID and spike times of all connected
    presynaptic point cells.

    Args:
        fname (str): The name of the file to write to.
        cells (dict): A dictionary with cell types as keys and lists of cells as values.

    Returns:
        None. Writes out the presynaptic spike times file to :param:`fname`.

    Example:

        >>> cells = {'cell_type_1': [cell1, cell2], 'cell_type_2': [cell3]}
        >>> write_presynaptic_spike_times('presynaptic_spikes.param', cells)
        >>> presynaptic_spikes.param
        # presynaptic cell type	cell ID	spike times
        cell_type_1	0	100.4,
        cell_type_1	1	
        cell_type_2	0	30.6,205.1,500.0,
    '''
    if fname is None or cells is None:
        err_str = 'Incomplete data! Cannot write presynaptic spike times'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# presynaptic cell type\tcell ID\tspike times\n'
        outputFile.write(header)
        preTypes = list(cells.keys())
        preTypes.sort()
        for preType in preTypes:
            for i in range(len(cells[preType])):
                cell = cells[preType][i]
                spikeTimes = cell.spikeTimes
                if not len(cell.spikeTimes):
                    continue
                line = preType
                line += '\t'
                line += str(i)
                line += '\t'
                spikeTimes.sort()
                for t in spikeTimes:
                    line += str(t)
                    line += ','
                line += '\n'
                outputFile.write(line)
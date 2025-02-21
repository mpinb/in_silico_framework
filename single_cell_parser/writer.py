'''Write out anatomical, morphology or simulation data.
'''

from data_base.dbopen import dbopen
from matplotlib import cm
from matplotlib.colors import Normalize
import os

__author__  = 'Robert Egger'
__date__    = '2012-03-08'

labels2int = {\
    "Neuron":                 2,\
    "Dendrite":               3,\
    "ApicalDendrite":         4,\
    "BasalDendrite":          5,\
    "Axon":                   6,\
    "AIS":                    6,\
    "Myelin":                 6,\
    "Node":                   6,\
    "Soma":                   7,\
    "Landmark":               8,\
    "Pia":                    9,\
    "WhiteMatter":           48,\
    "Vessel":                10,\
    "Barrel":                11,\
    "ZAxis":                 50,\
    "aRow":                  12,\
    "A1":                    13,\
    "A2":                    14,\
    "A3":                    15,\
    "A4":                    16,\
    "bRow":                  17,\
    "B1":                    18,\
    "B2":                    19,\
    "B3":                    20,\
    "B4":                    21,\
    "cRow":                  22,\
    "C1":                    23,\
    "C2":                    24,\
    "C3":                    25,\
    "C4":                    26,\
    "C5":                    27,\
    "C6":                    28,\
    "dRow":                  29,\
    "D1":                    30,\
    "D2":                    31,\
    "D3":                    32,\
    "D4":                    33,\
    "D5":                    34,\
    "D6":                    35,\
    "eRow":                  36,\
    "E1":                    37,\
    "E2":                    38,\
    "E3":                    39,\
    "E4":                    40,\
    "E5":                    41,\
    "E6":                    42,\
    "greekRow":              43,\
    "Alpha":                 44,\
    "Beta":                  45,\
    "Gamma":                 46,\
    "Delta":                 47,\
    "Septum":                 0,\
              }


def write_landmark_file(fname=None, landmarkList=None):
    '''Write an AMIRA landmark file from 3D coordinates

    Args:
        fname (str): string, name of the output file
        landmarkList (list): list of tuples, each of which holds 3 float coordinates

    Returns:
        None. Writes out the landmark file to :paramref:`fname`

    Raises:
        RuntimeError: if no file name is given or if the landmark list is empty
        RuntimeError: if the landmarks have the wrong format (not 3 coordinates)

    Example:
        >>> landmarkList = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
        >>> write_landmark_file('landmarks.landmarkAscii', landmarkList)
    '''
    if fname is None:
        err_str = 'No landmark output file name given'
        raise RuntimeError(err_str)

    #if not landmarkList:
    #    print 'Landmark list empty!'
    #return
    nrCoords = 3 if not landmarkList else len(landmarkList[0])
    if nrCoords != 3:
        err_str = 'Landmarks have wrong format! Number of coordinates is ' + str(
            nrCoords) + ', should be 3'
        raise RuntimeError(err_str)

    if not fname.endswith('.landmarkAscii'):
        fname += '.landmarkAscii'

    with dbopen(fname, 'w') as landmarkFile:
        nrOfLandmarks = len(landmarkList)
        header = '# AmiraMesh 3D ASCII 2.0\n\n'\
                'define Markers ' + str(nrOfLandmarks) + '\n\n'\
                'Parameters {\n'\
                '\tNumSets 1,\n'\
                '\tContentType \"LandmarkSet\"\n'\
                '}\n\n'\
                'Markers { float[3] Coordinates } @1\n\n'\
                '# Data section follows\n'\
                '@1\n'
        landmarkFile.write(header)
        for pt in landmarkList:
            line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
            landmarkFile.write(line)


def write_sim_results(fname, t, v):
    """Write out a voltage trace file.
    
    Args:
        fname (str): The name of the file to write to.
        t (list): The time points of the voltage trace.
        v (list): The voltage trace.
        
    Returns:
        None. Writes out the voltage trace file to :paramref:`fname`.
        
    Example:
        
        >>> t = [0.0, 0.1, 0.2]
        >>> v = [-65.0, -64.9, -64.8]
        >>> write_sim_results('voltage_trace.dat', t, v)
    """
    with dbopen(fname, 'w') as outputFile:
        header = '# t\tvsoma'
        header += '\n\n'
        outputFile.write(header)
        for i in range(len(t)):
            line = str(t[i])
            line += '\t'
            line += str(v[i])
            line += '\n'
            outputFile.write(line)


def write_all_traces(fname, t, vTraces):
    """Write out a list of voltage traces.

    Args:
        fname (str): The name of the file to write to.
        t (list): The time points of the voltage traces.
        vTraces (list): A list of voltage traces.

    Returns:
        None. Writes out the voltage traces to :paramref:`fname`.
    
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


def write_cell_synapse_locations(fname=None, synapses=None, cellID=None):
    '''Write a :ref:`syn_file_format` file.
     
    :ref:`syn_file_format` files contain a cell's synapses with the locations
    coded by section ID and section x of cell with ID "cellID".

    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :py:meth:`single_cell_parser.reader.read_synapse_realization` for the corresponding reader function.
    - :py:meth:`write_pruned_synapse_locations` for a similar function that includes a `pruned` flag.

    Args:
        fname (str): The name of the file to write to.
        synapses (dict): A dictionary of synapses, with keys as synapse types and values as lists of synapses.
        cellID (str): The ID of the cell.

    Returns:
        None. Writes out the synapse location file to :paramref:`fname`.
    '''
    if fname is None or synapses is None or cellID is None:
        err_str = 'Incomplete data! Cannot write synapse location file'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# Synapse distribution file\n'
        header += '# corresponding to cell: '
        header += cellID
        header += '\n'
        header += '# Type - section - section.x\n\n'
        outputFile.write(header)
        for synType in list(synapses.keys()):
            for syn in synapses[synType]:
                line = syn.preCellType
                line += '\t'
                line += str(syn.secID)
                line += '\t'
                if syn.x > 1.0:
                    syn.x = 1.0
                if syn.x < 0.0:
                    syn.x = 0.0
                line += str(syn.x)
                line += '\n'
                outputFile.write(line)


def write_pruned_synapse_locations(fname=None, synapses=None, cellID=None):
    '''Write a :ref:`syn_file_format` file with a `pruned` flag.

    :ref:`syn_file_format` files contain a cell's synapses with the locations
    coded by section ID and section x of cell with ID "cellID" and a pruned flag (1 or 0).

    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :py:meth:`single_cell_parser.reader.read_pruned_synapse_realization` for the corresponding reader function.
    - :py:meth:`write_cell_synapse_locations` for a similar function that does not include a `pruned` flag.

    Args:
        fname (str): The name of the file to write to.
        synapses (dict): A dictionary of synapses (see :py:meth:`~single_cell_parser.reader.read_pruned_synapse_locations`).
        cellID (str): The ID of the cell.

    Returns:
        None. Writes out the synapse location file to :paramref:`fname`.
    '''
    if fname is None or synapses is None or cellID is None:
        err_str = 'Incomplete data! Cannot write synapse location file'
        raise RuntimeError(err_str)

    with dbopen(fname, 'w') as outputFile:
        header = '# Synapse distribution file\n'
        header += '# corresponding to cell: '
        header += cellID
        header += '\n'
        header += '# Type - section - section.x - pruned\n\n'
        outputFile.write(header)
        for synType in list(synapses.keys()):
            for syn in synapses[synType]:
                line = syn.preCellType
                line += '\t'
                line += str(syn.secID)
                line += '\t'
                if syn.x > 1.0:
                    syn.x = 1.0
                if syn.x < 0.0:
                    syn.x = 0.0
                line += str(syn.x)
                line += '\t'
                line += str(syn.pruned)
                line += '\n'
                outputFile.write(line)


def write_functional_realization_map(
        fname=None,
        functionalMap=None,
        anatomicalID=None):
    '''Write out a :ref:`con_file_format` file.

    Writes list of all functional connections coded by tuples (cell type, presynaptic cell index, synapse index).
    Only valid for anatomical synapse realization given by anatomicalID

    See also:

    - :ref:`con_file_format` for more information on the `.con` file format.
    - :py:meth:`single_cell_parser.reader.read_functional_realization_map` for the corresponding reader function.

    Args:
        fname (str): The name of the file to write to.
        functionalMap (list): 
            A list of tuples, each containing a cell type, a presynaptic cell ID, and a synapse ID.
        anatomicalID (str): The ID of the anatomical synapse realization.

    Example:

        >>> functionalMap = [('cell_type_1', 0, 0), ('cell_type_2', 0, 1)]
        >>> write_functional_realization_map('functional_realization.con', functionalMap, 'syn_file.syn')
    '''
    if fname is None or functionalMap is None or anatomicalID is None:
        err_str = 'Incomplete data! Cannot write functional realization file'
        raise RuntimeError(err_str)

    if not fname.endswith('.con') and not fname.endswith('.CON'):
        fname += '.con'

    with dbopen(fname, 'w') as outputFile:
        header = '# Functional realization file; only valid with synapse realization:\n'
        header += '# ' + anatomicalID
        header += '\n'
        header += '# Type - cell ID - synapse ID\n\n'
        outputFile.write(header)
        for con in functionalMap:
            line = con[0]
            line += '\t'
            line += str(con[1])
            line += '\t'
            line += str(con[2])
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

    Used in :py:meth:`~single_cell_parser.analyze.synanalysis.compute_synapse_distances_times` 
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
        fname (str): The output file name as a ful path, including the file extension. Preferably unique (see e.g. :py:meth:`~simrun.generate_synapse_activations._evoked_activity` for the generation of unique syapse activation filenames)
        cell (:py:class:`single_cell_parser.cell.Cell`): Cell object.
        synTypes (list): list of synapse types.
        synDistances (dict): dictionary of synapse distances per synapse type.
        synTimes (dict): dictionary of synapse activation times per synapse type. Values are a list of the activation times for each synapse within that type.
        activeSyns (dict): dictionary of active synapses per synapse type. Values are a list of booleans indicating whether each synapse of that type is active.

    Returns:
        None. Writes out the synapse activation file to :paramref:`fname`.

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
        cell (:py:class:`single_cell_parser.cell.Cell`): The cell object, containing synapses.
    
    Returns:
        None. Writes out the synapse weight file to :paramref:`fname`.
        
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
        None. Writes out the PSTH file to :paramref:`fname`.

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
        None. Writes out the spike times file to :paramref:`fname`.

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
        None. Writes out the presynaptic spike times file to :paramref:`fname`.

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


def write_cell_simulation(
        fname=None,
        cell=None,
        traces=None,
        tVec=None,
        allPoints=False,
        step_frames=10,
        selected_index=None):
    '''Write Amira SpatialGraph files corresponding to time steps of entire simulation run. 
    
    Recorded quantities are passed in tuple traces with strings and recorded in Vectors
    attached to Sections of cell

    Attention:
        Make sure to have created the cell with ``allPoints = True``.
    
    Attention:
        Performs interpolation if ``nseg != nrOfPts`` for a Section

    Args:
        fname (str): The name of the file to write to.
        cell (:py:class:`single_cell_parser.cell.Cell`): The cell object.
        traces (list): A list of strings, each representing a recorded quantity.
        tVec (list): A list of time points.
        allPoints (bool): If True, all points of the cell are written to the file.
        step_frames (int): The number of frames to write.
        selected_index (list): A list of indices of the sections to write.

    Example:
    
    >>> write_cell_simulation(
    ...     '/output/directory',
    ...     cell = cell,
    ...     traces = ['Vm'],
    ...     tVec = cell.tVec,
    ...     step_frames = 1,
    ...     selected_index=[selected_index],
    ...     allPoints = True)
    
    '''
    if fname is None or cell is None or traces is None or tVec is None:
        err_str = 'Incomplete data! Cannot write SpatialGraph simulation results'
        raise RuntimeError(err_str)

    axonLabels = ['Axon', 'AIS', 'Myelin']

    totalNrPts = 0
    nrOfEdges = 0
    for sec in cell.tree:
        if sec.label in axonLabels:
            continue
        nrOfEdges += 1
        if not allPoints:
            totalNrPts += sec.nseg
        else:
            totalNrPts += sec.nrOfPts

    if not os.path.exists(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))

    header = "# AmiraMesh 3D ASCII 2.0" + "\n"
    header += "# This SpatialGraph file was created by the Neuron Registration Tool NeuroMap " + "\n"
    header += "# NeuroMap was programmed by Robert Egger," + "\n"
    header += "# Max-Planck-Florida Institute, Jupiter, Florida " + "\n"
    header += "" + "\n"
    header += "define VERTEX " + str(nrOfEdges * 2) + "\n"
    header += "define EDGE " + str(nrOfEdges) + "\n"
    header += "define POINT " + str(totalNrPts) + "\n"
    header += "" + "\n"
    header += "Parameters {GraphLabels {" + "\n"
    header += "        Neuron { " + "\n"
    header += "            Dendrite {" + "\n"
    header += "                ApicalDendrite {" + "\n"
    header += "                    Color 1 0.5 0.5," + "\n"
    header += "                    Id 4 }" + "\n"
    header += "                BasalDendrite {" + "\n"
    header += "                    Color 0.8 0.4 0.4," + "\n"
    header += "                    Id 5 }" + "\n"
    header += "                Color 1 0 0," + "\n"
    header += "                Id 3 }" + "\n"
    header += "            Axon {" + "\n"
    header += "                Color 0 0 1," + "\n"
    header += "                Id 6 }" + "\n"
    header += "            Soma {" + "\n"
    header += "                Color 1 0 0," + "\n"
    header += "                Id 7 }" + "\n"
    header += "            Color 1 0 0," + "\n"
    header += "            Id 2 }" + "\n"
    header += "        Landmark {" + "\n"
    header += "            Pia {" + "\n"
    header += "                Color 0 1 0.5," + "\n"
    header += "                Id 9 }" + "\n"
    header += "            Vessel {" + "\n"
    header += "                Color 1 0.5 0," + "\n"
    header += "                Id 10 }" + "\n"
    header += "            Barrel {" + "\n"
    header += "                aRow {" + "\n"
    header += "                    A1 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 13 }" + "\n"
    header += "                    A2 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 14 }" + "\n"
    header += "                    A3 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 15 }" + "\n"
    header += "                    A4 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 16 }" + "\n"
    header += "                    Color 1 0.2 0.2," + "\n"
    header += "                    Id 12 }" + "\n"
    header += "                bRow {" + "\n"
    header += "                    B1 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 18 }" + "\n"
    header += "                    B2 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 19 }" + "\n"
    header += "                    B3 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 20 }" + "\n"
    header += "                    B4 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 21 }" + "\n"
    header += "                    Color 1 0.25 0.25," + "\n"
    header += "                    Id 17 }" + "\n"
    header += "                cRow {" + "\n"
    header += "                    C1 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 23 }" + "\n"
    header += "                    C2 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 24 }" + "\n"
    header += "                    C3 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 25 }" + "\n"
    header += "                    C4 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 26 }" + "\n"
    header += "                    C5 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 27 }" + "\n"
    header += "                    C6 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 28 }" + "\n"
    header += "                    Color 1 0.3 0.3," + "\n"
    header += "                    Id 22 }" + "\n"
    header += "                dRow {" + "\n"
    header += "                    D1 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 30 }" + "\n"
    header += "                    D2 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 31 }" + "\n"
    header += "                    D3 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 32 }" + "\n"
    header += "                    D4 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 33 }" + "\n"
    header += "                    D5 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 34 }" + "\n"
    header += "                    D6 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 35 }" + "\n"
    header += "                    Color 1 0.35 0.35," + "\n"
    header += "                    Id 29 }" + "\n"
    header += "                eRow {" + "\n"
    header += "                    E1 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 37 }" + "\n"
    header += "                    E2 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 38 }" + "\n"
    header += "                    E3 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 39 }" + "\n"
    header += "                    E4 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 40 }" + "\n"
    header += "                    E5 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 41 }" + "\n"
    header += "                    E6 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 42 }" + "\n"
    header += "                    Color 1 0.4 0.4," + "\n"
    header += "                    Id 36 }" + "\n"
    header += "                greekRow {" + "\n"
    header += "                    Alpha {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 44 }" + "\n"
    header += "                    Beta {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 45 }" + "\n"
    header += "                    Gamma {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 46 }" + "\n"
    header += "                    Delta {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 47 }" + "\n"
    header += "                    Color 1 0.1 0.1," + "\n"
    header += "                    Id 43 }" + "\n"
    header += "                Color 0 1 0," + "\n"
    header += "                Id 11 }" + "\n"
    header += "            WhiteMatter {" + "\n"
    header += "                Color 0.5 1 0.75," + "\n"
    header += "                Id 48 }" + "\n"
    header += "            OtherBarrels {" + "\n"
    header += "                Color 1 0 1," + "\n"
    header += "                Id 49 }" + "\n"
    header += "            ZAxis {" + "\n"
    header += "                Color 0 0 0," + "\n"
    header += "                Id 50 }" + "\n"
    header += "            Color 0 1 1," + "\n"
    header += "            Id 8 }" + "\n"
    header += "        Id 0," + "\n"
    header += "        Color 0 0 0 }" + "\n"
    header += "ContentType \"HxSpatialGraph\" }" + "\n"
    header += "" + "\n"
    header += "VERTEX { float[3] VertexCoordinates } @1 " + "\n"
    header += "VERTEX {int GraphLabels } @2 " + "\n"
    header += "" + "\n"
    header += "EDGE { int[2] EdgeConnectivity } @3 " + "\n"
    header += "EDGE { int NumEdgePoints } @4 " + "\n"
    header += "EDGE { int GraphLabels } @5 " + "\n"
    header += "" + "\n"
    header += "POINT { float[3] EdgePointCoordinates } @6 " + "\n"
    header += "POINT { float Diameter } @7 " + "\n"

    dataIndex = []
    for i in range(len(traces)):
        #        dataIndex.append(str(i + 7))
        #        header += "POINT { float " + traces[i] + " } @" + str(i + 7) + "\n"
        dataIndex.append(str(i + 8))
        header += "POINT { float " + traces[i] + " } @" + str(i + 8) + "\n"

    for i in range(len(tVec)):
        if selected_index is not None:
            if not i in selected_index:
                continue


#        only write every 10th time step for visualization
#        (step size for vis. will then be 0.25ms)
        if i % step_frames:
            continue
        stepFName = fname
        stepFName += '_'
        stepFName += '%07.3f' % tVec[i]
        stepFName += '.am'
        with dbopen(stepFName, 'w') as outFile:
            outFile.write(header)

            outFile.write('\n@1 # Vertices xyz coordinates\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                if not allPoints:
                    v1 = sec.segPts[0]
                    v2 = sec.segPts[-1]
                else:
                    v1 = sec.pts[0]
                    v2 = sec.pts[-1]
                line1 = '%.6f %.6f %.6f\n' % (v1[0], v1[1], v1[2])
                line2 = '%.6f %.6f %.6f\n' % (v2[0], v2[1], v2[2])
                outFile.write(line1)
                outFile.write(line2)

            outFile.write('\n@2 # Vertex Graph Label\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                line = '%d\n' % labels2int[sec.label]
                outFile.write(line)
                outFile.write(line)

            outFile.write('\n@3 # Edge Identifiers\n')
            j = 0
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                line = '%d %d\n' % (2 * j, 2 * j + 1)
                outFile.write(line)
                j += 1

            outFile.write('\n@4 # Number of Points per Edge\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                if not allPoints:
                    line = '%d\n' % sec.nseg
                else:
                    line = '%d\n' % sec.nrOfPts
                outFile.write(line)

            outFile.write('\n@5 # Edge Graph Labels\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                line = '%d\n' % labels2int[sec.label]
                outFile.write(line)

            outFile.write('\n@6 # Point xyz coordinates\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                if not allPoints:
                    for pt in sec.segPts:
                        line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
                        outFile.write(line)
                else:
                    for pt in sec.pts:
                        line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
                        outFile.write(line)

            outFile.write('\n@7 # Diameter at Point\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                for diam in sec.segDiams:
                    line = '%.6f\n' % diam
                    outFile.write(line)

            outFile.write('\n@8 # Vm at Point\n')
            for sec in cell.tree:
                if sec.label in axonLabels:
                    continue
                for vec in sec.recVList:
                    line = '%.6f\n' % vec[i]
                    outFile.write(line)

            if len(traces) > 1:
                for j in range(len(traces))[1:]:
                    var = traces[j]
                    outFile.write('\n@%d # %s at Point\n' % (j + 8, var))
                    for sec in cell.tree:
                        if sec.label in axonLabels:
                            continue

                        #Roberts original code only covered the case, that the mechanisms exist in
                        #every section:
                        #for vec in sec.recordVars[var]:
                        #    line = '%.6f\n' % vec[i]
                        #    outFile.write(line)
                        #END OF FUNCTION
                        #
                        #The following code extends this by first checking, if the segment contains the
                        #mechanism. If not, a zero-vector is used
                        #
                        #todo: allow other values than zero

                        #convert neuron section to convenient python list
                        segment_list = [seg for seg in sec]
                        #this is a seperated count variable for segments, that actually contain the mechanism
                        lv_for_record_vars = 0
                        #whereas lv reflects the number of segments, that have been processed
                        for lv, seg in enumerate(segment_list):
                            ## check if mechanism is in section
                            try:
                                href = eval('seg.' + var)
                                dummy_vec = sec.recordVars[var][
                                    lv_for_record_vars]
                                lv_for_record_vars = lv_for_record_vars + 1
                                line = '%.6f\n' % dummy_vec[i]
                            ##if not: use standard value
                            except NameError:
                                line = '%.6f\n' % 0

                            outFile.write(line)

                        assert lv_for_record_vars == len(sec.recordVars[var])


def write_functional_map(fname, functionalMap):
    """Write a functional map to an AMIRA file.
    
    Deprecated. Consider using :py:meth:`visualize.vtk.write_vtk_pointcloud_file` 
    or :py:meth:`visualize.vtk.write_vtk_frames` for visualization purposes.

    This method may still serve well if you need an AMIRA mesh file.
    
    Args:
        fname (str): The name of the file to write to.
        functionalMap (dict): A dictionary with cell labels as keys and lists of points as values.

    Returns:
        None. Writes out the functional map file to :paramref:`fname`.
    """
    totalNrPts = 0
    for key in list(functionalMap.keys()):
        totalNrPts += len(functionalMap[key])

    header = "# AmiraMesh 3D ASCII 2.0" + "\n"
    header += "# This SpatialGraph file was created by the Neuron Registration Tool NeuroMap " + "\n"
    header += "# NeuroMap was programmed by Robert Egger," + "\n"
    header += "# Max-Planck-Florida Institute, Jupiter, Florida " + "\n"
    header += "" + "\n"
    header += "define VERTEX " + str(totalNrPts * 2) + "\n"
    header += "define EDGE " + str(totalNrPts) + "\n"
    header += "define POINT " + str(totalNrPts * 2) + "\n"
    header += "" + "\n"
    header += "Parameters {GraphLabels {" + "\n"
    header += "        Neuron { " + "\n"
    header += "            Dendrite {" + "\n"
    header += "                ApicalDendrite {" + "\n"
    header += "                    Color 1 0.5 0.5," + "\n"
    header += "                    Id 4 }" + "\n"
    header += "                BasalDendrite {" + "\n"
    header += "                    Color 0.8 0.4 0.4," + "\n"
    header += "                    Id 5 }" + "\n"
    header += "                Color 1 0 0," + "\n"
    header += "                Id 3 }" + "\n"
    header += "            Axon {" + "\n"
    header += "                Color 0 0 1," + "\n"
    header += "                Id 6 }" + "\n"
    header += "            Soma {" + "\n"
    header += "                Color 1 0 0," + "\n"
    header += "                Id 7 }" + "\n"
    header += "            Color 1 0 0," + "\n"
    header += "            Id 2 }" + "\n"
    header += "        Landmark {" + "\n"
    header += "            Pia {" + "\n"
    header += "                Color 0 1 0.5," + "\n"
    header += "                Id 9 }" + "\n"
    header += "            Vessel {" + "\n"
    header += "                Color 1 0.5 0," + "\n"
    header += "                Id 10 }" + "\n"
    header += "            Barrel {" + "\n"
    header += "                aRow {" + "\n"
    header += "                    A1 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 13 }" + "\n"
    header += "                    A2 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 14 }" + "\n"
    header += "                    A3 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 15 }" + "\n"
    header += "                    A4 {" + "\n"
    header += "                        Color 1 0.2 0.2," + "\n"
    header += "                        Id 16 }" + "\n"
    header += "                Color 1 0.2 0.2," + "\n"
    header += "                Id 12 }" + "\n"
    header += "                bRow {" + "\n"
    header += "                    B1 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 18 }" + "\n"
    header += "                    B2 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 19 }" + "\n"
    header += "                    B3 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 20 }" + "\n"
    header += "                    B4 {" + "\n"
    header += "                        Color 1 0.25 0.25," + "\n"
    header += "                        Id 21 }" + "\n"
    header += "                    Color 1 0.25 0.25," + "\n"
    header += "                    Id 17 }" + "\n"
    header += "                cRow {" + "\n"
    header += "                    C1 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 23 }" + "\n"
    header += "                    C2 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 24 }" + "\n"
    header += "                    C3 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 25 }" + "\n"
    header += "                    C4 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 26 }" + "\n"
    header += "                    C5 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 27 }" + "\n"
    header += "                    C6 {" + "\n"
    header += "                        Color 1 0.3 0.3," + "\n"
    header += "                        Id 28 }" + "\n"
    header += "                    Color 1 0.3 0.3," + "\n"
    header += "                    Id 22 }" + "\n"
    header += "                dRow {" + "\n"
    header += "                    D1 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 30 }" + "\n"
    header += "                    D2 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 31 }" + "\n"
    header += "                    D3 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 32 }" + "\n"
    header += "                    D4 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 33 }" + "\n"
    header += "                    D5 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 34 }" + "\n"
    header += "                    D6 {" + "\n"
    header += "                        Color 1 0.35 0.35," + "\n"
    header += "                        Id 35 }" + "\n"
    header += "                    Color 1 0.35 0.35," + "\n"
    header += "                    Id 29 }" + "\n"
    header += "                eRow {" + "\n"
    header += "                    E1 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 37 }" + "\n"
    header += "                    E2 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 38 }" + "\n"
    header += "                    E3 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 39 }" + "\n"
    header += "                    E4 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 40 }" + "\n"
    header += "                    E5 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 41 }" + "\n"
    header += "                    E6 {" + "\n"
    header += "                        Color 1 0.4 0.4," + "\n"
    header += "                        Id 42 }" + "\n"
    header += "                    Color 1 0.4 0.4," + "\n"
    header += "                    Id 36 }" + "\n"
    header += "                greekRow {" + "\n"
    header += "                    Alpha {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 44 }" + "\n"
    header += "                    Beta {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 45 }" + "\n"
    header += "                    Gamma {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 46 }" + "\n"
    header += "                    Delta {" + "\n"
    header += "                        Color 1 0.1 0.1," + "\n"
    header += "                        Id 47 }" + "\n"
    header += "                    Color 1 0.1 0.1," + "\n"
    header += "                    Id 43 }" + "\n"
    header += "                Color 0 1 0," + "\n"
    header += "                Id 11 }" + "\n"
    header += "            WhiteMatter {" + "\n"
    header += "                Color 0.5 1 0.75," + "\n"
    header += "                Id 48 }" + "\n"
    header += "            OtherBarrels {" + "\n"
    header += "                Color 1 0 1," + "\n"
    header += "                Id 49 }" + "\n"
    header += "            ZAxis {" + "\n"
    header += "                Color 0 0 0," + "\n"
    header += "                Id 50 }" + "\n"
    header += "            Color 0 1 1," + "\n"
    header += "            Id 8 }" + "\n"
    header += "        Id 0," + "\n"
    header += "        Color 0 0 0 }" + "\n"
    header += "ContentType \"HxSpatialGraph\" }" + "\n"
    header += "" + "\n"
    header += "VERTEX { float[3] VertexCoordinates } @1 " + "\n"
    header += "VERTEX {int GraphLabels } @2 " + "\n"
    header += "" + "\n"
    header += "EDGE { int[2] EdgeConnectivity } @3 " + "\n"
    header += "EDGE { int NumEdgePoints } @4 " + "\n"
    header += "EDGE { int GraphLabels } @5 " + "\n"
    header += "" + "\n"
    header += "POINT { float[3] EdgePointCoordinates } @6 " + "\n"

    with dbopen(fname, 'w') as outFile:
        outFile.write(header)

        outFile.write('\n@1 # Vertices xyz coordinates\n')
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                v1, v2 = pair
                line1 = '%.6f %.6f %.6f\n' % (v1[0], v1[1], v1[2])
                line2 = '%.6f %.6f %.6f\n' % (v2[0], v2[1], v2[2])
                outFile.write(line1)
                outFile.write(line2)

        outFile.write('\n@2 # Vertex Graph Label\n')
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                line = '3\n'
                outFile.write(line)
                outFile.write(line)

        outFile.write('\n@3 # Edge Identifiers\n')
        j = 0
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                line = '%d %d\n' % (2 * j, 2 * j + 1)
                outFile.write(line)
                j += 1

        outFile.write('\n@4 # Number of Points per Edge\n')
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                line = '2\n'
                outFile.write(line)

        outFile.write('\n@5 # Edge Graph Labels\n')
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                line = '3\n'
                outFile.write(line)

        outFile.write('\n@6 # Point xyz coordinates\n')
        for key in list(functionalMap.keys()):
            for pair in functionalMap[key]:
                for pt in pair:
                    line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
                    outFile.write(line)


template_init = '''
# Amira Project 640
# AmiraZIBEdition
# Generated by AmiraZIBEdition 6.4.0
remove -all

# Create viewers
viewer setVertical 0

viewer 0 setTransparencyType 5
viewer 0 setAutoRedraw 0
viewer 0 show
mainWindow show

set hideNewModules 1
[ load ${AMIRA_ROOT}/data/colormaps/glow.col ] setLabel "glow.col"
"glow.col" setIconPosition 0 0
"glow.col" setNoRemoveAll 1
"glow.col" setVar "CustomHelp" {HxColormap256}
"glow.col" fire
"glow.col" setMinMax 0 255
"glow.col" flags setValue 1
"glow.col" shift setMinMax -1 1
"glow.col" shift setButtons 0
"glow.col" shift setEditButton 1
"glow.col" shift setIncrement 0.133333
"glow.col" shift setValue 0
"glow.col" shift setSubMinMax -1 1
"glow.col" scale setMinMax 0 1
"glow.col" scale setButtons 0
"glow.col" scale setEditButton 1
"glow.col" scale setIncrement 0.1
"glow.col" scale setValue 1
"glow.col" scale setSubMinMax 0 1
"glow.col" fire
"glow.col" setViewerMask 16383
'''
template_landmark = '''
set hideNewModules 0
[ load ${SCRIPTDIR}/LANDMARKNAME ] setLabel "LANDMARKNAME"
"LANDMARKNAME" setIconPosition 19 10
"LANDMARKNAME" fire
"LANDMARKNAME" fire
"LANDMARKNAME" setViewerMask 16383

set hideNewModules 0
create HxDisplayVertices "VERTEXVIEWID"
"VERTEXVIEWID" setIconPosition 59 59
"VERTEXVIEWID" setVar "CustomHelp" {HxDisplayVertices}
"VERTEXVIEWID" data connect "LANDMARKNAME"
"VERTEXVIEWID" colormap disconnect
"VERTEXVIEWID" colormap setDefaultColor 0.8 0.5 0.2
"VERTEXVIEWID" colormap setDefaultAlpha 1.000000
"VERTEXVIEWID" colormap activateLocalRange 1
"VERTEXVIEWID" colormap setLocalMinMax 0.000000 0.000000
"VERTEXVIEWID" colormap enableAlpha 1
"VERTEXVIEWID" colormap enableAlphaToggle 1
"VERTEXVIEWID" colormap setAutoAdjustRangeMode 1
"VERTEXVIEWID" colormap setColorbarMinMax 0 120
"VERTEXVIEWID" fire
"VERTEXVIEWID" color setIndex 0 0
"VERTEXVIEWID" drawStyle setValue 2
"VERTEXVIEWID" sphereRadius setMinMax 0 15.9162673950195
"VERTEXVIEWID" sphereRadius setButtons 0
"VERTEXVIEWID" sphereRadius setEditButton 1
"VERTEXVIEWID" sphereRadius setIncrement 1.06108
"VERTEXVIEWID" sphereRadius setValue 7
"VERTEXVIEWID" sphereRadius setSubMinMax 0 15.9162673950195
"VERTEXVIEWID" pointSize setMinMax 1 10
"VERTEXVIEWID" pointSize setButtons 1
"VERTEXVIEWID" pointSize setEditButton 1
"VERTEXVIEWID" pointSize setIncrement 1
"VERTEXVIEWID" pointSize setValue 7
"VERTEXVIEWID" pointSize setSubMinMax 1 10
"VERTEXVIEWID" complexity setMinMax 0 1
"VERTEXVIEWID" complexity setButtons 0
"VERTEXVIEWID" complexity setEditButton 1
"VERTEXVIEWID" complexity setIncrement 0.1
"VERTEXVIEWID" complexity setValue 0.2
"VERTEXVIEWID" complexity setSubMinMax 0 1
"VERTEXVIEWID" textOnOff setValue 0
"VERTEXVIEWID" transparentOnOff setValue 0
"VERTEXVIEWID" displaySelectionOnOff setValue 0
"VERTEXVIEWID" fontSize setMinMax 5 50
"VERTEXVIEWID" fontSize setButtons 1
"VERTEXVIEWID" fontSize setEditButton 1
"VERTEXVIEWID" fontSize setIncrement 1
"VERTEXVIEWID" fontSize setValue 15
"VERTEXVIEWID" fontSize setSubMinMax 5 50
"VERTEXVIEWID" transparency setMinMax 0 1
"VERTEXVIEWID" transparency setButtons 0
"VERTEXVIEWID" transparency setEditButton 1
"VERTEXVIEWID" transparency setIncrement 0.0666667
"VERTEXVIEWID" transparency setValue 0.9
"VERTEXVIEWID" transparency setSubMinMax 0 1
"VERTEXVIEWID" setTextColor 1 1 1
"VERTEXVIEWID" pointStarts0
"VERTEXVIEWID" fire
"VERTEXVIEWID" drawStyle setValue 2
"VERTEXVIEWID" setColor 0 LEN RRRR GGGG BBBB
"VERTEXVIEWID" fire
"VERTEXVIEWID" setViewerMask 16383
"VERTEXVIEWID" select
"VERTEXVIEWID" setPickable 1
'''


def generate_landmark_template(landmark_name, c, vertexviewid, len):
    """Generate a template for a landmark file in Amira.
    
    Args:
        landmark_name (str): The name of the landmark file.
        c (tuple): The color of the landmark.
        vertexviewid (int): The vertex view id.
        len (int): The length of the landmark.
    
    Returns:
        str: The template for the landmark file.
    """
    return template_landmark\
        .replace('LANDMARKNAME', landmark_name)\
        .replace('RRRR', str(c[0]))\
        .replace('GGGG', str(c[1]))\
        .replace('BBBB', str(c[2]))\
        .replace('VERTEXVIEWID', str(vertexviewid))\
        .replace('LEN', str(len))


# def write_landmarks_colorcoded_to_folder(basedir, landmarks, values, vmin = 0, vmax = 10, vbinsize = .1):
#     import os
#     if not os.path.exists(basedir):
#         os.makedirs(basedir)
#     lv = 0
#     with open(os.path.join(basedir, 'out.hx'), 'w') as f:
#         f.write(template_init)
#         for l, v in zip(landmarks, values):
#             landmark_name = str(v)+'.landmarkAscii'
#             write_landmark_file(os.path.join(basedir, landmark_name), [l])
#             c = value_to_color(v, vmin = vmin, vmax =vmax)
#             print c
#             f.write(generate_landmark_template(landmark_name, c, lv))
#             lv = lv + 1


def write_landmarks_colorcoded_to_folder(
        basedir,
        landmarks,
        values,
        vmin=0,
        vmax=10,
        vbinsize=.1):
    """Write landmarks to a folder, colorcoded by their values.
    
    Args:
        basedir (str): The directory to write the landmarks to.
        landmarks (numpy.array): The landmarks to write.
        values (numpy.array): The values to color the landmarks by.
        vmin (float): The minimum value to color by.
        vmax (float): The maximum value to color by.
        vbinsize (float): The size of the bins to color by.
        
    Returns:
        None. Writes out the landmarks to the directory :paramref:`basedir`.
    """
    import os
    from itertools import groupby
    # os.makedirs(basedir)
    lv = 0
    key = lambda x: int(x[1] / vbinsize)
    complete_list = list(zip(landmarks.tolist(), values.tolist()))
    complete_list = sorted(complete_list, key=key)

    with open(os.path.join(basedir, 'out.hx'), 'w') as f:
        f.write(template_init)
        for v, group in groupby(complete_list, key=key):
            v = v * vbinsize
            landmark_name = str(v) + '.landmarkAscii'
            print('writing landmarks for values between {} and {} to {}'.format(
                v, v + vbinsize, landmark_name))
            group = list(zip(*group))
            l, _ = group[0], group[1]
            print(len(l))
            write_landmark_file(os.path.join(basedir, landmark_name), l)
            c = value_to_color(v, vmin=vmin, vmax=vmax)
            f.write(generate_landmark_template(landmark_name, c, lv,
                                               len(l) - 1))
            lv = lv + 1


def value_to_color(v, vmin=0, vmax=1):
    '''Map a value to a color.
        
    See: https://stackoverflow.com/questions/15140072/how-to-map-number-to-color-using-matplotlibs-colormap
    
    Args:
        v (float): The value to map to a color.
        vmin (float): The minimum value of the range. Default is 0.
        vmax (float): The maximum value of the range. Default is 1.
        
    Returns:
        tuple: The RGBA color tuple.
    '''
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.inferno
    m = cm.ScalarMappable(norm=norm, cmap=cmap)
    return m.to_rgba(v)[:-1]
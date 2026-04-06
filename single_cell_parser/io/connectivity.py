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

def read_synapse_realization(fname):
    """Read a :ref:`syn_file_format` file and returns a dictionary of synapse locations.

    
    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :func:`~single_cell_parser.reader.read_pruned_synapse_realization`.
    - :func:`~single_cell_parser.writer.write_cell_synapse_locations` for the corresponding writer.
    
    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.syn` or `.SYN` suffix.

    Returns:
        dict: A dictionary with synapse types as keys and lists of synapse locations as values.
        Each synapse location is a tuple of (section ID, section point ID).

    Example:

        >>> synapse_file
        # Synapse distribution file
        # corresponding to cell: 86_C2_center
        # Type - section - section.x
        VPM_E1  112     0.138046479525
        VPM_E1  130     0.305058053119
        VPM_E1  130     0.190509288017
        VPM_E1  9       0.368760777084
        VPM_E1  110     0.0
        VPM_E1  11      0.120662910562
        ...
        >>> read_synapse_realization(synapse_file)
        {
            'VPM_E1': [
                (112, 0.138046479525),
                (130, 0.305058053119),
                (130, 0.190509288017),
                (9, 0.368760777084),
                (110, 0.0),
                (11, 0.120662910562),
                ...
            ]
        }
    """
    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        raise IOError('Input file is not a synapse realization file!')

    synapses = {}
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine or stripLine[0] == '#':
                continue
            splitLine = stripLine.split('\t')
            synType = splitLine[0]
            sectionID = int(splitLine[1])
            sectionx = float(splitLine[2])
            if synType not in synapses:
                synapses[synType] = [(sectionID, sectionx)]
            else:
                synapses[synType].append((sectionID, sectionx))

    return synapses


def read_pruned_synapse_realization(fname):
    """Read in a :ref:`syn_file_format` and returns a dictionary of synapse locations and whether they are pruned or not.
    
    Pruned synapses are synapses that have been removed from the model.
    Whether or not they are pruned is indicated by an additional column in the synapse realization file.
    
    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :func:`~single_cell_parser.reader.read_synapse_realization`.
    - :func:`~single_cell_parser.writer.write_pruned_synapse_locations` for the corresponding writer.
    
    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.syn` or `.SYN` suffix.
        
    Returns:
        dict: A dictionary with synapse types as keys and lists of synapse locations as values.
        
    Example:
        >>> synapse_file
        # Synapse distribution file
        # corresponding to cell: 86_C2_center
        # Type - section - section.x - pruned
        VPM_E1  112     0.138046479525  0
        VPM_E1  130     0.305058053119  0
        ...
        >>> read_pruned_synapse_realization(synapse_file)
        {
            'VPM_E1': [
                (112, 0.138046479525, 0),
                (130, 0.305058053119, 0),  
                ...
                ]
        }
    """
    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        raise IOError('Input file is not a synapse realization file!')

    synapses = {}
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine or stripLine[0] == '#':
                continue
            splitLine = stripLine.split('\t')
            synType = splitLine[0]
            sectionID = int(splitLine[1])
            sectionx = float(splitLine[2])
            pruned = int(splitLine[3])
            if synType not in synapses:
                synapses[synType] = [(sectionID, sectionx, pruned)]
            else:
                synapses[synType].append((sectionID, sectionx, pruned))

    return synapses


def read_functional_realization_map(fname):
    '''Read in a :ref:`con_file_format` file and return a dictionary of functional connections.

    Only valid for anatomical synapse realization given by anatomicalID.

    See also:

    - :ref:`con_file_format` for more information on the `.con` file format.
    - :func:`~single_cell_parser.writer.write_functional_realization_map` for the corresponding writer.

    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.con` or `.CON` suffix.

    Returns:
        tuple: 
            A dictionary with cell types as keys and a list of synapse information for each synapse as values.
            Synapse information is a 3-tuple with (cell type, cell ID, synapse ID)
            The filename of the corresponding :ref:`syn_file_format` file.
    '''
    if not fname.endswith('.con') and not fname.endswith('.CON'):
        raise IOError('Input file is not a functional map realization file!')

    connections = {}
    anatomicalID = None
    lineCnt = 0
    with dbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine:
                continue
            lineCnt += 1
            if stripLine[0] == '#':
                if lineCnt == 2:
                    splitLine = stripLine.split(' ')
                    anatomicalID = splitLine[-1]
                continue
            splitLine = stripLine.split('\t')
            cellType = splitLine[0]
            cellID = int(splitLine[1])
            synID = int(splitLine[2])
            if cellType not in connections:
                connections[cellType] = [(cellType, cellID, synID)]
            else:
                connections[cellType].append((cellType, cellID, synID))
    return connections, anatomicalID


def write_pruned_synapse_locations(fname=None, synapses=None, cellID=None):
    '''Write a :ref:`syn_file_format` file with a `pruned` flag.

    :ref:`syn_file_format` files contain a cell's synapses with the locations
    coded by section ID and section x of cell with ID "cellID" and a pruned flag (1 or 0).

    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :func:`single_cell_parser.reader.read_pruned_synapse_realization` for the corresponding reader function.
    - :func:`write_cell_synapse_locations` for a similar function that does not include a `pruned` flag.

    Args:
        fname (str): The name of the file to write to.
        synapses (dict): A dictionary of synapses (see :func:`~single_cell_parser.reader.read_pruned_synapse_locations`).
        cellID (str): The ID of the cell.

    Returns:
        None. Writes out the synapse location file to :param:`fname`.
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


def write_cell_synapse_locations(fname=None, synapses=None, cellID=None):
    '''Write a :ref:`syn_file_format` file.
     
    :ref:`syn_file_format` files contain a cell's synapses with the locations
    coded by section ID and section x of cell with ID "cellID".

    See also:

    - :ref:`syn_file_format` for more information on the `.syn` file format.
    - :func:`single_cell_parser.reader.read_synapse_realization` for the corresponding reader function.
    - :func:`write_pruned_synapse_locations` for a similar function that includes a `pruned` flag.

    Args:
        fname (str): The name of the file to write to.
        synapses (dict): A dictionary of synapses, with keys as synapse types and values as lists of synapses.
        cellID (str): The ID of the cell.

    Returns:
        None. Writes out the synapse location file to :param:`fname`.
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


def write_functional_realization_map(
        fname=None,
        functionalMap=None,
        anatomicalID=None):
    '''Write out a :ref:`con_file_format` file.

    Writes list of all functional connections coded by tuples (cell type, presynaptic cell index, synapse index).
    Only valid for anatomical synapse realization given by anatomicalID

    See also:

    - :ref:`con_file_format` for more information on the `.con` file format.
    - :func:`single_cell_parser.reader.read_functional_realization_map` for the corresponding reader function.

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
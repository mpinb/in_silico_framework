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

'''Read and parse :ref:`hoc_file_format`, :ref:`syn_file_format`, :ref:`con_file_format`, and :ref:`am_file_format` files.

See also:
    :mod:`data_base.IO.LoaderDumper` for dask and pandas related IO.
'''
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import re
from . import scalar_field
from data_base.dbopen import dbopen
from config.isf_logging import get_isf_logger
from typing import Optional
from config.user.morphology import HOC_LABEL_MAP
import logging

__author__  = 'Robert Egger'
__date__    = '2012-03-08'

logger = get_isf_logger().getChild(__name__)


class _Edge(object):
    r'''Convenience class for NEURON segments.

    Private class used in :func:`~single_cell_parser.reader.read_hoc_file` to store information about a single morphological segment spanning from point to point.
    These edges are loosely similar to NEURON segments if full segmentation is used, but should not be used as API to neuron segments.
    If :math:`d-\lambda` segmentation is used, these edges are **not** comparable to NEURON segments.
    
    The purpose of this class is for private use in reading in hoc files: it should not be invoked directly.
        
    See also:
        :func:`~single_cell_parser.cell_parser.CellParser.determine_nseg` for determining the number of segments in a section, and API
        access to NEURON segments.
        
    See also:
        :class:`singlecell_input_mapper.singlecell_input_mapper.reader._Edge` for a similar class 
        that is used in the :mod:`singlecell_input_mapper` module.

    Attributes:
        label (str): label and ID of the segment (e.g. "Dendrite_1_0_0").
        hocLabel (str): Hoc label of the segment (e.g. "Soma", "Axon" ...).
        edgePts (list): List of points in the segment.
        diameterList (list): List of diameters at each point.
        parentID (int): label and ID of the parent segment.
        parentConnect (float): How far along the parent section the connection is (i.e. the `x`-coordinate).
        valid (bool): Flag indicating if the segment is valid.
    '''
    def __init__(self):
        self.label: str | None = None
        self.hocLabel: str | None = None
        self.edgePts: List[List[float]] | None = None
        self.diameterList: List[float] | None = None
        self.parentID: int | None = None
        self.parentConnect: float | None = None
        self.valid: bool | None = None


    def is_valid(self):
        """Check if this edge is valid.
        
        Edges are only valid if they have a :param:`label`, a :param:`hocLabel`, and at least one :param:`edgePts`.
        
        Returns:
            bool: True if the edge is valid, False otherwise.
        """
        if not self.label:
            self.valid = False
            return False
        if not self.hocLabel:
            self.valid = False
            return False
        if not self.edgePts:
            self.valid = False
            return False
        self.valid = True
        return True

    def __eq__(self, other):
        for attr, val in self.__dict__.items():
            if not val == getattr(other, attr): return False 
        for attr in other.__dict__:
            if attr not in self.__dict__: return False
        return True


def read_hoc_file(
    fname: str = '',
    label_map: Optional[Dict[str, str]] = None,
) -> List[_Edge]:
    """Read a .hoc morphology file and return a list of Edge objects.

    Instead of hard-coding section-type names, the function extracts the raw
    label from every ``create <label>`` statement via regex and resolves it
    through *label_map*.  
    
    The map key is compared against the **prefix** of
    the raw label (everything before the first ``_``), case-
    insensitively.  If no key matches, the raw label itself is used as the
    semantic label so that unknown section types are preserved.

    Mapping a prefix to ``None`` causes those sections to be skipped entirely.

    Args:
        fname (str): Path to the :ref:`hoc_file_format`
        label_map (dict[str, str]): Mapping between labels in the :ref:`hoc_file_format` and actual label used in ISF.

    Returns:
        A list of :class:`_Edge` objects representing the cell morphology
        (axon sections excluded by default).

    Raises:
        IOError: If :paramref:`fname` is not a :ref:`hoc_file_format` file, or if the parsed data are internally inconsistent.
    """
    # Pre-compiled patterns
    _RE_CREATE    = re.compile(r'{create\s+(\w+)}')
    _RE_PT3DADD   = re.compile(r'{pt3dadd\(([^)]+)\)}')  # matches {pt3dadd(anything that isn't a closing bracket)}
    _RE_CONNECT   = re.compile(r'{connect\s+\w+\((\d)\)\s*,\s*(\w+)\(([\d.]+)\)}') # matches {connect(anything that isn't a closing bracket)}


    if not fname.lower().endswith('.hoc'):
        raise IOError('Input file is not a .hoc file!')

    # Build the effective mapping (caller overrides defaults)
    effective_map = HOC_LABEL_MAP
    if label_map is not None: effective_map.update(label_map)

    with dbopen(fname, 'r') as fh:
        logger.info("Reading hoc file: %s", fname)
        text = fh.read()

    # Remove /* ... */ comments (including multi-line ones)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    create_idxs = [m.start() for m in _RE_CREATE.finditer(text)]
    if not create_idxs: return []

    block_texts = [
        text[start:end]
        for start, end in zip(
            create_idxs,
            create_idxs[1:] + [len(text)]
        )
    ]

    sections: list[Dict[str, Any]] = [] 
    insert_order: Dict[str, int] = {}  # hoc_label -> sequential index

    for block in block_texts:
        m_create = _RE_CREATE.search(block)
        if not m_create: continue
        hoc_label: str = m_create.group(1)          # e.g. "dend_1_0"

        # Derive the base label: everything before the first '_' or digit
        label = re.match(r'([A-Za-z\d]+)', hoc_label)  # match letters and numbers, NOT underscores
        label = label.group(1).lower() if label else hoc_label.lower()

        if label in effective_map:
            semantic_label = effective_map[label]
            if semantic_label is None: continue
        else: semantic_label = hoc_label 

        if 'Spine' in block: continue

        pt_matches = _RE_PT3DADD.findall(block)    # list of "x,y,z,d" strings
        if not pt_matches: continue  # ignore non-matches

        coords = [list(map(float, s.split(','))) for s in pt_matches]
        edge_pts      = [[c[0], c[1], c[2]] for c in coords]
        diameter_list = [c[3]               for c in coords]

        parent_hoc_label: Optional[str] = None
        parent_connect:   Optional[float] = None
        m_connect = _RE_CONNECT.search(block)
        if m_connect and semantic_label != 'Soma':
            if int(m_connect.group(1)) != 0: raise ValueError("HOC file contains sections whose starting point connects at a nonzero relative coordinate.")
            parent_hoc_label = m_connect.group(2)
            parent_connect   = float(m_connect.group(3))

        insert_idx = len(sections)
        insert_order[hoc_label] = insert_idx

        sections.append({
            'hoc_label':        hoc_label,
            'semantic_label':   semantic_label,
            'edge_pts':         edge_pts,
            'diameter_list':    diameter_list,
            'parent_hoc_label': parent_hoc_label,
            'parent_connect':   parent_connect,
        })


    edge_list = []
    for sec in sections:
        edge     = _Edge()
        edge.label      = sec['semantic_label']
        edge.hocLabel   = sec['hoc_label']
        edge.edgePts    = sec['edge_pts']
        edge.diameterList = sec['diameter_list']

        if sec['semantic_label'] != 'Soma' and sec['parent_hoc_label']:
            if sec['parent_hoc_label'] not in insert_order:
                raise IOError(f"Logical error: parent '{sec['parent_hoc_label']}' of section '{sec['hoc_label']}' was not found.")
            edge.parentID      = insert_order[sec['parent_hoc_label']]
            edge.parentConnect = sec['parent_connect']
        else:
            edge.parentID = None

        if edge.is_valid(): edge_list.append(edge)
        else: raise IOError(f"Logical error reading hoc file: invalid segment '{sec['hoc_label']}'")

    return edge_list



def read_scalar_field(fname='', dtype=np.float64):
    """Read ASCII AMIRA scalar field mesh files with high speed.
    
    This function reads in AMIRA scalar fields. Particular attention is given to speeding up reading of 
    the actual data.
    
    Args:
        fname (str): Filename of the Amira Mesh file to be read.
        dtype (numpy.dtype): Data type of the scalar field, default is `np.float64`.

    Raises:
        IOError: If the input file does not have a `.am` or `.AM` suffix.
        
    Returns:
        :class:`~single_cell_parser.scalar_field.ScalarField`: A scalar field object containing the mesh data, origin, extent, spacing, and bounds.
    """
    if not fname.endswith(('.am', '.AM')):
        raise IOError('Input file is not an Amira Mesh file!')

    with dbopen(fname, 'r') as meshFile:
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], []
        header_lines = []

        # Read until we reach the data section
        for line in meshFile:
            header_lines.append(line)
            if line.strip().startswith('@1'):
                break

        # Parse header info
        for line in header_lines:
            line = line.strip()
            if not line:
                continue
            if 'define' in line and 'Lattice' in line:
                dims = list(map(int, line.split()[-3:]))
                extent = [v for dim in dims for v in (0, dim - 1)]
            elif 'BoundingBox' in line:
                bounds = list(map(float, line.strip(' \t\n,').split()[-6:]))
                origin = [bounds[2 * i] for i in range(3)]
            elif 'Spacing' in line:
                spacing = list(map(float, line.strip(' \t\n,').split()[-3:]))

        # Adjust bounds/origin before reading the data section
        for i in range(3):
            bounds[2 * i + 1] += 0.5 * spacing[i]
            bounds[2 * i] -= 0.5 * spacing[i]
            origin[i] -= 0.5 * spacing[i]

        # Read the remainder of the file as one string and convert to float64
        data_str = meshFile.read()
        data = np.fromstring(data_str, sep=' ', dtype=dtype)

        # Reshape into a 3D array in Fortran order
        mesh = data.reshape(dims, order='F')

        return scalar_field.ScalarField(mesh, origin, extent, spacing, bounds)



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


def read_landmark_file(landmarkFilename):
    '''Read an AMIRA landmark file

    Args:
        landmarkFilename (str): Filename of the landmark file to be read.

    Raises:
        RuntimeError: If the input file does not have a `.landmarkAscii` suffix.    

    Returns:
        list: (x,y,z) points of landmarks.
    '''
    if not landmarkFilename.endswith('.landmarkAscii'):
        errstr = 'Wrong input format: has to be landmarkAscii format'
        raise RuntimeError(errstr)

    landmarks = []
    with dbopen(landmarkFilename, 'r') as landmarkFile:
        readPoints = False
        for line in landmarkFile:
            stripLine = line.strip()
            if not stripLine:
                continue
            if stripLine[:2] == '@1':
                readPoints = True
                continue
            if readPoints:
                splitLine = stripLine.split()
                x = float(splitLine[0])
                y = float(splitLine[1])
                z = float(splitLine[2])
                landmarks.append((x, y, z))

    return landmarks


# Old versions ---------------------------------------------------

def read_scalar_field_legacy(fname=''):
    """Read AMIRA scalar fields.
    
    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.am` or `.AM` suffix.

    Returns:
        :class:`~single_cell_parser.scalar_field.ScalarField`: A scalar field object.

    .. deprecated:: 0.5.0
       This has been deprecated in favor of the faster :func:`read_scalar_field`

    :skip-doc:
    """
    if not fname.endswith('.am') and not fname.endswith('.AM'):
        raise IOError('Input file is not an Amira Mesh file!')

    with dbopen(fname, 'r') as meshFile:
        # logger.info "Reading Amira Mesh file", fname
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], [0., 0., 0.]
        dataSection, hasExtent, hasBounds = False, False, False
        index = 0
        for line in meshFile:
            if line.strip():
                # set up lattice
                if not dataSection:
                    if 'define' in line and 'Lattice' in line:
                        dimStr = line.strip().split()[-3:]
                        for dim in dimStr:
                            dims.append(int(dim))
                        for dim in dims:
                            extent.append(0)
                            extent.append(dim - 1)
                        hasExtent = True
                    if 'BoundingBox' in line:
                        bBoxStr = line.strip(' \t\n,').split()[-6:]
                        for val in bBoxStr:
                            bounds.append(float(val))
                        for i in range(3):
                            origin.append(bounds[2 * i])
                        hasBounds = True
                    if hasExtent and hasBounds and mesh is None:
                        for i in range(3):
                            spacing[i] = (bounds[2 * i + 1] - bounds[2 * i]) / (
                                extent[2 * i + 1] - extent[2 * i])
                            bounds[2 * i + 1] += 0.5 * spacing[i]
                            bounds[2 * i] -= 0.5 * spacing[i]
                            origin[i] -= 0.5 * spacing[i]
                        mesh = np.empty(shape=dims)
                    if '@1' in line and line[:2] == '@1':
                        dataSection = True
                        continue
                # main data loop
                else:
                    data = float(line.strip())
                    k = index // (dims[0] * dims[1])
                    j = index // dims[0] - dims[1] * k
                    i = index - dims[0] * (j + dims[1] * k)
                    mesh[i, j, k] = data
                    index += 1
                    # logger.info 'i,j,k = %s,%s,%s' % (i, j, k)

        return scalar_field.ScalarField(mesh, origin, extent, spacing, bounds)


if __name__ == '__main__':
    #    testHocFname = raw_input('Enter hoc filename: ')
    #    testReader = Reader(testHocFname)
    #    testReader.read_hoc_file()
    #    testAmFname = raw_input('Enter Amira filename: ')
    for i in range(1000):
        testAmFname = 'SynapseCount.14678.am'
        read_scalar_field(testAmFname)
    logger.info('Done!')

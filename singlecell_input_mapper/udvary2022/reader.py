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

'''Read in hoc files, Amira Mesh files, and spreadsheets with connection probabilities.
'''
from __future__ import annotations
from pandas.core.frame import DataFrame
from pandas.core.frame import DataFrame
import numpy as np
import os, re
from config.isf_logging import logger
from . import scalar_field
from data_base.dbopen import dbopen
from typing import List, Dict, Any, Optional
from config.isf_logging import get_isf_logger
from config.user.morphology import HOC_LABEL_MAP
import pandas as pd
import logging

logger = get_isf_logger().getChild(__name__)

__author__ = 'Robert Egger'
__date__ = '2012-03-08'

class _Edge(object):
    r'''Convenience class for NEURON segments.

    Private class used in :func:`~read_hoc_file` to store information about a single morphological segment spanning from point to point.
    These edges are loosely similar to NEURON segments if full segmentation is used, but should not be used as API to neuron segments.
    
    The purpose of this class is for private use in reading in hoc files: it should not be invoked directly.
        
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
    effective_label_map = HOC_LABEL_MAP
    if label_map is not None: effective_label_map.update(label_map)
    # ignore axons here
    effective_label_map['axon'] = None

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

    sections = [] 
    insert_order: Dict[str, int] = {}  # hoc_label -> sequential index

    for block in block_texts:
        m_create = _RE_CREATE.search(block)
        if not m_create: continue
        hoc_label: str = m_create.group(1)          # e.g. "dend_1_0"

        # Derive the base label: everything before the first '_' or digit
        label = re.match(r'([A-Za-z\d]+)', hoc_label)  # match letters and numbers, NOT underscores
        label = label.group(1).lower() if label else hoc_label.lower()

        if label in effective_label_map:
            semantic_label = effective_label_map[label]
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


def read_scalar_field_legacy(fname=''):
    """Read AMIRA scalar fields.
    
    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.am` or `.AM` suffix.

    Returns:
        :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`: A scalar field object.

    .. deprecated:: 0.5.0
       This has been deprecated in favor of the faster :func:`read_scalar_field`

    :skip-doc:
    """
    if not fname.endswith('.am') and not fname.endswith('.AM'):
        raise IOError('Input file is not an Amira Mesh file!')

    with dbopen(fname, 'r') as meshFile:
        #            print "Reading Amira Mesh file", fname
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], []
        dataSection, hasExtent, hasBounds, hasSpacing = False, False, False, False
        index = 0
        for line in meshFile:
            if line.strip():
                #                    set up lattice
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
                    if 'Spacing' in line:
                        spacingStr = line.strip(' \t\n,').split()[-3:]
                        for val in spacingStr:
                            spacing.append(float(val))
                        hasSpacing = True
                    if hasExtent and hasBounds and hasSpacing and mesh is None:
                        for i in range(3):
                            #spacing[i] = (bounds[2*i+1]-bounds[2*i])/(extent[2*i+1]-extent[2*i])
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


                        # print 'i,j,k = %s,%s,%s' % (i, j, k)

        return scalar_field.ScalarField(mesh, origin, extent, spacing, bounds)


def _rename_columns(df: DataFrame) -> DataFrame:
    colmap = {}
    for col in df:
        parts = col.split("_")
        struct = parts[-1]
        struct = HOC_LABEL_MAP.get(struct.lower(), struct)
        parts[-1] = struct
        colmap[col] = "_".join(parts)
    df = df.rename(columns=colmap)
    return df


def read_connections_spreadsheet(
    fname, 
    rename_presyn_map=None
    ):
    """
    Read a connections spreadsheet.

    Connections spreadsheets define the empirically measured connectivity between
    presynaptic cells, and all structures of a postsynaptic cell, in units of 
    connections per unit of area and length.

    Args:
        fname (str): Filename of the connections spreadsheet file.
        rename_presyn_map (dict): 
            Mapping between presynaptic cell type names, and the internal representation to use.
            If ``None`` (default), maps "ALL_EXCITATORY" to "EXC" and "ALL_INHIBITORY" to "INH".
    """
    if rename_presyn_map == None:
        rename_presyn_map = {
            "ALL_EXCITATORY": "EXC",
            "ALL_INHIBITORY": "INH"
        }
    df = pd.read_csv(fname, sep='\t')

    df['PRESYNAPTIC_CELLTYPE'] = df['PRESYNAPTIC_CELLTYPE'].map(
        lambda x: rename_presyn_map.get(x, x)
    )

    df = _rename_columns(df)
    return df


def read_celltype_numbers_spreadsheet(fname):
    """Reads a spreadsheet with cell type numbers for each anatomical area.

    Args:
        fname (str): The name of the file to be read

    Returns:
        dict: A dictionary with the following structure: {anatomical_area: {cell_type: number_of_cells, ...}, ...}
    """
    columns = None
    cellTypeNumbers = {}

    with dbopen(fname, 'r') as spreadsheet:
        header = False
        for line in spreadsheet:
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            if splitLine[0] == 'CELL TYPE':
                header = True
            if header:
                columns = [splitLine[i] for i in range(1, len(splitLine))]
                for col in columns:
                    cellTypeNumbers[col] = {}
                header = False
            else:
                cellType = splitLine[0]
                for i in range(len(columns)):
                    col = columns[i]
                    nrCells = int(splitLine[i + 1])
                    cellTypeNumbers[col][cellType] = nrCells

    return cellTypeNumbers


def read_bouton_densities_per_area_per_ct(dirname, anatomical_areas, cell_types):
    boutonDensities = {}
    for anatomical_area in anatomical_areas:
        boutonDensities[anatomical_area] = {}  # type is Dict[str, Dict[str, List[scim.ScalarField]]]

        for preCellType in cell_types:
            boutonDensities[anatomical_area][preCellType] = []  # type is List[scim.ScalarField]

            boutonDensityFolder = os.path.join(dirname, anatomical_area, preCellType)
            if not os.path.isdir(boutonDensityFolder):
                raise FileNotFoundError("Could not find bouton density folder: {}".format(boutonDensityFolder))

            boutonDensityNames = []
            with os.scandir(boutonDensityFolder) as it:
                for entry in it:
                    if entry.is_file():
                        name = entry.name
                        if name.endswith(".am") or name.endswith(".AM"):
                            boutonDensityNames.append(entry.path)

            logger.debug("    Loading {:d} bouton densities from {:s}".format(len(boutonDensityNames), boutonDensityFolder))

            # small local bindings reduce overhead in the tight loop
            _read_scalar_field = read_scalar_field
            _append = boutonDensities[anatomical_area][preCellType].append

            for densityName in boutonDensityNames:
                boutonDensity = _read_scalar_field(densityName)
                boutonDensity.resize_mesh()
                _append(boutonDensity)
    return boutonDensities